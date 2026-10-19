import click
import pytest
from app.cli import create_user
from click.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_create_user_rejects_short_password(runner: CliRunner) -> None:
    result = runner.invoke(create_user, ["--email", "a@b.com", "--password", "short"])

    assert result.exit_code != 0
    assert "at least 8 characters" in result.output
