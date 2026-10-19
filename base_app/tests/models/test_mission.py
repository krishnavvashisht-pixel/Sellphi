from app.models.mission import Mission, MissionStatus


def test_mission_status_column_is_configured_to_default_to_draft() -> None:
    # SQLAlchemy defaults apply when a row is actually inserted, not on
    # plain Python construction — so this checks the column is configured
    # correctly rather than asserting a pre-insert attribute value.
    assert Mission.__table__.c.status.default.arg == MissionStatus.DRAFT


def test_mission_json_columns_are_configured_to_default_to_empty_dict() -> None:
    # SQLAlchemy can't introspect the builtin `dict`'s signature, so it
    # wraps it as a context-aware default — hence the dummy `None` argument.
    assert Mission.__table__.c.icp_criteria.default.arg(None) == {}
    assert Mission.__table__.c.product_info.default.arg(None) == {}


def test_mission_stores_icp_and_product_info_as_given() -> None:
    mission = Mission(
        name="Find Series A SaaS companies",
        icp_criteria={"industry": ["B2B SaaS"]},
        product_info={"name": "Sellphi"},
    )

    assert mission.icp_criteria == {"industry": ["B2B SaaS"]}
    assert mission.product_info == {"name": "Sellphi"}


def test_sample_mission_fixture_is_well_formed(sample_mission: Mission) -> None:
    # Guards the shared fixture every later pipeline stage's tests will
    # depend on: if this ever breaks, every downstream stage's tests would
    # fail for a confusing reason, so it gets its own direct check.
    assert sample_mission.name
    assert "industry" in sample_mission.icp_criteria
    assert "name" in sample_mission.product_info
    assert sample_mission.status == MissionStatus.ACTIVE
