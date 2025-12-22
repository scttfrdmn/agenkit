"""Production middleware stack composition."""

import logging
from pathlib import Path

from agenkit.interfaces import Agent
from agenkit.middleware import (CachingConfig, CachingDecorator,
                                PerUserRateLimiterConfig,
                                PerUserRateLimiterDecorator, TimeoutConfig,
                                TimeoutDecorator)
from agenkit.observability import AuditLogger, FileAuditAdapter

from ..config import Settings

logger = logging.getLogger(__name__)


def create_middleware_stack(agent: Agent, settings: Settings, agent_type: str = "default") -> Agent:
    """
    Wrap agent with production middleware stack.

    Stack (innermost to outermost):
    1. Base agent
    2. Caching (if enabled)
    3. Per-user rate limiting
    4. Timeout (per-method)
    5. Audit logging (integrated)

    Args:
        agent: Base agent to wrap
        settings: Application settings
        agent_type: Agent type for custom configuration (faq, rag, default)

    Returns:
        Agent wrapped with middleware stack
    """
    wrapped_agent = agent

    # 1. Caching (innermost - cache actual results)
    if settings.enable_caching:
        ttl = settings.cache_ttl_faq if agent_type == "faq" else settings.cache_ttl_rag
        caching_config = CachingConfig(max_cache_size=settings.cache_max_size, default_ttl=ttl)

        wrapped_agent = CachingDecorator(wrapped_agent, caching_config)
        logger.info(f"Added caching middleware (TTL={ttl}s)")

    # 2. Timeout (per-method configuration)
    timeout_map = {
        "faq": settings.timeout_faq,
        "rag": settings.timeout_rag,
        "default": settings.timeout_default,
    }

    timeout_config = TimeoutConfig(
        timeout=settings.timeout_default,
        method_timeouts={"process": timeout_map.get(agent_type, settings.timeout_default)},
    )

    wrapped_agent = TimeoutDecorator(wrapped_agent, timeout_config)
    logger.info(f"Added timeout middleware (timeout={timeout_map.get(agent_type)}s)")

    # 3. Per-user rate limiting
    def get_user_id(message):
        return message.metadata.get("user_id", "anonymous")

    rate_limit_config = PerUserRateLimiterConfig(
        user_rate=settings.rate_limit_user_rate,
        user_capacity=settings.rate_limit_user_capacity,
        global_rate=settings.rate_limit_global_rate,
        global_capacity=settings.rate_limit_global_capacity,
        identifier_fn=get_user_id,
    )

    # 4. Audit logger
    audit_logger = None
    if settings.enable_audit_logging:
        log_dir = Path(settings.audit_log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        audit_logger = AuditLogger(
            [FileAuditAdapter(settings.audit_log_file, structured=settings.audit_log_structured)]
        )
        logger.info(f"Initialized audit logging to {settings.audit_log_file}")

    wrapped_agent = PerUserRateLimiterDecorator(
        wrapped_agent, rate_limit_config, audit_logger=audit_logger
    )
    logger.info("Added per-user rate limiting middleware")

    return wrapped_agent
