"""
Scraper específico para Los Andes
"""
import logging
import re
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from base_scraper import BaseNewsScraper

logger = logging.getLogger(__name__)

class LosAndesScraper(BaseNewsScraper):
    """Scraper para Los Andes"""
    
    def __init__(self):
        super().__init__(
            source_name="Los Andes",
            base_url="https://losandes.com.pe",
            delay=1
        )
    
    def is_news_url(self, url: str) -> bool:
        """Determinar si una URL es de un artículo"""
        # Filtros para identificar artículos
        article_patterns = [
            r'/\d{4}/',  # Contiene año
            r'/noticia/',
            r'/news/',
            r'/articulo/',
            r'/post/',
        ]
        
        # Filtros para excluir
        exclude_patterns = [
            r'/categoria/',
            r'/tag/',
            r'/author/',
            r'/page/',
            r'/search/',
            r'/wp-',
            r'\.pdf$',
            r'\.jpg$',
            r'\.png$',
            r'\.gif$',
            r'#',
            r'javascript:',
            r'mailto:',
        ]
        
        # Verificar que sea del dominio correcto
        if not url.startswith(self.base_url):
            return False
        
        # Verificar patrones de exclusión
        for pattern in exclude_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False
        
        # Verificar patrones de artículos
        for pattern in article_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        
        # Si tiene estructura de noticia típica
        path = urlparse(url).path
        if len(path.split('/')) >= 3 and path.endswith('/'):
            return True
            
        return False
    
    def extract_news_urls(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extraer URLs de artículos de una página"""
        article_urls = set()
        
        # Patrones de selección para diferentes tipos de enlaces de artículos
        selectors = [
            'article a[href]',
            '.post a[href]',
            '.entry-title a[href]',
            '.news-item a[href]',
            '.article-title a[href]',
            'h2 a[href]',
            'h3 a[href]',
            '.headline a[href]',
            '.title a[href]',
            'a[href*="/202"]',  # URLs que contienen años
            'a[href*="/noticia"]',
            'a[href*="/news"]'
        ]
        
        for selector in selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin(self.base_url, href)
                    # Filtrar URLs que parecen artículos
                    if self.is_news_url(full_url):
                        article_urls.add(full_url)
        
        return list(article_urls)
    
    def discover_news_urls(self, max_pages: int = 50) -> List[str]:
        """Obtener todas las URLs de artículos del sitio"""
        article_urls = set()
        
        # URLs principales a explorar
        main_sections = [
            "",  # Página principal
            "/categoria/actualidad/",
            "/categoria/deportes/",
            "/categoria/economia/",
            "/categoria/politica/",
            "/categoria/opinion/",
            "/categoria/cultura/",
            "/categoria/sociedad/",
            "/categoria/tecnologia/",
            "/categoria/salud/",
            "/categoria/educacion/",
        ]
        
        # Explorar páginas principales y sus paginaciones
        for section in main_sections:
            section_url = urljoin(self.base_url, section)
            logger.info(f"[{self.source_name}] Explorando sección: {section_url}")
            
            # Explorar paginación de cada sección
            page = 1
            pages_processed = 0
            
            while page <= 20 and pages_processed < max_pages:  # Límite de páginas por sección
                if page == 1:
                    page_url = section_url
                else:
                    page_url = f"{section_url}page/{page}/"
                
                logger.info(f"[{self.source_name}] Explorando página {page} de {section}")
                soup = self.make_request(page_url)
                
                if not soup:
                    break
                    
                # Buscar enlaces de artículos
                page_articles = self.extract_news_urls(soup, page_url)
                
                if not page_articles:
                    logger.info(f"[{self.source_name}] No se encontraron más artículos en página {page} de {section}")
                    break
                
                article_urls.update(page_articles)
                logger.info(f"[{self.source_name}] Encontrados {len(page_articles)} artículos en página {page}")
                
                page += 1
                pages_processed += 1
        
        # Explorar sitemap si está disponible
        self.explore_sitemap(article_urls)
        
        logger.info(f"[{self.source_name}] Total de URLs de artículos encontradas: {len(article_urls)}")
        return list(article_urls)
    
    def explore_sitemap(self, article_urls: set):
        """Explora el sitemap para encontrar más URLs"""
        sitemaps = [
            "/sitemap.xml",
            "/sitemap_index.xml",
            "/news-sitemap.xml",
            "/sitemap-news.xml"
        ]
        
        for sitemap in sitemaps:
            sitemap_url = urljoin(self.base_url, sitemap)
            logger.info(f"[{self.source_name}] Explorando sitemap: {sitemap_url}")
            
            soup = self.make_request(sitemap_url)
            if soup:
                urls = soup.find_all('loc')
                
                for url_tag in urls:
                    url = url_tag.get_text().strip()
                    if self.is_news_url(url):
                        article_urls.add(url)
                
                logger.info(f"[{self.source_name}] URLs encontradas en sitemap: {len(urls)}")
    
    def extract_news_data(self, url: str) -> Optional[Dict]:
        """Extraer datos de un artículo individual"""
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
