#!/usr/bin/env python3
"""
Script definitivo para AWS - Scraping directo sin Celery
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

def main():
    """Ejecutar scraping directo"""
    try:
        logger.info("🚀 INICIANDO SCRAPING EN AWS")
        logger.info("=" * 50)
        
        # Importar scraper unificado
        from unified_scraper import UnifiedNewsScraper

        # Crear instancia
        scraper = UnifiedNewsScraper()
        
        # Configurar logging detallado
        scraper.setup_detailed_logging()
        
        # Lista de fuentes
        sources = ['pachamama', 'los_andes', 'puno_noticias', 'diario_sin_fronteras']
        
        total_noticias = 0
        
        for source in sources:
            try:
                logger.info(f"📰 INICIANDO SCRAPING DE {source.upper()}")
                logger.info("-" * 40)
                
                # Scraping de una fuente
                scraper.scrape_single_source(source)
                
                # Obtener noticias
                noticias = scraper.get_news_by_source(source)
                
                logger.info(f"✅ {source.upper()}: {len(noticias)} noticias extraídas")
                total_noticias += len(noticias)
                
                # Mostrar algunas noticias
                for i, noticia in enumerate(noticias[:3]):
                    logger.info(f"   {i+1}. {noticia.get('titulo', 'Sin título')[:80]}...")
                
                if len(noticias) > 3:
                    logger.info(f"   ... y {len(noticias) - 3} noticias más")
                
                logger.info(f"✅ {source.upper()} completado")
                logger.info("")
                
            except Exception as e:
                logger.error(f"❌ Error en {source}: {e}")
                continue
        
        # Estadísticas finales
        logger.info("📊 ESTADÍSTICAS FINALES")
        logger.info("=" * 50)
        logger.info(f"Total noticias extraídas: {total_noticias}")
        
        # Verificar base de datos
        try:
            from database import DatabaseManager
            with DatabaseManager() as db:
                if db.connection:
                    stats = db.get_estadisticas()
                    logger.info(f"Total noticias en BD: {stats.get('total_noticias', 0)}")
                    logger.info("Por fuente:")
                    for fuente, cantidad in stats.get('noticias_por_fuente', {}).items():
                        logger.info(f"  {fuente}: {cantidad}")
        except Exception as e:
            logger.error(f"Error verificando BD: {e}")
        
        # Verificar archivos generados
        try:
            data_dir = 'data'
            if os.path.exists(data_dir):
                files = [f for f in os.listdir(data_dir) if f.endswith(('.csv', '.json'))]
                logger.info(f"📁 Archivos generados: {len(files)}")
                for file in files:
                    logger.info(f"   - {file}")
        except Exception as e:
            logger.error(f"Error verificando archivos: {e}")
        
        logger.info("🎉 SCRAPING COMPLETADO EXITOSAMENTE")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error general en scraping: {e}")
        return False

if __name__ == "__main__":
    main()
