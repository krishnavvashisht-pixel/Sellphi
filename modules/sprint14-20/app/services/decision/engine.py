from uuid import UUID
from app.repositories.decision_repository import DecisionRepository
from app.services.decision.next_best_action import NextBestActionEngine
from app.services.decision.policy_engine import PolicyEngine
from app.models.decision import Decision

class AutonomousDecisionEngine:
    def __init__(self, repo: DecisionRepository, nba: NextBestActionEngine, policy: PolicyEngine):
        self.repo = repo
        self.nba = nba
        self.policy = policy

    async def evaluate_opportunity(self, workspace_id: UUID, opportunity_id: UUID, context: dict, predictions: dict) -> Decision:
        action_data = self.nba.generate_action(context, predictions)
        decision = Decision(workspace_id=workspace_id, opportunity_id=opportunity_id, action=action_data["action"], confidence=action_data["confidence"])
        decision = await self.policy.evaluate_decision(decision)
        
        async with self.repo.session.begin():
            decision = await self.repo.create(decision)
            
        if decision.is_autonomous:
            await self.execute_decision(decision.id)
        return decision
