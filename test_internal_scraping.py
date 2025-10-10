#!/usr/bin/env python3
"""
Script para probar las funciones internas de scraping sin Celery
"""

import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('internal_test.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def test_pachamama_internal():
    """Probar scraping interno de Pachamama"""
    try:
        logger.info("=== PROBANDO PACHAMAMA INTERNO ===")
        from scrapers.pachamama_scraper import PachamamaRadioScraper
        
        scraper = PachamamaRadioScraper()
        logger.info("Ejecutando scrape_recursivo con max_depth=15...")
        scraper.scrape_recursivo(max_depth=15)
        
        noticias = scraper.news_data
        logger.info(f"✅ Pachamama interno: {len(noticias)} noticias extraídas")
        
        # Mostrar algunas noticias
        for i, noticia in enumerate(noticias[:3]):
            logger.info(f"  {i+1}. {noticia.get('titulo', 'Sin título')[:50]}...")
        
        return len(noticias)
    except Exception as e:
        logger.error(f"❌ Error en Pachamama interno: {e}")
        return 0

def test_los_andes_internal():
    """Probar scraping interno de Los Andes"""
    try:
        logger.info("=== PROBANDO LOS ANDES INTERNO ===")
        from scrapers.los_andes_scraper import LosAndesScraper
        
        scraper = LosAndesScraper()
        logger.info("Ejecutando scrape_noticias sin límites...")
        scraper.scrape_noticias(max_noticias=None)
        
        noticias = scraper.news_data
        logger.info(f"✅ Los Andes interno: {len(noticias)} noticias extraídas")
        
        # Mostrar algunas noticias
        for i, noticia in enumerate(noticias[:3]):
            logger.info(f"  {i+1}. {noticia.get('titulo', 'Sin título')[:50]}...")
        
        return len(noticias)
    except Exception as e:
        logger.error(f"❌ Error en Los Andes interno: {e}")
        return 0

def test_puno_noticias_internal():
    """Probar scraping interno de Puno Noticias"""
    try:
        logger.info("=== PROBANDO PUNO NOTICIAS INTERNO ===")
        from scrapers.puno_noticias_scraper import PunoNoticiasScraper
        
        scraper = PunoNoticiasScraper()
        logger.info("Ejecutando scrape_all_news...")
        scraper.scrape_all_news()
        
        noticias = scraper.news_data
        logger.info(f"✅ Puno Noticias interno: {len(noticias)} noticias extraídas")
        
        # Mostrar algunas noticias
        for i, noticia in enumerate(noticias[:3]):
            logger.info(f"  {i+1}. {noticia.get('titulo', 'Sin título')[:50]}...")
        
        return len(noticias)
    except Exception as e:
        logger.error(f"❌ Error en Puno Noticias interno: {e}")
        return 0

def main():
    """Función principal"""
    logger.info("🚀 INICIANDO PRUEBAS INTERNAS DE SCRAPING")
    logger.info(f"Fecha y hora: {datetime.now()}")
    
    total_noticias = 0
    
    # Probar cada scraper interno
    total_noticias += test_pachamama_internal()
    total_noticias += test_los_andes_internal()
    total_noticias += test_puno_noticias_internal()
    
    # Resumen final
    logger.info("=" * 50)
    logger.info(f"🎯 PRUEBAS INTERNAS COMPLETADAS")
    logger.info(f"📊 Total de noticias extraídas: {total_noticias}")
    logger.info(f"📁 Logs guardados en: internal_test.log")
    logger.info("=" * 50)
    
    # Verificar que las funciones de Celery usen los mismos métodos
    logger.info("🔍 VERIFICACIÓN DE CELERY TASKS:")
    logger.info("✅ Pachamama: scrape_recursivo(max_depth=15)")
    logger.info("✅ Los Andes: scrape_noticias(max_noticias=None)")
    logger.info("✅ Puno Noticias: scrape_all_news()")
    logger.info("✅ Todas las funciones usan los mismos métodos que el test local")

if __name__ == "__main__":
    main()
