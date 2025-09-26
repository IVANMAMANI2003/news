"""
Clase base para scrapers de noticias
"""
import hashlib
import logging
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class BaseNewsScraper:
    """Clase base para todos los scrapers de noticias"""
    
    def __init__(self, source_name: str, base_url: str, delay: int = 2):
        self.source_name = source_name
        self.base_url = base_url
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # URLs ya procesadas para evitar duplicados
        self.processed_urls: Set[str] = set()
        
    def make_request(self, url: str, retries: int = 3) -> Optional[BeautifulSoup]:
        """Realizar petición HTTP con reintentos"""
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                response.encoding = response.apparent_encoding or 'utf-8'
                return BeautifulSoup(response.content, 'html.parser')
            except Exception as e:
                logger.warning(f"Intento {attempt + 1} fallido para {url}: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Backoff exponencial
        logger.error(f"No se pudo acceder a {url} después de {retries} intentos")
        return None
    
    def is_news_url(self, url: str) -> bool:
        """Verificar si una URL es de noticia (implementar en subclases)"""
        raise NotImplementedError("Subclases deben implementar is_news_url")
    
    def extract_news_urls(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extraer URLs de noticias de una página (implementar en subclases)"""
        raise NotImplementedError("Subclases deben implementar extract_news_urls")
    
    def extract_news_data(self, url: str) -> Optional[Dict]:
        """Extraer datos de una noticia específica (implementar en subclases)"""
        raise NotImplementedError("Subclases deben implementar extract_news_data")
    
    def extract_title(self, soup: BeautifulSoup) -> str:
        """Extraer título del artículo"""
        title_selectors = [
            'h1.entry-title', 'h1.post-title', 'h1.article-title', 'h1.news-title',
            '.title h1', 'h1', '.entry-title', '.post-title', '.article-title',
            'title', '.headline h1', '.news-title h1'
        ]
        
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                return self.clean_text(element.get_text())
        return "Sin título"
    
    def extract_date_time(self, soup: BeautifulSoup) -> tuple:
        """Extraer fecha y hora del artículo"""
        fecha, hora = "", ""
        
        # Buscar en meta tags primero
        date_meta = soup.find('meta', {'property': 'article:published_time'}) or \
                   soup.find('meta', {'name': 'publishdate'}) or \
                   soup.find('meta', {'name': 'date'})
        
        if date_meta:
            date_str = date_meta.get('content', '')
            if date_str:
                try:
                    dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    fecha = dt.strftime('%Y-%m-%d')
                    hora = dt.strftime('%H:%M:%S')
                    return fecha, hora
                except:
                    pass
        
        # Buscar en elementos del DOM
        date_selectors = [
            '.entry-date', '.post-date', '.date', '.published', '.article-date',
            'time[datetime]', '.entry-meta time', '.post-meta .date',
            '[class*="date"]', '[class*="time"]', '.news-date'
        ]
        
        for selector in date_selectors:
            element = soup.select_one(selector)
            if element:
                date_text = element.get_text(strip=True)
                if not date_text and element.get('datetime'):
                    date_text = element['datetime']
                
                if date_text:
                    # Extraer fecha
                    date_match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', date_text)
                    if date_match:
                        day, month, year = date_match.groups()
                        fecha = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    
                    # Extraer hora
                    time_match = re.search(r'(\d{1,2}):(\d{2})(?::(\d{2}))?', date_text)
                    if time_match:
                        hour, minute, second = time_match.groups()
                        hora = f"{hour.zfill(2)}:{minute}:{second or '00'}"
                    
                    if fecha or hora:
                        break
        
        return fecha or datetime.now().strftime('%Y-%m-%d'), hora or "00:00:00"
    
    def extract_content(self, soup: BeautifulSoup) -> str:
        """Extraer contenido del artículo"""
        content_selectors = [
            '.entry-content', '.post-content', '.article-content', '.news-content',
            '.content', '.post-body', '.entry-body', 'article .content',
            '.single-content', '.news-body'
        ]
        
        for selector in content_selectors:
            element = soup.select_one(selector)
            if element:
                # Remover elementos no deseados
                for unwanted in element.select('script, style, .ad, .advertisement, .social-share'):
                    unwanted.decompose()
                
                content = self.clean_text(element.get_text())
                if content and len(content) > 50:  # Contenido significativo
                    return content
        
        return ""
    
    def extract_summary(self, soup: BeautifulSoup, content: str = "") -> str:
        """Extraer resumen del artículo"""
        # Buscar meta description
        meta_desc = soup.find('meta', {'name': 'description'}) or \
                   soup.find('meta', {'property': 'og:description'})
        
        if meta_desc:
            summary = meta_desc.get('content', '').strip()
            if summary:
                return summary
        
        # Buscar excerpt
        excerpt_selectors = [
            '.entry-excerpt', '.post-excerpt', '.excerpt', '.summary',
            '.lead', '.news-excerpt', '.article-excerpt'
        ]
        
        for selector in excerpt_selectors:
            element = soup.select_one(selector)
            if element:
                excerpt = self.clean_text(element.get_text())
                if excerpt and len(excerpt) > 20:
                    return excerpt
        
        # Usar primeros párrafos del contenido
        if content:
            paragraphs = content.split('\n\n')
            for p in paragraphs:
                p = p.strip()
                if len(p) > 50:
                    return p[:300] + '...' if len(p) > 300 else p
        
        return ""
    
    def extract_author(self, soup: BeautifulSoup) -> str:
        """Extraer autor del artículo"""
        # Buscar en meta tags
        author_meta = soup.find('meta', {'name': 'author'}) or \
                     soup.find('meta', {'property': 'article:author'})
        
        if author_meta:
            return author_meta.get('content', '').strip()
        
        # Buscar en elementos del DOM
        author_selectors = [
            '.author', '.post-author', '.article-author', '.by-author',
            '.byline', '.author-name', '.writer', 'span.author',
            '.entry-author', '.news-author'
        ]
        
        for selector in author_selectors:
            element = soup.select_one(selector)
            if element:
                author = self.clean_text(element.get_text())
                # Limpiar prefijos comunes
                author = re.sub(r'^(por|by|autor:?)\s*', '', author, flags=re.IGNORECASE)
                if author:
                    return author
        
        return "Autor desconocido"
    
    def extract_category(self, soup: BeautifulSoup, url: str = "") -> str:
        """Extraer categoría del artículo"""
        # Buscar en breadcrumbs
        breadcrumbs = soup.select('.breadcrumb a, .breadcrumbs a, .breadcrumb li')
        if breadcrumbs and len(breadcrumbs) > 1:
            return self.clean_text(breadcrumbs[-2].get_text())
        
        # Buscar en meta
        category_meta = soup.find('meta', {'property': 'article:section'})
        if category_meta:
            return category_meta.get('content', '').strip()
        
        # Extraer de la URL
        if url:
            path_parts = urlparse(url).path.strip('/').split('/')
            if 'categoria' in path_parts:
                idx = path_parts.index('categoria')
                if idx + 1 < len(path_parts):
                    return path_parts[idx + 1].replace('-', ' ').title()
        
        # Buscar en elementos específicos
        category_selectors = [
            '.category', '.post-category', '.article-category', '.news-category',
            '.entry-category', '.cat-links a', '.categories a'
        ]
        
        for selector in category_selectors:
            element = soup.select_one(selector)
            if element:
                return self.clean_text(element.get_text())
        
        return "Sin categoría"
    
    def extract_tags(self, soup: BeautifulSoup) -> List[str]:
        """Extraer tags del artículo"""
        tags = []
        
        # Buscar en meta keywords
        keywords_meta = soup.find('meta', {'name': 'keywords'})
        if keywords_meta:
            keywords = keywords_meta.get('content', '')
            tags.extend([tag.strip() for tag in keywords.split(',') if tag.strip()])
        
        # Buscar elementos de tags
        tag_selectors = [
            '.tags a', '.post-tags a', '.tag a', '.article-tags a',
            '.entry-tags a', '.news-tags a', '.tag-links a'
        ]
        
        for selector in tag_selectors:
            elements = soup.select(selector)
            for element in elements:
                tag_text = self.clean_text(element.get_text())
                if tag_text and tag_text not in tags:
                    tags.append(tag_text)
        
        return tags[:10]  # Máximo 10 tags
    
    def extract_images(self, soup: BeautifulSoup, url: str) -> List[str]:
        """Extraer imágenes del artículo (máximo 2)"""
        images = []
        base_domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        
        # Selectores para imágenes principales
        img_selectors = [
            '.entry-content img', '.post-content img', '.article-content img',
            '.featured-image img', '.post-thumbnail img', '.wp-post-image',
            'article img', '.content img', '.news-content img'
        ]
        
        for selector in img_selectors:
            imgs = soup.select(selector)
            for img in imgs:
                if len(images) >= 2:
                    break
                    
                src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                if src:
                    # Convertir a URL absoluta
                    if src.startswith('//'):
                        src = f"https:{src}"
                    elif src.startswith('/'):
                        src = f"{base_domain}{src}"
                    elif not src.startswith('http'):
                        src = urljoin(url, src)
                    
                    # Filtrar imágenes pequeñas o iconos
                    if not any(x in src.lower() for x in ['icon', 'logo', 'avatar', 'emoji', 'sprite']):
                        if src not in images:
                            images.append(src)
            
            if len(images) >= 2:
                break
        
        return images
    
    def clean_text(self, text: str) -> str:
        """Limpiar y formatear texto"""
        if not text:
            return ""
        
        # Eliminar etiquetas HTML residuales
        text = re.sub(r'<[^>]+>', '', text)
        # Normalizar espacios
        text = re.sub(r'\s+', ' ', text)
        # Eliminar caracteres especiales problemáticos
        text = text.replace('\u00a0', ' ').replace('\r', '').replace('\n', ' ')
        return text.strip()
    
    def format_news_data(self, raw_data: Dict) -> Dict:
        """Formatear datos de noticia para la base de datos"""
        # Convertir listas a strings
        tags_str = ', '.join(raw_data.get('tags', []))
        images_str = '; '.join(raw_data.get('link_imagenes', []))
        
        return {
            'titulo': raw_data.get('titulo', ''),
            'fecha': raw_data.get('fecha', ''),
            'hora': raw_data.get('hora', ''),
            'resumen': raw_data.get('resumen', ''),
            'contenido': raw_data.get('contenido', ''),
            'categoria': raw_data.get('categoria', ''),
            'autor': raw_data.get('autor', ''),
            'tags': tags_str,
            'url': raw_data.get('url', ''),
            'link_imagenes': images_str,
            'fuente': self.source_name
        }
    
    def discover_news_urls(self, max_pages: int = 50) -> List[str]:
        """Descubrir URLs de noticias (implementar en subclases)"""
        raise NotImplementedError("Subclases deben implementar discover_news_urls")
    
    def scrape_news(self, urls: List[str]) -> List[Dict]:
        """Scrapear noticias de una lista de URLs"""
        news_data = []
        
        for i, url in enumerate(urls, 1):
            if url in self.processed_urls:
                continue
                
            logger.info(f"[{self.source_name}] Procesando {i}/{len(urls)}: {url}")
            
            try:
                news_item = self.extract_news_data(url)
                if news_item and news_item.get('titulo'):
                    formatted_data = self.format_news_data(news_item)
                    news_data.append(formatted_data)
                    self.processed_urls.add(url)
                    logger.info(f"[{self.source_name}] Noticia extraída: {news_item['titulo'][:50]}...")
                else:
                    logger.warning(f"[{self.source_name}] No se pudo extraer datos de {url}")
                    
            except Exception as e:
                logger.error(f"[{self.source_name}] Error procesando {url}: {e}")
            
            # Delay entre requests
            time.sleep(self.delay)
        
        return news_data
