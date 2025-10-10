"""
Tareas de Celery para el sistema de scraping asíncrono
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

from celery import current_task

from celery_config import celery_app
# Importar scrapers
from database import DatabaseManager
from unified_scraper import normalize_news_data, save_news_files

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name='news_scraper.tasks.scrape_source')
def scrape_source(self, source_name: str, source_config: Dict) -> Dict:
    """
    Tarea para hacer scraping de una fuente específica
    """
    try:
        logger.info(f"Iniciando scraping de {source_name}")
        
        # Actualizar estado de la tarea
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': 100, 'status': f'Iniciando scraping de {source_name}'}
        )
        
        # Importar scraper según la fuente
        scraper = None
        noticias = []
        
        if source_name == 'pachamama':
            from scrapers.pachamama_scraper import PachamamaRadioScraper
            scraper = PachamamaRadioScraper()
            
            # Ejecutar scraping
            scraper.scrape_noticias()
            noticias = scraper.news_data
                    
        elif source_name == 'los_andes':
            from scrapers.los_andes_scraper import LosAndesScraper
            scraper = LosAndesScraper()
            
            # Ejecutar scraping
            scraper.scrape_noticias()
            noticias = scraper.news_data
            
        elif source_name == 'puno_noticias':
            from scrapers.puno_noticias_scraper import PunoNoticiasScraper
            scraper = PunoNoticiasScraper()
            
            # Ejecutar scraping
            scraper.scrape_noticias()
            noticias = scraper.news_data
            
        elif source_name == 'diario_sin_fronteras':
            from scrapers.diario_sin_fronteras_scraper import \
                DiarioSinFronterasScraper
            scraper = DiarioSinFronterasScraper()
            
            # Ejecutar scraping
            scraper.scrape_noticias()
            noticias = scraper.news_data
        
        # Actualizar progreso
        self.update_state(
            state='PROGRESS',
            meta={'current': 50, 'total': 100, 'status': f'Procesando {len(noticias)} noticias de {source_name}'}
        )
        
        # Normalizar noticias
        noticias_normalizadas = []
        for noticia in noticias:
            noticia_normalizada = normalize_news_data(noticia, source_name)
            noticias_normalizadas.append(noticia_normalizada)
        
        # Actualizar progreso
        self.update_state(
            state='PROGRESS',
            meta={'current': 80, 'total': 100, 'status': f'Guardando {len(noticias_normalizadas)} noticias'}
        )
        
        # Guardar archivos
        save_news_files(noticias_normalizadas, source_name)
        
        # Actualizar progreso final
        self.update_state(
            state='PROGRESS',
            meta={'current': 100, 'total': 100, 'status': f'Completado: {len(noticias_normalizadas)} noticias'}
        )
        
        return {
            'source': source_name,
            'noticias_count': len(noticias_normalizadas),
            'status': 'completed',
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error en scraping de {source_name}: {e}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'source': source_name}
        )
        raise

@celery_app.task(name='news_scraper.tasks.process_news_batch')
def process_news_batch(noticias_data: List[Dict], source_name: str) -> Dict:
    """
    Procesar un lote de noticias
    """
    try:
        logger.info(f"Procesando lote de {len(noticias_data)} noticias de {source_name}")
        
        # Normalizar datos
        noticias_normalizadas = []
        for noticia in noticias_data:
            noticia_normalizada = normalize_news_data(noticia, source_name)
            noticias_normalizadas.append(noticia_normalizada)
        
        # Guardar archivos
        save_news_files(noticias_normalizadas, source_name)
        
        return {
            'processed_count': len(noticias_normalizadas),
            'source': source_name,
            'status': 'completed'
        }
        
    except Exception as e:
        logger.error(f"Error procesando lote de {source_name}: {e}")
        raise

@celery_app.task(name='news_scraper.tasks.save_to_database')
def save_to_database(noticias_data: List[Dict]) -> Dict:
    """
    Guardar noticias en la base de datos
    """
    try:
        logger.info(f"Guardando {len(noticias_data)} noticias en la base de datos")
        
        with DatabaseManager() as db:
            if not db.connection:
                raise Exception("No se pudo conectar a la base de datos")
            
            inserted_count = db.insert_noticias_batch(noticias_data)
            
            return {
                'inserted_count': inserted_count,
                'total_count': len(noticias_data),
                'status': 'completed'
            }
            
    except Exception as e:
        logger.error(f"Error guardando en base de datos: {e}")
        raise

def save_scraping_stats(results):
    """
    Guardar estadísticas del scraping
    """
    try:
        stats = {
            'timestamp': datetime.now().isoformat(),
            'total_sources': len(results),
            'successful_sources': len([r for r in results if 'error' not in r]),
            'failed_sources': len([r for r in results if 'error' in r]),
            'results': results
        }
        
        # Guardar en archivo JSON
        with open('logs/scraping_stats.json', 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Estadísticas guardadas: {stats['successful_sources']}/{stats['total_sources']} fuentes exitosas")
        
    except Exception as e:
        logger.error(f"Error guardando estadísticas: {e}")

@celery_app.task(name='news_scraper.tasks.scheduled_scraping')
def scheduled_scraping():
    """
    Tarea programada para hacer scraping completo inicial de todas las fuentes
    """
    try:
        logger.info("Iniciando scraping completo inicial")
        
        # Lista de fuentes
        sources = [
            {'name': 'pachamama', 'enabled': True},
            {'name': 'los_andes', 'enabled': True},
            {'name': 'puno_noticias', 'enabled': True},
            {'name': 'diario_sin_fronteras', 'enabled': True}
        ]
        
        # Ejecutar scraping secuencial (una fuente a la vez)
        results = []
        for source in sources:
            if source['enabled']:
                try:
                    logger.info(f"Procesando fuente completa: {source['name']}")
                    # Ejecutar scraping directamente sin usar .get()
                    result = scrape_source(source['name'], {})
                    results.append(result)
                    logger.info(f"Completado: {source['name']}")
                except Exception as e:
                    logger.error(f"Error en fuente {source['name']}: {e}")
                    results.append({'error': str(e), 'source': source['name']})
        
        # Guardar estadísticas
        save_scraping_stats(results)
        
        return {
            'sources_processed': len(results),
            'results': results,
            'timestamp': datetime.now().isoformat(),
            'type': 'complete_initial'
        }
        
    except Exception as e:
        logger.error(f"Error en scraping completo inicial: {e}")
        raise

@celery_app.task(name='news_scraper.tasks.scrape_new_news')
def scrape_new_news():
    """
    Tarea para hacer scraping solo de nuevas noticias (cada hora)
    """
    try:
        logger.info("Iniciando scraping de nuevas noticias")
        
        # Lista de fuentes
        sources = [
            {'name': 'pachamama', 'enabled': True},
            {'name': 'los_andes', 'enabled': True},
            {'name': 'puno_noticias', 'enabled': True},
            {'name': 'diario_sin_fronteras', 'enabled': True}
        ]
        
        # Ejecutar scraping secuencial (una fuente a la vez)
        results = []
        for source in sources:
            if source['enabled']:
                try:
                    logger.info(f"Procesando nuevas noticias de: {source['name']}")
                    # Ejecutar scraping directamente sin usar .get()
                    result = scrape_source(source['name'], {})
                    results.append(result)
                    logger.info(f"Completado: {source['name']}")
                except Exception as e:
                    logger.error(f"Error en fuente {source['name']}: {e}")
                    results.append({'error': str(e), 'source': source['name']})
        
        # Guardar estadísticas
        save_scraping_stats(results)
        
        return {
            'sources_processed': len(results),
            'results': results,
            'timestamp': datetime.now().isoformat(),
            'type': 'new_news'
        }
        
    except Exception as e:
        logger.error(f"Error en scraping de nuevas noticias: {e}")
        raise

@celery_app.task(name='news_scraper.tasks.cleanup_old_logs_only')
def cleanup_old_logs_only():
    """
    Limpiar solo logs antiguos (NO elimina noticias)
    """
    try:
        logger.info("Iniciando limpieza de logs antiguos (manteniendo todas las noticias)")
        
        # Solo limpiar logs antiguos, NO archivos de noticias
        cleanup_old_logs()
        
        return {
            'status': 'completed',
            'timestamp': datetime.now().isoformat(),
            'note': 'Solo se limpiaron logs, se mantuvieron todas las noticias'
        }
        
    except Exception as e:
        logger.error(f"Error en limpieza de logs: {e}")
        raise

@celery_app.task(name='news_scraper.tasks.cleanup_old_data')
def cleanup_old_data():
    """
    Limpiar datos antiguos (DEPRECATED - ya no se usa)
    """
    try:
        logger.info("Tarea de limpieza de datos deshabilitada - se mantienen todas las noticias")
        
        return {
            'status': 'disabled',
            'timestamp': datetime.now().isoformat(),
            'note': 'Limpieza de datos deshabilitada para mantener todas las noticias'
        }
        
    except Exception as e:
        logger.error(f"Error en limpieza: {e}")
        raise

def normalize_news_data(noticia: Dict, source: str) -> Dict:
    """Normalizar datos de noticias"""
    return {
        'titulo': noticia.get('titulo', ''),
        'fecha': noticia.get('fecha', ''),
        'hora': noticia.get('hora', ''),
        'resumen': noticia.get('resumen', ''),
        'contenido': noticia.get('contenido', ''),
        'categoria': noticia.get('categoria', ''),
        'autor': noticia.get('autor', ''),
        'tags': noticia.get('tags', ''),
        'url': noticia.get('url', ''),
        'link_imagenes': noticia.get('link_imagenes', ''),
        'fuente': source,
        'fecha_extraccion': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

def save_news_files(noticias: List[Dict], source_name: str):
    """Guardar noticias en archivos CSV y JSON"""
    if not noticias:
        return
    
    # Crear directorio data si no existe
    os.makedirs('data', exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Guardar JSON
    json_file = f"data/noticias_{source_name}_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(noticias, f, ensure_ascii=False, indent=2)
    
    # Guardar CSV
    import csv
    csv_file = f"data/noticias_{source_name}_{timestamp}.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        if noticias:
            fieldnames = noticias[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(noticias)
    
    logger.info(f"Archivos guardados: {json_file}, {csv_file}")

def save_scraping_stats(results: List[Dict]):
    """Guardar estadísticas del scraping"""
    stats = {
        'timestamp': datetime.now().isoformat(),
        'sources_processed': len(results),
        'results': results
    }
    
    with open('data/scraping_stats.json', 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

def cleanup_old_files():
    """Limpiar archivos antiguos (DESHABILITADO - se mantienen todas las noticias)"""
    logger.info("Limpieza de archivos de noticias DESHABILITADA - se mantienen todas las noticias")
    # Ya no se eliminan archivos de noticias para mantener la mayor cantidad posible

def cleanup_old_logs():
    """Limpiar logs antiguos"""
    import glob
    import time
    
    cutoff_time = time.time() - (30 * 24 * 60 * 60)  # 30 días
    
    for pattern in ['*.log']:
        for file_path in glob.glob(pattern):
            if os.path.getmtime(file_path) < cutoff_time:
                os.remove(file_path)
                logger.info(f"Log eliminado: {file_path}")

if __name__ == '__main__':
    celery_app.start()
