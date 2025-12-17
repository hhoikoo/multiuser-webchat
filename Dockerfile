# ==============================================================================
# Stage 1: Build stage - use Pants to package the application

FROM python:3.13-slim AS builder

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Pants using the official installer
RUN curl --proto '=https' --tlsv1.2 -sSfL \
    'https://static.pantsbuild.org/setup/get-pants.sh' | bash

# Add Pants to PATH
ENV PATH="/root/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy Pants configuration files first (for better layer caching)
COPY pants.toml BUILD mypy.ini ruff.toml pyproject.toml ./
COPY src/server/BUILD src/server/BUILD
COPY frontend/BUILD frontend/BUILD

# Bootstrap Pants (downloads and caches dependencies)
RUN pants --version

# Copy the entire project
COPY . .

# Run Pants to package the application into a PEX
RUN pants package src/server:app

# Verify the PEX was created
RUN ls -lh dist/src.server



# ==============================================================================
# Stage 2: Runtime stage - minimal image with just the application

FROM python:3.13-slim

# Create non-root user for security with explicit UID/GID for tmpfs permissions
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -d /app -s /bin/bash appuser

# Create prometheus multiprocess directory
RUN mkdir -p /tmp/prometheus_multiproc && \
    chown -R appuser:appuser /tmp/prometheus_multiproc

# Set working directory
WORKDIR /app

# Copy the PEX from builder stage
COPY --from=builder /app/dist/src.server/app.pex /app/app.pex

# Copy static files (needed at runtime)
COPY --from=builder /app/frontend/static /app/static

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose the default port
EXPOSE 8080

# Set default environment variables
ENV PORT=8080 \
    HOST=0.0.0.0 \
    WORKERS=1 \
    REDIS_URL=redis://redis:6379 \
    PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus_multiproc

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/healthz')"

# Run the PEX
ENTRYPOINT ["python", "/app/app.pex"]
