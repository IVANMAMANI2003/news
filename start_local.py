#!/usr/bin/env python3
"""
Script para iniciar el sistema de scraping local con Redis y Celery
"""

import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LocalScrapingSystem:
    def __init__(self):
        self.processes = []
        self.running = False
    
    def check_redis(self):
        """Verificar si Redis está ejecutándose"""
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, db=0)
            r.ping()
            logger.info("✅ Redis está ejecutándose")
            return True
        except Exception as e:
            logger.error(f"❌ Redis no está ejecutándose: {e}")
            return False
    
    def start_redis(self):
        """Iniciar Redis localmente"""
        try:
            logger.info("🚀 Iniciando Redis...")
            
            # Intentar iniciar Redis
            if os.name == 'nt':  # Windows
                # En Windows, Redis debe estar instalado como servicio
                logger.info("⚠️ En Windows, asegúrate de que Redis esté instalado y ejecutándose")
                logger.info("   Descarga desde: https://github.com/microsoftarchive/redis/releases")
                return False
            else:  # Linux/Mac
                process = subprocess.Popen(['redis-server'], 
                                        stdout=subprocess.PIPE, 
                                        stderr=subprocess.PIPE)
                self.processes.append(process)
                time.sleep(2)
                
                if self.check_redis():
                    logger.info("✅ Redis iniciado correctamente")
                    return True
                else:
                    logger.error("❌ Error iniciando Redis")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Error iniciando Redis: {e}")
            return False
    
    def start_celery_worker(self):
        """Iniciar worker de Celery"""
        try:
            logger.info("🚀 Iniciando Celery worker...")
            
            cmd = [
                sys.executable, '-m', 'celery', 
                '-A', 'celery_tasks', 
                'worker', 
                '--loglevel=info',
                '--concurrency=4',
                '--queues=scraping,processing,database'
            ]
            
            process = subprocess.Popen(cmd, 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.PIPE)
            self.processes.append(process)
            
            logger.info("✅ Celery worker iniciado")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error iniciando Celery worker: {e}")
            return False
    
    def start_celery_beat(self):
        """Iniciar beat scheduler de Celery"""
        try:
            logger.info("🚀 Iniciando Celery beat...")
            
            cmd = [
                sys.executable, '-m', 'celery', 
                '-A', 'celery_tasks', 
                'beat', 
                '--loglevel=info'
            ]
            
            process = subprocess.Popen(cmd, 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.PIPE)
            self.processes.append(process)
            
            logger.info("✅ Celery beat iniciado")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error iniciando Celery beat: {e}")
            return False
    
    def start_flower(self):
        """Iniciar Flower para monitoreo"""
        try:
            logger.info("🚀 Iniciando Flower...")
            
            cmd = [
                sys.executable, '-m', 'celery', 
                '-A', 'celery_tasks', 
                'flower', 
                '--port=5555'
            ]
            
            process = subprocess.Popen(cmd, 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.PIPE)
            self.processes.append(process)
            
            logger.info("✅ Flower iniciado en http://localhost:5555")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error iniciando Flower: {e}")
            return False
    
    def start_system(self):
        """Iniciar todo el sistema"""
        logger.info("🚀 INICIANDO SISTEMA DE SCRAPING LOCAL")
        logger.info("=" * 60)
        
        # Verificar Redis
        if not self.check_redis():
            logger.info("⚠️ Redis no está ejecutándose. Intentando iniciar...")
            if not self.start_redis():
                logger.error("❌ No se pudo iniciar Redis. Instala Redis primero.")
                return False
        
        # Verificar base de datos
        try:
            from database import DatabaseManager
            with DatabaseManager() as db:
                if not db.connection:
                    logger.error("❌ No se pudo conectar a PostgreSQL")
                    return False
            logger.info("✅ PostgreSQL conectado")
        except Exception as e:
            logger.error(f"❌ Error conectando a PostgreSQL: {e}")
            return False
        
        # Iniciar servicios
        services_started = 0
        
        if self.start_celery_worker():
            services_started += 1
        
        if self.start_celery_beat():
            services_started += 1
        
        if self.start_flower():
            services_started += 1
        
        if services_started == 3:
            self.running = True
            logger.info("🎉 Sistema iniciado correctamente")
            logger.info("📊 Monitoreo: http://localhost:5555")
            logger.info("💾 Base de datos: PostgreSQL")
            logger.info("🔄 Cache: Redis")
            return True
        else:
            logger.error(f"❌ Solo {services_started}/3 servicios iniciados")
            return False
    
    def stop_system(self):
        """Detener todo el sistema"""
        logger.info("🛑 Deteniendo sistema...")
        
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                try:
                    process.kill()
                except:
                    pass
        
        self.processes.clear()
        self.running = False
        logger.info("✅ Sistema detenido")
    
    def signal_handler(self, signum, frame):
        """Manejar señales de interrupción"""
        logger.info(f"Recibida señal {signum}, deteniendo sistema...")
        self.stop_system()
        sys.exit(0)

def main():
    """Función principal"""
    print("🚀 SISTEMA DE SCRAPING LOCAL CON REDIS Y CELERY")
    print("=" * 60)
    
    system = LocalScrapingSystem()
    
    # Configurar manejo de señales
    signal.signal(signal.SIGINT, system.signal_handler)
    signal.signal(signal.SIGTERM, system.signal_handler)
    
    print("Opciones:")
    print("1. Iniciar sistema completo")
    print("2. Solo verificar servicios")
    print("3. Ejecutar scraping manual")
    
    opcion = input("\nSelecciona una opción (1-3): ").strip()
    
    if opcion == "1":
        if system.start_system():
            print("\n✅ Sistema iniciado correctamente")
            print("📊 Monitoreo: http://localhost:5555")
            print("🔄 El sistema ejecutará scraping cada hora automáticamente")
            print("⏹️ Presiona Ctrl+C para detener")
            
            try:
                while system.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                system.stop_system()
        else:
            print("❌ Error iniciando el sistema")
    
    elif opcion == "2":
        print("\n🔍 Verificando servicios...")
        
        if system.check_redis():
            print("✅ Redis: OK")
        else:
            print("❌ Redis: No disponible")
        
        try:
            from database import DatabaseManager
            with DatabaseManager() as db:
                if db.connection:
                    print("✅ PostgreSQL: OK")
                else:
                    print("❌ PostgreSQL: No disponible")
        except:
            print("❌ PostgreSQL: Error")
    
    elif opcion == "3":
        print("\n🚀 Ejecutando scraping manual...")
        
        if not system.check_redis():
            print("❌ Redis no está ejecutándose")
            return
        
        try:
            from celery_client import CeleryScrapingClient
            client = CeleryScrapingClient()
            
            print("Iniciando scraping de todas las fuentes...")
            task_ids = client.start_scraping_all_sources()
            
            if task_ids:
                print(f"✅ {len(task_ids)} tareas iniciadas")
                print("👀 Monitoreando progreso...")
                
                results = client.monitor_tasks(timeout=1800)
                
                print(f"\n📊 RESULTADOS:")
                print(f"✅ Completadas: {len(results['completed'])}")
                print(f"❌ Fallidas: {len(results['failed'])}")
                print(f"⏱️ Duración: {results['total_duration']:.2f}s")
            else:
                print("❌ No se pudieron iniciar tareas")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    else:
        print("❌ Opción no válida")

if __name__ == "__main__":
    main()
