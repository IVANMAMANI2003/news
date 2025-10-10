#!/usr/bin/env python3
"""
Script para probar scraping completo localmente sin Celery
"""

import logging
import os
import sys
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraping_test.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def test_pachamama_scraping():
    """Probar scraping de Pachamama"""
    try:
        logger.info("=== INICIANDO SCRAPING PACHAMAMA ===")
        from scrapers.pachamama_scraper import PachamamaRadioScraper
        
        scraper = PachamamaRadioScraper()
        logger.info("Ejecutando scraping recursivo con max_depth=15...")
        scraper.scrape_recursivo(max_depth=15)
        
        noticias = scraper.news_data
        logger.info(f"✅ Pachamama: {len(noticias)} noticias extraídas")
        
        # Mostrar algunas noticias
        for i, noticia in enumerate(noticias[:3]):
            logger.info(f"  {i+1}. {noticia.get('titulo', 'Sin título')[:50]}...")
        
        return len(noticias)
    except Exception as e:
        logger.error(f"❌ Error en Pachamama: {e}")
        return 0

def test_los_andes_scraping():
    """Probar scraping de Los Andes"""
    try:
        logger.info("=== INICIANDO SCRAPING LOS ANDES ===")
        from scrapers.los_andes_scraper import LosAndesScraper
        
        scraper = LosAndesScraper()
        logger.info("Ejecutando scraping completo sin límites...")
        scraper.scrape_noticias(max_noticias=None)
        
        noticias = scraper.news_data
        logger.info(f"✅ Los Andes: {len(noticias)} noticias extraídas")
        
        # Mostrar algunas noticias
        for i, noticia in enumerate(noticias[:3]):
            logger.info(f"  {i+1}. {noticia.get('titulo', 'Sin título')[:50]}...")
        
        return len(noticias)
    except Exception as e:
        logger.error(f"❌ Error en Los Andes: {e}")
        return 0

def test_puno_noticias_scraping():
    """Probar scraping de Puno Noticias"""
    try:
        logger.info("=== INICIANDO SCRAPING PUNO NOTICIAS ===")
        from scrapers.puno_noticias_scraper import PunoNoticiasScraper
        
        scraper = PunoNoticiasScraper()
        logger.info("Ejecutando scraping completo...")
        scraper.scrape_all_news()
        
        noticias = scraper.news_data
        logger.info(f"✅ Puno Noticias: {len(noticias)} noticias extraídas")
        
        # Mostrar algunas noticias
        for i, noticia in enumerate(noticias[:3]):
            logger.info(f"  {i+1}. {noticia.get('titulo', 'Sin título')[:50]}...")
        
        return len(noticias)
    except Exception as e:
        logger.error(f"❌ Error en Puno Noticias: {e}")
        return 0

def main():
    """Función principal"""
    logger.info("🚀 INICIANDO SCRAPING COMPLETO LOCAL")
    logger.info(f"Fecha y hora: {datetime.now()}")
    
    total_noticias = 0
    
    # Probar cada scraper
    total_noticias += test_pachamama_scraping()
    total_noticias += test_los_andes_scraping()
    total_noticias += test_puno_noticias_scraping()
    
    # Resumen final
    logger.info("=" * 50)
    logger.info(f"🎯 SCRAPING COMPLETO FINALIZADO")
    logger.info(f"📊 Total de noticias extraídas: {total_noticias}")
    logger.info(f"📁 Logs guardados en: scraping_test.log")
    logger.info("=" * 50)

if __name__ == "__main__":
    main()
