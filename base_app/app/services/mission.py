"""Mission setup: two paths that produce the same shape of record.

- Fixture path: a Mission is constructed directly with hand-written
  icp_criteria (see tests/conftest.py's sample_mission) — no code here.
- AI path: parse_objective_to_icp() turns a plain-English objective into
  that same icp_criteria shape via Gemini, through the single
  app/llm_client.py wrapper.
"""

from app.llm_client import LLMClient, generate_structured
from app.models.mission import Mission, MissionStatus
from app.repositories.mission import MissionRepository
from app.schemas.mission import MissionICP

MISSION_ICP_PROMPT_TEMPLATE = """\
You are extracting a structured Ideal Customer Profile (ICP) from a sales \
objective written in plain English, for an AI SDR system.

Sales objective:
\"\"\"{raw_objective}\"\"\"

Fill in every field of the requested schema based on this objective:
- industry: the industries/verticals of companies to target
- geography: countries or regions to target
- company_size_range: employee count bounds (use null for a bound that's \
genuinely unstated/unbounded, not a guess)
- personas: job titles/roles of the people who should actually be contacted
- signals: concrete, observable buying signals that indicate this is a \
good time to reach out (e.g. "recently raised a funding round", \
"actively hiring for data engineering roles") — not vague ideas
- exclusions: company types or situations to explicitly rule out

Be specific. Infer reasonable industry/geography/persona values even where \
the objective doesn't spell every one out explicitly, but never invent \
signals or exclusions that aren't actually implied by the objective — an \
empty exclusions list is correct if none are implied. If the objective \
gives no geography at all, default to ["United States"] rather than \
leaving it empty.
"""


async def parse_objective_to_icp(
    raw_objective: str,
    client: LLMClient | None = None,
) -> MissionICP:
    prompt = MISSION_ICP_PROMPT_TEMPLATE.format(raw_objective=raw_objective)
    return await generate_structured(prompt, MissionICP, client=client)


async def create_mission_from_objective(
    repository: MissionRepository,
    raw_objective: str,
    product_info: dict,
    name: str | None = None,
    client: LLMClient | None = None,
) -> Mission:
    """The AI path end to end: objective in, a saved Mission out.

    product_info is NOT AI-derived — the product owner's doc only has the
    AI translating the objective into ICP fields (industry, geography,
    size, personas, signals, exclusions); what you're selling is supplied
    directly, not inferred from a one-line goal.
    """
    icp = await parse_objective_to_icp(raw_objective, client=client)

    mission = Mission(
        name=name or raw_objective[:255],
        raw_objective=raw_objective,
        icp_criteria=icp.model_dump(),
        product_info=product_info,
        status=MissionStatus.ACTIVE,
    )
    created = await repository.create(mission)
    await repository.commit()
    return created
