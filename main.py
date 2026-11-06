import sys
from pathlib import Path

# Ensure base_app is in Python search path
_base_app_dir = Path(__file__).resolve().parent / "base_app"
if str(_base_app_dir) not in sys.path:
    sys.path.insert(0, str(_base_app_dir))

from app.main import app
