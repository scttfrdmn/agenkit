# ============================================================
# Agenkit Python Agent - Production Dockerfile
# ============================================================

FROM python:3.12-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -r agenkit && useradd -r -g agenkit agenkit

WORKDIR /app

# ============================================================
# Builder Stage
# ============================================================

FROM base as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --user --no-warn-script-location -r requirements.txt

# ============================================================
# Runtime Stage
# ============================================================

FROM base as runtime

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Add Python dependencies to PATH
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY app.py .
COPY agents/ ./agents/

# Create directories
RUN mkdir -p /app/logs /app/data && \
    chown -R agenkit:agenkit /app

# Switch to non-root user
USER agenkit

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose ports
EXPOSE 8000 8001

# Run application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
