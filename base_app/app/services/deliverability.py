"""Real-time deliverability and spam analysis engine for cold outbound outreach.

Benchmarks against market leaders (Lavender, Apollo, Salesloft):
- Word count target: 50-100 words.
- Reading time: ideally < 30 seconds (based on 200 wpm).
- Spam buzzwords detection (e.g., 'guarantee', 'free', 'risk-free').
- Low-friction single CTA / question check.
- Deliverability score from 0 to 100.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

SPAM_KEYWORDS = {
    "guarantee", "guaranteed", "100%", "free", "risk-free", "risk free",
    "urgent", "act now", "exclusive deal", "no cost", "no obligation",
    "instant", "miracle", "winner", "cash", "billionaire", "make money",
    "pure profit", "revolutionary", "revolutionize", "unbelievable"
}


@dataclass
class DeliverabilityReport:
    score: int  # 0 to 100
    rating: str  # Great, Good, Fair, Needs Work
    word_count: int
    char_count: int
    reading_time_seconds: int
    question_count: int
    spam_words_found: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


def analyze_email_deliverability(subject: str, body: str) -> DeliverabilityReport:
    """Analyze subject and body for outbound deliverability, spam triggers, and conversion."""
    full_text = f"{subject or ''} {body or ''}".strip()

    # Word count
    words = [w for w in re.findall(r"\b[\w'-]+\b", full_text) if w]
    word_count = len(words)
    char_count = len(full_text)

    # Reading time assuming average 200 words per minute
    reading_time_seconds = max(1, round((word_count / 200.0) * 60))

    # Question count (question marks)
    question_count = body.count("?")

    # Spam keywords search
    text_lower = full_text.lower()
    spam_found: list[str] = []
    for spam_word in SPAM_KEYWORDS:
        if re.search(rf"\b{re.escape(spam_word)}\b", text_lower):
            spam_found.append(spam_word)

    # Calculate 0-100 Deliverability Score
    score = 100
    suggestions: list[str] = []

    # 1. Word count penalty
    if word_count < 30:
        score -= 15
        suggestions.append("Email is too short (<30 words); add context or specific value trigger.")
    elif 50 <= word_count <= 110:
        pass  # Sweet spot (50-100 words)
    elif 111 <= word_count <= 150:
        score -= 8
        suggestions.append("Word count is slightly high (>110 words). Aim for 50-100 words.")
    else:
        score -= 20
        suggestions.append(f"Word count is high ({word_count} words). Long cold emails get skipped on mobile.")

    # 2. Reading time penalty
    if reading_time_seconds > 45:
        score -= 10
        suggestions.append(f"Reading time is {reading_time_seconds}s. Try to keep reading time under 30s.")

    # 3. Spam keywords penalty
    if spam_found:
        penalty = min(len(spam_found) * 12, 35)
        score -= penalty
        suggestions.append(f"Avoid spam buzzwords: {', '.join(spam_found)}.")

    # 4. CTA / Question count penalty
    if question_count == 0:
        score -= 8
        suggestions.append("No clear call-to-action found. Include 1 low-friction question at the end.")
    elif question_count > 2:
        score -= 12
        suggestions.append(f"Too many questions ({question_count}). Stick to a single clear, low-friction CTA.")

    # Ensure score stays bounded
    final_score = max(10, min(100, score))

    if final_score >= 88:
        rating = "Great Deliverability"
    elif final_score >= 75:
        rating = "Good Deliverability"
    elif final_score >= 60:
        rating = "Fair Deliverability"
    else:
        rating = "Needs Work"

    return DeliverabilityReport(
        score=final_score,
        rating=rating,
        word_count=word_count,
        char_count=char_count,
        reading_time_seconds=reading_time_seconds,
        question_count=question_count,
        spam_words_found=spam_found,
        suggestions=suggestions,
    )
