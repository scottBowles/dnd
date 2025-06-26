# Coolify Docker Deployment Quick Reference

## 🚀 Quick Deploy Commands

### Service Deployment Order

1. **Redis** (if not already deployed)
2. **Django Web App**
3. **Celery Worker**
4. **Celery Beat** (optional)

### 1. Redis Service
```bash
# If deploying new Redis service in Coolify:
# - Use: redis:7-alpine
# - Enable persistence
# - Note the service URL for other services
```

### 2. Django Web Application
```yaml
# Coolify Service Configuration
Source: Repository
Build Pack: Dockerfile
Port: 8000
Environment Variables:
  SECRET_KEY: "your-secret-key-here"
  DEBUG: "False"
  DATABASE_URL: "postgresql://user:pass@host:5432/db"
  CELERY_BROKER_URL: "redis://your-redis-service:6379/0"
  CELERY_RESULT_BACKEND: "redis://your-redis-service:6379/0"
  # ... other variables from .env.template
```

### 3. Celery Worker
```yaml
# Coolify Service Configuration
Source: Same repository
Build Pack: Dockerfile
Custom Start Command: "celery -A website worker --loglevel=info --concurrency=2 --prefetch-multiplier=1"
Environment Variables: [Same as Django Web App]
Port: [Not needed]
```

### 4. Celery Beat (Optional)
```yaml
# Coolify Service Configuration
Source: Same repository
Build Pack: Dockerfile
Custom Start Command: "celery -A website beat --loglevel=info --schedule=/tmp/celerybeat-schedule"
Environment Variables: [Same as Django Web App]
Port: [Not needed]
```

## 🔧 Environment Variables

Copy from `.env.template` and set appropriate values:

**Required:**
- `SECRET_KEY`
- `DATABASE_URL` 
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`

**Optional but Recommended:**
- `OPENAI_API_KEY`
- `CLOUDFLARE_R2_*` (for file storage)
- `GOOGLE_API_KEY`
- `ALGOLIA_*` (for search)

## 🏥 Health Checks

All services include health checks:
- **Web App**: `GET /healthcheck/` → "OK"
- **Celery Worker**: `celery inspect ping`
- **Redis**: `redis-cli ping`

## 📊 Monitoring (Optional)

For staging/development environments:

### Flower (Celery Monitoring)
```yaml
Source: Same repository
Build Pack: Dockerfile
Custom Start Command: "celery -A website flower --port=5555"
Port: 5555
Environment Variables:
  CELERY_BROKER_URL: "redis://your-redis-service:6379/0"
  FLOWER_BASIC_AUTH: "admin:secure-password"
```

### Redis Commander (Redis GUI)
```yaml
Image: rediscommander/redis-commander:latest
Port: 8081
Environment Variables:
  REDIS_HOSTS: "local:your-redis-service:6379"
  HTTP_USER: "admin"
  HTTP_PASSWORD: "secure-password"
```

## 🔍 Troubleshooting

### Common Issues

1. **Can't connect to Redis**
   - Check service names in environment variables
   - Verify Redis service is running

2. **Static files not loading**
   - Environment variables set correctly?
   - Check build logs for `collectstatic` errors

3. **Celery tasks not processing**
   - Worker service running?
   - Same environment variables as web app?
   - Check worker logs

### Debug Commands
```bash
# Test Redis connection
redis-cli -h your-redis-service ping

# Check Celery worker status
celery -A website inspect active

# Test Django health
curl http://your-app/healthcheck/
```

## 📈 Scaling

- **Web App**: Multiple instances behind load balancer
- **Workers**: Add more worker services
- **Redis**: Use Redis cluster for high availability

For detailed deployment instructions, see `COOLIFY_DEPLOYMENT.md`