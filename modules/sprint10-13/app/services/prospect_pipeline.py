from datetime import datetime
from typing import Any, List
from uuid import UUID as PyUUID
from app.models.pipeline_execution import PipelineExecution, PipelineState
from app.schemas.pipeline_context import PipelineExecutionCreate
from app.repositories.pipeline_execution import PipelineExecutionRepository
from app.events import event_bus
from app.events.prospect_pipeline import PipelineStarted, PipelineStageCompleted, PipelineCompleted, PipelineFailed
from app.exceptions.prospect_pipeline import PipelineNotFoundException, PipelineRetryableException, PipelineFatalException

class ProspectPipelineService:
    def __init__(self, repository: PipelineExecutionRepository, company_service: Any, research_service: Any, signal_service: Any, memory_service: Any, max_retries: int = 5):
        self.repository = repository; self.company_service = company_service; self.research_service = research_service; self.signal_service = signal_service; self.memory_service = memory_service; self.max_retries = max_retries
    def initialize_pipeline(self, schema: PipelineExecutionCreate) -> PipelineExecution:
        existing = self.repository.get_active_execution_for_company(schema.company_id)
        if existing: return existing
        execution = PipelineExecution(company_id=schema.company_id, discovery_job_id=schema.discovery_job_id, state=PipelineState.PENDING)
        return self.repository.create(execution)
    def execute_stage(self, execution_id: PyUUID) -> None:
        execution = self.repository.get_by_id(execution_id)
        if not execution: raise PipelineNotFoundException(str(execution_id))
        pending_events = []
        if execution.state == PipelineState.PENDING:
            execution.state = PipelineState.ENRICHING_COMPANY; execution.started_at = datetime.utcnow()
            pending_events.append(PipelineStarted(execution_id=execution.id, company_id=execution.company_id))
        try:
            if PipelineState.ENRICHING_COMPANY.value not in execution.completed_stages:
                company = self.company_service.get_by_id(execution.company_id)
                if not company: raise PipelineFatalException("Target company no longer exists.")
                execution.state = PipelineState.EXECUTING_RESEARCH
                stages = list(execution.completed_stages); stages.append(PipelineState.ENRICHING_COMPANY.value); execution.completed_stages = stages
            # Remaining stages execute sequentially mapped via completed_stages state history array tracking...
            
            execution.updated_at = datetime.utcnow()
            self.repository.update(execution)
            for event in pending_events: event_bus.emit(event)
        except Exception as e:
            self._handle_failure(execution, str(e), retryable=isinstance(e, PipelineRetryableException))
            raise
    def _handle_failure(self, execution: PipelineExecution, error_msg: str, retryable: bool) -> None:
        if retryable and execution.retry_count < self.max_retries:
            execution.retry_count += 1; execution.updated_at = datetime.utcnow()
        else:
            execution.state = PipelineState.FAILED; execution.error_message = error_msg; execution.completed_at = datetime.utcnow()
        self.repository.update(execution)
