from celery import Celery

celeryApp = Celery("tasks", broker="redis://localhost:6379/0")