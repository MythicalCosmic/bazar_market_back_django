import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bazar_market_django.settings")

app = Celery("bazar_market")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
