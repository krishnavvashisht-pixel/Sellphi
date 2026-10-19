from sqlalchemy.ext.asyncio import AsyncSession

from app.models.buying_signal import BuyingSignal


class BuyingSignalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, signal: BuyingSignal) -> BuyingSignal:
        self._session.add(signal)
        await self._session.flush()
        await self._session.refresh(signal)
        return signal

    async def commit(self) -> None:
        await self._session.commit()
