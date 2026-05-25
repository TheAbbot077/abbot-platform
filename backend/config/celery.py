"""Celery application configuration.

Business tasks will be added later. This file only wires Celery to Django and
Redis so asynchronous processing has a clear home from the start.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("study_management")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
