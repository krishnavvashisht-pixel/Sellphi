from app.models.buying_signal import BuyingSignal, SignalType, SignalUrgency


def test_buying_signal_stores_all_fields() -> None:
    from uuid import uuid4

    signal = BuyingSignal(
        company_id=uuid4(),
        mission_id=uuid4(),
        source="google_news_rss",
        signal_type=SignalType.FUNDING,
        score=0.8,
        urgency=SignalUrgency.HIGH,
        evidence="Acme Corp raised a Series A.",
        sales_implication="Worth reaching out now.",
    )

    assert signal.signal_type == SignalType.FUNDING
    assert signal.urgency == SignalUrgency.HIGH
    assert signal.score == 0.8


def test_detected_at_column_is_configured_to_default_to_now() -> None:
    # Same pattern as Mission's status default test: this checks the
    # column is configured correctly, not a pre-insert attribute value.
    assert BuyingSignal.__table__.c.detected_at.default is not None
