from uuid import UUID
from typing import Dict
from app.repositories.learning_repository import LearningRepository
from app.models.enums.learning import ModelCategory

class WeightOptimizer:
    def __init__(self, repo: LearningRepository):
        self.repo = repo
        self.learning_rate = 0.05

    async def optimize_weights(self, workspace_id: UUID, feature_vector: Dict[str, float], actual_outcome: float, category: ModelCategory) -> None:
        for feature_name, feature_val in feature_vector.items():
            if feature_val <= 0: continue
            weight_record = await self.repo.get_or_create_weight(workspace_id, category, feature_name, 0.5)
            error = actual_outcome - weight_record.weight_value
            weight_record.weight_value += self.learning_rate * error * feature_val
