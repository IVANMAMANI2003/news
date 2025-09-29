import csv
import json
import logging
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Importar los scrapers existentes
sys.path.append('codigos-claude/diario-sinfronteras')
sys.path.append('codigos-claude/los-andes')
sys.path.append('codigos-claude/pachamama')
sys.path.append('codigos-claude/puno-noticias')

from database import DatabaseManager

# Importar los scrapers (adaptados para el sistema unificado)
try:
    from sin_fronteras import NewsScraper as SinFronterasScraper
except ImportError:
    SinFronterasScraper = None

try:
    from los_andes import LosAndesScraper
except ImportError:
    LosAndesScraper = None

try:
    from pachamama import PachamamaRadioScraper
except ImportError:
    PachamamaRadioScraper = None

try:
    from puno_noticias import PunoNoticiasScraper
except ImportError:
    PunoNoticiasScraper = None


class UnifiedNewsScraper:
    def __init__(self, config_file="scraper_config.json"):
        """
        Sistema unificado de scraping que integra todas las fuentes de noticias
        """
        self.config = self.load_config(config_file)
        self.db_manager = DatabaseManager()
        
        # Configurar logging
        self.setup_logging()
        
        # Inicializar scrapers
        self.scrapers = {}
        
        if SinFronterasScraper:
            self.scrapers['diario_sin_fronteras'] = {
                'scraper': SinFronterasScraper(),
                'base_url': 'https://diariosinfronteras.com.pe/',
                'enabled': True
            }
        
        if LosAndesScraper:
            self.scrapers['los_andes'] = {
                'scraper': LosAndesScraper(),
                'base_url': 'https://losandes.com.pe',
                'enabled': True
            }
        
        if PachamamaRadioScraper:
            self.scrapers['pachamama'] = {
                'scraper': PachamamaRadioScraper(),
                'base_url': 'https://pachamamaradio.org/',
                'enabled': True
            }
        
        if PunoNoticiasScraper:
            self.scrapers['puno_noticias'] = {
                'scraper': PunoNoticiasScraper(),
                'base_url': 'https://punonoticias.pe/',
                'enabled': True
            }
        
        # Estadísticas
        self.stats = {
            'total_noticias': 0,
            'noticias_por_fuente': {},
            'errores': 0,
            'inicio_ejecucion': None,
            'fin_ejecucion': None
        }
        
        # Lock para operaciones thread-safe
        self.lock = threading.Lock()
    
    def load_config(self, config_file):
        """Cargar configuración del sistema"""
        default_config = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "database": "news_scraper",
                "user": "postgres",
                "password": "123456"
            },
            "scraping": {
                "delay_between_sources": 5,  # segundos entre fuentes
                "max_workers_per_source": 3,
                "timeout": 30,
                "max_retries": 3,
                "enable_incremental": True,
                "max_articles_per_source": 1000
            },
            "output": {
                "save_csv": True,
                "save_json": True,
                "output_directory": "output",
                "include_timestamp": True
            },
            "sources": {
                "diario_sin_fronteras": True,
                "los_andes": True,
                "pachamama": True,
                "puno_noticias": True
            },
            "logging": {
                "level": "INFO",
                "file": "unified_scraper.log",
                "max_size_mb": 10
            }
        }
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    # Merge con configuración por defecto
                    self.merge_config(default_config, user_config)
            except Exception as e:
                self.logger.error(f"Error cargando configuración: {e}")
        else:
            # Crear archivo de configuración por defecto
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
            print(f"Archivo de configuración creado: {config_file}")
        
        return default_config
    
    def merge_config(self, default, user):
        """Merge recursivo de configuraciones"""
        for key, value in user.items():
            if key in default:
                if isinstance(value, dict) and isinstance(default[key], dict):
                    self.merge_config(default[key], value)
                else:
                    default[key] = value
            else:
                default[key] = value
    
    def setup_logging(self):
        """Configurar sistema de logging"""
        log_config = self.config.get('logging', {})
        
        # Crear directorio de logs si no existe
        log_dir = os.path.dirname(log_config.get('file', 'unified_scraper.log'))
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        logging.basicConfig(
            level=getattr(logging, log_config.get('level', 'INFO')),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_config.get('file', 'unified_scraper.log'), encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def normalize_news_data(self, raw_data: Dict, source: str) -> Dict:
        """Normalizar datos de noticias de diferentes fuentes"""
        # Mapear campos comunes
        normalized = {
            'titulo': raw_data.get('titulo', ''),
            'fecha': self.normalize_date(raw_data.get('fecha', '')),
            'hora': self.normalize_time(raw_data.get('hora', '')),
            'resumen': raw_data.get('resumen', ''),
            'contenido': raw_data.get('contenido', ''),
            'categoria': raw_data.get('categoria', ''),
            'autor': raw_data.get('autor', ''),
            'tags': self.normalize_tags(raw_data.get('tags', '')),
            'url': raw_data.get('url', ''),
            'link_imagenes': self.normalize_images(raw_data.get('link_imagenes', [])),
            'fuente': source,
            'fecha_extraccion': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return normalized
    
    def normalize_date(self, date_str: str) -> str:
        """Normalizar formato de fecha"""
        if not date_str:
            return datetime.now().strftime('%Y-%m-%d')
        
        try:
            # Intentar diferentes formatos de fecha
            formats = [
                '%Y-%m-%d',
                '%d/%m/%Y',
                '%d-%m-%Y',
                '%Y/%m/%d',
                '%d/%m/%y',
                '%d-%m-%y'
            ]
            
            for fmt in formats:
                try:
                    date_obj = datetime.strptime(date_str, fmt)
                    return date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    continue
            
            # Si no se puede parsear, usar fecha actual
            return datetime.now().strftime('%Y-%m-%d')
            
        except Exception:
            return datetime.now().strftime('%Y-%m-%d')
    
    def normalize_time(self, time_str: str) -> str:
        """Normalizar formato de hora"""
        if not time_str:
            return '00:00:00'
        
        try:
            # Limpiar y normalizar hora
            time_str = time_str.strip()
            
            # Si ya tiene formato correcto
            if ':' in time_str and len(time_str.split(':')) >= 2:
                parts = time_str.split(':')
                if len(parts) == 2:
                    return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}:00"
                elif len(parts) == 3:
                    return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}:{parts[2].zfill(2)}"
            
            return '00:00:00'
            
        except Exception:
            return '00:00:00'
    
    def normalize_tags(self, tags) -> str:
        """Normalizar tags"""
        if not tags:
            return ''
        
        if isinstance(tags, list):
            return ', '.join([str(tag).strip() for tag in tags if tag])
        elif isinstance(tags, str):
            return tags.strip()
        
        return ''
    
    def normalize_images(self, images) -> str:
        """Normalizar imágenes"""
        if not images:
            return ''
        
        if isinstance(images, list):
            return '; '.join([str(img).strip() for img in images if img])
        elif isinstance(images, str):
            return images.strip()
        
        return ''
    
    def scrape_source(self, source_name: str, source_config: Dict) -> List[Dict]:
        """Scraper individual para una fuente"""
        self.logger.info(f"Iniciando scraping de {source_name}")
        
        try:
            scraper = source_config['scraper']
            noticias = []
            
            # Ejecutar scraping según el tipo de scraper
            if source_name == 'diario_sin_fronteras':
                # Sin Fronteras tiene método run()
                scraper.run()
                noticias = scraper.news_data
                
            elif source_name == 'los_andes':
                # Los Andes tiene método run_scraping()
                scraper.run_scraping()
                noticias = scraper.news_data
                
            elif source_name == 'pachamama':
                # Pachamama tiene método scrape_recursivo()
                scraper.scrape_recursivo(max_depth=10)
                # Cargar datos del archivo JSON
                if os.path.exists(scraper.json_file):
                    with open(scraper.json_file, 'r', encoding='utf-8') as f:
                        noticias = json.load(f)
                        
            elif source_name == 'puno_noticias':
                # Puno Noticias tiene método scrape_all_news()
                scraper.scrape_all_news()
                noticias = scraper.news_data
            
            # Normalizar datos
            normalized_noticias = []
            for noticia in noticias:
                try:
                    normalized = self.normalize_news_data(noticia, source_name)
                    normalized_noticias.append(normalized)
                except Exception as e:
                    self.logger.error(f"Error normalizando noticia de {source_name}: {e}")
                    continue
            
            self.logger.info(f"Scraping de {source_name} completado: {len(normalized_noticias)} noticias")
            return normalized_noticias
            
        except Exception as e:
            self.logger.error(f"Error en scraping de {source_name}: {e}")
            with self.lock:
                self.stats['errores'] += 1
            return []
    
    def save_to_database(self, noticias: List[Dict]) -> int:
        """Guardar noticias en la base de datos"""
        if not noticias:
            return 0
        
        try:
            with self.db_manager as db:
                inserted_count = db.insert_noticias_batch(noticias)
                self.logger.info(f"Insertadas {inserted_count} noticias en la base de datos")
                return inserted_count
        except Exception as e:
            self.logger.error(f"Error guardando en base de datos: {e}")
            return 0
    
    def save_to_files(self, noticias: List[Dict], source_name: str = None):
        """Guardar noticias en archivos CSV y JSON"""
        if not noticias:
            return
        
        try:
            # Crear directorio de salida
            output_dir = self.config['output']['output_directory']
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Nombre de archivo
            if source_name:
                base_filename = f"noticias_{source_name}_{timestamp}"
            else:
                base_filename = f"noticias_todas_{timestamp}"
            
            # Guardar JSON
            if self.config['output']['save_json']:
                json_file = os.path.join(output_dir, f"{base_filename}.json")
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(noticias, f, ensure_ascii=False, indent=2)
                self.logger.info(f"Datos guardados en JSON: {json_file}")
            
            # Guardar CSV
            if self.config['output']['save_csv'] and noticias:
                csv_file = os.path.join(output_dir, f"{base_filename}.csv")
                fieldnames = noticias[0].keys()
                
                with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(noticias)
                self.logger.info(f"Datos guardados en CSV: {csv_file}")
                
        except Exception as e:
            self.logger.error(f"Error guardando archivos: {e}")
    
    def run_full_scraping(self):
        """Ejecutar scraping completo de todas las fuentes"""
        self.stats['inicio_ejecucion'] = datetime.now()
        self.logger.info("=== INICIANDO SCRAPING UNIFICADO ===")
        
        all_noticias = []
        
        try:
            # Inicializar base de datos
            with self.db_manager as db:
                if not db.connection:
                    self.logger.error("No se pudo conectar a la base de datos")
                    return
            
            # Procesar cada fuente habilitada
            for source_name, source_config in self.scrapers.items():
                if not source_config['enabled']:
                    self.logger.info(f"Fuente {source_name} deshabilitada, saltando...")
                    continue
                
                if not self.config['sources'].get(source_name, True):
                    self.logger.info(f"Fuente {source_name} deshabilitada en configuración, saltando...")
                    continue
                
                self.logger.info(f"Procesando fuente: {source_name}")
                
                # Scraping de la fuente
                noticias = self.scrape_source(source_name, source_config)
                
                if noticias:
                    # Guardar en base de datos
                    inserted_count = self.save_to_database(noticias)
                    
                    # Guardar archivos individuales por fuente
                    self.save_to_files(noticias, source_name)
                    
                    # Acumular para archivo general
                    all_noticias.extend(noticias)
                    
                    # Actualizar estadísticas
                    with self.lock:
                        self.stats['noticias_por_fuente'][source_name] = len(noticias)
                        self.stats['total_noticias'] += len(noticias)
                
                # Delay entre fuentes
                delay = self.config['scraping']['delay_between_sources']
                if delay > 0:
                    self.logger.info(f"Esperando {delay} segundos antes de la siguiente fuente...")
                    time.sleep(delay)
            
            # Guardar archivo general con todas las noticias
            if all_noticias:
                self.save_to_files(all_noticias)
                self.logger.info(f"Total de noticias procesadas: {len(all_noticias)}")
            
            # Mostrar estadísticas finales
            self.show_final_stats()
            
        except Exception as e:
            self.logger.error(f"Error durante el scraping unificado: {e}")
        finally:
            self.stats['fin_ejecucion'] = datetime.now()
    
    def run_incremental_scraping(self):
        """Ejecutar scraping incremental (solo noticias nuevas)"""
        self.logger.info("=== INICIANDO SCRAPING INCREMENTAL ===")
        
        # Para scraping incremental, usar métodos específicos de cada scraper
        # que ya implementan lógica de detección de noticias nuevas
        
        for source_name, source_config in self.scrapers.items():
            if not source_config['enabled']:
                continue
                
            if not self.config['sources'].get(source_name, True):
                continue
            
            self.logger.info(f"Scraping incremental de {source_name}")
            
            try:
                scraper = source_config['scraper']
                
                if source_name == 'pachamama':
                    # Pachamama tiene método específico para incremental
                    scraper.ejecutar_scraping_incremental()
                else:
                    # Para otros scrapers, ejecutar método normal
                    # (ya tienen lógica interna para evitar duplicados)
                    if hasattr(scraper, 'run_scraping'):
                        scraper.run_scraping()
                    elif hasattr(scraper, 'run'):
                        scraper.run()
                    elif hasattr(scraper, 'scrape_all_news'):
                        scraper.scrape_all_news()
                
                # Cargar y procesar datos nuevos
                noticias = self.get_new_news_from_scraper(scraper, source_name)
                
                if noticias:
                    self.save_to_database(noticias)
                    self.save_to_files(noticias, source_name)
                    
                    with self.lock:
                        self.stats['noticias_por_fuente'][source_name] = len(noticias)
                        self.stats['total_noticias'] += len(noticias)
                
            except Exception as e:
                self.logger.error(f"Error en scraping incremental de {source_name}: {e}")
                with self.lock:
                    self.stats['errores'] += 1
        
        self.show_final_stats()
    
    def get_new_news_from_scraper(self, scraper, source_name):
        """Obtener noticias nuevas del scraper"""
        noticias = []
        
        try:
            if hasattr(scraper, 'news_data'):
                noticias = scraper.news_data
            elif hasattr(scraper, 'json_file') and os.path.exists(scraper.json_file):
                with open(scraper.json_file, 'r', encoding='utf-8') as f:
                    noticias = json.load(f)
            
            # Normalizar datos
            normalized_noticias = []
            for noticia in noticias:
                try:
                    normalized = self.normalize_news_data(noticia, source_name)
                    normalized_noticias.append(normalized)
                except Exception as e:
                    self.logger.error(f"Error normalizando noticia: {e}")
                    continue
            
            return normalized_noticias
            
        except Exception as e:
            self.logger.error(f"Error obteniendo noticias del scraper: {e}")
            return []
    
    def show_final_stats(self):
        """Mostrar estadísticas finales"""
        self.logger.info("=== ESTADÍSTICAS FINALES ===")
        self.logger.info(f"Total de noticias procesadas: {self.stats['total_noticias']}")
        self.logger.info(f"Errores encontrados: {self.stats['errores']}")
        
        if self.stats['inicio_ejecucion'] and self.stats['fin_ejecucion']:
            duracion = self.stats['fin_ejecucion'] - self.stats['inicio_ejecucion']
            self.logger.info(f"Duración total: {duracion}")
        
        self.logger.info("Noticias por fuente:")
        for fuente, cantidad in self.stats['noticias_por_fuente'].items():
            self.logger.info(f"  {fuente}: {cantidad}")
        
        # Mostrar estadísticas de la base de datos
        try:
            with self.db_manager as db:
                stats_db = db.get_estadisticas()
                self.logger.info("=== ESTADÍSTICAS DE BASE DE DATOS ===")
                self.logger.info(f"Total en BD: {stats_db.get('total_noticias', 0)}")
                self.logger.info("Por fuente en BD:")
                for fuente, cantidad in stats_db.get('noticias_por_fuente', {}).items():
                    self.logger.info(f"  {fuente}: {cantidad}")
        except Exception as e:
            self.logger.error(f"Error obteniendo estadísticas de BD: {e}")

def main():
    """Función principal"""
    print("=== SISTEMA UNIFICADO DE SCRAPING DE NOTICIAS ===")
    print("1. Scraping completo (primera vez)")
    print("2. Scraping incremental (solo nuevas noticias)")
    print("3. Solo mostrar estadísticas de BD")
    
    opcion = input("Selecciona una opción (1, 2 o 3): ").strip()
    
    scraper = UnifiedNewsScraper()
    
    if opcion == "1":
        print("Iniciando scraping completo...")
        scraper.run_full_scraping()
    elif opcion == "2":
        print("Iniciando scraping incremental...")
        scraper.run_incremental_scraping()
    elif opcion == "3":
        print("Mostrando estadísticas de base de datos...")
        try:
            with scraper.db_manager as db:
                stats = db.get_estadisticas()
                print(f"Total de noticias: {stats.get('total_noticias', 0)}")
                print("Por fuente:")
                for fuente, cantidad in stats.get('noticias_por_fuente', {}).items():
                    print(f"  {fuente}: {cantidad}")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Opción no válida")

if __name__ == "__main__":
    main()
