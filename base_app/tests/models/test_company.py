from app.models.company import Company


def test_company_metadata_column_defaults_to_empty_dict() -> None:
    assert Company.__table__.c.metadata.default.arg(None) == {}


def test_company_metadata_maps_to_a_metadata_db_column_but_a_different_python_name() -> None:
    # SQLAlchemy reserves `.metadata` on every model for its own use, so
    # the Python attribute is named company_metadata — but the actual
    # database column is still called "metadata", matching the plan's
    # schema exactly.
    assert Company.__table__.c.metadata.name == "metadata"
    company = Company(name="Acme Corp")
    assert hasattr(company, "company_metadata")


def test_company_only_requires_a_name() -> None:
    company = Company(name="Acme Corp")

    assert company.name == "Acme Corp"
    assert company.domain is None
    assert company.industry is None
    assert company.size is None
