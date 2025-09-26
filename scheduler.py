"""
Sistema de programación de tareas para ejecución recursiva
"""
import logging
import time
from datetime import datetime

import schedule

from news_scraper_manager import NewsScraperManager

logger = logging.getLogger(__name__)

class NewsScrapingScheduler:
    """Programador de tareas para scraping recursivo"""
    
    def __init__(self):
        self.manager = NewsScraperManager()
        self.running = False
        
    def setup_database(self):
        """Configurar la base de datos al inicio"""
        return self.manager.setup_database()
    
    def run_scraping_job(self):
        """Tarea de scraping programada"""
        try:
            logger.info("=== EJECUTANDO TAREA PROGRAMADA DE SCRAPING ===")
            logger.info(f"Hora de ejecución: {datetime.now()}")
            
            # Ejecutar scraping incremental
            results = self.manager.run_incremental_scraping()
            
            logger.info("=== TAREA PROGRAMADA COMPLETADA ===")
            logger.info(f"Resultados: {results}")
            
        except Exception as e:
            logger.error(f"Error en tarea programada: {e}")
    
    def start_scheduler(self, interval_hours: int = 1):
        """Iniciar el programador de tareas"""
        logger.info(f"Iniciando programador de tareas cada {interval_hours} hora(s)")
        
        # Configurar la tarea
        schedule.every(interval_hours).hours.do(self.run_scraping_job)
        
        # Ejecutar una vez al inicio
        logger.info("Ejecutando primera tarea de scraping...")
        self.run_scraping_job()
        
        # Iniciar el bucle principal
        self.running = True
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Verificar cada minuto
            except KeyboardInterrupt:
                logger.info("Deteniendo programador por interrupción del usuario")
                break
            except Exception as e:
                logger.error(f"Error en el programador: {e}")
                time.sleep(60)  # Esperar antes de reintentar
    
    def stop_scheduler(self):
        """Detener el programador de tareas"""
        logger.info("Deteniendo programador de tareas...")
        self.running = False
        self.manager.close()
    
    def run_once(self):
        """Ejecutar scraping una sola vez"""
        logger.info("Ejecutando scraping una sola vez...")
        try:
            if not self.manager.setup_database():
                logger.error("Error configurando base de datos")
                return False
            
            results = self.manager.run_incremental_scraping()
            logger.info(f"Scraping completado. Resultados: {results}")
            return True
            
        except Exception as e:
            logger.error(f"Error ejecutando scraping: {e}")
            return False
        finally:
            self.manager.close()

def main():
    """Función principal para ejecutar el programador"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Sistema de Scraping de Noticias')
    parser.add_argument('--mode', choices=['once', 'schedule'], default='once',
                       help='Modo de ejecución: una vez o programado')
    parser.add_argument('--interval', type=int, default=1,
                       help='Intervalo en horas para modo programado')
    parser.add_argument('--source', type=str, choices=[
        'diario_sin_fronteras', 'los_andes', 'pachamama', 'puno_noticias'
    ], help='Ejecutar solo una fuente específica')
    
    args = parser.parse_args()
    
    scheduler = NewsScrapingScheduler()
    
    try:
        if args.mode == 'once':
            if args.source:
                # Ejecutar solo una fuente
                if not scheduler.manager.setup_database():
                    logger.error("Error configurando base de datos")
                    return
                
                results = scheduler.manager.scrape_single_source(args.source)
                logger.info(f"Scraping de {args.source} completado. Noticias: {results}")
            else:
                # Ejecutar todas las fuentes
                scheduler.run_once()
        else:
            # Modo programado
            if not scheduler.setup_database():
                logger.error("Error configurando base de datos")
                return
            
            scheduler.start_scheduler(args.interval)
            
    except KeyboardInterrupt:
        logger.info("Deteniendo sistema...")
    except Exception as e:
        logger.error(f"Error en el sistema: {e}")
    finally:
        scheduler.stop_scheduler()

if __name__ == "__main__":
    main()
