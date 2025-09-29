#!/usr/bin/env python3
"""
Script para monitorear el scraping en tiempo real
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

def monitor_scraping():
    """Monitorear scraping en tiempo real"""
    try:
        logger.info("👀 INICIANDO MONITOREO DE SCRAPING")
        logger.info("=" * 50)
        
        from database import DatabaseManager
        
        previous_count = 0
        start_time = datetime.now()
        
        while True:
            try:
                # Verificar base de datos
                with DatabaseManager() as db:
                    if db.connection:
                        stats = db.get_estadisticas()
                        current_count = stats.get('total_noticias', 0)
                        
                        # Calcular noticias nuevas
                        new_news = current_count - previous_count
                        
                        if new_news > 0:
                            logger.info(f"📈 +{new_news} noticias nuevas! Total: {current_count}")
                        else:
                            logger.info(f"📊 Total noticias: {current_count}")
                        
                        # Mostrar por fuente
                        sources = stats.get('noticias_por_fuente', {})
                        if sources:
                            logger.info("📰 Por fuente:")
                            for fuente, cantidad in sources.items():
                                logger.info(f"   {fuente}: {cantidad}")
                        
                        previous_count = current_count
                        
                        # Verificar archivos
                        import os
                        data_dir = 'data'
                        if os.path.exists(data_dir):
                            files = [f for f in os.listdir(data_dir) if f.endswith(('.csv', '.json'))]
                            if files:
                                logger.info(f"📁 Archivos generados: {len(files)}")
                
                # Tiempo transcurrido
                elapsed = datetime.now() - start_time
                logger.info(f"⏱️ Tiempo transcurrido: {elapsed}")
                logger.info("-" * 40)
                
                time.sleep(30)  # Verificar cada 30 segundos
                
            except Exception as e:
                logger.error(f"Error en monitoreo: {e}")
                time.sleep(10)
                
    except KeyboardInterrupt:
        logger.info("🛑 Monitoreo detenido por usuario")
    except Exception as e:
        logger.error(f"❌ Error en monitoreo: {e}")

def main():
    """Función principal"""
    print("👀 MONITOR DE SCRAPING")
    print("=" * 30)
    print("Presiona Ctrl+C para detener")
    print("")
    
    monitor_scraping()

if __name__ == "__main__":
    main()
