from datetime import datetime
from typing import Any, UUID
from app.models.buying_signal import BuyingSignal
from app.models.enums import SignalStatus, ProcessingStatus
from app.schemas.buying_signal import BuyingSignalCreate, BuyingSignalUpdate
from app.repositories.buying_signal import BuyingSignalRepository
from app.exceptions.buying_signal import BuyingSignalNotFoundException, DuplicateBuyingSignalException, InvalidCompanyException, InvalidMissionException
from app.events import event_bus 
from app.events.buying_signal import BuyingSignalCreated, BuyingSignalUpdated, BuyingSignalVerified, BuyingSignalArchived, BuyingSignalExpired, BuyingSignalDeleted, BuyingSignalScored
class BuyingSignalService:
    def __init__(self, repository: BuyingSignalRepository, company_repo: Any, mission_repo: Any):
        self.repository = repository; self.company_repo = company_repo; self.mission_repo = mission_repo
    def _calculate_freshness(self, published_at: datetime) -> int:
        hours = (datetime.utcnow() - published_at).total_seconds() / 3600
        return max(0, min(100, 100 - int(hours * 2))) if hours > 0 else 100
    def _calculate_ai_score(self, confidence: int, impact: int, urgency: int, freshness: int) -> int:
        return int((confidence * 0.30) + (impact * 0.25) + (urgency * 0.25) + (freshness * 0.20))
    def create_signal(self, schema: BuyingSignalCreate, current_user_id: UUID) -> BuyingSignal:
        if not self.company_repo.get_by_id(schema.company_id): raise InvalidCompanyException(str(schema.company_id))
        if schema.mission_id and not self.mission_repo.get_by_id(schema.mission_id): raise InvalidMissionException(str(schema.mission_id))
        if self.repository.get_duplicate(schema.company_id, schema.signal_type, schema.source_url, schema.published_at): raise DuplicateBuyingSignalException()
        freshness = self._calculate_freshness(schema.published_at)
        ai_score = self._calculate_ai_score(schema.confidence_score, schema.impact_score, schema.urgency_score, freshness)
        db_signal = BuyingSignal(**schema.model_dump(), freshness_score=freshness, ai_score=ai_score, processing_status=ProcessingStatus.COMPLETED, status=SignalStatus.ACTIVE, is_verified=False, created_by=current_user_id)
        created_signal = self.repository.create(db_signal)
        event_bus.emit(BuyingSignalCreated(signal_id=created_signal.id, company_id=created_signal.company_id, created_by=current_user_id))
        event_bus.emit(BuyingSignalScored(signal_id=created_signal.id, freshness_score=freshness, ai_score=ai_score))
        return created_signal
    def update_signal(self, signal_id: UUID, schema: BuyingSignalUpdate) -> BuyingSignal:
        signal = self.repository.get_by_id(signal_id)
        if not signal: raise BuyingSignalNotFoundException(str(signal_id))
        if schema.mission_id and not self.mission_repo.get_by_id(schema.mission_id): raise InvalidMissionException(str(schema.mission_id))
        update_data = schema.model_dump(exclude_unset=True)
        for key, value in update_data.items(): setattr(signal, key, value)
        if any(k in update_data for k in ["confidence_score", "impact_score", "urgency_score", "published_at"]):
            signal.freshness_score = self._calculate_freshness(signal.published_at)
            signal.ai_score = self._calculate_ai_score(signal.confidence_score, signal.impact_score, signal.urgency_score, signal.freshness_score)
            event_bus.emit(BuyingSignalScored(signal_id=signal.id, freshness_score=signal.freshness_score, ai_score=signal.ai_score))
        self.repository.update(signal)
        event_bus.emit(BuyingSignalUpdated(signal_id=signal.id, updated_fields=list(update_data.keys())))
        return signal
    def archive_signal(self, signal_id: UUID) -> BuyingSignal:
        signal = self.repository.get_by_id(signal_id)
        if not signal: raise BuyingSignalNotFoundException(str(signal_id))
        signal.status = SignalStatus.ARCHIVED; self.repository.update(signal)
        event_bus.emit(BuyingSignalArchived(signal_id=signal.id)); return signal
    def recalculate_scores(self, signal_id: UUID) -> BuyingSignal:
        signal = self.repository.get_by_id(signal_id)
        if not signal: raise BuyingSignalNotFoundException(str(signal_id))
        signal.freshness_score = self._calculate_freshness(signal.published_at)
        signal.ai_score = self._calculate_ai_score(signal.confidence_score, signal.impact_score, signal.urgency_score, signal.freshness_score)
        self.repository.update(signal)
        event_bus.emit(BuyingSignalScored(signal_id=signal.id, freshness_score=signal.freshness_score, ai_score=signal.ai_score))
        return signal
    def delete_signal(self, signal_id: UUID, user_id: UUID) -> bool:
        if not self.repository.get_by_id(signal_id): raise BuyingSignalNotFoundException(str(signal_id))
        success = self.repository.soft_delete(signal_id)
        if success: event_bus.emit(BuyingSignalDeleted(signal_id=signal_id, deleted_by=user_id))
        return success
