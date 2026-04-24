from celery import Celery
import config

app = Celery("cbio_importer")
app.conf.update(
    broker_url=config.BROKER_URL,
    result_backend=config.RESULT_BACKEND,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Berlin",
    enable_utc=True,
    beat_schedule={
        "scan-for-new-studies": {
            "task": "tasks.watcher.scan",
            "schedule": 300.0,
        }
    },
    imports=[
        "tasks.watcher",
        "tasks.etl",
        "tasks.validator",
        "tasks.db_check",
        "tasks.importer",
        "tasks.docker_ops",
    ],
)
