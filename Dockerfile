# KoSPA - Korean Speech Pronunciation Analyzer
# Dockerfile for containerized deployment

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
# - ffmpeg: for audio conversion
# - libpq-dev: for PostgreSQL client
# - gcc: for compiling Python packages
# - fonts-nanum: Korean fonts for matplotlib
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libpq-dev \
    gcc \
    fonts-nanum \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -fv

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for analysis plots
RUN mkdir -p static/images/analysis

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
