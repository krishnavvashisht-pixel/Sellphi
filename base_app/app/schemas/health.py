from typing import Literal

from pydantic import BaseModel

ConnectionStatus = Literal["connected", "disconnected"]
ServiceStatus = Literal["healthy", "unhealthy"]


class HealthResponse(BaseModel):
    status: ServiceStatus
    database: ConnectionStatus
    redis: ConnectionStatus
    version: str
