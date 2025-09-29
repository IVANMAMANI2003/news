"""
Tareas de Celery corregidas para el sistema de scraping asíncrono
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

from celery import current_task

from celery_config import celery_app
from database import DatabaseManager
# Importar el scraper unificado
from unified_scraper import UnifiedNewsScraper

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name='news_scraper.tasks.scrape_source')
def scrape_source(self, source_name: str, source_config: Dict) -> Dict:
    """
    Tarea para hacer scraping de una fuente específica
    """
    try:
        logger.info(f"🚀 Iniciando scraping de {source_name}")
        
        # Actualizar estado de la tarea
        self.update_state(
            state='PROGRESS',
            meta={'current': 10, 'total': 100, 'status': f'Iniciando scraping de {source_name}'}
        )
        
        # Crear instancia del scraper unificado
        scraper = UnifiedNewsScraper()
        
        # Actualizar progreso
        self.update_state(
            state='PROGRESS',
            meta={'current': 30, 'total': 100, 'status': f'Configurando scraper para {source_name}'}
        )
        
        # Ejecutar scraping de la fuente específica
        logger.info(f"📰 Ejecutando scraping de {source_name}")
        scraper.scrape_single_source(source_name)
        
        # Actualizar progreso
        self.update_state(
            state='PROGRESS',
            meta={'current': 70, 'total': 100, 'status': f'Procesando noticias de {source_name}'}
        )
        
        # Obtener noticias extraídas
        noticias = scraper.get_news_by_source(source_name)
        
        # Actualizar progreso final
        self.update_state(
            state='PROGRESS',
            meta={'current': 100, 'total': 100, 'status': f'Completado: {len(noticias)} noticias de {source_name}'}
        )
        
        logger.info(f"✅ Scraping de {source_name} completado: {len(noticias)} noticias")
        
        return {
            'source': source_name,
            'noticias_count': len(noticias),
            'status': 'completed',
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error en scraping de {source_name}: {e}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'source': source_name}
        )
        raise

@celery_app.task(name='news_scraper.tasks.scheduled_scraping')
def scheduled_scraping():
    """
    Tarea programada para hacer scraping de todas las fuentes
    """
    try:
        logger.info("🚀 Iniciando scraping programado de todas las fuentes")
        
        # Crear instancia del scraper unificado
        scraper = UnifiedNewsScraper()
        
        # Ejecutar scraping completo
        logger.info("📰 Ejecutando scraping completo...")
        scraper.run_full_scrape()
        
        # Obtener estadísticas
        stats = scraper.get_scraping_stats()
        
        logger.info(f"✅ Scraping programado completado: {stats}")
        
        return {
            'status': 'completed',
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error en scraping programado: {e}")
        raise

@celery_app.task(name='news_scraper.tasks.process_news_batch')
def process_news_batch(noticias_data: List[Dict], source_name: str) -> Dict:
    """
    Procesar un lote de noticias
    """
    try:
        logger.info(f"📦 Procesando lote de {len(noticias_data)} noticias de {source_name}")
        
        # Guardar en base de datos
        with DatabaseManager() as db:
            if db.connection:
                inserted_count = 0
                for noticia in noticias_data:
                    try:
                        db.insert_news(noticia)
                        inserted_count += 1
                    except Exception as e:
                        logger.warning(f"Error insertando noticia: {e}")
                
                logger.info(f"✅ {inserted_count} noticias guardadas en BD")
        
        return {
            'processed_count': len(noticias_data),
            'inserted_count': inserted_count,
            'source': source_name,
            'status': 'completed'
        }
        
    except Exception as e:
        logger.error(f"❌ Error procesando lote de {source_name}: {e}")
        raise

@celery_app.task(name='news_scraper.tasks.save_to_database')
def save_to_database(noticias_data: List[Dict]) -> Dict:
    """
    Guardar noticias en la base de datos
    """
    try:
        logger.info(f"💾 Guardando {len(noticias_data)} noticias en la base de datos")
        
        with DatabaseManager() as db:
            if not db.connection:
                raise Exception("No se pudo conectar a la base de datos")
            
            inserted_count = 0
            for noticia in noticias_data:
                try:
                    db.insert_news(noticia)
                    inserted_count += 1
                except Exception as e:
                    logger.warning(f"Error insertando noticia: {e}")
            
            logger.info(f"✅ {inserted_count} noticias guardadas en BD")
            
            return {
                'inserted_count': inserted_count,
                'total_count': len(noticias_data),
                'status': 'completed'
            }
            
    except Exception as e:
        logger.error(f"❌ Error guardando en base de datos: {e}")
        raise

@celery_app.task(name='news_scraper.tasks.cleanup_old_data')
def cleanup_old_data():
    """
    Limpiar datos antiguos
    """
    try:
        logger.info("🧹 Iniciando limpieza de datos antiguos")
        
        # Limpiar archivos antiguos
        cleanup_old_files()
        
        # Limpiar logs antiguos
        cleanup_old_logs()
        
        logger.info("✅ Limpieza completada")
        
        return {
            'status': 'completed',
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error en limpieza: {e}")
        raise

def cleanup_old_files():
    """Limpiar archivos antiguos"""
    import glob
    import time

    # Limpiar archivos CSV y JSON antiguos (más de 7 días)
    cutoff_time = time.time() - (7 * 24 * 60 * 60)
    
    for pattern in ['data/*.csv', 'data/*.json']:
        for file_path in glob.glob(pattern):
            try:
                if os.path.getmtime(file_path) < cutoff_time:
                    os.remove(file_path)
                    logger.info(f"🗑️ Archivo eliminado: {file_path}")
            except Exception as e:
                logger.warning(f"Error eliminando {file_path}: {e}")

def cleanup_old_logs():
    """Limpiar logs antiguos"""
    import glob
    import time
    
    cutoff_time = time.time() - (30 * 24 * 60 * 60)  # 30 días
    
    for pattern in ['*.log']:
        for file_path in glob.glob(pattern):
            try:
                if os.path.getmtime(file_path) < cutoff_time:
                    os.remove(file_path)
                    logger.info(f"🗑️ Log eliminado: {file_path}")
            except Exception as e:
                logger.warning(f"Error eliminando {file_path}: {e}")

if __name__ == '__main__':
    celery_app.start()
