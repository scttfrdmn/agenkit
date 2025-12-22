"""Main entry point for customer support API."""

import logging
import sys

import uvicorn

from .api import create_app
from .config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def main():
    """Start the FastAPI server."""
    settings = get_settings()

    # Set log level from config
    logging.getLogger().setLevel(settings.log_level)

    logger.info("Starting Customer Support API")
    logger.info(f"Go worker endpoint: {settings.go_worker_endpoint}")
    logger.info(
        f"Features: caching={settings.enable_caching}, audit={settings.enable_audit_logging}, tracing={settings.enable_tracing}"
    )

    # Create app
    app = create_app(settings)

    # Run server
    uvicorn.run(
        app,
        host=settings.python_api_host,
        port=settings.python_api_port,
        log_level=settings.log_level.lower(),
        access_log=True,
    )


if __name__ == "__main__":
    main()
