FROM python:3.11-slim

# Set environment variables for production
ENV PYTHONPATH=/app
ENV DJANGO_SETTINGS_MODULE=website.settings
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    ffmpeg \
    curl \
    wget \
    net-tools \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories and set permissions
RUN mkdir -p /app/logs /app/staticfiles \
    && chown -R appuser:appuser /app \
    && chmod +x /app/manage.py

# Collect static files for production
RUN python manage.py collectstatic --noinput || echo "Static files collection skipped (likely missing env vars)"

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check - try multiple approaches with debugging
HEALTHCHECK --interval=30s --timeout=15s --start-period=90s --retries=3 \
    CMD curl -v http://127.0.0.1:8000/healthcheck/ || curl -v http://localhost:8000/healthcheck/ || python -c "import urllib.request; print('Testing connection...'); urllib.request.urlopen('http://127.0.0.1:8000/healthcheck/', timeout=5); print('Success')" || exit 1

# Default command for Django app (can be overridden for celery workers)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "website.wsgi:application"]