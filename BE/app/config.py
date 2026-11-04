from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    database_url: str = "sqlite:///data/job_agent.db"
    max_upload_mb: int = 5
    allowed_origin: str = "http://localhost:8501"

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


def load_search_config(path: Path | None = None) -> dict[str, Any]:
    config_path = path or ROOT_DIR / "config.yaml"
    with config_path.open("r", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)
    if not isinstance(config, dict):
        raise ValueError(f"Search configuration must be a YAML mapping: {config_path}")
    return config
