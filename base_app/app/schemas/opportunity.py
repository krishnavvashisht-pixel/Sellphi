from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OpportunityCreate(BaseModel):
    workspace_id: UUID
    company_name: str = Field(min_length=1)
    company_domain: str | None = None
    title: str = Field(min_length=1)
    article_link: str = Field(min_length=1)
    score: float = 0.0
    evidence: str = ""
    sales_implication: str = ""
    target_persona: str | None = None
    subject_line: str | None = None
    email_body: str | None = None
    follow_up_email: str | None = None
    status: str = "new"
    notes: str | None = None


class OpportunityUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None
    target_persona: str | None = None
    subject_line: str | None = None
    email_body: str | None = None
    follow_up_email: str | None = None


class OpportunityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    company_name: str
    company_domain: str | None = None
    title: str
    article_link: str
    score: float
    evidence: str
    sales_implication: str
    target_persona: str | None = None
    subject_line: str | None = None
    email_body: str | None = None
    follow_up_email: str | None = None
    status: str
    notes: str | None = None
    created_at: datetime
