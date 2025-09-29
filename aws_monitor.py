#!/usr/bin/env python3
"""
Monitor simple para AWS
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

def monitor():
    """Monitor simple"""
    try:
        logger.info("👀 MONITOR DE SCRAPING EN AWS")
        logger.info("=" * 40)
        
        from database import DatabaseManager
        
        while True:
            try:
                # Verificar base de datos
                with DatabaseManager() as db:
                    if db.connection:
                        stats = db.get_estadisticas()
                        total = stats.get('total_noticias', 0)
                        
                        logger.info(f"📊 Total noticias: {total}")
                        
                        # Mostrar por fuente
                        sources = stats.get('noticias_por_fuente', {})
                        if sources:
                            for fuente, cantidad in sources.items():
                                logger.info(f"   {fuente}: {cantidad}")
                        
                        # Verificar archivos
                        import os
                        data_dir = 'data'
                        if os.path.exists(data_dir):
                            files = [f for f in os.listdir(data_dir) if f.endswith(('.csv', '.json'))]
                            if files:
                                logger.info(f"📁 Archivos: {len(files)}")
                
                logger.info("-" * 40)
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"Error: {e}")
                time.sleep(10)
                
    except KeyboardInterrupt:
        logger.info("🛑 Monitor detenido")

if __name__ == "__main__":
    monitor()
