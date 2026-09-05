import time
import asyncio
from uuid import UUID as PyUUID
from app.models.pipeline_execution import PipelineState
from app.services.prospect_pipeline import ProspectPipelineService
from app.exceptions.prospect_pipeline import PipelineRetryableException, PipelineTimeoutException
class PipelineWorker:
    def __init__(self, pipeline_service: ProspectPipelineService): self.pipeline_service = pipeline_service
    async def process_execution_async(self, execution_id: PyUUID, timeout_seconds: int = 300) -> None:
        start_time = time.time()
        while True:
            if (time.time() - start_time) > timeout_seconds: raise PipelineTimeoutException(str(execution_id), "WORKER_TIMEOUT")
            execution = self.pipeline_service.repository.get_by_id(execution_id)
            if not execution or execution.state in [PipelineState.COMPLETED, PipelineState.FAILED]: break
            try:
                self.pipeline_service.execute_stage(execution_id)
            except PipelineRetryableException:
                backoff_time = min(2 ** execution.retry_count, 60)
                await asyncio.sleep(backoff_time)
                continue
            except Exception:
                break
