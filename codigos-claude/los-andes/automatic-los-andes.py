# scheduler.py - Script para automatización
import logging
import os
import subprocess
import sys
import time
from datetime import datetime

import schedule

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class ScrapingScheduler:
    """Programador automático para el scraping"""
    
    def __init__(self):
        self.scraper_script = "losandes_scraper.py"
        self.is_running = False
    
    def run_scraping(self):
        """Ejecuta el scraping si no está corriendo"""
        if self.is_running:
            logger.warning("Scraping ya está en ejecución, saltando...")
            return
        
        self.is_running = True
        start_time = datetime.now()
        logger.info("Iniciando ejecución programada del scraping...")
        
        try:
            # Ejecutar el scraper
            result = subprocess.run([sys.executable, self.scraper_script], 
                                  capture_output=True, text=True, encoding='utf-8')
            
            end_time = datetime.now()
            duration = end_time - start_time
            
            if result.returncode == 0:
                logger.info(f"Scraping completado exitosamente en {duration}")
                if result.stdout:
                    logger.info(f"Salida: {result.stdout}")
            else:
                logger.error(f"Error en scraping: {result.stderr}")
                
        except Exception as e:
            logger.error(f"Error ejecutando scraper: {str(e)}")
        
        finally:
            self.is_running = False
    
    def setup_schedule(self):
        """Configura los horarios de ejecución"""
        
        # Opciones de programación (descomenta la que prefieras):
        
        # Cada 6 horas
        schedule.every(6).hours.do(self.run_scraping)
        
        # Cada 12 horas
        # schedule.every(12).hours.do(self.run_scraping)
        
        # Diariamente a las 8:00 AM
        # schedule.every().day.at("08:00").do(self.run_scraping)
        
        # Dos veces al día (8:00 AM y 8:00 PM)
        # schedule.every().day.at("08:00").do(self.run_scraping)
        # schedule.every().day.at("20:00").do(self.run_scraping)
        
        # Cada lunes a las 9:00 AM
        # schedule.every().monday.at("09:00").do(self.run_scraping)
        
        # Cada 30 minutos (para testing - no recomendado en producción)
        # schedule.every(30).minutes.do(self.run_scraping)
        
        logger.info("Programación configurada - Ejecutando cada 6 horas")
    
    def run_scheduler(self):
        """Ejecuta el programador"""
        self.setup_schedule()
        logger.info("Scheduler iniciado. Presiona Ctrl+C para detener.")
        
        # Ejecutar una vez al inicio
        logger.info("Ejecutando scraping inicial...")
        self.run_scraping()
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Verificar cada minuto
        except KeyboardInterrupt:
            logger.info("Scheduler detenido por el usuario.")

def main():
    scheduler = ScrapingScheduler()
    scheduler.run_scheduler()

if __name__ == "__main__":
    main()

# requirements.txt - Dependencias necesarias
"""
requests>=2.28.0
beautifulsoup4>=4.11.0
lxml>=4.9.0
schedule>=1.2.0
"""