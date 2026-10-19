from pydantic import BaseModel, Field


class CompanySizeRange(BaseModel):
    min_employees: int | None = None
    max_employees: int | None = None


class MissionICP(BaseModel):
    """The confirmed shape of icp_criteria (product owner's MVP Scope doc):
    industry, geography, company size, personas, signals, exclusions.

    Both the hand-written fixture path (tests/conftest.py) and the AI path
    (parse_objective_to_icp below) produce this exact shape, so downstream
    pipeline stages can't tell which one a given mission came from.
    """

    industry: list[str] = Field(min_length=1)
    geography: list[str] = Field(min_length=1)
    company_size_range: CompanySizeRange
    personas: list[str] = Field(min_length=1)
    signals: list[str] = Field(min_length=1)
    exclusions: list[str] = Field(default_factory=list)
