#!/usr/bin/env python3
"""
Script para ejecutar scraping con logs detallados
"""

import logging
import os
import sys
import time
from datetime import datetime

# Configurar logging detallado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scraping_detailed.log')
    ]
)
logger = logging.getLogger(__name__)

def run_scraping_with_detailed_logs():
    """Ejecutar scraping con logs detallados"""
    try:
        logger.info("🚀 INICIANDO SCRAPING CON LOGS DETALLADOS")
        logger.info("=" * 60)
        
        # Importar scraper unificado
        from unified_scraper import UnifiedNewsScraper

        # Crear instancia
        scraper = UnifiedNewsScraper()
        
        # Configurar logging del scraper
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
        logger.info("=" * 60)
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
        
        logger.info("🎉 SCRAPING COMPLETADO")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error general en scraping: {e}")
        return False

def run_single_source_with_logs(source_name):
    """Ejecutar scraping de una fuente con logs detallados"""
    try:
        logger.info(f"🚀 INICIANDO SCRAPING DE {source_name.upper()}")
        logger.info("=" * 50)
        
        from unified_scraper import UnifiedNewsScraper
        scraper = UnifiedNewsScraper()
        
        # Configurar logging detallado
        scraper.setup_detailed_logging()
        
        # Scraping de una fuente
        scraper.scrape_single_source(source_name)
        
        # Obtener noticias
        noticias = scraper.get_news_by_source(source_name)
        
        logger.info(f"✅ {source_name.upper()}: {len(noticias)} noticias extraídas")
        
        # Mostrar todas las noticias
        for i, noticia in enumerate(noticias):
            logger.info(f"   {i+1}. {noticia.get('titulo', 'Sin título')}")
            logger.info(f"      URL: {noticia.get('url', 'N/A')}")
            logger.info(f"      Fecha: {noticia.get('fecha', 'N/A')}")
            logger.info("")
        
        return len(noticias)
        
    except Exception as e:
        logger.error(f"❌ Error en scraping de {source_name}: {e}")
        return 0

def main():
    """Función principal"""
    print("🚀 SCRAPING CON LOGS DETALLADOS")
    print("=" * 50)
    
    print("Opciones:")
    print("1. Scraping completo (todas las fuentes)")
    print("2. Scraping de Pachamama")
    print("3. Scraping de Los Andes")
    print("4. Scraping de Puno Noticias")
    print("5. Scraping de Diario Sin Fronteras")
    
    opcion = input("\nSelecciona una opción (1-5): ").strip()
    
    if opcion == "1":
        print("\n🚀 Ejecutando scraping completo...")
        success = run_scraping_with_detailed_logs()
        print(f"\nResultado: {'✅ Éxito' if success else '❌ Error'}")
    
    elif opcion == "2":
        print("\n🚀 Ejecutando scraping de Pachamama...")
        count = run_single_source_with_logs('pachamama')
        print(f"\nResultado: {count} noticias extraídas")
    
    elif opcion == "3":
        print("\n🚀 Ejecutando scraping de Los Andes...")
        count = run_single_source_with_logs('los_andes')
        print(f"\nResultado: {count} noticias extraídas")
    
    elif opcion == "4":
        print("\n🚀 Ejecutando scraping de Puno Noticias...")
        count = run_single_source_with_logs('puno_noticias')
        print(f"\nResultado: {count} noticias extraídas")
    
    elif opcion == "5":
        print("\n🚀 Ejecutando scraping de Diario Sin Fronteras...")
        count = run_single_source_with_logs('diario_sin_fronteras')
        print(f"\nResultado: {count} noticias extraídas")
    
    else:
        print("❌ Opción no válida")

if __name__ == "__main__":
    main()
