from uuid import UUID
from app.models.agent_state import AgentState
from app.models.discovery_job import DiscoveryStage
from app.models.discovery_result import DiscoveryResult, ResultStatus
from app.schemas.discovery_context import DiscoveryContext
from app.events import event_bus
from app.events.discovery_intelligence import CompaniesDiscovered, CompaniesEnriched, CompaniesQualified, CompanyCreationTriggered
from app.exceptions.agent_orchestrator import IllegalStateTransitionException, MissingContextException, RetryableAgentException

class ProspectDiscoveryOrchestrator:
    def __init__(self, job_service, mission_service, icp_service, persona_service, company_service, result_repo, provider_registry, processor):
        self.job_service = job_service; self.mission_service = mission_service; self.icp_service = icp_service; self.persona_service = persona_service
        self.company_service = company_service; self.result_repo = result_repo; self.provider_registry = provider_registry; self.processor = processor
        self.current_state = AgentState.CREATED
    def run(self, job_id: UUID) -> DiscoveryContext:
        job = self.job_service.get_by_id(job_id)
        mission = self.mission_service.get_by_id(job.mission_id)
        icp = self.icp_service.get_by_mission_id(mission.id)
        persona = self.persona_service.get_by_mission_id(mission.id)
        
        if not icp or not persona: raise MissingContextException("ICP or Buyer Persona Configuration")
        context = DiscoveryContext(job_id=job_id, workspace_id=job.workspace_id, mission_id=job.mission_id, icp=icp, buyer_persona=persona)
        
        provider = self.provider_registry.get_provider(job.provider)
        raw_companies = provider.search_companies(icp)
        context.discovered_companies = raw_companies
        
        duplicates_count = 0; processed_count = 0
        for raw in raw_companies:
            domain = raw.get("raw_domain", "").replace("www.", "").strip("/")
            if self.company_service.exists_by_domain(domain):
                duplicates_count += 1
                continue
            processed_count += 1
            provider_enrichment = provider.enrich_company(raw.get("id"))
            processed_data, status, reasons = self.processor.process(raw, provider_enrichment, icp)
            
            if status == "SAVED": context.matched_companies.append(processed_data)
        
        if hasattr(self.job_service, 'update_job_metrics'):
            self.job_service.update_job_metrics(job_id=job_id, total_discovered=len(context.discovered_companies), total_processed=processed_count, total_saved=len(context.matched_companies), total_duplicates=duplicates_count)
            
        for prospect in context.matched_companies:
            event_bus.emit(CompanyCreationTriggered(job_id=job_id, company_data=prospect))
            
        self.current_state = AgentState.COMPLETED
        return context
