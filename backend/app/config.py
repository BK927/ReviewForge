from functools import lru_cache
from pathlib import Path
import os

from pydantic import BaseModel


class AppSettings(BaseModel):
    db_path: Path
    steam_app_id: str
    steam_language: str = "all"
    steam_review_type: str = "all"
    steam_purchase_type: str = "all"
    refresh_batch_size: int = 100


@lru_cache
def get_settings() -> AppSettings:
    default_db = Path(__file__).resolve().parents[1] / "data" / "reviewforge.duckdb"
    return AppSettings(
        db_path=Path(os.getenv("REVIEWFORGE_DB_PATH", default_db)),
        steam_app_id=os.getenv("REVIEWFORGE_STEAM_APP_ID", "1145350"),
        steam_language=os.getenv("REVIEWFORGE_STEAM_LANGUAGE", "all"),
        steam_review_type=os.getenv("REVIEWFORGE_STEAM_REVIEW_TYPE", "all"),
        steam_purchase_type=os.getenv("REVIEWFORGE_STEAM_PURCHASE_TYPE", "all"),
        refresh_batch_size=int(os.getenv("REVIEWFORGE_REFRESH_BATCH_SIZE", "100")),
    )
