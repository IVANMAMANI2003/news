"""
Módulo de scrapers para diferentes fuentes de noticias
"""
from .diario_sin_fronteras_scraper import DiarioSinFronterasScraper
from .los_andes_scraper import LosAndesScraper
from .pachamama_scraper import PachamamaScraper
from .puno_noticias_scraper import PunoNoticiasScraper

__all__ = [
    'DiarioSinFronterasScraper',
    'LosAndesScraper', 
    'PachamamaScraper',
    'PunoNoticiasScraper'
]
