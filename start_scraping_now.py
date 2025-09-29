#!/usr/bin/env python3
"""
Script para iniciar scraping inmediatamente
"""

import logging
import time
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def start_immediate_scraping():
    """Iniciar scraping inmediatamente"""
    try:
        logger.info("🚀 INICIANDO SCRAPING INMEDIATO")
        logger.info("=" * 50)
        
        # Importar tareas de Celery
        from celery_tasks import scheduled_scraping, scrape_source

        # Enviar tareas inmediatamente
        logger.info("📤 Enviando tareas de scraping...")
        
        # Tarea completa
        task1 = scheduled_scraping.delay()
        logger.info(f"✅ Tarea completa enviada: {task1.id}")
        
        # Tarea de Pachamama
        task2 = scrape_source.delay('pachamama', {})
        logger.info(f"✅ Tarea Pachamama enviada: {task2.id}")
        
        # Tarea de Los Andes
        task3 = scrape_source.delay('los_andes', {})
        logger.info(f"✅ Tarea Los Andes enviada: {task3.id}")
        
        # Tarea de Puno Noticias
        task4 = scrape_source.delay('puno_noticias', {})
        logger.info(f"✅ Tarea Puno Noticias enviada: {task4.id}")
        
        # Tarea de Diario Sin Fronteras
        task5 = scrape_source.delay('diario_sin_fronteras', {})
        logger.info(f"✅ Tarea Diario Sin Fronteras enviada: {task5.id}")
        
        logger.info("🎉 Todas las tareas enviadas exitosamente")
        logger.info("📊 Monitorea el progreso en Flower: http://localhost:5555")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error enviando tareas: {e}")
        return False

def monitor_progress():
    """Monitorear progreso de las tareas"""
    try:
        from database import DatabaseManager
        
        logger.info("📊 Monitoreando progreso...")
        
        # Verificar base de datos cada 10 segundos
        for i in range(30):  # 5 minutos máximo
            try:
                with DatabaseManager() as db:
                    if db.connection:
                        stats = db.get_estadisticas()
                        total = stats.get('total_noticias', 0)
                        logger.info(f"📈 Noticias en BD: {total}")
                        
                        if total > 0:
                            logger.info("✅ ¡Scraping funcionando correctamente!")
                            break
            except Exception as e:
                logger.warning(f"Error verificando BD: {e}")
            
            time.sleep(10)
        
    except Exception as e:
        logger.error(f"Error monitoreando: {e}")

def main():
    """Función principal"""
    print("🚀 INICIADOR DE SCRAPING AUTOMÁTICO")
    print("=" * 50)
    
    # Iniciar scraping
    success = start_immediate_scraping()
    
    if success:
        print("\n📊 Monitoreando progreso...")
        monitor_progress()
    else:
        print("❌ Error iniciando scraping")

if __name__ == "__main__":
    main()
