# Celery with Redis - Local Development Setup

This guide explains how to set up and use Celery with Redis for background task processing in your local development environment.

## Prerequisites

- Python 3.11+ with pip
- Redis server (installed locally via Homebrew on Mac - recommended)
- Or Docker and Docker Compose (available for production deployment patterns)

## Quick Start

### 1. Install Dependencies

Dependencies are already included in `requirements.txt`:
- `celery==5.3.4`
- `redis==5.0.1`

Install all dependencies:
```bash
pip install -r requirements.txt
```

### 2. Start Redis

#### Option A: Using Homebrew on Mac (Recommended for Mac Development)
```bash
# Install Redis using Homebrew
brew install redis

# Start Redis as a service
brew services start redis

# Or run Redis directly
redis-server

# Verify Redis is running
redis-cli ping
# Should respond with "PONG"
```

Redis will be available at `localhost:6379`

**Managing Redis on Mac:**
```bash
# Start Redis service
brew services start redis

# Stop Redis service
brew services stop redis

# Restart Redis service
brew services restart redis

# Check Redis service status
brew services list | grep redis
```

Redis will be available at `localhost:6379`

#### Option B: Docker Compose (For Production-like Setup)
If you want to test the production Docker setup locally:

```bash
# Start only Redis (recommended for local development)
docker-compose up -d redis

# Or start the full stack (Redis + Celery workers)
docker-compose up -d

# Start with development profile to include Redis Commander GUI
docker-compose --profile dev up -d
```

Redis will be available at `localhost:6379`
Redis Commander GUI will be available at `http://localhost:8081` (with dev profile)

#### Option C: Using Local Redis Installation (Linux)
```bash
# Install Redis (Ubuntu/Debian)
sudo apt-get install redis-server

# Start Redis
sudo systemctl start redis-server

# Or run directly
redis-server
```

### 3. Configure Environment Variables

Create a `.env` file in your project root (if not already present):
```bash
# Redis Configuration for Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Other existing environment variables...
SECRET_KEY=your-secret-key
OPENAI_API_KEY=your-openai-api-key
# ... etc
```

### 4. Test the Setup

Test that Celery can connect to Redis:
```bash
# Test synchronously (doesn't require worker)
python manage.py test_celery

# Test asynchronously (requires worker running)
python manage.py test_celery --async
```

### 5. Start Celery Worker

In a separate terminal, start the Celery worker:
```bash
# Basic worker
celery -A website worker --loglevel=info

# Worker with specific queue (recommended for production)
celery -A website worker -Q transcription --loglevel=info

# Worker with concurrency control
celery -A website worker --concurrency=2 --loglevel=info
```

**Note**: You may see deprecation warnings about `broker_connection_retry` configuration. These warnings are harmless and will be addressed in future Celery versions. The worker will function normally despite these warnings.

### 6. Optional: Start Celery Beat (for scheduled tasks)

If you plan to use scheduled tasks:
```bash
# In another terminal
celery -A website beat --loglevel=info
```

## Usage Examples

### Asynchronous Audio Transcription

```python
from transcription.services import TranscriptionService
from nucleus.models import SessionAudio

# Get a SessionAudio instance
session_audio = SessionAudio.objects.first()

# Create service
service = TranscriptionService()

# Process asynchronously (recommended for large files)
async_result = service.process_session_audio_async(
    session_audio=session_audio,
    previous_transcript="Previous session content...",
    session_notes="Session notes...",
    use_celery=True  # Default
)

# Get task ID
print(f"Task ID: {async_result.id}")

# Check if task is ready
if async_result.ready():
    result = async_result.get()
    print(f"Result: {result}")
else:
    print("Task is still processing...")
```

### Direct Task Usage

```python
from transcription.tasks import process_session_audio_task

# Submit task directly
result = process_session_audio_task.delay(
    session_audio_id=1,
    previous_transcript="",
    session_notes=""
)

# Monitor task
print(f"Task state: {result.state}")
print(f"Task info: {result.info}")
```

## Monitoring and Debugging

### Check Redis Connection
```bash
# Connect to Redis CLI
redis-cli

# Test connection
127.0.0.1:6379> ping
PONG

# Check if Celery is using Redis
127.0.0.1:6379> keys celery*
```

**Success response**: An empty array `(empty array)` is normal when no Celery tasks are currently queued or running. You may also see keys like `_kombu.binding.*` or task-specific keys if tasks are active.

### Monitor Celery Tasks
```bash
# Check active tasks
celery -A website inspect active

# Check scheduled tasks
celery -A website inspect scheduled

# Check worker stats
celery -A website inspect stats
```

### Flower (Celery Monitoring Tool)
```bash
# Install Flower
pip install flower

# Start Flower
celery -A website flower

# Access at http://localhost:5555
```

## Development Tips

### 1. Task Development Workflow
1. Write your task in `transcription/tasks.py`
2. Test it synchronously first: `your_task.apply(args=())`
3. Test it asynchronously: `your_task.delay()`
4. Monitor execution with Flower or worker logs

### 2. Testing Tasks
```python
# In Django shell or tests
from transcription.tasks import health_check_task

# Test synchronously (good for debugging)
result = health_check_task.apply()
print(result.result)

# Test asynchronously
async_result = health_check_task.delay()
print(async_result.get(timeout=10))
```

### 3. Environment-Specific Behavior

The application automatically detects whether Celery is available:
- If Celery is properly configured and running: tasks run asynchronously
- If Celery is not available: falls back to synchronous processing
- Use `use_celery=False` parameter to force synchronous processing

### 4. Task Retry Behavior

**Retry Policy**: Tasks automatically retry on certain types of failures:
- **Retryable**: Network errors, timeouts, rate limits, temporary API issues
- **Non-retryable**: Validation errors, business logic failures, malformed data
- **Retry Count**: Up to 3 attempts with 60-second delays
- **Billing Safety**: Retries only occur for connection/infrastructure failures, not successful API calls that return data

**Important**: A task that successfully processes audio and gets a response from the Whisper API will not retry, even if downstream processing fails. This prevents duplicate billing.

## Troubleshooting

### Common Issues

**1. "Cannot connect to Redis"**
```bash
# Check if Redis is running (Mac with Homebrew)
brew services list | grep redis

# Start Redis if not running
brew services start redis

# Check system service (Linux)
sudo systemctl status redis-server

# Or check with Docker Compose
docker-compose ps redis

# Check Redis connectivity
redis-cli ping
```

**3. "Test task times out but no logs in worker"**
This is normal behavior when:
- Task is submitted successfully to Redis queue
- No Celery worker is currently running to process it
- The task remains in the queue until a worker starts

To verify everything is working:
1. Run `python manage.py test_celery --async` (should succeed at submitting)
2. Start a worker in another terminal: `celery -A website worker --loglevel=info`  
3. Check worker logs for task execution
4. Or run `python manage.py test_celery` (synchronous) to test without worker

**2. "Worker not receiving tasks"**
```bash
# Check worker is connected to same Redis instance
# Verify CELERY_BROKER_URL in settings matches Redis URL
# Restart worker with correct settings
```

**3. "Tasks hanging/not completing"**
```bash
# Check worker logs for errors
# Verify task function doesn't have infinite loops
# Check task time limits in settings
```

**4. "ImportError: No module named 'celery'"**
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Or install directly
pip install celery redis
```

### Logs and Debugging

```bash
# Verbose worker logging
celery -A website worker --loglevel=debug

# Check Django logs for task-related errors
# Enable logging in settings.py:
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'celery.log',
        },
    },
    'loggers': {
        'transcription.tasks': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## Configuration Reference

### Key Settings in `website/settings.py`

```python
# Redis connection
CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "redis://localhost:6379/0"

# Task serialization
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

# Task routing
CELERY_TASK_ROUTES = {
    "transcription.tasks.*": {"queue": "transcription"},
}

# Worker configuration
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True

# Time limits (important for long-running transcription tasks)
# For transcribing multiple 2-hour audio files (chunked into 10-min segments),
# processing can take 60-90+ minutes depending on file count and API response times
CELERY_TASK_SOFT_TIME_LIMIT = 7200  # 2 hours (120 minutes)
CELERY_TASK_TIME_LIMIT = 7500  # 2 hours 5 minutes (125 minutes)
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Redis URL for Celery message broker |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0` | Redis URL for storing task results |

## Next Steps

- See `CELERY_PRODUCTION.md` for production deployment with Coolify
- Explore task monitoring with Flower
- Consider implementing custom task error handling
- Add periodic tasks using Celery Beat