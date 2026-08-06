# Python Agenkit Base Image
# Multi-stage build for minimal production image

# Build stage
# Must satisfy `requires-python = ">=3.12"` in pyproject.toml. This was pinned to
# 3.11-slim, so the runtime stage failed installing the project's own wheel:
# `Package 'agenkit' requires a different Python: 3.11.15 not in '>=3.12'` — the
# image had not built since requires-python moved (#856). 3.13 matches CI (#458).
FROM python:3.13-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy Python package files
COPY pyproject.toml README.md ./
COPY agenkit/ ./agenkit/
COPY proto/ ./proto/

# Install uv for fast dependency resolution
RUN pip install --no-cache-dir uv

# Build wheel
RUN uv pip install --system build && \
    python -m build --wheel

# Runtime stage
FROM python:3.13-slim

# Taken from the root VERSION file at build time rather than hardcoded — see the
# matching note in agenkit-go.Dockerfile (#842/#856).
ARG VERSION=dev

LABEL org.opencontainers.image.title="Agenkit Python"
LABEL org.opencontainers.image.description="Foundation layer for AI agents - Python runtime"
LABEL org.opencontainers.image.authors="Scott Friedman <scttfrdmn@users.noreply.github.com>"
LABEL org.opencontainers.image.source="https://github.com/scttfrdmn/agenkit"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.licenses="Apache-2.0"

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy wheel from builder and install
COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && \
    rm /tmp/*.whl

# Create non-root user
RUN useradd -m -u 1000 agenkit && \
    chown -R agenkit:agenkit /app

USER agenkit

# Default command - show help
CMD ["python", "-c", "import agenkit; print('Agenkit', agenkit.__version__, 'installed')"]
