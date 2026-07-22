from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Values come from environment or a .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Where uploads and generated artifacts live. Mounted as a volume in Docker.
    data_dir: Path = Path("data")

    database_url: str = "sqlite:///data/app.db"

    # "claude" for real assessments, "null" for deterministic offline runs.
    llm_provider: str = "null"
    anthropic_api_key: str | None = None
    llm_model: str = "claude-opus-4-8"

    # Face pairing tolerances, see analysis/stages/pairing.py.
    pairing_distance_tol: float = 1e-3
    pairing_area_rel_tol: float = 1e-3

    cors_origins: list[str] = ["http://localhost:5173"]

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def artifact_dir(self) -> Path:
        return self.data_dir / "artifacts"


@lru_cache
def get_settings() -> Settings:
    return Settings()
