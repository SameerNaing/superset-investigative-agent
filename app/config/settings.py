import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str
    superset_base_url: str
    superset_username: str
    superset_password: str


@lru_cache
def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv(
            "DATABASE_URL",
        ),
        superset_base_url=os.getenv("SUPERSET_BASEURL", "").rstrip("/"),
        superset_username=os.getenv("SUPERSET_USER_NAME", ""),
        superset_password=os.getenv("SUPERSET_PASSWORD", ""),
    )
