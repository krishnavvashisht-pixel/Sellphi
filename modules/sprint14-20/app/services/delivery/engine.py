import logging
from uuid import UUID
from datetime import datetime, timezone
from app.repositories.delivery_tracking_repo import DeliveryTrackingRepository
from app.models.enums.delivery_v2 import JobStatus

logger = logging.getLogger(__name__)

class DeliveryEngine:
    def __init__(self, repo: DeliveryTrackingRepository):
        self.repo = repo

    async def execute_job(self, job_id: UUID) -> None:
        async with self.repo.session.begin():
            job = await self.repo.get_job(job_id)
            if job.status != JobStatus.PROCESSING: return
            
            try:
                # Simulated dispatch
                job.status = JobStatus.DELIVERED
                job.executed_at = datetime.now(timezone.utc)
            except Exception as e:
                job.status = JobStatus.FAILED
                job.error_log.append(str(e))
            await self.repo.update_job(job)
