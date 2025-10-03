"""
Configuración de tareas programadas para Celery Beat
"""

from celery.schedules import crontab

# Configuración de tareas programadas
beat_schedule = {
    # Scraping cada hora
    'scraping-cada-hora': {
        'task': 'news_scraper.tasks.scheduled_scraping',
        'schedule': crontab(minute=0),  # Cada hora en el minuto 0
    },
    
    # Scraping cada 30 minutos (opcional)
    'scraping-cada-30min': {
        'task': 'news_scraper.tasks.scheduled_scraping',
        'schedule': crontab(minute='*/30'),  # Cada 30 minutos
    },
    
    # Limpieza de datos antiguos cada día a las 2 AM
    'limpieza-diaria': {
        'task': 'news_scraper.tasks.cleanup_old_data',
        'schedule': crontab(hour=2, minute=0),  # 2:00 AM
    },
}

# Configuración de timezone
timezone = 'America/Lima'
