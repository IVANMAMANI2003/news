#!/usr/bin/env python3
"""
Script simple para probar el scraping
"""

import logging
import os
import sys
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_scraping():
    """Probar scraping directo"""
    try:
        logger.info("🚀 Iniciando prueba de scraping")
        
        # Importar scraper unificado
        from unified_scraper import UnifiedNewsScraper

        # Crear instancia
        scraper = UnifiedNewsScraper()
        
        # Ejecutar scraping completo
        logger.info("📰 Ejecutando scraping completo...")
        scraper.run_full_scrape()
        
        # Obtener estadísticas
        stats = scraper.get_scraping_stats()
        
        logger.info(f"✅ Scraping completado: {stats}")
        
        # Verificar base de datos
        from database import DatabaseManager
        with DatabaseManager() as db:
            if db.connection:
                total = db.get_estadisticas()
                logger.info(f"📊 Total noticias en BD: {total}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en scraping: {e}")
        return False

def test_single_source(source_name):
    """Probar scraping de una fuente específica"""
    try:
        logger.info(f"🚀 Iniciando scraping de {source_name}")
        
        from unified_scraper import UnifiedNewsScraper
        scraper = UnifiedNewsScraper()
        
        # Scraping de una fuente
        scraper.scrape_single_source(source_name)
        
        # Obtener noticias
        noticias = scraper.get_news_by_source(source_name)
        
        logger.info(f"✅ {source_name}: {len(noticias)} noticias extraídas")
        
        return len(noticias)
        
    except Exception as e:
        logger.error(f"❌ Error en scraping de {source_name}: {e}")
        return 0

def main():
    """Función principal"""
    print("🧪 PRUEBA DE SCRAPING")
    print("=" * 50)
    
    # Probar scraping de Pachamama
    print("1. Probando Pachamama...")
    count = test_single_source('pachamama')
    print(f"   Resultado: {count} noticias")
    
    # Probar scraping completo
    print("\n2. Probando scraping completo...")
    success = test_scraping()
    print(f"   Resultado: {'✅ Éxito' if success else '❌ Error'}")
    
    print("\n🎉 Prueba completada")

if __name__ == "__main__":
    main()
