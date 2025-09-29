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
sys.path.append('codigos-claude/diario-sinfronteras')
sys.path.append('codigos-claude/los-andes')
sys.path.append('codigos-claude/pachamama')
sys.path.append('codigos-claude/puno-noticias')

from database import DatabaseManager

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
            from pachamama import PachamamaRadioScraper
            scraper = PachamamaRadioScraper()
            
            # Configurar para scraping rápido
            scraper.delay = 1  # Reducir delay
            scraper.scrape_recursivo(max_depth=3)  # Reducir profundidad
            
            # Cargar noticias del archivo JSON
            if os.path.exists(scraper.json_file):
                with open(scraper.json_file, 'r', encoding='utf-8') as f:
                    noticias = json.load(f)
                    
        elif source_name == 'los_andes':
            from los_andes import LosAndesScraper
            scraper = LosAndesScraper()
            scraper.delay_between_requests = 1
            scraper.max_workers = 10  # Aumentar workers
            
            scraper.run_scraping()
            noticias = scraper.news_data
            
        elif source_name == 'puno_noticias':
            from puno_noticias import PunoNoticiasScraper
            scraper = PunoNoticiasScraper()
            scraper.delay = 1
            
            scraper.scrape_all_news()
            noticias = scraper.news_data
            
        elif source_name == 'diario_sin_fronteras':
            from sin_fronteras import NewsScraper
            scraper = SinFronterasScraper()
            scraper.config['delay_between_requests'] = 1
            scraper.config['max_workers'] = 10
            
            scraper.run()
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

@celery_app.task(name='news_scraper.tasks.scheduled_scraping')
def scheduled_scraping():
    """
    Tarea programada para hacer scraping de todas las fuentes
    """
    try:
        logger.info("Iniciando scraping programado")
        
        # Lista de fuentes
        sources = [
            {'name': 'pachamama', 'enabled': True},
            {'name': 'los_andes', 'enabled': True},
            {'name': 'puno_noticias', 'enabled': True},
            {'name': 'diario_sin_fronteras', 'enabled': True}
        ]
        
        # Ejecutar scraping en paralelo
        tasks = []
        for source in sources:
            if source['enabled']:
                task = scrape_source.delay(source['name'], {})
                tasks.append(task)
        
        # Esperar resultados
        results = []
        for task in tasks:
            try:
                result = task.get(timeout=600)  # 10 minutos timeout
                results.append(result)
            except Exception as e:
                logger.error(f"Error en tarea: {e}")
                results.append({'error': str(e)})
        
        # Guardar estadísticas
        save_scraping_stats(results)
        
        return {
            'sources_processed': len(results),
            'results': results,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error en scraping programado: {e}")
        raise

@celery_app.task(name='news_scraper.tasks.cleanup_old_data')
def cleanup_old_data():
    """
    Limpiar datos antiguos
    """
    try:
        logger.info("Iniciando limpieza de datos antiguos")
        
        # Limpiar archivos antiguos
        cleanup_old_files()
        
        # Limpiar logs antiguos
        cleanup_old_logs()
        
        return {
            'status': 'completed',
            'timestamp': datetime.now().isoformat()
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
    """Limpiar archivos antiguos"""
    import glob
    import time

    # Limpiar archivos CSV y JSON antiguos (más de 7 días)
    cutoff_time = time.time() - (7 * 24 * 60 * 60)
    
    for pattern in ['data/*.csv', 'data/*.json']:
        for file_path in glob.glob(pattern):
            if os.path.getmtime(file_path) < cutoff_time:
                os.remove(file_path)
                logger.info(f"Archivo eliminado: {file_path}")

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
