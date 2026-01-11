FROM python:3.10-slim as builder

WORKDIR /build

# Install uv for fast dependency resolution
RUN pip install --no-cache-dir uv

COPY pyproject.toml ./
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install -e .

# Production stage
FROM python:3.10-slim

WORKDIR /app

# Install runtime and build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        gcc \
        g++ \
        python3-dev \
        build-essential && \
    rm -rf /var/lib/apt/lists/*

# Copy application
COPY server/ /app/server/
COPY pyproject.toml /app/

# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Install uv for runtime package installation
RUN pip install --no-cache-dir uv

# Create uploads directory
RUN mkdir -p /app/uploads && chmod 755 /app/uploads

# Create venv directory (will be mounted as volume, but ensure it exists)
RUN mkdir -p /opt/venv

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
