from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./keystroke_sentinel.db"
    model_storage_path: str = "./models"
    anomaly_threshold: float = 0.65
    enrollment_min_keystrokes: int = 300
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:4173"]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "protected_namespaces": (),
    }

    def model_post_init(self, __context: object) -> None:
        Path(self.model_storage_path).mkdir(parents=True, exist_ok=True)


settings = Settings()

ANOMALY_HISTORY_LIMIT = 200
BURST_MIN_KEYSTROKES = 10
DIGRAPH_TOP_N = 50
FEATURE_VERSION = "v1"
