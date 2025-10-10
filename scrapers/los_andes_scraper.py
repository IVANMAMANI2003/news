import csv
import hashlib
import json
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LosAndesScraper:
    def __init__(self):
        self.base_url = "https://losandes.com.pe"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Archivos de control
        self.scraped_urls_file = "scraped_urls.json"
        self.news_data = []
        self.scraped_urls = self.load_scraped_urls()
        self.new_articles_count = 0
        
        # Configuración sin límites
        self.delay_between_requests = 1  # segundos entre requests
        self.max_workers = 10  # más workers para ser más agresivo
        self.timeout = None  # sin timeout
        
    def load_scraped_urls(self):
        """Carga las URLs ya scrapeadas desde el archivo de control"""
        if os.path.exists(self.scraped_urls_file):
            try:
                with open(self.scraped_urls_file, 'r', encoding='utf-8') as f:
                    return set(json.load(f))
            except:
                return set()
        return set()
    
    def save_scraped_urls(self):
        """Guarda las URLs scrapeadas en el archivo de control"""
        with open(self.scraped_urls_file, 'w', encoding='utf-8') as f:
            json.dump(list(self.scraped_urls), f, ensure_ascii=False, indent=2)
    
    def make_request(self, url, retries=3):
        """Realiza petición HTTP con reintentos"""
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=self.timeout)
                if response.status_code == 200:
                    return response
                elif response.status_code == 429:  # Rate limit
                    time.sleep(5 * (attempt + 1))
                    continue
            except Exception as e:
                logger.warning(f"Error en intento {attempt + 1} para {url}: {str(e)}")
                time.sleep(2 * (attempt + 1))
        
        logger.error(f"No se pudo acceder a {url} después de {retries} intentos")
        return None
    
    def get_all_article_urls(self):
        """Obtiene todas las URLs de artículos del sitio"""
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
            logger.info(f"Explorando sección: {section_url}")
            
            # Explorar paginación de cada sección
            page = 1
            while True:
                if page == 1:
                    page_url = section_url
                else:
                    page_url = f"{section_url}page/{page}/"
                
                logger.info(f"Explorando página {page} de {section}")
                response = self.make_request(page_url)
                
                if not response:
                    break
                    
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Buscar enlaces de artículos
                page_articles = self.extract_article_urls_from_page(soup)
                
                if not page_articles:
                    logger.info(f"No se encontraron más artículos en página {page} de {section}")
                    break
                
                article_urls.update(page_articles)
                logger.info(f"Encontrados {len(page_articles)} artículos en página {page}")
                
                page += 1
                time.sleep(self.delay_between_requests)
                
                # Sin límite de páginas - explorar todo
                # if page > 100:
                #     logger.warning(f"Límite de páginas alcanzado para {section}")
                #     break
        
        # Explorar sitemap si está disponible
        self.explore_sitemap(article_urls)
        
        # Explorar archivo robots.txt para encontrar más rutas
        self.explore_robots_txt(article_urls)
        
        logger.info(f"Total de URLs de artículos encontradas: {len(article_urls)}")
        return article_urls
    
    def extract_article_urls_from_page(self, soup):
        """Extrae URLs de artículos de una página"""
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
            'a[href*="/20"]',  # URLs que contienen años
            'a[href*="/noticia"]',
            'a[href*="/news"]',
            'a[href*="/articulo"]',
            'a[href*="/post"]',
            '.content a[href]',
            '.main-content a[href]',
            '.news-content a[href]'
        ]
        
        for selector in selectors:
            links = soup.select(selector)
            logger.info(f"Selector '{selector}' encontró {len(links)} enlaces")
            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin(self.base_url, href)
                    # Filtrar URLs que parecen artículos
                    if self.is_article_url(full_url):
                        article_urls.add(full_url)
        
        return article_urls
    
    def is_article_url(self, url):
        """Determina si una URL es de un artículo"""
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
    
    def explore_sitemap(self, article_urls):
        """Explora el sitemap para encontrar más URLs (como codigos-claude)"""
        sitemaps = [
            "/sitemap.xml",
            "/sitemap_index.xml",
            "/news-sitemap.xml",
            "/sitemap-news.xml"
        ]
        
        for sitemap in sitemaps:
            sitemap_url = urljoin(self.base_url, sitemap)
            logger.info(f"Explorando sitemap: {sitemap_url}")
            
            response = self.make_request(sitemap_url)
            if response:
                soup = BeautifulSoup(response.content, 'xml')
                urls = soup.find_all('loc')
                
                for url_tag in urls:
                    url = url_tag.get_text().strip()
                    if self.is_article_url(url):
                        article_urls.add(url)
                
                logger.info(f"URLs encontradas en sitemap: {len(urls)}")
        
        # Explorar robots.txt para encontrar más sitemaps
        self.explore_robots_txt(article_urls)
    
    def explore_robots_txt(self, article_urls):
        """Explora robots.txt para encontrar más rutas (como codigos-claude)"""
        robots_url = urljoin(self.base_url, "/robots.txt")
        response = self.make_request(robots_url)
        
        if response:
            logger.info("Explorando robots.txt")
            for line in response.text.split('\n'):
                if 'Sitemap:' in line:
                    sitemap_url = line.split('Sitemap:')[1].strip()
                    if sitemap_url:
                        logger.info(f"Sitemap encontrado en robots.txt: {sitemap_url}")
                        response_sitemap = self.make_request(sitemap_url)
                        if response_sitemap:
                            soup = BeautifulSoup(response_sitemap.content, 'xml')
                            urls = soup.find_all('loc')
                            for url_tag in urls:
                                url = url_tag.get_text().strip()
                                if self.is_article_url(url):
                                    article_urls.add(url)
    
    def extract_article_data(self, url):
        """Extrae datos de un artículo individual"""
        if url in self.scraped_urls:
            return None  # Ya fue scrapeado
        
        logger.info(f"Extrayendo: {url}")
        response = self.make_request(url)
        
        if not response:
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        try:
            # Extraer datos del artículo
            article_data = {
                'titulo': self.extract_title(soup),
                'fecha': self.extract_date(soup),
                'hora': self.extract_time(soup),
                'resumen': self.extract_summary(soup),
                'contenido': self.extract_content(soup),
                'categoria': self.extract_category(soup, url),
                'autor': self.extract_author(soup),
                'tags': self.extract_tags(soup),
                'url': url,
                'fecha_extraccion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'link_imagenes': self.extract_images(soup, url)
            }
            
            # Marcar URL como scrapeada
            self.scraped_urls.add(url)
            self.new_articles_count += 1
            
            return article_data
            
        except Exception as e:
            logger.error(f"Error extrayendo datos de {url}: {str(e)}")
            return None
    
    def extract_title(self, soup):
        """Extrae el título del artículo"""
        title_selectors = [
            'h1.entry-title', 'h1.post-title', 'h1', '.entry-title', '.post-title', 'title'
        ]
        
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text().strip()
        
        return ""
    
    def extract_date(self, soup):
        """Extrae la fecha del artículo"""
        date_selectors = [
            '.entry-date', '.post-date', '.date', '.published',
            'time[datetime]', '.entry-meta time', '.post-meta .date',
            '[class*="date"]', '[class*="time"]'
        ]
        
        for selector in date_selectors:
            element = soup.select_one(selector)
            if element:
                if element.get('datetime'):
                    date_text = element['datetime']
                else:
                    date_text = element.get_text().strip()
                
                if date_text:
                    # Extraer solo la fecha
                    match = re.search(r'\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}', date_text)
                    if match:
                        return match.group()
        
        return ""
    
    def extract_time(self, soup):
        """Extrae la hora del artículo"""
        time_selectors = [
            '.entry-date', '.post-date', '.date', '.published',
            'time[datetime]', '.entry-meta time', '.post-meta .date',
            '[class*="date"]', '[class*="time"]'
        ]
        
        for selector in time_selectors:
            element = soup.select_one(selector)
            if element:
                if element.get('datetime'):
                    time_text = element['datetime']
                else:
                    time_text = element.get_text().strip()
                
                if time_text:
                    # Extraer solo la hora
                    match = re.search(r'\d{1,2}:\d{2}(?::\d{2})?', time_text)
                    if match:
                        return match.group()
        
        return ""
    
    def extract_summary(self, soup):
        """Extrae el resumen del artículo"""
        summary_selectors = ['.entry-excerpt', '.post-excerpt', '.excerpt', '.summary']
        
        for selector in summary_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text().strip()
        
        return ""
    
    def extract_content(self, soup):
        """Extrae el contenido del artículo"""
        content_selectors = [
            '.entry-content', '.post-content', '.article-content',
            '.content', 'article .content', '.post-body', '.entry-body'
        ]
        
        for selector in content_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text().strip()
        
        return ""
    
    def extract_category(self, soup, url):
        """Extrae la categoría del artículo"""
        category_selectors = ['.category', '.post-category', '.entry-category', '.categories']
        
        for selector in category_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text().strip()
        
        # Intentar extraer de la URL
        if '/categoria/' in url:
            parts = url.split('/categoria/')
            if len(parts) > 1:
                category = parts[1].split('/')[0]
                return category.replace('-', ' ').title()
        
        return ""
    
    def extract_author(self, soup):
        """Extrae el autor del artículo"""
        author_selectors = ['.author', '.post-author', '.entry-author', '.by-author', '[rel="author"]']
        
        for selector in author_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text().strip()
        
        return ""
    
    def extract_tags(self, soup):
        """Extrae las etiquetas del artículo"""
        tags_selectors = ['.tags', '.post-tags', '.entry-tags', '.tag-links']
        
        for selector in tags_selectors:
            elements = soup.select(selector + ' a, ' + selector)
            if elements:
                tags = ", ".join([tag.get_text().strip() for tag in elements])
                return tags
        
        return ""
    
    def extract_images(self, soup, url):
        """Extrae imágenes del artículo"""
        images = []
        base_domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        
        img_selectors = [
            '.entry-content img', '.post-content img', '.article-content img',
            '.featured-image img', '.post-thumbnail img', '.wp-post-image',
            'article img', '.content img', 'img[src*="wp-content"]'
        ]
        
        for selector in img_selectors:
            imgs = soup.select(selector)
            for img in imgs:
                src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                if src and len(images) < 2:
                    # Convertir a URL absoluta
                    if src.startswith('//'):
                        src = f"https:{src}"
                    elif src.startswith('/'):
                        src = f"{base_domain}{src}"
                    elif not src.startswith('http'):
                        src = urljoin(url, src)
                    
                    # Filtrar imágenes pequeñas o iconos
                    if not any(x in src.lower() for x in ['icon', 'logo', 'avatar', 'emoji']):
                        if src not in images:
                            images.append(src)
                
                if len(images) >= 2:
                    break
            
            if len(images) >= 2:
                break
        
        return "; ".join(images)
    
    def scrape_noticias(self, max_noticias=None):
        """Método principal para extraer noticias"""
        logger.info("Iniciando scraping de Los Andes")
        
        # Obtener todas las URLs de artículos
        article_urls = self.get_all_article_urls()
        
        # Filtrar URLs ya scrapeadas
        new_urls = [url for url in article_urls if url not in self.scraped_urls]
        
        if max_noticias:
            new_urls = new_urls[:max_noticias]
        
        logger.info(f"Procesando {len(new_urls)} noticias nuevas")
        
        # Procesar artículos con hilos concurrentes
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {executor.submit(self.extract_article_data, url): url for url in new_urls}
            
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    article_data = future.result()
                    if article_data:
                        self.news_data.append(article_data)
                        logger.info(f"Artículo procesado: {article_data['titulo'][:50]}...")
                except Exception as e:
                    logger.error(f"Error procesando {url}: {str(e)}")
        
        # Guardar URLs scrapeadas
        self.save_scraped_urls()
        
        logger.info(f"Scraping completado. Nuevos artículos: {self.new_articles_count}")
        logger.info(f"Total de artículos en memoria: {len(self.news_data)}")
        
        return self.new_articles_count