#!/usr/bin/env python3
"""
Script para forzar scraping inmediatamente
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

def force_scraping():
    """Forzar scraping inmediatamente"""
    try:
        logger.info("🚀 FORZANDO SCRAPING INMEDIATO")
        logger.info("=" * 50)
        
        # Importar scraper unificado
        from unified_scraper import UnifiedNewsScraper

        # Crear instancia
        scraper = UnifiedNewsScraper()
        
        # Configurar logging detallado
        scraper.setup_detailed_logging()
        
        # Ejecutar scraping completo
        logger.info("📰 Ejecutando scraping completo...")
        scraper.run_full_scrape()
        
        # Obtener estadísticas
        stats = scraper.get_scraping_stats()
        
        logger.info(f"✅ Scraping completado: {stats}")
        
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
                        logger.info("📰 Por fuente:")
                        for fuente, cantidad in sources.items():
                            logger.info(f"   {fuente}: {cantidad}")
        except Exception as e:
            logger.error(f"Error verificando BD: {e}")
        
        logger.info("🎉 SCRAPING FORZADO COMPLETADO")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en scraping forzado: {e}")
        return False

def main():
    """Función principal"""
    print("🚀 FORZADOR DE SCRAPING")
    print("=" * 30)
    
    success = force_scraping()
    
    if success:
        print("✅ Scraping completado exitosamente")
    else:
        print("❌ Error en scraping")

if __name__ == "__main__":
    main()
