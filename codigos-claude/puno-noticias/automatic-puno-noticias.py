import logging
import os
import subprocess
import time
from datetime import datetime

import schedule


class ScrapingScheduler:
    def __init__(self):
        # Configurar logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('scheduler.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def run_scraper(self):
        """Ejecutar el scraper"""
        try:
            self.logger.info("Iniciando ejecución programada del scraper...")
            
            # Importar y ejecutar el scraper
            from puno_scraper import PunoNoticiasScraper
            
            scraper = PunoNoticiasScraper()
            scraper.run_incremental()
            
            self.logger.info("Scraping completado exitosamente")
            
        except Exception as e:
            self.logger.error(f"Error en ejecución del scraper: {e}")

    def start_scheduler(self):
        """Iniciar el programador"""
        # Programar ejecuciones
        schedule.every(2).hours.do(self.run_scraper)  # Cada 2 horas
        schedule.every().day.at("06:00").do(self.run_scraper)  # Diario a las 6 AM
        schedule.every().day.at("12:00").do(self.run_scraper)  # Diario a las 12 PM
        schedule.every().day.at("18:00").do(self.run_scraper)  # Diario a las 6 PM
        
        self.logger.info("Scheduler iniciado. Programado para ejecutar cada 2 horas y 3 veces al día.")
        
        # Ejecutar una vez al iniciar
        self.run_scraper()
        
        # Loop principal
        while True:
            schedule.run_pending()
            time.sleep(60)  # Revisar cada minuto

if __name__ == "__main__":
    scheduler = ScrapingScheduler()
    scheduler.start_scheduler()