# Celery with Redis - Production Setup (Coolify)

This guide explains how to deploy Celery with Redis in a production environment using Coolify.

## Overview

In production, you'll need to run multiple services:
1. **Django Application** - Your main web application
2. **Redis** - Message broker and result backend
3. **Celery Worker(s)** - Background task processors
4. **Celery Beat** (optional) - Scheduled task scheduler

## Coolify Configuration

### 1. Redis Service

First, deploy a Redis service in Coolify:

#### Option A: Using Coolify's Built-in Redis
1. Go to your Coolify dashboard
2. Create a new service → Database → Redis
3. Configure:
   - **Name**: `dnd-redis`
   - **Password**: Generate a secure password
   - **Memory Limit**: 512MB (adjust based on needs)
   - **Persistent Storage**: Enable for data persistence

#### Option B: Custom Redis Deployment
Create a `redis.yml` service definition:

```yaml
# redis.yml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD} --appendonly yes
    volumes:
      - redis_data:/data
    environment:
      - REDIS_PASSWORD=${REDIS_PASSWORD}
    restart: unless-stopped
    ports:
      - "6379:6379"

volumes:
  redis_data:
```

### 2. Environment Variables

Configure these environment variables in your Coolify application:

```bash
# Django Settings
SECRET_KEY=your-production-secret-key
DEBUG=False
COOLIFY_URL=your-coolify-url

# Database (your existing config)
DATABASE_URL=postgresql://user:pass@host:port/dbname

# Redis/Celery Configuration
REDIS_URL=redis://:${REDIS_PASSWORD}@dnd-redis:6379/0
CELERY_BROKER_URL=${REDIS_URL}
CELERY_RESULT_BACKEND=${REDIS_URL}

# OpenAI (your existing config)
OPENAI_API_KEY=your-openai-api-key

# File Storage (your existing config)
CLOUDFLARE_R2_ACCESS_KEY_ID=your-r2-key
CLOUDFLARE_R2_SECRET_ACCESS_KEY=your-r2-secret
# ... other R2 config
```

### 3. Celery Worker Service

Create a separate service for Celery workers:

#### Option A: Coolify Service Configuration
1. **Name**: `dnd-celery-worker`
2. **Source**: Same repository as your Django app
3. **Build Pack**: Dockerfile
4. **Custom Start Command**: 
   ```bash
   celery -A website worker --loglevel=info --concurrency=2
   ```

#### Option B: Docker Compose Deployment
You can use the included `docker-compose.yml` for multi-service deployment:

```yaml
# The repository includes a docker-compose.yml with:
# - redis: Message broker and result backend
# - celery-worker: Background task processor
# - celery-beat: Scheduled task scheduler (optional)

# To deploy individual services in Coolify:
# 1. Use the redis service definition for your Redis deployment
# 2. Deploy celery-worker as a separate service using the Dockerfile
# 3. Deploy celery-beat if you need scheduled tasks
```

The included `Dockerfile` is configured for production deployment with:
- Python 3.11 slim base image
- System dependencies (build tools, PostgreSQL client, FFmpeg)
- Application code and requirements
- Proper working directory and environment setup

### 4. Celery Beat Service (Optional)

If you need scheduled tasks:

#### Option A: Coolify Service Configuration
1. **Name**: `dnd-celery-beat`
2. **Source**: Same repository
3. **Custom Start Command**: 
   ```bash
   celery -A website beat --loglevel=info
   ```

#### Option B: Docker Compose
The included `docker-compose.yml` defines a `celery-beat` service that you can deploy separately or as part of a multi-service setup.

## Scaling and Performance

### Worker Scaling

Adjust worker concurrency based on your server resources:

```bash
# For CPU-intensive tasks (transcription)
celery -A website worker --concurrency=2 --loglevel=info

# For I/O-intensive tasks
celery -A website worker --concurrency=4 --loglevel=info

# Multiple workers for different queues
celery -A website worker -Q transcription --concurrency=2 --loglevel=info
celery -A website worker -Q default --concurrency=4 --loglevel=info
```

### Redis Configuration

For production Redis, consider:

```bash
# In Redis configuration
maxmemory 1gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

### Resource Allocation

Recommended resource allocation:
- **Django App**: 1-2 CPU cores, 1-2GB RAM
- **Celery Worker**: 1-2 CPU cores, 2-4GB RAM (for audio processing)
- **Redis**: 0.5 CPU cores, 512MB-1GB RAM
- **Celery Beat**: 0.2 CPU cores, 256MB RAM

## Monitoring and Logging

### 1. Application Logging

Update `settings.py` for production logging:

```python
# Production logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': '/app/logs/django.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console'],
    },
    'loggers': {
        'transcription.tasks': {
            'level': 'INFO',
            'handlers': ['console', 'file'],
            'propagate': False,
        },
        'celery': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False,
        },
    },
}
```

### 2. Health Checks

Add health check endpoints:

```python
# website/urls.py
urlpatterns = [
    # ... existing patterns
    path('health/celery/', celery_health_check),
    path('health/redis/', redis_health_check),
]

# website/views.py
from django.http import JsonResponse
from django.conf import settings
import redis
from celery import current_app

def celery_health_check(request):
    try:
        # Check if Celery can connect to broker
        celery_inspect = current_app.control.inspect()
        stats = celery_inspect.stats()
        
        if stats:
            return JsonResponse({
                'status': 'healthy',
                'workers': len(stats),
                'details': stats
            })
        else:
            return JsonResponse({
                'status': 'unhealthy',
                'error': 'No active workers'
            }, status=503)
            
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e)
        }, status=503)

def redis_health_check(request):
    try:
        r = redis.from_url(settings.CELERY_BROKER_URL)
        r.ping()
        return JsonResponse({'status': 'healthy'})
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e)
        }, status=503)
```

### 3. Monitoring with Flower

Deploy Flower for Celery monitoring:

```yaml
# flower.yml (separate Coolify service)
version: '3.8'
services:
  flower:
    image: mher/flower:latest
    command: celery flower --broker=${CELERY_BROKER_URL}
    environment:
      - CELERY_BROKER_URL=${CELERY_BROKER_URL}
      - FLOWER_BASIC_AUTH=${FLOWER_USER}:${FLOWER_PASSWORD}
    ports:
      - "5555:5555"
    depends_on:
      - redis
```

Access Flower at `https://your-flower-domain.com`

## Security Considerations

### 1. Redis Security
- Use strong passwords
- Disable dangerous commands in production
- Use Redis AUTH
- Consider Redis over TLS

### 2. Celery Security
- Don't serialize sensitive data in task arguments
- Use secure serialization (JSON, not pickle)
- Implement task rate limiting
- Monitor for suspicious task patterns

### 3. Network Security
- Use internal networking between services
- Limit Redis port exposure
- Implement proper firewall rules

## Backup and Recovery

### Redis Backup
```bash
# Regular Redis backups
redis-cli --rdb backup-$(date +%Y%m%d).rdb

# Restore from backup
redis-cli --rdb restore-file.rdb
```

### Task Recovery
```bash
# View failed tasks
celery -A website inspect active
celery -A website inspect reserved

# Purge all tasks (emergency)
celery -A website purge
```

## Deployment Checklist

- [ ] Redis service deployed and accessible
- [ ] Environment variables configured
- [ ] Django application deployed with Celery settings
- [ ] Celery worker service deployed
- [ ] Celery beat service deployed (if needed)
- [ ] Health checks responding
- [ ] Logging configured and working
- [ ] Monitoring (Flower) deployed
- [ ] Backup strategy implemented
- [ ] Security measures in place

## Troubleshooting

### Common Production Issues

**1. Workers not connecting to Redis**
```bash
# Check network connectivity between services
# Verify CELERY_BROKER_URL matches Redis service URL
# Check Redis authentication
```

**2. High memory usage**
```bash
# Monitor Redis memory usage
# Implement task result expiration
# Consider using different Redis databases for broker/results
```

**3. Task timeouts**
```bash
# Adjust CELERY_TASK_SOFT_TIME_LIMIT and CELERY_TASK_TIME_LIMIT
# Monitor task execution times
# Implement task chunking for large operations
```

**4. Performance issues**
```bash
# Scale worker instances
# Optimize task serialization
# Use task routing for different workloads
# Monitor CPU and memory usage
```

## Best Practices Summary

1. **Separate services**: Run Django, Celery workers, and Redis as separate services
2. **Resource allocation**: Allocate appropriate CPU/memory based on workload
3. **Monitoring**: Implement comprehensive health checks and monitoring
4. **Logging**: Configure detailed logging for debugging
5. **Security**: Use authentication, internal networking, and secure configuration
6. **Backup**: Regular backups of Redis data
7. **Scaling**: Design for horizontal scaling of workers
8. **Error handling**: Implement robust error handling and retry logic

For development setup, see `CELERY_LOCAL_DEVELOPMENT.md`.