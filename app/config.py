"""Application configuration management."""
from functools import lru_cache
from typing import Optional

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Environment-driven application settings."""

    use_vertex: bool = Field(default=False, env="USE_VERTEX")
    gcp_project: Optional[str] = Field(default=None, env="GCP_PROJECT")
    gcp_location: str = Field(default="us-central1", env="GCP_LOCATION")
    arcgis_token: Optional[str] = Field(default=None, env="ARCGIS_TOKEN")
    gw_stress_threshold_m: float = Field(default=10.0, env="GW_STRESS_THRESHOLD_M")
    nearest_poi_radius_m: float = Field(default=50000.0, env="NEAREST_POI_RADIUS_M")
    stub_mode: bool = Field(default=False, env="STUB_MODE")

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""

    return Settings()

