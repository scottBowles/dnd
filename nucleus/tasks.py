"""
Celery tasks for general application functionality.
"""

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def health_check_task():
    """
    Simple health check task to verify Celery is working.
    """
    logger.info("Celery health check task executed successfully")
    return "Celery is working!"