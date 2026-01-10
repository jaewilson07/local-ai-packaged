FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy application files
COPY pyproject.toml ./
COPY bot/ ./bot/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Create data directory
RUN mkdir -p /app/data && chmod 755 /app/data

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Expose MCP server port (default: 8001)
EXPOSE 8001

CMD ["python", "-m", "bot.main"]
