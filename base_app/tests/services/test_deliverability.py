from app.services.deliverability import analyze_email_deliverability


def test_perfect_deliverability_score() -> None:
    subject = "Quick question on your new plant expansion"
    body = (
        "Hi Alex,\n\n"
        "Saw your recent groundbreaking announcement in Pune—congrats on scaling the facility. "
        "When other industrial plant heads double capacity, they typically lose 2-3 weeks configuring ventilation ducts. "
        "We helped Tata Power streamline their airflow setup in under 4 days.\n\n"
        "Open to a brief 5-minute chat on Thursday?"
    )

    report = analyze_email_deliverability(subject, body)
    assert report.score >= 90
    assert report.rating == "Great Deliverability"
    assert 50 <= report.word_count <= 100
    assert report.reading_time_seconds <= 25
    assert report.question_count == 1
    assert len(report.spam_words_found) == 0


def test_spam_words_detection_and_penalty() -> None:
    subject = "100% Guaranteed free profit for your business"
    body = (
        "Act now! We offer a risk-free, unbelievable guarantee that will revolutionize your sales team. "
        "Pure profit with zero risk. Why wait?"
    )

    report = analyze_email_deliverability(subject, body)
    assert report.score < 70
    assert any("guarantee" in w or "100%" in w or "free" in w for w in report.spam_words_found)
    assert any("Avoid spam buzzwords" in s for s in report.suggestions)


def test_too_many_questions_penalty() -> None:
    subject = "Questions about your tech stack"
    body = (
        "Hi Sarah,\n\n"
        "Are you using Kubernetes? Have you considered migrating to AWS? "
        "What is your budget this quarter? Who is your main DevOps lead? "
        "Let me know when we can meet?"
    )

    report = analyze_email_deliverability(subject, body)
    assert report.question_count >= 4
    assert any("Too many questions" in s for s in report.suggestions)


def test_short_email_penalty() -> None:
    subject = "Hi"
    body = "Call me back please."

    report = analyze_email_deliverability(subject, body)
    assert report.word_count < 30
    assert any("too short" in s for s in report.suggestions)
