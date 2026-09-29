import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Electricity Distribution Department API"
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = "sqlite:///./electricity_department.db"

    # Chaos / Failure Simulation Configuration
    CHAOS_ENABLED: bool = False
    APPLICATION_FAILURE_RATE: float = 0.10
    VERIFY_FAILURE_RATE: float = 0.10
    STATUS_FAILURE_RATE: float = 0.05
    SCHEMA_DRIFT_RATE: float = 0.20
    SIMULATED_DELAY_RATE: float = 0.05
    SIMULATED_DELAY_MS: int = 3000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
