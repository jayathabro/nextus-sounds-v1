# Nextus Sounds - Railway Docker Container
# Build: docker build -t nextus-sounds .
# Run:   docker run -d --env-file .env nextus-sounds

FROM python:3.13-slim-bookworm

# Install system dependencies (FFmpeg is required for music playback)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create sounds and data directories
RUN mkdir -p sounds data

# Health check (optional)
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Run the bot
CMD ["python", "bot.py"]
