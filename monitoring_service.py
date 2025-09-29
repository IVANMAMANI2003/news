#!/usr/bin/env python3
"""
Servicio de monitoreo automático para el sistema de scraping
"""

import logging
import os
import signal
import sys
import time
from datetime import datetime

from monitoring import ScrapingMonitor

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/monitoring_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MonitoringService:
    def __init__(self):
        self.monitor = ScrapingMonitor()
        self.running = False
        self.interval = 300  # 5 minutos
        
    def signal_handler(self, signum, frame):
        """Manejar señales de interrupción"""
        logger.info(f"Recibida señal {signum}, deteniendo servicio...")
        self.running = False
    
    def run_monitoring_cycle(self):
        """Ejecutar un ciclo de monitoreo"""
        try:
            logger.info("🔍 Iniciando ciclo de monitoreo...")
            
            # Ejecutar monitoreo
            data = self.monitor.run_monitoring_cycle()
            
            # Guardar reporte
            self.monitor.save_status_report()
            
            # Log de resultados
            logger.info(f"✅ Monitoreo completado - Salud: {data['system_health']}")
            
            # Verificar alertas
            self.check_alerts(data)
            
        except Exception as e:
            logger.error(f"❌ Error en ciclo de monitoreo: {e}")
    
    def check_alerts(self, data):
        """Verificar alertas del sistema"""
        try:
            # Alertas de sitios web
            unavailable_sites = []
            for source_id, source_data in data.get('sources_status', {}).items():
                if not source_data['status']['available']:
                    unavailable_sites.append(source_data['name'])
            
            if unavailable_sites:
                logger.warning(f"⚠️ Sitios no disponibles: {', '.join(unavailable_sites)}")
            
            # Alertas de base de datos
            if not data.get('database_status', False):
                logger.error("❌ Base de datos no disponible")
            
            # Alertas de recursos del sistema
            resources = data.get('system_resources', {})
            if 'error' not in resources:
                cpu = resources.get('cpu_percent', 0)
                memory = resources.get('memory_percent', 0)
                disk = resources.get('disk_percent', 0)
                
                if cpu > 90:
                    logger.warning(f"⚠️ CPU alto: {cpu:.1f}%")
                if memory > 90:
                    logger.warning(f"⚠️ Memoria alta: {memory:.1f}%")
                if disk > 90:
                    logger.warning(f"⚠️ Disco lleno: {disk:.1f}%")
            
            # Alerta de salud general
            health = data.get('system_health', 'unknown')
            if health == 'critical':
                logger.error("🚨 ALERTA CRÍTICA: Sistema en estado crítico")
            elif health == 'warning':
                logger.warning("⚠️ ALERTA: Sistema en estado de advertencia")
            
        except Exception as e:
            logger.error(f"Error verificando alertas: {e}")
    
    def start(self):
        """Iniciar el servicio de monitoreo"""
        logger.info("🚀 Iniciando servicio de monitoreo...")
        
        # Configurar manejo de señales
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        self.running = True
        
        # Crear directorios necesarios
        os.makedirs('logs', exist_ok=True)
        os.makedirs('data', exist_ok=True)
        
        logger.info(f"⏰ Monitoreo cada {self.interval} segundos")
        logger.info("🛑 Presiona Ctrl+C para detener")
        
        try:
            while self.running:
                self.run_monitoring_cycle()
                
                # Esperar hasta el próximo ciclo
                for _ in range(self.interval):
                    if not self.running:
                        break
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            logger.info("🛑 Servicio detenido por el usuario")
        except Exception as e:
            logger.error(f"❌ Error en servicio: {e}")
        finally:
            self.running = False
            logger.info("✅ Servicio de monitoreo detenido")

def main():
    """Función principal"""
    print("🔍 SERVICIO DE MONITOREO AUTOMÁTICO")
    print("=" * 50)
    
    service = MonitoringService()
    
    print("Opciones:")
    print("1. Iniciar servicio de monitoreo")
    print("2. Ejecutar monitoreo una vez")
    print("3. Verificar configuración")
    
    opcion = input("\nSelecciona una opción (1-3): ").strip()
    
    if opcion == "1":
        service.start()
    elif opcion == "2":
        print("\n🔍 Ejecutando monitoreo una vez...")
        service.run_monitoring_cycle()
        print("✅ Monitoreo completado")
    elif opcion == "3":
        print("\n🔍 Verificando configuración...")
        
        # Verificar directorios
        os.makedirs('logs', exist_ok=True)
        os.makedirs('data', exist_ok=True)
        print("✅ Directorios creados")
        
        # Verificar monitoreo
        monitor = ScrapingMonitor()
        print("✅ Monitor inicializado")
        
        # Verificar base de datos
        db_status = monitor.check_database_health()
        print(f"✅ Base de datos: {'OK' if db_status else 'Error'}")
        
        print("\n✅ Configuración verificada")
    else:
        print("❌ Opción no válida")

if __name__ == "__main__":
    main()
