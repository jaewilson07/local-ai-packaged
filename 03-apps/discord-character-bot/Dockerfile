FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy application code
COPY bot/ ./bot/
# Note: config.py is in bot/ directory, no separate config/ directory needed

# Create data directory
RUN mkdir -p /app/data

# Run the bot
CMD ["python", "-m", "bot.main"]
