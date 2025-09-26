"""
Scraper específico para Puno Noticias
"""
import logging
import re
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from base_scraper import BaseNewsScraper

logger = logging.getLogger(__name__)

class PunoNoticiasScraper(BaseNewsScraper):
    """Scraper para Puno Noticias"""
    
    def __init__(self):
        super().__init__(
            source_name="Puno Noticias",
            base_url="https://punonoticias.pe/",
            delay=1
        )
    
    def is_news_url(self, url: str) -> bool:
        """Verificar si URL es de noticia"""
        parsed = urlparse(url)
        if parsed.netloc != urlparse(self.base_url).netloc:
            return False
            
        # Patrones que indican noticias
        news_patterns = [
            r'/noticia/',
            r'/news/',
            r'/articulo/',
            r'/\d{4}/\d{2}/',  # Fecha en URL
            r'/[a-zA-Z-]+-\d+',  # Título con ID
        ]
        
        return any(re.search(pattern, url) for pattern in news_patterns)
    
    def extract_news_urls(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extraer URLs de noticias de una página"""
        news_urls = []
        
        # Patrones comunes para enlaces de noticias
        selectors = [
            'a[href*="/noticia/"]',
            'a[href*="/news/"]', 
            'a[href*="/articulo/"]',
            '.post-title a',
            '.entry-title a',
            '.news-title a',
            'h1 a', 'h2 a', 'h3 a',
            '.card a',
            '.item a'
        ]
        
        for selector in selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    if self.is_news_url(full_url):
                        news_urls.append(full_url)
        
        return list(set(news_urls))
    
    def extract_pagination_urls(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extraer URLs de paginación"""
        pagination_urls = []
        
        selectors = [
            '.pagination a',
            '.page-numbers a',
            '.pager a',
            'a[href*="page"]',
            'a[href*="pagina"]',
            '.next',
            '.siguiente'
        ]
        
        for selector in selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    pagination_urls.append(full_url)
        
        return list(set(pagination_urls))
    
    def extract_category_urls(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extraer URLs de categorías"""
        category_urls = []
        
        selectors = [
            '.menu a',
            '.nav a',
            '.categories a',
            '.category a',
            'nav a',
            '.main-menu a'
        ]
        
        for selector in selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    parsed = urlparse(full_url)
                    if parsed.netloc == urlparse(self.base_url).netloc:
                        category_urls.append(full_url)
        
        return list(set(category_urls))
    
    def discover_news_urls(self, max_pages: int = 50) -> List[str]:
        """Descubrir todas las URLs del sitio"""
        discovered_urls = set()
        to_visit = [self.base_url]
        visited = set()
        pages_processed = 0

        logger.info(f"[{self.source_name}] Iniciando descubrimiento de URLs...")

        while to_visit and pages_processed < max_pages:
            current_url = to_visit.pop(0)
            
            if current_url in visited:
                continue
                
            visited.add(current_url)
            logger.info(f"[{self.source_name}] Explorando: {current_url}")
            
            soup = self.make_request(current_url)
            if not soup:
                continue

            # Encontrar URLs de noticias
            news_urls = self.extract_news_urls(soup, current_url)
            discovered_urls.update(news_urls)
            
            # Encontrar páginas de paginación
            pagination_urls = self.extract_pagination_urls(soup, current_url)
            to_visit.extend([url for url in pagination_urls if url not in visited])
            
            # Encontrar URLs de categorías
            category_urls = self.extract_category_urls(soup, current_url)
            to_visit.extend([url for url in category_urls if url not in visited])
            
            pages_processed += 1

        logger.info(f"[{self.source_name}] Descubiertas {len(discovered_urls)} URLs de noticias")
        return list(discovered_urls)
    
    def extract_news_data(self, url: str) -> Optional[Dict]:
        """Extraer datos de una noticia específica"""
        try:
            soup = self.make_request(url)
            if not soup:
                return None

            # Extraer datos básicos
            titulo = self.extract_title(soup)
            fecha, hora = self.extract_date_time(soup)
            contenido = self.extract_content(soup)
            resumen = self.extract_summary(soup, contenido)
            categoria = self.extract_category(soup, url)
            autor = self.extract_author(soup)
            tags = self.extract_tags(soup)
            imagenes = self.extract_images(soup, url)

            return {
                'titulo': titulo,
                'fecha': fecha,
                'hora': hora,
                'resumen': resumen,
                'contenido': contenido,
                'categoria': categoria,
                'autor': autor,
                'tags': tags,
                'url': url,
                'link_imagenes': imagenes
            }

        except Exception as e:
            logger.error(f"[{self.source_name}] Error extrayendo datos de {url}: {e}")
            return None
