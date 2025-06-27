# Coolify Docker Deployment Guide

This guide explains how to deploy the Django application with Celery workers using Docker on Coolify.

## Overview

The application consists of three main services:

1. **Django Web Application** - Main web server
2. **Celery Worker** - Background task processor
3. **Redis** - Message broker and result backend

## Deployment Options

### Option 1: Docker Compose (Recommended)

Since Coolify doesn't currently support custom start commands for individual services, the easiest approach is to deploy everything together using docker-compose.

### Option 2: Individual Services

Deploy each service separately (requires manual Redis setup).

## Prerequisites

-   Coolify instance set up and accessible
-   Repository connected to Coolify
-   PostgreSQL database configured (external or Coolify-managed)

## Deployment Steps

### Method 1: Docker Compose Deployment (Recommended)

1. **Create new service** in Coolify
2. **Source**: Connect to this repository
3. **Build Pack**: Docker Compose
4. **Ports Exposes**: `8000` (for the web service)
5. **Environment Variables**: Set the following in Coolify:
    ```
    SECRET_KEY=your-secret-key
    DEBUG=False
    DATABASE_URL=your-postgresql-url
    OPENAI_API_KEY=your-openai-key
    CLOUDFLARE_R2_ACCESS_KEY_ID=your-r2-access-key
    CLOUDFLARE_R2_SECRET_ACCESS_KEY=your-r2-secret-key
    CLOUDFLARE_R2_BUCKET_NAME=your-r2-bucket
    CLOUDFLARE_R2_ACCOUNT_ID=your-r2-account-id
    # ... other variables from your environment
    ```

**What this deploys:**

-   **Django web app** on port 8000
-   **Celery worker** for background tasks
-   **Celery beat** for scheduled tasks
-   **Redis** as message broker
-   **Optional monitoring tools** (flower, redis-commander) for development

### Method 2: Individual Services (Alternative)

### Method 2: Individual Services (Alternative)

If you prefer to deploy services separately:

#### 1. Redis Service

1. Create new service in Coolify
2. Use Redis Docker image: `redis:7-alpine`
3. Configure persistent storage for `/data`
4. Note the internal Redis URL for use in other services

#### 2. Django Web Application

1. **Create new service** in Coolify
2. **Source**: Connect to this repository
3. **Build Pack**: Dockerfile
4. **Ports Exposes**: `8000`
5. **Environment Variables**:
    ```
    SECRET_KEY=your-secret-key
    DEBUG=False
    DATABASE_URL=your-postgresql-url
    CELERY_BROKER_URL=redis://your-redis-service:6379/0
    CELERY_RESULT_BACKEND=redis://your-redis-service:6379/0
    OPENAI_API_KEY=your-openai-key
    # ... other variables
    ```

#### 3. Celery Worker Service

**Note**: Since Coolify doesn't support custom start commands yet, you'll need to:

1. Create a separate Dockerfile for the worker, or
2. Use the docker-compose method above, or
3. Wait for Coolify to implement custom start commands

For now, **Method 1 (Docker Compose) is strongly recommended**.

## Environment Variables Reference

### Required Variables

| Variable                | Description                  | Example                               |
| ----------------------- | ---------------------------- | ------------------------------------- |
| `SECRET_KEY`            | Django secret key            | `your-very-long-secret-key`           |
| `DATABASE_URL`          | PostgreSQL connection string | `postgresql://user:pass@host:5432/db` |
| `CELERY_BROKER_URL`     | Redis URL for Celery         | `redis://redis-service:6379/0`        |
| `CELERY_RESULT_BACKEND` | Redis URL for results        | `redis://redis-service:6379/0`        |

### Optional Variables

| Variable          | Description       | Default |
| ----------------- | ----------------- | ------- |
| `DEBUG`           | Django debug mode | `False` |
| `OPENAI_API_KEY`  | OpenAI API key    | -       |
| `CLOUDFLARE_R2_*` | R2 storage config | -       |
| `GOOGLE_API_KEY`  | Google API key    | -       |
| `ALGOLIA_*`       | Search config     | -       |

## Service Communication

### Docker Compose Method

-   All services communicate via Docker Compose internal networking
-   Redis is accessible at `redis://redis:6379/0` from other services
-   Django app exposes port 8000 externally
-   Workers and beat scheduler communicate internally only

### Individual Services Method

-   Services communicate using Coolify's internal networking
-   Use service names as hostnames (e.g., `redis://your-redis-service:6379/0`)
-   Django app exposes port 8000 for web traffic
-   Workers connect to Redis and database but don't expose ports

## Health Checks

The Docker Compose configuration includes health checks for all services:

-   **Django**: `GET /healthcheck/` (returns "OK")
-   **Celery Worker**: `celery -A website inspect ping`
-   **Celery Beat**: `celery -A website inspect ping`
-   **Redis**: `redis-cli ping`

## Scaling

### Docker Compose Method

-   Scale the entire stack by creating multiple instances of the compose service
-   Individual service scaling requires switching to Method 2

### Individual Services Method

-   **Django App**: Scale by adding more instances
-   **Celery Workers**: Scale by adding more worker services
-   **Redis**: Use Redis cluster for high availability

### Resource Allocation

-   **Django App**: 512MB RAM, 0.5 CPU minimum
-   **Celery Worker**: 512MB RAM, 0.5 CPU minimum (adjust based on workload)
-   **Redis**: 256MB RAM, 0.25 CPU minimum

## Monitoring

### Built-in Monitoring

-   Coolify provides basic metrics and logs
-   Health checks monitor service status

### Optional Tools

For development/staging environments, you can deploy additional monitoring:

1. **Flower** (Celery monitoring):

    - Add service with command: `celery -A website flower --port=5555`
    - Expose port 5555
    - Set `FLOWER_BASIC_AUTH=user:password`

2. **Redis Commander** (Redis GUI):
    - Use image: `rediscommander/redis-commander:latest`
    - Set `REDIS_HOSTS=local:your-redis-service:6379`
    - Expose port 8081

## Troubleshooting

### Common Issues

1. **Services can't connect to Redis**

    - Check Redis service is running
    - Verify `CELERY_BROKER_URL` uses correct service name
    - Check internal networking configuration

2. **Workers not processing tasks**

    - Check worker logs for errors
    - Verify all environment variables are set
    - Test Redis connection: `redis-cli -h redis-service ping`

3. **Static files not loading**
    - Ensure `DJANGO_SETTINGS_MODULE=website.settings`
    - Check if `collectstatic` ran during build
    - Verify storage configuration (R2/local)

### Useful Commands

```bash
# Check Celery worker status
celery -A website inspect active

# Monitor Celery tasks
celery -A website events

# Test Redis connection
redis-cli -h your-redis-service ping

# Django management commands
python manage.py migrate
python manage.py createsuperuser
python manage.py test_celery
```

## Security Notes

1. **Environment Variables**: Never commit real secrets to the repository
2. **Network**: Use Coolify's internal networking, don't expose unnecessary ports
3. **User Permissions**: Docker runs as non-root user for security
4. **Redis**: Consider Redis AUTH if Redis is exposed externally

## Migration from Nixpacks

If migrating from a Nixpacks deployment:

1. Deploy new Docker-based services alongside existing deployment
2. Test thoroughly with staging data
3. Update DNS/routing to point to new services
4. Remove old Nixpacks deployment

## Support

-   Check Coolify documentation for platform-specific issues
-   Review Django and Celery logs for application issues
-   Monitor service health checks and resource usage
