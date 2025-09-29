#!/usr/bin/env python3
"""
Script simple para probar scraping
"""

import logging
import os
import sys

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_scraping():
    """Probar scraping simple"""
    try:
        logger.info("🧪 PROBANDO SCRAPING SIMPLE")
        logger.info("=" * 40)
        
        # Importar scraper
        from unified_scraper import UnifiedNewsScraper

        # Crear instancia
        scraper = UnifiedNewsScraper()
        
        # Configurar logging detallado
        scraper.setup_detailed_logging()
        
        # Ejecutar solo Pachamama para prueba rápida
        logger.info("📰 Probando solo Pachamama Radio...")
        
        # Configurar para solo Pachamama
        scraper.config['sources'] = {
            'sin_fronteras': False,
            'los_andes': False,
            'pachamama': True,
            'puno_noticias': False
        }
        
        # Ejecutar scraping
        scraper.run_full_scrape()
        
        # Mostrar estadísticas
        stats = scraper.get_scraping_stats()
        logger.info(f"✅ Prueba completada: {stats}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en prueba: {e}")
        return False

if __name__ == "__main__":
    success = test_scraping()
    if success:
        print("✅ Prueba exitosa")
    else:
        print("❌ Prueba fallida")
        sys.exit(1)
