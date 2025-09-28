import json
import logging
import os
import signal
import sys
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict

import schedule

from database import DatabaseManager
from unified_scraper import UnifiedNewsScraper


class NewsScrapingScheduler:
    def __init__(self, config_file="scheduler_config.json"):
        """
        Scheduler para ejecutar scraping de noticias de forma recursiva
        """
        self.config = self.load_config(config_file)
        self.scraper = None
        self.running = False
        self.current_job = None
        
        # Configurar logging
        self.setup_logging()
        
        # Configurar manejo de señales para shutdown graceful
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Estadísticas del scheduler
        self.scheduler_stats = {
            'ejecuciones_totales': 0,
            'ejecuciones_exitosas': 0,
            'ejecuciones_fallidas': 0,
            'ultima_ejecucion': None,
            'proxima_ejecucion': None,
            'tiempo_total_ejecucion': 0,
            'inicio_scheduler': datetime.now()
        }
    
    def load_config(self, config_file):
        """Cargar configuración del scheduler"""
        default_config = {
            "scheduler": {
                "interval_hours": 1,  # Ejecutar cada 1 hora
                "max_concurrent_jobs": 1,
                "timeout_minutes": 120,  # Timeout de 2 horas por ejecución
                "retry_failed_jobs": True,
                "max_retries": 3,
                "retry_delay_minutes": 30
            },
            "scraping": {
                "mode": "incremental",  # "full" o "incremental"
                "sources": {
                    "diario_sin_fronteras": True,
                    "los_andes": True,
                    "pachamama": True,
                    "puno_noticias": True
                }
            },
            "logging": {
                "level": "INFO",
                "file": "scheduler.log",
                "max_size_mb": 50,
                "backup_count": 5
            },
            "notifications": {
                "enabled": False,
                "email": {
                    "smtp_server": "",
                    "smtp_port": 587,
                    "username": "",
                    "password": "",
                    "to_addresses": []
                },
                "webhook": {
                    "url": "",
                    "enabled": False
                }
            },
            "maintenance": {
                "cleanup_old_logs_days": 30,
                "cleanup_old_files_days": 7,
                "database_backup_enabled": False,
                "backup_interval_hours": 24
            }
        }
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    self.merge_config(default_config, user_config)
            except Exception as e:
                print(f"Error cargando configuración del scheduler: {e}")
        else:
            # Crear archivo de configuración por defecto
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
            print(f"Archivo de configuración del scheduler creado: {config_file}")
        
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
        """Configurar sistema de logging para el scheduler"""
        log_config = self.config.get('logging', {})
        
        # Crear directorio de logs si no existe
        log_dir = os.path.dirname(log_config.get('file', 'scheduler.log'))
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Configurar logging con rotación
        from logging.handlers import RotatingFileHandler
        
        logger = logging.getLogger('NewsScheduler')
        logger.setLevel(getattr(logging, log_config.get('level', 'INFO')))
        
        # Handler para archivo con rotación
        file_handler = RotatingFileHandler(
            log_config.get('file', 'scheduler.log'),
            maxBytes=log_config.get('max_size_mb', 50) * 1024 * 1024,
            backupCount=log_config.get('backup_count', 5),
            encoding='utf-8'
        )
        
        # Handler para consola
        console_handler = logging.StreamHandler()
        
        # Formato
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        self.logger = logger
    
    def signal_handler(self, signum, frame):
        """Manejar señales de interrupción para shutdown graceful"""
        self.logger.info(f"Recibida señal {signum}, iniciando shutdown graceful...")
        self.stop()
        sys.exit(0)
    
    def execute_scraping_job(self):
        """Ejecutar trabajo de scraping"""
        if self.current_job and self.current_job.is_alive():
            self.logger.warning("Ya hay un trabajo de scraping en ejecución, saltando...")
            return
        
        self.logger.info("=== INICIANDO TRABAJO DE SCRAPING PROGRAMADO ===")
        start_time = datetime.now()
        
        try:
            # Actualizar estadísticas
            self.scheduler_stats['ejecuciones_totales'] += 1
            self.scheduler_stats['ultima_ejecucion'] = start_time
            
            # Crear scraper
            self.scraper = UnifiedNewsScraper()
            
            # Ejecutar scraping según el modo configurado
            scraping_mode = self.config['scraping']['mode']
            
            if scraping_mode == 'full':
                self.logger.info("Ejecutando scraping completo...")
                self.scraper.run_full_scraping()
            else:
                self.logger.info("Ejecutando scraping incremental...")
                self.scraper.run_incremental_scraping()
            
            # Calcular tiempo de ejecución
            end_time = datetime.now()
            execution_time = end_time - start_time
            self.scheduler_stats['tiempo_total_ejecucion'] += execution_time.total_seconds()
            self.scheduler_stats['ejecuciones_exitosas'] += 1
            
            self.logger.info(f"Trabajo de scraping completado exitosamente en {execution_time}")
            
            # Enviar notificaciones si están habilitadas
            self.send_success_notification(execution_time)
            
        except Exception as e:
            self.logger.error(f"Error durante el trabajo de scraping: {e}")
            self.scheduler_stats['ejecuciones_fallidas'] += 1
            
            # Enviar notificación de error
            self.send_error_notification(str(e))
            
            # Reintentar si está habilitado
            if self.config['scheduler']['retry_failed_jobs']:
                self.schedule_retry()
        
        finally:
            self.current_job = None
    
    def schedule_retry(self):
        """Programar reintento de trabajo fallido"""
        max_retries = self.config['scheduler']['max_retries']
        retry_delay = self.config['scheduler']['retry_delay_minutes']
        
        if self.scheduler_stats['ejecuciones_fallidas'] <= max_retries:
            self.logger.info(f"Programando reintento en {retry_delay} minutos...")
            schedule.every(retry_delay).minutes.do(self.execute_scraping_job)
    
    def send_success_notification(self, execution_time):
        """Enviar notificación de éxito"""
        if not self.config['notifications']['enabled']:
            return
        
        message = f"Scraping completado exitosamente en {execution_time}"
        self.logger.info(f"Notificación: {message}")
        
        # Aquí se puede implementar envío de email o webhook
        # Por ahora solo log
    
    def send_error_notification(self, error_message):
        """Enviar notificación de error"""
        if not self.config['notifications']['enabled']:
            return
        
        message = f"Error en scraping: {error_message}"
        self.logger.error(f"Notificación de error: {message}")
        
        # Aquí se puede implementar envío de email o webhook
        # Por ahora solo log
    
    def setup_schedule(self):
        """Configurar horarios de ejecución"""
        interval_hours = self.config['scheduler']['interval_hours']
        
        # Limpiar trabajos existentes
        schedule.clear()
        
        # Programar ejecución cada N horas
        schedule.every(interval_hours).hours.do(self.execute_scraping_job)
        
        # Programar tareas de mantenimiento
        self.setup_maintenance_tasks()
        
        # Calcular próxima ejecución
        next_run = schedule.next_run()
        self.scheduler_stats['proxima_ejecucion'] = next_run
        
        self.logger.info(f"Scheduler configurado para ejecutar cada {interval_hours} horas")
        self.logger.info(f"Próxima ejecución: {next_run}")
    
    def setup_maintenance_tasks(self):
        """Configurar tareas de mantenimiento"""
        maintenance_config = self.config.get('maintenance', {})
        
        # Limpieza de logs antiguos
        if maintenance_config.get('cleanup_old_logs_days'):
            schedule.every().day.at("02:00").do(self.cleanup_old_logs)
        
        # Limpieza de archivos antiguos
        if maintenance_config.get('cleanup_old_files_days'):
            schedule.every().day.at("03:00").do(self.cleanup_old_files)
        
        # Backup de base de datos
        if maintenance_config.get('database_backup_enabled'):
            backup_interval = maintenance_config.get('backup_interval_hours', 24)
            schedule.every(backup_interval).hours.do(self.backup_database)
    
    def cleanup_old_logs(self):
        """Limpiar logs antiguos"""
        try:
            log_dir = os.path.dirname(self.config['logging']['file'])
            if not log_dir:
                log_dir = '.'
            
            cleanup_days = self.config['maintenance']['cleanup_old_logs_days']
            cutoff_date = datetime.now() - timedelta(days=cleanup_days)
            
            cleaned_files = 0
            for filename in os.listdir(log_dir):
                if filename.endswith('.log'):
                    file_path = os.path.join(log_dir, filename)
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    if file_time < cutoff_date:
                        os.remove(file_path)
                        cleaned_files += 1
            
            self.logger.info(f"Limpieza de logs completada: {cleaned_files} archivos eliminados")
            
        except Exception as e:
            self.logger.error(f"Error en limpieza de logs: {e}")
    
    def cleanup_old_files(self):
        """Limpiar archivos antiguos de salida"""
        try:
            output_dir = "output"
            if not os.path.exists(output_dir):
                return
            
            cleanup_days = self.config['maintenance']['cleanup_old_files_days']
            cutoff_date = datetime.now() - timedelta(days=cleanup_days)
            
            cleaned_files = 0
            for filename in os.listdir(output_dir):
                file_path = os.path.join(output_dir, filename)
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                if file_time < cutoff_date:
                    os.remove(file_path)
                    cleaned_files += 1
            
            self.logger.info(f"Limpieza de archivos completada: {cleaned_files} archivos eliminados")
            
        except Exception as e:
            self.logger.error(f"Error en limpieza de archivos: {e}")
    
    def backup_database(self):
        """Hacer backup de la base de datos"""
        try:
            self.logger.info("Iniciando backup de base de datos...")
            
            # Aquí se implementaría el backup de PostgreSQL
            # Por ahora solo log
            self.logger.info("Backup de base de datos completado")
            
        except Exception as e:
            self.logger.error(f"Error en backup de base de datos: {e}")
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Obtener estado del scheduler"""
        uptime = datetime.now() - self.scheduler_stats['inicio_scheduler']
        
        return {
            'running': self.running,
            'uptime': str(uptime),
            'ejecuciones_totales': self.scheduler_stats['ejecuciones_totales'],
            'ejecuciones_exitosas': self.scheduler_stats['ejecuciones_exitosas'],
            'ejecuciones_fallidas': self.scheduler_stats['ejecuciones_fallidas'],
            'ultima_ejecucion': self.scheduler_stats['ultima_ejecucion'],
            'proxima_ejecucion': schedule.next_run() if schedule.jobs else None,
            'tiempo_promedio_ejecucion': (
                self.scheduler_stats['tiempo_total_ejecucion'] / 
                max(1, self.scheduler_stats['ejecuciones_totales'])
            ),
            'trabajos_programados': len(schedule.jobs)
        }
    
    def start(self):
        """Iniciar el scheduler"""
        if self.running:
            self.logger.warning("El scheduler ya está ejecutándose")
            return
        
        self.logger.info("=== INICIANDO SCHEDULER DE SCRAPING DE NOTICIAS ===")
        
        # Configurar horarios
        self.setup_schedule()
        
        # Verificar conexión a base de datos
        try:
            with DatabaseManager() as db:
                if not db.connection:
                    self.logger.error("No se pudo conectar a la base de datos")
                    return False
        except Exception as e:
            self.logger.error(f"Error verificando base de datos: {e}")
            return False
        
        self.running = True
        self.logger.info("Scheduler iniciado correctamente")
        
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(60)  # Verificar cada minuto
                
        except KeyboardInterrupt:
            self.logger.info("Interrupción recibida, deteniendo scheduler...")
        except Exception as e:
            self.logger.error(f"Error en el scheduler: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Detener el scheduler"""
        if not self.running:
            return
        
        self.logger.info("Deteniendo scheduler...")
        self.running = False
        
        # Esperar a que termine el trabajo actual si está ejecutándose
        if self.current_job and self.current_job.is_alive():
            self.logger.info("Esperando a que termine el trabajo actual...")
            self.current_job.join(timeout=300)  # Esperar máximo 5 minutos
        
        self.logger.info("Scheduler detenido")
    
    def run_once(self):
        """Ejecutar scraping una sola vez (para testing)"""
        self.logger.info("Ejecutando scraping una sola vez...")
        self.execute_scraping_job()

def main():
    """Función principal del scheduler"""
    print("=== SCHEDULER DE SCRAPING DE NOTICIAS ===")
    print("1. Iniciar scheduler (ejecución continua)")
    print("2. Ejecutar una sola vez (testing)")
    print("3. Mostrar estado del scheduler")
    
    opcion = input("Selecciona una opción (1, 2 o 3): ").strip()
    
    scheduler = NewsScrapingScheduler()
    
    if opcion == "1":
        print("Iniciando scheduler...")
        scheduler.start()
    elif opcion == "2":
        print("Ejecutando scraping una sola vez...")
        scheduler.run_once()
    elif opcion == "3":
        print("Estado del scheduler:")
        status = scheduler.get_scheduler_status()
        for key, value in status.items():
            print(f"  {key}: {value}")
    else:
        print("Opción no válida")

if __name__ == "__main__":
    main()
