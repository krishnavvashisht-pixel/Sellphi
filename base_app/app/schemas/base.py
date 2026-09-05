from pydantic import BaseModel, ConfigDict


class SellphiBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseModel):
    detail: str
