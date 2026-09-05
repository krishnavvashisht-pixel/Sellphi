from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.models.buying_signal import BuyingSignal
from app.models.enums import SignalType, SignalCategory, SignalStatus, ProcessingStatus
from app.repositories.base import BaseRepository 
class BuyingSignalRepository(BaseRepository[BuyingSignal]):
    def __init__(self, db: Session): super().__init__(model=BuyingSignal, db=db)
    def get_by_id(self, signal_id: UUID) -> Optional[BuyingSignal]:
        return self.db.query(BuyingSignal).filter(BuyingSignal.id == signal_id, BuyingSignal.deleted_at.is_(None)).first()
    def get_duplicate(self, company_id: UUID, signal_type: SignalType, source_url: str, published_at: datetime) -> Optional[BuyingSignal]:
        return self.db.query(BuyingSignal).filter(BuyingSignal.company_id == company_id, BuyingSignal.signal_type == signal_type, BuyingSignal.source_url == source_url, BuyingSignal.published_at == published_at, BuyingSignal.deleted_at.is_(None)).first()
    def search_signals(self, company_id=None, mission_id=None, category=None, signal_type=None, status=None, processing_status=None, min_confidence=None, search_term=None, page=1, size=20):
        query = self.db.query(BuyingSignal).filter(BuyingSignal.deleted_at.is_(None))
        if company_id: query = query.filter(BuyingSignal.company_id == company_id)
        if mission_id: query = query.filter(BuyingSignal.mission_id == mission_id)
        if category: query = query.filter(BuyingSignal.category == category)
        if signal_type: query = query.filter(BuyingSignal.signal_type == signal_type)
        if status: query = query.filter(BuyingSignal.status == status)
        if processing_status: query = query.filter(BuyingSignal.processing_status == processing_status)
        if min_confidence is not None: query = query.filter(BuyingSignal.confidence_score >= min_confidence)
        if search_term:
            term = f"%{search_term}%"
            query = query.filter(or_(BuyingSignal.title.ilike(term), BuyingSignal.description.ilike(term), BuyingSignal.summary.ilike(term)))
        total = query.count()
        items = query.order_by(BuyingSignal.published_at.desc()).offset((page - 1) * size).limit(size).all()
        return items, total
    def soft_delete(self, signal_id: UUID) -> bool:
        signal = self.get_by_id(signal_id)
        if signal: signal.deleted_at = datetime.utcnow(); self.db.commit(); return True
        return False
    def get_expired_active_signals(self) -> List[BuyingSignal]:
        return self.db.query(BuyingSignal).filter(BuyingSignal.status == SignalStatus.ACTIVE, BuyingSignal.expires_at.is_not(None), BuyingSignal.expires_at <= datetime.utcnow(), BuyingSignal.deleted_at.is_(None)).all()
