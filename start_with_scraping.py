#!/usr/bin/env python3
"""
Script que inicia scraping inmediatamente al levantar el contenedor
"""

import logging
import os
import sys
import time
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def wait_for_database():
    """Esperar a que la base de datos esté lista"""
    logger.info("⏳ Esperando conexión a PostgreSQL...")
    
    max_attempts = 30
    attempt = 0
    
    while attempt < max_attempts:
        try:
            from database import DatabaseManager
            with DatabaseManager() as db:
                if db.connection:
                    logger.info("✅ PostgreSQL conectado exitosamente")
                    return True
        except Exception as e:
            logger.info(f"Intento {attempt + 1}/{max_attempts}: {e}")
            time.sleep(2)
            attempt += 1
    
    logger.error("❌ No se pudo conectar a PostgreSQL después de 60 segundos")
    return False

def start_immediate_scraping():
    """Iniciar scraping inmediatamente"""
    try:
        logger.info("🚀 INICIANDO SCRAPING INMEDIATO AL LEVANTAR CONTENEDOR")
        logger.info("=" * 60)
        
        # Esperar base de datos
        if not wait_for_database():
            logger.error("❌ No se puede continuar sin base de datos")
            return False
        
        # Importar scraper unificado
        from unified_scraper import UnifiedNewsScraper

        # Crear instancia
        scraper = UnifiedNewsScraper()
        
        # Configurar logging detallado
        scraper.setup_detailed_logging()
        
        # Ejecutar scraping completo
        logger.info("📰 Ejecutando scraping completo de todas las fuentes...")
        scraper.run_full_scrape()
        
        # Obtener estadísticas
        stats = scraper.get_scraping_stats()
        
        logger.info(f"✅ Scraping inicial completado: {stats}")
        
        # Verificar base de datos
        try:
            from database import DatabaseManager
            with DatabaseManager() as db:
                if db.connection:
                    total = db.get_estadisticas()
                    logger.info(f"📊 Total noticias en BD: {total.get('total_noticias', 0)}")
                    
                    # Mostrar por fuente
                    sources = total.get('noticias_por_fuente', {})
                    if sources:
                        logger.info("📰 Noticias por fuente:")
                        for fuente, cantidad in sources.items():
                            logger.info(f"   {fuente}: {cantidad}")
        except Exception as e:
            logger.error(f"Error verificando BD: {e}")
        
        logger.info("🎉 SCRAPING INICIAL COMPLETADO - INICIANDO CELERY WORKER")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en scraping inicial: {e}")
        return False

def main():
    """Función principal"""
    print("🚀 INICIADOR DE SCRAPING + CELERY WORKER")
    print("=" * 50)
    
    # Ejecutar scraping inicial
    success = start_immediate_scraping()
    
    if success:
        logger.info("✅ Scraping inicial completado, iniciando Celery Worker...")
        
        # Iniciar Celery Worker
        import subprocess
        import sys
        
        try:
            # Comando para iniciar Celery Worker
            cmd = [
                "celery", "-A", "celery_tasks", "worker", 
                "--loglevel=info", 
                "--concurrency=4", 
                "--queues=scraping,processing,database"
            ]
            
            logger.info(f"🔄 Iniciando Celery Worker: {' '.join(cmd)}")
            subprocess.run(cmd)
            
        except Exception as e:
            logger.error(f"❌ Error iniciando Celery Worker: {e}")
    else:
        logger.error("❌ Error en scraping inicial, no se iniciará Celery Worker")

if __name__ == "__main__":
    main()
