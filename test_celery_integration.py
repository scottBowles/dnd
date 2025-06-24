"""
Simple integration test for Celery setup.
Run this to verify that Celery is properly configured.
"""

import os
import sys
import django

# Add the project directory to the Python path
project_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_dir)

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website.settings')
django.setup()

def test_celery_config():
    """Test basic Celery configuration."""
    print("Testing Celery configuration...")
    
    try:
        from website.celery import app
        print("✅ Celery app imported successfully")
        
        # Test connection to broker
        inspect = app.control.inspect()
        stats = inspect.stats()
        
        if stats:
            print(f"✅ Found {len(stats)} active workers")
            return True
        else:
            print("⚠️  No active workers found (start a worker to test fully)")
            return True  # Configuration is OK, just no workers
            
    except Exception as e:
        print(f"❌ Celery configuration error: {e}")
        return False

def test_tasks_import():
    """Test that tasks can be imported."""
    print("Testing task imports...")
    
    try:
        from transcription.tasks import health_check_task, process_session_audio_task
        print("✅ Tasks imported successfully")
        return True
    except Exception as e:
        print(f"❌ Task import error: {e}")
        return False

def test_sync_task_execution():
    """Test synchronous task execution."""
    print("Testing synchronous task execution...")
    
    try:
        from transcription.tasks import health_check_task
        
        # Execute task synchronously
        result = health_check_task.apply()
        print(f"✅ Sync task result: {result.result}")
        return True
    except Exception as e:
        print(f"❌ Sync task execution error: {e}")
        return False

def test_redis_connection():
    """Test Redis connection."""
    print("Testing Redis connection...")
    
    try:
        from django.conf import settings
        import redis
        
        r = redis.from_url(settings.CELERY_BROKER_URL)
        r.ping()
        print("✅ Redis connection successful")
        return True
    except Exception as e:
        print(f"❌ Redis connection error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Running Celery integration tests...\n")
    
    tests = [
        test_celery_config,
        test_tasks_import,
        test_redis_connection,
        test_sync_task_execution,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Celery setup is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        
    print("\n💡 To test asynchronous execution:")
    print("   1. Start Redis: docker-compose up -d redis")
    print("   2. Start worker: celery -A website worker --loglevel=info")
    print("   3. Run: python manage.py test_celery --async")