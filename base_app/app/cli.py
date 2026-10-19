"""One-off CLI for operations that don't warrant an HTTP endpoint yet.

For the single-user MVP, there's deliberately no public signup endpoint —
the one user is provisioned by whoever has shell/DB access, via this
command. Revisit if/when there's ever a second real user.
"""

import asyncio
import getpass

import click

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.repositories.user import UserRepository


@click.group()
def cli() -> None:
    pass


@cli.command("create-user")
@click.option("--email", required=True)
@click.option(
    "--password",
    default=None,
    help="Omit to be prompted (safer — avoids the password landing in shell history).",
)
def create_user(email: str, password: str | None) -> None:
    """Create the single MVP user. Fails loudly if the email is already taken."""
    resolved_password = password or getpass.getpass("Password: ")
    if len(resolved_password) < 8:
        raise click.ClickException("Password must be at least 8 characters.")

    asyncio.run(_create_user(email, resolved_password))
    click.echo(f"Created user {email}")


async def _create_user(email: str, password: str) -> None:
    async with AsyncSessionLocal() as session:
        repository = UserRepository(session)
        existing = await repository.get_by_email(email)
        if existing is not None:
            raise click.ClickException(f"A user with email {email} already exists.")

        user = User(email=email, hashed_password=hash_password(password), is_active=True)
        await repository.create(user)
        await repository.commit()


if __name__ == "__main__":
    cli()
