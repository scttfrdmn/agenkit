"""Research Assistant settings."""

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    openai_api_key: str = Field(..., description="OpenAI API key")

    # Services
    python_api_port: int = Field(default=8000)
    go_scraper_endpoint: str = Field(default="grpc://go-scraper:50051")

    # PostgreSQL
    postgres_host: str = Field(default="postgres")
    postgres_port: int = Field(default=5432)
    postgres_db: str = Field(default="research_assistant")
    postgres_user: str = Field(default="research")
    postgres_password: str = Field(...)

    # Observability
    otel_exporter_otlp_endpoint: str = Field(default="http://jaeger:4318")

    # Middleware
    timeout_default: float = Field(default=60.0)
    timeout_scraping: float = Field(default=120.0)
    timeout_research: float = Field(default=180.0)
    rate_limit_user_rate: float = Field(default=5.0)

    # App settings
    log_level: str = Field(default="INFO")
    max_research_steps: int = Field(default=10)


@lru_cache
def get_settings() -> Settings:
    return Settings()
