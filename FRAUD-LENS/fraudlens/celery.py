import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fraudlens.settings")

app = Celery("fraudlens")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "nightly-behavior-profiles": {
        "task": "fraudlens.rebuild_behavior_profiles",
        "schedule": crontab(hour=1, minute=45),
    },
    "nightly-fraud-detection": {
        "task": "fraudlens.run_detection_for_all_organizations",
        "schedule": crontab(hour=2, minute=15),
    },
}
