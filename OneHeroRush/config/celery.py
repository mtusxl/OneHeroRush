# config/celery.py
import os
from celery import Celery

# Указываем Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('OneHeroRush')

# Загружаем конфиг из settings.py (все ключи, начинающиеся с CELERY_)
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматически ищет tasks.py во всех приложениях Django
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
