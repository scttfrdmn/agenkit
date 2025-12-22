"""Configuration for Code Review Bot."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM API Keys (all required for consensus)
    anthropic_api_key: str = Field(..., description="Anthropic API key for Claude")
    openai_api_key: str = Field(..., description="OpenAI API key for GPT-4")
    google_api_key: str = Field(..., description="Google API key for Gemini")

    # Service Configuration
    python_api_port: int = Field(default=8000, description="Python API port")
    go_analyzer_endpoint: str = Field(
        default="grpc://go-analyzer:50051", description="Go analyzer gRPC endpoint"
    )

    # Redis Configuration
    redis_host: str = Field(default="redis", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")

    # GitHub Configuration
    github_token: str = Field(..., description="GitHub personal access token")
    github_webhook_secret: str = Field(default="", description="GitHub webhook secret (optional)")

    # Observability
    otel_exporter_otlp_endpoint: str = Field(
        default="http://jaeger:4318", description="OpenTelemetry OTLP endpoint"
    )

    # Middleware Configuration
    timeout_default: float = Field(default=30.0, description="Default timeout in seconds")
    timeout_review: float = Field(default=120.0, description="Code review timeout in seconds")
    timeout_analysis: float = Field(default=60.0, description="Static analysis timeout in seconds")
    rate_limit_repo_rate: float = Field(
        default=10.0, description="Rate limit per repository (reviews per hour)"
    )

    # Feature Flags
    enable_caching: bool = Field(default=True, description="Enable response caching with Redis")
    enable_audit_logging: bool = Field(default=True, description="Enable audit logging for reviews")

    # Application Settings
    log_level: str = Field(default="INFO", description="Logging level")
    max_files_per_review: int = Field(
        default=50, description="Maximum files to review in single PR"
    )
    consensus_threshold: float = Field(
        default=0.7, description="Minimum consensus score for approval"
    )
