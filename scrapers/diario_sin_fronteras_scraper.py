"""
Scraper específico para Diario Sin Fronteras
"""
import logging
import re
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from base_scraper import BaseNewsScraper

logger = logging.getLogger(__name__)

class DiarioSinFronterasScraper(BaseNewsScraper):
    """Scraper para Diario Sin Fronteras"""
    
    def __init__(self):
        super().__init__(
            source_name="Diario Sin Fronteras",
            base_url="https://diariosinfronteras.com.pe/",
            delay=2
        )
    
    def is_news_url(self, url: str) -> bool:
        """Determinar si una URL es un artículo de noticia"""
        # Patrones que indican que es un artículo
        article_patterns = [
            r'/\d{4}/',  # Contiene año
            r'/\d{4}/\d{2}/',  # Contiene año/mes
            r'-\d{4}-',  # Fecha en el slug
            r'\.html$',  # Termina en .html
        ]
        
        # Patrones que indican que NO es un artículo
        exclude_patterns = [
            r'/page/',
            r'/categoria/',
            r'/tag/',
            r'/author/',
            r'/search/',
            r'#',
            r'\?',
            r'/wp-',
            r'/feed',
            r'\.pdf$',
            r'\.jpg$',
            r'\.png$',
            r'\.gif$'
        ]
        
        # Verificar patrones de exclusión
        for pattern in exclude_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False
        
        # Verificar patrones de artículo
        for pattern in article_patterns:
            if re.search(pattern, url):
                return True
        
        # Si la URL pertenece al dominio y no está excluida, probablemente es un artículo
        return self.base_url in url
    
    def extract_news_urls(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extraer URLs de artículos de una página"""
        article_urls = set()
        
        # Diferentes selectores para encontrar enlaces de artículos
        selectors = [
            'article a[href]',
            '.entry-title a[href]',
            '.post-title a[href]',
            'h2 a[href]',
            'h3 a[href]',
            '.news-title a[href]',
            '.article-title a[href]',
            'a[href*="/2"]',  # URLs que contienen años
            '.content a[href]'
        ]
        
        for selector in selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    if self.is_news_url(full_url):
                        article_urls.add(full_url)
        
        return list(article_urls)
    
    def extract_pagination_urls(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extraer URLs de paginación"""
        pagination_urls = set()
        
        # Selectores comunes para paginación
        pagination_selectors = [
            '.pagination a[href]',
            '.page-numbers a[href]',
            '.nav-links a[href]',
            'a[href*="page"]',
            '.next-page a[href]',
            '.older-posts a[href]'
        ]
        
        for selector in pagination_selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href and ('page' in href.lower() or 'siguiente' in link.text.lower() or 'next' in link.text.lower()):
                    full_url = urljoin(base_url, href)
                    pagination_urls.add(full_url)
        
        return list(pagination_urls)
    
    def extract_category_urls(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extraer URLs de categorías"""
        category_urls = set()
        
        category_selectors = [
            '.menu a[href]',
            '.category a[href]',
            '.nav a[href]',
            'nav a[href]',
            '.categories a[href]'
        ]
        
        for selector in category_selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href and self.base_url in href:
                    full_url = urljoin(base_url, href)
                    if '/categoria' in full_url or '/category' in full_url:
                        category_urls.add(full_url)
        
        return list(category_urls)
    
    def discover_news_urls(self, max_pages: int = 50) -> List[str]:
        """Descubrir todas las URLs del sitio de forma recursiva"""
        logger.info(f"[{self.source_name}] Iniciando descubrimiento de URLs...")
        
        urls_to_visit = {self.base_url}
        all_article_urls = set()
        visited_urls = set()
        pages_processed = 0
        
        while urls_to_visit and pages_processed < max_pages:
            current_urls = list(urls_to_visit)[:10]  # Procesar en lotes
            urls_to_visit = set(list(urls_to_visit)[10:])
            
            for url in current_urls:
                if url in visited_urls:
                    continue
                
                logger.info(f"[{self.source_name}] Explorando: {url}")
                soup = self.make_request(url)
                if not soup:
                    continue
                
                # Extraer URLs de artículos
                article_urls = self.extract_news_urls(soup, url)
                all_article_urls.update(article_urls)
                
                # Extraer URLs de paginación y categorías para continuar explorando
                pagination_urls = self.extract_pagination_urls(soup, url)
                category_urls = self.extract_category_urls(soup, url)
                
                new_urls = set(pagination_urls + category_urls)
                for new_url in new_urls:
                    if new_url not in visited_urls:
                        urls_to_visit.add(new_url)
                
                visited_urls.add(url)
                pages_processed += 1
        
        logger.info(f"[{self.source_name}] Descubrimiento completado. Encontradas {len(all_article_urls)} URLs de artículos")
        return list(all_article_urls)
    
    def extract_news_data(self, url: str) -> Optional[Dict]:
        """Extraer datos de un artículo específico"""
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
            logger.error(f"[{self.source_name}] Error extrayendo artículo de {url}: {e}")
            return None
