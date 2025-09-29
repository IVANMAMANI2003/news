"""
Configuración de Celery para el sistema de scraping
"""

import os

from celery import Celery

# Configuración de Redis
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Configuración de Celery
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

# Crear instancia de Celery
celery_app = Celery('news_scraper')

# Configuración de Celery
celery_app.conf.update(
    broker_url=CELERY_BROKER_URL,
    result_backend=CELERY_RESULT_BACKEND,
    
    # Configuración de tareas
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='America/Lima',
    enable_utc=True,
    
    # Configuración de workers
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    
    # Configuración de timeouts
    task_soft_time_limit=300,  # 5 minutos
    task_time_limit=600,       # 10 minutos
    
    # Configuración de reintentos
    task_default_retry_delay=60,
    task_max_retries=3,
    
    # Configuración de rutas de tareas
    task_routes={
        'news_scraper.tasks.scrape_source': {'queue': 'scraping'},
        'news_scraper.tasks.process_news_batch': {'queue': 'processing'},
        'news_scraper.tasks.save_to_database': {'queue': 'database'},
    },
    
    # Configuración de colas
    task_default_queue='default',
    task_queues={
        'default': {
            'exchange': 'default',
            'routing_key': 'default',
        },
        'scraping': {
            'exchange': 'scraping',
            'routing_key': 'scraping',
        },
        'processing': {
            'exchange': 'processing', 
            'routing_key': 'processing',
        },
        'database': {
            'exchange': 'database',
            'routing_key': 'database',
        },
    },
    
    # Configuración de monitoreo
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Configuración de resultados
    result_expires=3600,  # 1 hora
    result_persistent=True,
)

# Configuración de logging
celery_app.conf.update(
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',
)

# Configuración de beat (scheduler)
celery_app.conf.beat_schedule = {
    'scrape-news-every-hour': {
        'task': 'news_scraper.tasks.scheduled_scraping',
        'schedule': 3600.0,  # Cada hora
        'options': {'queue': 'scraping'}
    },
    'cleanup-old-data': {
        'task': 'news_scraper.tasks.cleanup_old_data',
        'schedule': 86400.0,  # Cada día
        'options': {'queue': 'processing'}
    },
}

# Configuración de AWS (si está disponible)
if os.getenv('AWS_ACCESS_KEY_ID'):
    celery_app.conf.update(
        broker_transport_options={
            'region': os.getenv('AWS_REGION', 'us-east-1'),
            'visibility_timeout': 3600,
            'polling_interval': 20,
        }
    )

if __name__ == '__main__':
    celery_app.start()
