import asyncio
import re
from fastapi import APIRouter, HTTPException

from app.models.mission import Mission, MissionStatus
from app.schemas.signal import (
    OutreachPitchResponse,
    PitchRequest,
    SignalItemResponse,
    SignalScanRequest,
)
from app.services.pitch_generator import generate_outreach_pitch
from app.services.rss_ingestion import fetch_google_news_rss
from app.services.signal_classifier import classify_signal

router = APIRouter(prefix="/signals", tags=["signals"])

EDITORIAL_PREFIXES = (
    "exclusive:", "report:", "breaking:", "just in:", "news:", "watch:",
    "update:", "photos:", "analysis:", "opinion:", "editorial:"
)

EDITORIAL_STOPWORDS = {
    "to", "in", "on", "at", "for", "of", "and", "with", "a", "an", "the",
    "by", "as", "its", "new", "plant", "manufacturing", "expansion", "india",
    "crore", "invest", "investment", "facility", "opens", "inaugurates",
    "expands", "expand", "first", "plans", "targets", "eyes", "secures",
    "announces", "breaks", "ground", "unit", "units", "doubling", "doubles",
    "scouts", "exploring", "boost", "capacity", "set", "sets", "up",
    "raises", "raised", "raising", "funding", "round", "series", "seed",
    "million", "capital", "firm", "tech", "startups", "startup"
}

NOISE_KEYWORDS = [
    "how india can", "why global", "opinion:", "editorial:", "gulf war",
    "only china has", "trade deficit", "beyond cyber hub", "real estate map",
    "market trends", "macroeconomic", "outlook 2026", "funding guide",
    "pmi rose", "pmi shows", "sector growth hits", "growth climbs", "market report"
]

COMPANY_SUFFIXES = {
    "ltd", "limited", "pvt", "private", "inc", "incorporated", "corp", "corporation",
    "llc", "plc", "gmbh", "sa", "india", "group", "holdings", "motors", "motor",
    "systems", "technologies", "technology", "solutions", "co", "company"
}


def clean_headline(title: str) -> str:
    """Strips publisher source suffixes and journalistic prefixes from headlines."""
    if " - " in title:
        title = title.rsplit(" - ", 1)[0]
    title = title.strip()
    lowered = title.lower()
    for prefix in EDITORIAL_PREFIXES:
        if lowered.startswith(prefix):
            title = title[len(prefix):].strip()
            lowered = title.lower()
    return title


def get_headline_tokens(title: str) -> set[str]:
    """Extracts informative tokens from a headline."""
    headline = clean_headline(title).lower()
    words = re.findall(r"[a-zA-Z0-9]+", headline)
    return {w for w in words if w not in EDITORIAL_STOPWORDS and len(w) > 2}


def deduplicate_raw_items(items, max_candidates: int = 30):
    """Filters editorial noise and removes duplicate story items reporting the same event."""
    selected = []
    seen_token_sets = []
    seen_lead_words = set()

    for item in items:
        if any(term in item.title.lower() for term in NOISE_KEYWORDS):
            continue

        headline = clean_headline(item.title)
        tokens = get_headline_tokens(item.title)
        words = re.findall(r"[a-zA-Z0-9]+", headline.lower())
        lead_word = words[0] if words else ""

        is_dup = False
        if lead_word and lead_word not in EDITORIAL_STOPWORDS and lead_word in seen_lead_words:
            is_dup = True
        else:
            for s_tokens in seen_token_sets:
                overlap = tokens.intersection(s_tokens)
                if len(overlap) >= 3 or (len(s_tokens) > 0 and len(overlap) / min(len(tokens), len(s_tokens)) >= 0.5):
                    is_dup = True
                    break

        if not is_dup:
            selected.append(item)
            seen_token_sets.append(tokens)
            if lead_word and lead_word not in EDITORIAL_STOPWORDS:
                seen_lead_words.add(lead_word)

        if len(selected) >= max_candidates:
            break

    return selected


def normalize_company_name(name: str) -> str:
    """Normalizes company names (removes legal suffixes, punctuation, case) to detect duplicate companies."""
    cleaned = re.sub(r"[^\w\s]", " ", name.lower())
    tokens = [w for w in cleaned.split() if w not in COMPANY_SUFFIXES and len(w) > 1]
    return " ".join(tokens[:2]) if tokens else cleaned.strip()


def resolve_mission_for_product(payload: SignalScanRequest) -> Mission:
    name = payload.product_name or "Sellphi"
    category = (payload.product_category or "").lower()
    desc = (payload.product_description or "").lower()
    combined = f"{name.lower()} {category} {desc}"

    # Check if this product is industrial / manufacturing / ventilation / fans / hardware
    is_industrial = any(
        term in combined
        for term in [
            "fan", "blower", "ventilation", "exhaust", "dust", "manufacturing",
            "industrial", "equipment", "pollution", "air movement", "factory", "machinery"
        ]
    )

    if is_industrial:
        return Mission(
            name=f"{name} Mission",
            icp_criteria={
                "industry": [
                    "Industrial Manufacturing", "Factories", "Processing Plants",
                    "Commercial & Industrial Facilities", "Warehouses", "Chemical, Metal, Packaging & Food Processing"
                ],
                "geography": ["India", "Global", "United States", "Worldwide"],
                "company_size_range": {"min_employees": 10, "max_employees": 50000},
                "personas": [
                    "Plant Manager", "Director of Operations", "Facility Manager",
                    "EHS / Safety Director", "VP of Manufacturing", "Maintenance Manager"
                ],
                "signals": [
                    "New manufacturing facility or plant expansion",
                    "Factory construction, groundbreaking, or capacity addition",
                    "Industrial ventilation, HVAC, or exhaust upgrades",
                    "Pollution control, dust collection, or air quality OSHA/pollution board compliance"
                ],
                "exclusions": [],
            },
            product_info={
                "name": name,
                "description": payload.product_description
                or "Industrial ventilation, exhaust fans, dust collection, and air movement equipment.",
            },
            status=MissionStatus.ACTIVE,
        )

    # Check if this product is agriculture / agritech / farming / agrochemicals
    is_agritech = any(
        term in combined
        for term in [
            "agri", "agriculture", "farming", "crop", "farmer", "fertilizer",
            "pesticide", "seed", "agritech", "tractor", "irrigation", "herbicide"
        ]
    )

    if is_agritech:
        return Mission(
            name=f"{name} Mission",
            icp_criteria={
                "industry": [
                    "Agriculture", "Agritech", "Farming", "Agribusiness",
                    "Crop Protection & Agrochemicals", "Agri-Food & Processing"
                ],
                "geography": ["India", "Global", "United States", "Worldwide"],
                "company_size_range": {"min_employees": 10, "max_employees": 20000},
                "personas": [
                    "Managing Director", "Head of Commercial / Sales", "Chief Technology Officer",
                    "Founder", "VP of Operations", "Product Head"
                ],
                "signals": [
                    "New product launch or commercial distribution expansion",
                    "Secured funding or venture capital investment",
                    "Partnership, facility expansion, or regional rollout"
                ],
                "exclusions": [],
            },
            product_info={
                "name": name,
                "description": payload.product_description
                or "Agricultural technology, inputs, and solutions for farms and agribusinesses.",
            },
            status=MissionStatus.ACTIVE,
        )

    # Dynamic fallback based on user's category or default
    custom_industry = payload.product_category or "B2B SaaS, Software & Tech"
    return Mission(
        name=f"{name} Mission",
        icp_criteria={
            "industry": [custom_industry, "B2B SaaS", "Software", "Tech", "AI"],
            "geography": ["India", "Global", "United States", "Worldwide"],
            "company_size_range": {"min_employees": 10, "max_employees": 1000},
            "personas": ["VP of Sales", "Head of Growth", "Founder", "CEO", "Director of Operations"],
            "signals": ["Recently raised a funding round", "Expanding sales team or operations", "New product launch"],
            "exclusions": [],
        },
        product_info={
            "name": name,
            "description": payload.product_description
            or f"Solutions and products in {custom_industry}.",
        },
        status=MissionStatus.ACTIVE,
    )


@router.post("/scan", response_model=list[SignalItemResponse])
async def scan_signals(payload: SignalScanRequest) -> list[SignalItemResponse]:
    """Scan Google News RSS feeds for buying signals, deduplicate repetitive press releases,
    and classify distinct company opportunities using Gemini."""
    try:
        raw_items = await fetch_google_news_rss(payload.query, region=payload.region)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch news feed: {exc}") from exc

    # Filter noise and deduplicate candidate headlines so Gemini evaluates diverse companies
    candidates = deduplicate_raw_items(raw_items, max_candidates=max(payload.limit * 3, 20))
    if not candidates and raw_items:
        candidates = raw_items[: payload.limit]

    active_mission = resolve_mission_for_product(payload)
    results: list[SignalItemResponse] = []
    seen_companies: set[str] = set()
    has_generic_discarded = False

    for item in candidates:
        try:
            classification = await classify_signal(item, active_mission)
            norm_company = normalize_company_name(classification.company_name)

            # Deduplicate by company name so the user gets distinct corporate accounts
            if norm_company and norm_company not in {"not applicable", "n a", "none", "unknown", "n"}:
                if norm_company in seen_companies:
                    continue  # Skip duplicate company opportunity
                seen_companies.add(norm_company)
            else:
                # For non-company / macroeconomic noise that slipped through, allow at most one
                if has_generic_discarded:
                    continue
                has_generic_discarded = True

            verdict = "KEPT" if classification.score >= 0.5 else "discarded"
            results.append(
                SignalItemResponse(
                    title=item.title,
                    link=item.link,
                    company_name=classification.company_name,
                    company_domain=classification.company_domain,
                    score=classification.score,
                    verdict=verdict,
                    signal_type=classification.signal_type.value
                    if hasattr(classification.signal_type, "value")
                    else str(classification.signal_type),
                    urgency=classification.urgency.value
                    if hasattr(classification.urgency, "value")
                    else str(classification.urgency),
                    icp_match=classification.icp_match,
                    evidence=classification.evidence,
                    sales_implication=classification.sales_implication,
                )
            )

            if len(results) >= payload.limit:
                break

            # Short courtesy pause between requests
            await asyncio.sleep(0.3)
        except Exception:
            # Continue on individual classification failure rather than failing the whole batch
            continue

    return results


@router.post("/pitch", response_model=OutreachPitchResponse)
async def create_pitch(payload: PitchRequest) -> OutreachPitchResponse:
    """Generate a 1-to-1 personalized cold email and follow-up using Gemini."""
    try:
        return await generate_outreach_pitch(
            company_name=payload.company_name,
            evidence=payload.evidence,
            sales_implication=payload.sales_implication,
            product_name=payload.product_name,
            product_description=payload.product_description,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate pitch with Gemini: {exc}") from exc
