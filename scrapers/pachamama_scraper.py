"""
Scraper específico para Pachamama Radio
"""
import logging
import re
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from base_scraper import BaseNewsScraper

logger = logging.getLogger(__name__)

class PachamamaScraper(BaseNewsScraper):
    """Scraper para Pachamama Radio"""
    
    def __init__(self):
        super().__init__(
            source_name="Pachamama Radio",
            base_url="https://pachamamaradio.org/",
            delay=2
        )
    
    def is_news_url(self, url: str) -> bool:
        """Determinar si una URL es de noticia"""
        # Patrones que indican noticias
        news_patterns = [
            r'/20',  # Contiene año
            r'/noticia',
            r'/post',
            r'/articulo',
            r'/blog'
        ]
        
        # Patrones que indican que NO es noticia
        exclude_patterns = [
            r'/wp-admin',
            r'/wp-content',
            r'/wp-includes',
            r'/feed',
            r'/rss',
            r'/category',
            r'/tag',
            r'/author',
            r'/archive',
            r'/search',
            r'\.jpg',
            r'\.png',
            r'\.gif',
            r'\.pdf',
            r'\.doc'
        ]
        
        # Verificar que sea del mismo dominio
        if urlparse(url).netloc != urlparse(self.base_url).netloc:
            return False
        
        # Verificar patrones de exclusión
        for pattern in exclude_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False
        
        # Verificar patrones de noticias
        for pattern in news_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        
        return False
    
    def extract_news_urls(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Encuentra todos los enlaces a noticias"""
        enlaces = set()
        
        # Selectores para enlaces de noticias
        selectores_enlaces = [
            'a[href*="/noticia"]', 'a[href*="/post"]', 'a[href*="/article"]',
            '.entry-title a', '.post-title a', '.article-title a',
            'article a', '.blog-post a', '.news-item a',
            'a[href*="' + urlparse(base_url).netloc + '"]'
        ]
        
        for selector in selectores_enlaces:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href:
                    # Convertir a URL absoluta
                    if href.startswith('/'):
                        href = urljoin(base_url, href)
                    elif not href.startswith('http'):
                        href = urljoin(base_url, href)
                    
                    # Verificar que sea del mismo dominio
                    if urlparse(href).netloc == urlparse(base_url).netloc:
                        # Filtrar URLs que no son noticias
                        if not any(x in href.lower() for x in [
                            'wp-admin', 'wp-content', 'wp-includes', 'feed', 'rss',
                            'category', 'tag', 'author', 'archive', 'search',
                            '.jpg', '.png', '.gif', '.pdf', '.doc'
                        ]):
                            enlaces.add(href)
        
        return list(enlaces)
    
    def discover_news_urls(self, max_pages: int = 50) -> List[str]:
        """Ejecuta descubrimiento recursivo de URLs"""
        logger.info(f"[{self.source_name}] Iniciando descubrimiento recursivo de URLs")
        
        urls_por_procesar = {self.base_url}
        urls_visitadas = set()
        all_news_urls = set()
        pages_processed = 0
        
        while urls_por_procesar and pages_processed < max_pages:
            logger.info(f"[{self.source_name}] Procesando nivel, URLs pendientes: {len(urls_por_procesar)}")
            
            urls_nivel_actual = list(urls_por_procesar)[:10]  # Procesar en lotes
            urls_por_procesar = set(list(urls_por_procesar)[10:])
            
            for url in urls_nivel_actual:
                if url in urls_visitadas:
                    continue
                
                logger.info(f"[{self.source_name}] Procesando: {url}")
                urls_visitadas.add(url)
                
                soup = self.make_request(url)
                if not soup:
                    continue
                
                # Si parece ser una noticia individual, agregarla
                if self.es_noticia_individual(soup, url):
                    all_news_urls.add(url)
                
                # Buscar más enlaces
                enlaces_noticias = self.extract_news_urls(soup, url)
                enlaces_paginas = self.encontrar_paginas_navegacion(soup, url)
                
                # Añadir enlaces no visitados
                for enlace in enlaces_noticias + enlaces_paginas:
                    if enlace not in urls_visitadas:
                        urls_por_procesar.add(enlace)
                
                pages_processed += 1
        
        logger.info(f"[{self.source_name}] Descubrimiento completado. Total de noticias encontradas: {len(all_news_urls)}")
        return list(all_news_urls)
    
    def es_noticia_individual(self, soup: BeautifulSoup, url: str) -> bool:
        """Determina si una página es una noticia individual"""
        # Indicadores de que es una noticia individual
        indicadores = [
            soup.select_one('article'),
            soup.select_one('.entry-content'),
            soup.select_one('.post-content'),
            soup.select_one('h1.entry-title'),
            soup.select_one('.single-post')
        ]
        
        # También verificar por estructura de URL
        url_patterns = ['/20', '/noticia', '/post', '/articulo']
        url_indica_noticia = any(pattern in url.lower() for pattern in url_patterns)
        
        return any(indicadores) or url_indica_noticia
    
    def encontrar_paginas_navegacion(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Encuentra enlaces de paginación y navegación"""
        paginas = set()
        
        # Selectores para paginación
        selectores_paginacion = [
            '.pagination a', '.nav-links a', '.page-numbers a',
            '.next-posts-link', '.prev-posts-link',
            'a[href*="page"]', 'a[href*="paged"]'
        ]
        
        for selector in selectores_paginacion:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href:
                    if href.startswith('/'):
                        href = urljoin(base_url, href)
                    elif not href.startswith('http'):
                        href = urljoin(base_url, href)
                    
                    if urlparse(href).netloc == urlparse(base_url).netloc:
                        paginas.add(href)
        
        return list(paginas)
    
    def extract_news_data(self, url: str) -> Optional[Dict]:
        """Extraer todos los datos de una noticia individual"""
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
            logger.error(f"[{self.source_name}] Error extrayendo noticia de {url}: {e}")
            return None
