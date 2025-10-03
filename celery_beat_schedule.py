"""
Configuración de tareas programadas para Celery Beat
"""

from celery.schedules import crontab

# Configuración de tareas programadas
beat_schedule = {
    # Scraping de nuevas noticias cada hora
    'scraping-nuevas-noticias': {
        'task': 'news_scraper.tasks.scrape_new_news',
        'schedule': crontab(minute=0),  # Cada hora en el minuto 0
    },
    
    # Limpieza de datos antiguos cada día a las 2 AM
    'limpieza-diaria': {
        'task': 'news_scraper.tasks.cleanup_old_data',
        'schedule': crontab(hour=2, minute=0),  # 2:00 AM
    },
}

# Configuración de timezone
timezone = 'America/Lima'
