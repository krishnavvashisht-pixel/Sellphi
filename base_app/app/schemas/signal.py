from datetime import datetime

from pydantic import BaseModel, Field

from app.models.buying_signal import SignalType, SignalUrgency


class RawSignalItem(BaseModel):
    """One raw item pulled from a source (a Google News RSS entry, for now)
    before it's been classified at all.
    """

    title: str
    link: str
    summary: str = ""
    source: str = "google_news_rss"
    published_at: datetime | None = None


class SignalClassification(BaseModel):
    """What the classifier decides about one raw item.

    company_name (and company_domain, when the article states one) aren't
    in the plan's own list of classifier outputs (score/signal_type/
    urgency/icp_match) — but buying_signals.company_id is a required
    foreign key, so something has to identify which company the article is
    actually about before a row can be created. Added here rather than
    guessed at insert time.
    """

    company_name: str = Field(min_length=1)
    company_domain: str | None = None
    score: float = Field(ge=0.0, le=1.0)
    signal_type: SignalType
    urgency: SignalUrgency
    icp_match: bool
    evidence: str = Field(min_length=1)
    sales_implication: str = Field(min_length=1)


class SignalScanRequest(BaseModel):
    query: str = Field(default="new manufacturing plant OR factory expansion India", min_length=2)
    limit: int = Field(default=5, ge=1, le=10)
    region: str = Field(default="IN", description="IN for India, US for United States")
    product_name: str | None = None
    product_category: str | None = None
    product_description: str | None = None


class SignalItemResponse(BaseModel):
    title: str
    link: str
    company_name: str
    company_domain: str | None = None
    score: float
    verdict: str
    signal_type: str
    urgency: str
    icp_match: bool
    evidence: str
    sales_implication: str


class PitchRequest(BaseModel):
    company_name: str
    evidence: str
    sales_implication: str
    product_name: str | None = None
    product_description: str | None = None
    tone: str = "direct"
    custom_instructions: str | None = None


class OutreachPitchResponse(BaseModel):
    target_persona: str
    subject_line: str
    email_body: str
    follow_up_email: str
    step2_email: str | None = None
    step3_email: str | None = None
    step4_breakup: str | None = None
    tone: str = "direct"

