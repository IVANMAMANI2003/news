"""
Gestor principal del sistema de scraping de noticias
"""
import csv
import json
import logging
import os
from datetime import datetime
from typing import Dict, List

import pandas as pd

from config import LoggingConfig, NewsSources, ScrapingConfig
from database import DatabaseManager
from scrapers import (DiarioSinFronterasScraper, LosAndesScraper,
                      PachamamaScraper, PunoNoticiasScraper)

# Configurar logging
logging.basicConfig(
    level=getattr(logging, LoggingConfig.LEVEL),
    format=LoggingConfig.FORMAT,
    handlers=[
        logging.FileHandler(LoggingConfig.FILE_HANDLER and ScrapingConfig.LOG_FILE or None),
        logging.StreamHandler() if LoggingConfig.CONSOLE_HANDLER else logging.NullHandler()
    ]
)

logger = logging.getLogger(__name__)

class NewsScraperManager:
    """Gestor principal del sistema de scraping"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.scrapers = self._initialize_scrapers()
        self.output_dir = ScrapingConfig.OUTPUT_DIR
        
        # Crear directorio de salida si no existe
        os.makedirs(self.output_dir, exist_ok=True)
        
    def _initialize_scrapers(self) -> Dict:
        """Inicializar todos los scrapers disponibles"""
        scrapers = {}
        
        for source_key, source_config in NewsSources.SOURCES.items():
            if not source_config['enabled']:
                continue
                
            try:
                if source_key == 'diario_sin_fronteras':
                    scrapers[source_key] = DiarioSinFronterasScraper()
                elif source_key == 'los_andes':
                    scrapers[source_key] = LosAndesScraper()
                elif source_key == 'pachamama':
                    scrapers[source_key] = PachamamaScraper()
                elif source_key == 'puno_noticias':
                    scrapers[source_key] = PunoNoticiasScraper()
                
                logger.info(f"Scraper inicializado: {source_config['name']}")
                
            except Exception as e:
                logger.error(f"Error inicializando scraper {source_key}: {e}")
        
        return scrapers
    
    def setup_database(self) -> bool:
        """Configurar la base de datos"""
        try:
            logger.info("Configurando base de datos...")
            
            # Crear base de datos si no existe
            if not self.db_manager.create_database_if_not_exists():
                return False
            
            # Conectar a la base de datos
            if not self.db_manager.connect():
                return False
            
            # Crear tablas
            if not self.db_manager.create_tables():
                return False
            
            logger.info("Base de datos configurada correctamente")
            return True
            
        except Exception as e:
            logger.error(f"Error configurando base de datos: {e}")
            return False
    
    def scrape_all_sources(self) -> Dict[str, int]:
        """Ejecutar scraping de todas las fuentes habilitadas"""
        results = {}
        total_news = 0
        
        logger.info("=== INICIANDO SCRAPING DE TODAS LAS FUENTES ===")
        
        for source_key, scraper in self.scrapers.items():
            try:
                logger.info(f"Procesando fuente: {scraper.source_name}")
                
                # Descubrir URLs de noticias
                news_urls = scraper.discover_news_urls(max_pages=30)
                logger.info(f"Encontradas {len(news_urls)} URLs en {scraper.source_name}")
                
                # Scrapear noticias
                news_data = scraper.scrape_news(news_urls)
                logger.info(f"Extraídas {len(news_data)} noticias de {scraper.source_name}")
                
                # Guardar en base de datos
                if news_data:
                    inserted_count = self.db_manager.insert_multiple_news(news_data)
                    results[source_key] = inserted_count
                    total_news += inserted_count
                    logger.info(f"Insertadas {inserted_count} noticias nuevas en BD")
                else:
                    results[source_key] = 0
                
                # Generar archivos individuales por fuente
                self._save_source_files(source_key, news_data)
                
                # Delay entre fuentes
                import time
                time.sleep(ScrapingConfig.DELAY_BETWEEN_SOURCES)
                
            except Exception as e:
                logger.error(f"Error procesando fuente {source_key}: {e}")
                results[source_key] = 0
        
        logger.info(f"=== SCRAPING COMPLETADO ===")
        logger.info(f"Total de noticias nuevas: {total_news}")
        logger.info(f"Resultados por fuente: {results}")
        
        return results
    
    def scrape_single_source(self, source_key: str) -> int:
        """Ejecutar scraping de una sola fuente"""
        if source_key not in self.scrapers:
            logger.error(f"Fuente {source_key} no disponible")
            return 0
        
        scraper = self.scrapers[source_key]
        logger.info(f"Procesando fuente individual: {scraper.source_name}")
        
        try:
            # Descubrir URLs de noticias
            news_urls = scraper.discover_news_urls(max_pages=30)
            logger.info(f"Encontradas {len(news_urls)} URLs en {scraper.source_name}")
            
            # Scrapear noticias
            news_data = scraper.scrape_news(news_urls)
            logger.info(f"Extraídas {len(news_data)} noticias de {scraper.source_name}")
            
            # Guardar en base de datos
            if news_data:
                inserted_count = self.db_manager.insert_multiple_news(news_data)
                logger.info(f"Insertadas {inserted_count} noticias nuevas en BD")
                
                # Generar archivos individuales por fuente
                self._save_source_files(source_key, news_data)
                
                return inserted_count
            else:
                return 0
                
        except Exception as e:
            logger.error(f"Error procesando fuente {source_key}: {e}")
            return 0
    
    def _save_source_files(self, source_key: str, news_data: List[Dict]):
        """Guardar archivos CSV y JSON para una fuente específica"""
        if not news_data:
            return
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        source_name = self.scrapers[source_key].source_name.replace(' ', '_').lower()
        
        # Archivo JSON
        json_filename = os.path.join(
            self.output_dir, 
            f"noticias_{source_name}_{timestamp}.json"
        )
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(news_data, f, ensure_ascii=False, indent=2)
        
        # Archivo CSV
        csv_filename = os.path.join(
            self.output_dir, 
            f"noticias_{source_name}_{timestamp}.csv"
        )
        with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
            if news_data:
                fieldnames = news_data[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(news_data)
        
        logger.info(f"Archivos guardados: {json_filename}, {csv_filename}")
    
    def generate_consolidated_files(self):
        """Generar archivos consolidados de todas las fuentes"""
        try:
            logger.info("Generando archivos consolidados...")
            
            # Obtener todas las noticias de la base de datos
            with self.db_manager:
                all_news = self.db_manager.get_recent_news(hours=24*7)  # Última semana
            
            if not all_news:
                logger.warning("No hay noticias para consolidar")
                return
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Convertir a formato de diccionario
            news_dicts = [dict(row) for row in all_news]
            
            # Archivo JSON consolidado
            json_filename = os.path.join(
                self.output_dir, 
                f"noticias_consolidadas_{timestamp}.json"
            )
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(news_dicts, f, ensure_ascii=False, indent=2)
            
            # Archivo CSV consolidado
            csv_filename = os.path.join(
                self.output_dir, 
                f"noticias_consolidadas_{timestamp}.csv"
            )
            with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
                if news_dicts:
                    fieldnames = news_dicts[0].keys()
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(news_dicts)
            
            logger.info(f"Archivos consolidados generados: {json_filename}, {csv_filename}")
            
        except Exception as e:
            logger.error(f"Error generando archivos consolidados: {e}")
    
    def get_statistics(self) -> Dict:
        """Obtener estadísticas del sistema"""
        try:
            with self.db_manager:
                stats = self.db_manager.get_statistics()
            return stats
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {}
    
    def run_incremental_scraping(self):
        """Ejecutar scraping incremental (solo nuevas noticias)"""
        logger.info("=== INICIANDO SCRAPING INCREMENTAL ===")
        
        results = self.scrape_all_sources()
        
        # Generar archivos consolidados
        self.generate_consolidated_files()
        
        # Mostrar estadísticas
        stats = self.get_statistics()
        logger.info(f"Estadísticas actuales: {stats}")
        
        return results
    
    def close(self):
        """Cerrar conexiones"""
        if self.db_manager:
            self.db_manager.close()
