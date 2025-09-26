"""
Tareas Celery para ejecutar scraping y programación periódica
"""
import logging

from celery import Celery
from celery.schedules import crontab

from config import CeleryConfig
from news_scraper_manager import NewsScraperManager

logger = logging.getLogger(__name__)

celery_app = Celery(
    'news_scraper',
    broker=CeleryConfig.BROKER_URL,
    backend=CeleryConfig.RESULT_BACKEND,
)

celery_app.conf.timezone = CeleryConfig.TIMEZONE
celery_app.conf.task_routes = {
    'tasks.scrape_all_sources': {'queue': 'scraping'},
    'tasks.scrape_single_source': {'queue': 'scraping'},
}

# Programación periódica (cada hora por defecto)
celery_app.conf.beat_schedule = {
    'scrape-all-sources-hourly': {
        'task': 'tasks.scrape_all_sources',
        'schedule': crontab(minute=0),  # cada hora al minuto 0
    },
}

@celery_app.task(name='tasks.scrape_all_sources')
def scrape_all_sources():
    logger.info("[Celery] Ejecutando scraping de todas las fuentes")
    manager = NewsScraperManager()
    try:
        if not manager.setup_database():
            logger.error("[Celery] Error configurando BD")
            return {'status': 'error', 'message': 'db_setup_failed'}
        results = manager.run_incremental_scraping()
        logger.info(f"[Celery] Resultados: {results}")
        return {'status': 'ok', 'results': results}
    finally:
        manager.close()

@celery_app.task(name='tasks.scrape_single_source')
def scrape_single_source(source_key: str):
    logger.info(f"[Celery] Ejecutando scraping de fuente: {source_key}")
    manager = NewsScraperManager()
    try:
        if not manager.setup_database():
            logger.error("[Celery] Error configurando BD")
            return {'status': 'error', 'message': 'db_setup_failed'}
        count = manager.scrape_single_source(source_key)
        logger.info(f"[Celery] Noticias insertadas: {count}")
        return {'status': 'ok', 'inserted': count}
    finally:
        manager.close()
