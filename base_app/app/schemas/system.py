from pydantic import BaseModel


class RootResponse(BaseModel):
    application: str
    version: str
    status: str
