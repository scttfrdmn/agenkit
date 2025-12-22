"""Application settings using pydantic for environment-based configuration."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM Configuration
    anthropic_api_key: str = Field(..., description="Anthropic API key for Claude")

    # Service Configuration
    python_api_host: str = Field(
        default="0.0.0.0",  # noqa: S104 - Example server configuration
        description="Python API host",
    )
    python_api_port: int = Field(default=8000, description="Python API port")
    go_worker_endpoint: str = Field(
        default="grpc://go-worker:50051", description="Go worker gRPC endpoint"
    )

    # Redis Configuration
    redis_host: str = Field(default="redis", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_password: str | None = Field(default=None, description="Redis password")

    # Observability
    otel_exporter_otlp_endpoint: str = Field(
        default="http://jaeger:4318", description="OpenTelemetry exporter endpoint"
    )
    otel_service_name: str = Field(
        default="customer-support-api", description="Service name for tracing"
    )

    # Middleware Configuration
    timeout_default: float = Field(default=5.0, description="Default timeout in seconds")
    timeout_rag: float = Field(default=30.0, description="RAG timeout in seconds")
    timeout_faq: float = Field(default=3.0, description="FAQ timeout in seconds")

    rate_limit_user_rate: float = Field(default=10.0, description="User rate limit (requests/sec)")
    rate_limit_user_capacity: int = Field(default=20, description="User rate limit capacity")
    rate_limit_global_rate: float = Field(
        default=100.0, description="Global rate limit (requests/sec)"
    )
    rate_limit_global_capacity: int = Field(default=200, description="Global rate limit capacity")

    cache_max_size: int = Field(default=1000, description="Max cache size")
    cache_ttl_faq: int = Field(default=300, description="FAQ cache TTL in seconds")
    cache_ttl_rag: int = Field(default=600, description="RAG cache TTL in seconds")

    # Audit Logging
    audit_log_file: str = Field(default="./logs/audit.log", description="Audit log file path")
    audit_log_structured: bool = Field(default=True, description="Use structured audit logging")

    # Feature Flags
    enable_caching: bool = Field(default=True, description="Enable caching middleware")
    enable_audit_logging: bool = Field(default=True, description="Enable audit logging")
    enable_tracing: bool = Field(default=True, description="Enable OpenTelemetry tracing")
    enable_metrics: bool = Field(default=True, description="Enable Prometheus metrics")

    # Application Settings
    log_level: str = Field(default="INFO", description="Logging level")
    debug: bool = Field(default=False, description="Debug mode")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
