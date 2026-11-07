import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

# Ensure base directory is in sys.path
_base_dir = Path(__file__).resolve().parent.parent
if str(_base_dir) not in sys.path:
    sys.path.insert(0, str(_base_dir))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_v1_router
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestLoggingMiddleware
from app.db.redis import close_redis_pool, init_redis_pool
from app.db.session import dispose_db_engine
from app.schemas.system import RootResponse

WEB_STATIC_DIR = Path(__file__).parent / "web" / "static"



@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    try:
        from app.db.base import Base
        import app.models  # noqa: F401
        from app.db.session import engine
        from sqlalchemy import text
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

            def _migrate_sqlite_columns(sync_conn):
                try:
                    res = sync_conn.execute(text("PRAGMA table_info(opportunities)"))
                    cols = {row[1] for row in res.fetchall()}
                    if cols:
                        if "step3_email" not in cols:
                            sync_conn.execute(text("ALTER TABLE opportunities ADD COLUMN step3_email TEXT"))
                        if "step4_breakup" not in cols:
                            sync_conn.execute(text("ALTER TABLE opportunities ADD COLUMN step4_breakup TEXT"))
                        if "tone" not in cols:
                            sync_conn.execute(text("ALTER TABLE opportunities ADD COLUMN tone VARCHAR(50) DEFAULT 'direct'"))

                    res_u = sync_conn.execute(text("PRAGMA table_info(users)"))
                    cols_u = {row[1] for row in res_u.fetchall()}
                    if cols_u:
                        if "role" not in cols_u:
                            sync_conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(50) DEFAULT 'sdr'"))
                        if "mfa_enabled" not in cols_u:
                            sync_conn.execute(text("ALTER TABLE users ADD COLUMN mfa_enabled BOOLEAN DEFAULT 0"))
                        if "mfa_secret" not in cols_u:
                            sync_conn.execute(text("ALTER TABLE users ADD COLUMN mfa_secret VARCHAR(255)"))
                        if "mfa_recovery_code" not in cols_u:
                            sync_conn.execute(text("ALTER TABLE users ADD COLUMN mfa_recovery_code VARCHAR(100)"))
                except Exception:
                    pass

            await conn.run_sync(_migrate_sqlite_columns)

            def _seed_initial_admin(sync_conn):
                try:
                    import uuid
                    from app.core.security import hash_password
                    pwd_hash = hash_password("admin12345")
                    res = sync_conn.execute(
                        text("SELECT id FROM users WHERE email = :email"),
                        {"email": "krishnav.vashisht@gmail.com"}
                    )
                    row = res.fetchone()
                    if row:
                        sync_conn.execute(
                            text("UPDATE users SET hashed_password = :pwd, is_admin = 1, is_active = 1, role = 'super_admin' WHERE email = :email"),
                            {"email": "krishnav.vashisht@gmail.com", "pwd": pwd_hash}
                        )
                    else:
                        uid = str(uuid.uuid4())
                        sync_conn.execute(
                            text("INSERT INTO users (id, email, hashed_password, is_admin, is_active, role) VALUES (:id, :email, :pwd, 1, 1, 'super_admin')"),
                            {"id": uid, "email": "krishnav.vashisht@gmail.com", "pwd": pwd_hash}
                        )
                except Exception:
                    pass

            await conn.run_sync(_seed_initial_admin)
    except Exception as exc:
        print(f"[Warning] DB table initialization: {exc}")

    try:
        await init_redis_pool(settings.redis_url)
    except Exception:
        pass
    yield
    await close_redis_pool()
    await dispose_db_engine()


def create_application(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)

    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        debug=resolved_settings.debug,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)
    register_exception_handlers(app)

    app.include_router(api_v1_router, prefix=resolved_settings.api_v1_prefix)

    # The two basic webpages: public login/signup, and admin-only user
    # management. Plain static HTML/JS — no build step, no framework —
    # calling the same JSON API above via fetch().
    app.mount("/static", StaticFiles(directory=WEB_STATIC_DIR), name="static")

    @app.get("/login", include_in_schema=False)
    async def login_page() -> FileResponse:
        return FileResponse(WEB_STATIC_DIR / "login.html")

    @app.get("/admin", include_in_schema=False)
    async def admin_page() -> FileResponse:
        # Access control happens in the page's own JS (it calls /auth/me and
        # /admin/users) and, for real security, server-side on those API
        # routes themselves via the require_admin dependency — a non-admin
        # loading this HTML file just sees an "access denied" message,
        # never any user data.
        return FileResponse(WEB_STATIC_DIR / "admin.html")

    @app.get("/dashboard", include_in_schema=False)
    async def dashboard_page() -> FileResponse:
        return FileResponse(WEB_STATIC_DIR / "dashboard.html")


    @app.get("/", tags=["system"])
    async def root(request: Request) -> Any:
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            return RedirectResponse(url="/dashboard", status_code=307)
        return RootResponse(
            application=resolved_settings.app_name,
            version=resolved_settings.app_version,
            status="running",
        )

    return app


app = create_application()
