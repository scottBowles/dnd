API for https://airel.onrender.com/

## Celery with Redis Background Tasks

This application now supports background task processing using Celery with Redis for improved performance, especially for audio transcription operations.

### Quick Start

1. **Install dependencies**: `pip install -r requirements.txt`
2. **Start Redis**: `brew install redis && brew services start redis` (Mac) or `docker-compose up -d redis` (Docker)
3. **Test setup**: `python manage.py test_celery`
4. **Start worker**: `celery -A website worker --loglevel=info`

### Documentation

- **Local Development**: See [CELERY_LOCAL_DEVELOPMENT.md](CELERY_LOCAL_DEVELOPMENT.md)
- **Production Deployment**: See [CELERY_PRODUCTION.md](CELERY_PRODUCTION.md)
- **Docker Support**: Included `docker-compose.yml` and `Dockerfile` for production deployment (Coolify compatible)

### Background Tasks Available

- Audio transcription processing
- Session log generation  
- Cleanup of temporary files
- Health checks
