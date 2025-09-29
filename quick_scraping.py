#!/usr/bin/env python3
"""
Script rápido para ejecutar scraping con logs detallados
"""

import logging
import sys
from datetime import datetime

# Configurar logging detallado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Ejecutar scraping con logs detallados"""
    try:
        logger.info("🚀 INICIANDO SCRAPING RÁPIDO")
        logger.info("=" * 50)
        
        # Importar scraper unificado
        from unified_scraper import UnifiedNewsScraper

        # Crear instancia
        scraper = UnifiedNewsScraper()
        
        # Configurar logging detallado
        scraper.setup_detailed_logging()
        
        # Ejecutar scraping de Pachamama (más rápido)
        logger.info("📰 Iniciando scraping de Pachamama...")
        scraper.scrape_single_source('pachamama')
        
        # Obtener noticias
        noticias = scraper.get_news_by_source('pachamama')
        
        logger.info(f"✅ Pachamama: {len(noticias)} noticias extraídas")
        
        # Mostrar algunas noticias
        for i, noticia in enumerate(noticias[:5]):
            logger.info(f"   {i+1}. {noticia.get('titulo', 'Sin título')}")
        
        if len(noticias) > 5:
            logger.info(f"   ... y {len(noticias) - 5} noticias más")
        
        # Verificar base de datos
        try:
            from database import DatabaseManager
            with DatabaseManager() as db:
                if db.connection:
                    stats = db.get_estadisticas()
                    logger.info(f"📊 Total noticias en BD: {stats.get('total_noticias', 0)}")
        except Exception as e:
            logger.error(f"Error verificando BD: {e}")
        
        logger.info("🎉 SCRAPING COMPLETADO")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
