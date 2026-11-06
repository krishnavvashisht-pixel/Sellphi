import os
import sys
from pathlib import Path

# Auto-configure cloud defaults for Vercel serverless environment
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:////tmp/sellphi.db"
if "JWT_ACCESS_SECRET_KEY" not in os.environ:
    os.environ["JWT_ACCESS_SECRET_KEY"] = "sellphi-vercel-cloud-jwt-access-secret-32-bytes"
if "JWT_REFRESH_SECRET_KEY" not in os.environ:
    os.environ["JWT_REFRESH_SECRET_KEY"] = "sellphi-vercel-cloud-jwt-refresh-secret-32-bytes"

_base_app_dir = Path(__file__).resolve().parent / "base_app"
if str(_base_app_dir) not in sys.path:
    sys.path.insert(0, str(_base_app_dir))

from app.main import app
