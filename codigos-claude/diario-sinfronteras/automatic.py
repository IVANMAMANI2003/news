import logging
import os
import subprocess
import time
from datetime import datetime

import schedule

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)

def run_scraper():
    """Ejecutar el scraper"""
    try:
        logging.info("=== INICIANDO EJECUCIÓN PROGRAMADA DEL SCRAPER ===")
        
        # Ejecutar el script principal
        result = subprocess.run(['python', 'news_scraper.py'], 
                              capture_output=True, text=True, timeout=3600)
        
        if result.returncode == 0:
            logging.info("Scraper ejecutado exitosamente")
            logging.info(f"Output: {result.stdout}")
        else:
            logging.error(f"Error ejecutando scraper: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        logging.error("El scraper excedió el tiempo límite de 1 hora")
    except Exception as e:
        logging.error(f"Error inesperado: {e}")

def main():
    """Configurar y ejecutar el scheduler"""
    
    # Configurar horarios de ejecución
    schedule.every().day.at("06:00").do(run_scraper)  # 6:00 AM
    schedule.every().day.at("12:00").do(run_scraper)  # 12:00 PM
    schedule.every().day.at("18:00").do(run_scraper)  # 6:00 PM
    
    # Opción alternativa: ejecutar cada N horas
    # schedule.every(4).hours.do(run_scraper)  # Cada 4 horas
    
    logging.info("Scheduler iniciado. Horarios configurados:")
    logging.info("- 06:00 AM")
    logging.info("- 12:00 PM") 
    logging.info("- 18:00 PM")
    logging.info("Presiona Ctrl+C para detener")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Verificar cada minuto
    except KeyboardInterrupt:
        logging.info("Scheduler detenido por el usuario")

if __name__ == "__main__":
    main()