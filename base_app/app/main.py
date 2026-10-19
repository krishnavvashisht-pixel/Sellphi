from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
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


    @app.get("/", response_model=RootResponse, tags=["system"])
    async def root() -> RootResponse:
        return RootResponse(
            application=resolved_settings.app_name,
            version=resolved_settings.app_version,
            status="running",
        )

    return app


app = create_application()
