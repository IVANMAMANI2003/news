#!/usr/bin/env python3
"""
Script para probar las funciones de Celery sin ejecutar Celery
"""

import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('celery_test.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def test_scrape_source_internal():
    """Probar la función scrape_source_internal de celery_tasks"""
    try:
        logger.info("=== PROBANDO scrape_source_internal ===")
        
        # Importar la función directamente
        from celery_tasks import scrape_source_internal

        # Probar cada fuente
        sources = ['pachamama', 'los_andes', 'puno_noticias']
        
        for source in sources:
            logger.info(f"Probando {source}...")
            result = scrape_source_internal(source, {})
            logger.info(f"✅ {source}: {result}")
            
    except Exception as e:
        logger.error(f"❌ Error en test_scrape_source_internal: {e}")

def test_scheduled_scraping():
    """Probar la función scheduled_scraping de celery_tasks"""
    try:
        logger.info("=== PROBANDO scheduled_scraping ===")
        
        # Importar la función directamente
        from celery_tasks import scheduled_scraping
        
        logger.info("Ejecutando scheduled_scraping...")
        result = scheduled_scraping()
        logger.info(f"✅ scheduled_scraping completado: {result}")
        
    except Exception as e:
        logger.error(f"❌ Error en test_scheduled_scraping: {e}")

def test_scrape_new_news():
    """Probar la función scrape_new_news de celery_tasks"""
    try:
        logger.info("=== PROBANDO scrape_new_news ===")
        
        # Importar la función directamente
        from celery_tasks import scrape_new_news
        
        logger.info("Ejecutando scrape_new_news...")
        result = scrape_new_news()
        logger.info(f"✅ scrape_new_news completado: {result}")
        
    except Exception as e:
        logger.error(f"❌ Error en test_scrape_new_news: {e}")

def main():
    """Función principal"""
    logger.info("🚀 INICIANDO PRUEBAS DE CELERY TASKS")
    logger.info(f"Fecha y hora: {datetime.now()}")
    
    # Probar funciones individuales
    test_scrape_source_internal()
    
    # Probar funciones completas
    test_scheduled_scraping()
    test_scrape_new_news()
    
    logger.info("=" * 50)
    logger.info("🎯 PRUEBAS DE CELERY TASKS COMPLETADAS")
    logger.info("📁 Logs guardados en: celery_test.log")
    logger.info("=" * 50)

if __name__ == "__main__":
    main()
