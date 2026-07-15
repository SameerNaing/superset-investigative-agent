import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

SUPERSET_USERNAME = os.getenv("SUPERSET_USER_NAME")
SUPERSET_PASSWORD = os.getenv("SUPERSET_PASSWORD")
SUPERSET_BASEURL = os.getenv("SUPERSET_BASEURL")
CHARTS_DIR = Path(os.getenv("CHARTS_DIR", str(_PROJECT_ROOT / "charts")))

