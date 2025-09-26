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
                logging.FileHandler('scheduler.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Archivo para marcar si ya se hizo scraping completo
        self.primera_ejecucion_file = '.primera_ejecucion_completada'

    def ejecutar_scraping_completo(self):
        """Ejecuta el scraping completo (primera vez)"""
        self.logger.info("Iniciando scraping completo programado")
        try:
            # Importar y ejecutar directamente
            from pachamama_scraper import PachamamaRadioScraper
            scraper = PachamamaRadioScraper(delay=2)
            scraper.scrape_recursivo(max_depth=15)
            
            # Marcar como completado
            with open(self.primera_ejecucion_file, 'w') as f:
                f.write(f"Completado: {datetime.now()}")
                
            self.logger.info("Scraping completo finalizado exitosamente")
        except Exception as e:
            self.logger.error(f"Error en scraping completo: {e}")

    def ejecutar_scraping_incremental(self):
        """Ejecuta el scraping incremental"""
        self.logger.info("Iniciando scraping incremental programado")
        try:
            from pachamama_scraper import PachamamaRadioScraper
            scraper = PachamamaRadioScraper(delay=1.5)  # Más rápido para incremental
            scraper.ejecutar_scraping_incremental()
            self.logger.info("Scraping incremental finalizado exitosamente")
        except Exception as e:
            self.logger.error(f"Error en scraping incremental: {e}")

    def verificar_primera_ejecucion(self):
        """Verifica si ya se ejecutó el scraping completo"""
        return os.path.exists(self.primera_ejecucion_file)

    def job_programado(self):
        """Job que decide qué tipo de scraping ejecutar"""
        if not self.verificar_primera_ejecucion():
            self.logger.info("Primera ejecución detectada - ejecutando scraping completo")
            self.ejecutar_scraping_completo()
        else:
            self.logger.info("Ejecutando scraping incremental")
            self.ejecutar_scraping_incremental()

    def iniciar_scheduler(self):
        """Inicia el scheduler con diferentes configuraciones"""
        print("=== SCHEDULER SCRAPING PACHAMAMA RADIO ===")
        print("Configuraciones disponibles:")
        print("1. Cada 2 horas (recomendado para sitios activos)")
        print("2. Cada 6 horas")
        print("3. Cada 12 horas") 
        print("4. Una vez al día (9:00 AM)")
        print("5. Dos veces al día (9:00 AM y 9:00 PM)")
        print("6. Personalizado")
        
        opcion = input("Selecciona una opción (1-6): ").strip()
        
        if opcion == "1":
            schedule.every(2).hours.do(self.job_programado)
            print("Programado: cada 2 horas")
        elif opcion == "2":
            schedule.every(6).hours.do(self.job_programado)
            print("Programado: cada 6 horas")
        elif opcion == "3":
            schedule.every(12).hours.do(self.job_programado)
            print("Programado: cada 12 horas")
        elif opcion == "4":
            schedule.every().day.at("09:00").do(self.job_programado)
            print("Programado: diariamente a las 9:00 AM")
        elif opcion == "5":
            schedule.every().day.at("09:00").do(self.job_programado)
            schedule.every().day.at("21:00").do(self.job_programado)
            print("Programado: 9:00 AM y 9:00 PM diariamente")
        elif opcion == "6":
            horas = input("Ingresa cada cuántas horas ejecutar (ej: 4): ")
            try:
                horas = int(horas)
                schedule.every(horas).hours.do(self.job_programado)
                print(f"Programado: cada {horas} horas")
            except ValueError:
                print("Valor inválido, usando cada 6 horas por defecto")
                schedule.every(6).hours.do(self.job_programado)
        else:
            print("Opción inválida, usando cada 6 horas por defecto")
            schedule.every(6).hours.do(self.job_programado)
        
        # Ejecutar inmediatamente la primera vez
        print("\nEjecutando scraping inicial...")
        self.job_programado()
        
        # Mantener el scheduler corriendo
        print(f"\nScheduler iniciado. Próxima ejecución: {schedule.next_run()}")
        print("Presiona Ctrl+C para detener")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Verificar cada minuto
        except KeyboardInterrupt:
            print("\nScheduler detenido por el usuario")
            self.logger.info("Scheduler detenido por el usuario")


def main():
    scheduler = ScrapingScheduler()
    scheduler.iniciar_scheduler()


if __name__ == "__main__":
    main()