#!/usr/bin/env python3
"""
Script para ejecutar el scraping completo de todas las fuentes
"""

import logging
import sys
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    print("🚀 INICIANDO SCRAPING COMPLETO DE TODAS LAS FUENTES")
    print("=" * 60)
    
    try:
        from unified_scraper import UnifiedNewsScraper

        # Crear scraper
        scraper = UnifiedNewsScraper()
        
        # Mostrar fuentes disponibles
        print(f"📰 Fuentes disponibles: {list(scraper.scrapers.keys())}")
        
        # Ejecutar scraping completo
        print("\n🔄 Iniciando scraping completo...")
        scraper.run_full_scraping()
        
        # Mostrar estadísticas finales
        print("\n📊 ESTADÍSTICAS FINALES:")
        print("-" * 40)
        
        from database import DatabaseManager
        with DatabaseManager() as db:
            stats = db.get_estadisticas()
            print(f"Total noticias en BD: {stats.get('total_noticias', 0)}")
            print("Por fuente:")
            for fuente, cantidad in stats.get('noticias_por_fuente', {}).items():
                print(f"  {fuente}: {cantidad}")
            
            # Mostrar últimas noticias
            print("\n📰 Últimas noticias extraídas:")
            noticias = db.get_noticias_recientes(10)
            for i, noticia in enumerate(noticias, 1):
                print(f"{i}. {noticia['titulo'][:60]}... ({noticia['fuente']})")
        
        print("\n✅ Scraping completado exitosamente!")
        
    except Exception as e:
        logger.error(f"Error durante el scraping: {e}")
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
