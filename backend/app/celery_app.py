from celery import Celery

from app.config import get_settings

settings = get_settings()
celery = Celery("signalgraph", broker=settings.redis_url, backend=settings.redis_url, include=["app.tasks"])
celery.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=False,
    beat_schedule={
        "collector-health-every-five-minutes": {
            "task": "signalgraph.collector_health",
            "schedule": 300.0,
        }
    },
)
