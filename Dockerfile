FROM python:3.11-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install --no-cache-dir \
    flask \
    curl-cffi \
    yt-dlp \
    requests

# Create directories
RUN mkdir -p /app /config /downloads

WORKDIR /app

# Copy application
COPY searcher.py /app/

# Expose port
EXPOSE 5000

# Run application
CMD ["python", "searcher.py"]
