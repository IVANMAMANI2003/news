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
        
        # Configuración
        self.delay_between_requests = 1  # segundos entre requests
        self.max_workers = 5  # hilos concurrentes
        self.timeout = 30
        
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
                
                # Límite de páginas por seguridad (ajustar según necesidad)
                if page > 100:
                    logger.warning(f"Límite de páginas alcanzado para {section}")
                    break
        
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
        """Explora el sitemap para encontrar más URLs"""
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
    
    def explore_robots_txt(self, article_urls):
        """Explora robots.txt para encontrar más rutas"""
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
            
            logger.info(f"Artículo extraído: {article_data['titulo'][:50]}...")
            return article_data
            
        except Exception as e:
            logger.error(f"Error extrayendo datos de {url}: {str(e)}")
            return None
    
    def extract_title(self, soup):
        """Extrae el título del artículo"""
        selectors = [
            'h1.entry-title',
            'h1.post-title', 
            'h1.article-title',
            'h1',
            '.title h1',
            '.post-title',
            'title'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text().strip()
        
        return "Sin título"
    
    def extract_date(self, soup):
        """Extrae la fecha del artículo"""
        # Buscar en meta tags
        date_meta = soup.find('meta', {'property': 'article:published_time'}) or \
                   soup.find('meta', {'name': 'publishdate'}) or \
                   soup.find('meta', {'name': 'date'})
        
        if date_meta:
            date_str = date_meta.get('content', '')
            if date_str:
                try:
                    # Parsear fecha ISO
                    date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    return date_obj.strftime('%Y-%m-%d')
                except:
                    pass
        
        # Buscar en el contenido
        selectors = [
            '.entry-date',
            '.post-date',
            '.date',
            '.published',
            '.article-date',
            'time'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                date_text = element.get_text().strip()
                # Extraer fecha con regex
                date_match = re.search(r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})', date_text)
                if date_match:
                    day, month, year = date_match.groups()
                    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        return datetime.now().strftime('%Y-%m-%d')
    
    def extract_time(self, soup):
        """Extrae la hora del artículo"""
        time_element = soup.find('time')
        if time_element:
            datetime_str = time_element.get('datetime', '')
            if datetime_str:
                try:
                    date_obj = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
                    return date_obj.strftime('%H:%M:%S')
                except:
                    pass
        
        # Buscar hora en el texto
        selectors = ['.entry-time', '.post-time', '.time']
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                time_text = element.get_text().strip()
                time_match = re.search(r'(\d{1,2}):(\d{2})', time_text)
                if time_match:
                    return f"{time_match.group(1).zfill(2)}:{time_match.group(2)}:00"
        
        return "00:00:00"
    
    def extract_summary(self, soup):
        """Extrae el resumen del artículo"""
        # Buscar en meta description
        meta_desc = soup.find('meta', {'name': 'description'}) or \
                   soup.find('meta', {'property': 'og:description'})
        
        if meta_desc:
            return meta_desc.get('content', '').strip()
        
        # Buscar en el contenido
        selectors = [
            '.entry-excerpt',
            '.post-excerpt', 
            '.summary',
            '.excerpt',
            '.lead'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text().strip()
        
        # Tomar los primeros párrafos del contenido
        content_element = soup.select_one('.entry-content, .post-content, .content, .article-content')
        if content_element:
            paragraphs = content_element.find_all('p')
            if paragraphs:
                summary = paragraphs[0].get_text().strip()
                return summary[:300] + "..." if len(summary) > 300 else summary
        
        return "Sin resumen disponible"
    
    def extract_content(self, soup):
        """Extrae el contenido completo del artículo"""
        selectors = [
            '.entry-content',
            '.post-content',
            '.article-content',
            '.content',
            '.post-body',
            '.entry-body'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                # Limpiar scripts y elementos no deseados
                for unwanted in element.find_all(['script', 'style', 'ads', '.advertisement']):
                    unwanted.decompose()
                
                # Extraer texto limpio
                paragraphs = element.find_all(['p', 'div', 'span'])
                content_parts = []
                
                for p in paragraphs:
                    text = p.get_text().strip()
                    if text and len(text) > 20:  # Filtrar texto muy corto
                        content_parts.append(text)
                
                return '\n\n'.join(content_parts)
        
        return "Contenido no disponible"
    
    def extract_category(self, soup, url):
        """Extrae la categoría del artículo"""
        # Buscar en breadcrumbs
        breadcrumbs = soup.select('.breadcrumb a, .breadcrumbs a')
        if breadcrumbs and len(breadcrumbs) > 1:
            return breadcrumbs[-2].get_text().strip()
        
        # Buscar en meta
        category_meta = soup.find('meta', {'property': 'article:section'})
        if category_meta:
            return category_meta.get('content', '').strip()
        
        # Extraer de la URL
        path_parts = urlparse(url).path.strip('/').split('/')
        if 'categoria' in path_parts:
            idx = path_parts.index('categoria')
            if idx + 1 < len(path_parts):
                return path_parts[idx + 1].replace('-', ' ').title()
        
        # Buscar en clases o elementos específicos
        category_element = soup.select_one('.category, .post-category, .article-category')
        if category_element:
            return category_element.get_text().strip()
        
        return "Sin categoría"
    
    def extract_author(self, soup):
        """Extrae el autor del artículo"""
        # Buscar en meta tags
        author_meta = soup.find('meta', {'name': 'author'}) or \
                     soup.find('meta', {'property': 'article:author'})
        
        if author_meta:
            return author_meta.get('content', '').strip()
        
        # Buscar en elementos específicos
        selectors = [
            '.author',
            '.post-author',
            '.article-author', 
            '.byline',
            '.author-name',
            '.by-author'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                author_text = element.get_text().strip()
                # Limpiar texto del autor
                author_text = re.sub(r'^(por|by|autor:?)\s*', '', author_text, flags=re.IGNORECASE)
                return author_text
        
        return "Autor desconocido"
    
    def extract_tags(self, soup):
        """Extrae los tags del artículo"""
        tags = []
        
        # Buscar en meta keywords
        keywords_meta = soup.find('meta', {'name': 'keywords'})
        if keywords_meta:
            keywords = keywords_meta.get('content', '')
            tags.extend([tag.strip() for tag in keywords.split(',') if tag.strip()])
        
        # Buscar elementos de tags
        tag_elements = soup.select('.tags a, .post-tags a, .tag a, .article-tags a')
        for tag_element in tag_elements:
            tag_text = tag_element.get_text().strip()
            if tag_text:
                tags.append(tag_text)
        
        return tags[:10]  # Máximo 10 tags
    
    def extract_images(self, soup, base_url):
        """Extrae las imágenes del artículo (máximo 2)"""
        images = []
        
        # Buscar imágenes en el contenido
        content_area = soup.select_one('.entry-content, .post-content, .article-content, .content')
        if content_area:
            img_elements = content_area.find_all('img')[:2]  # Máximo 2 imágenes
        else:
            img_elements = soup.find_all('img')[:2]
        
        for img in img_elements:
            src = img.get('src') or img.get('data-src')
            if src:
                full_url = urljoin(base_url, src)
                # Filtrar imágenes muy pequeñas (probablemente iconos)
                if not any(size in src.lower() for size in ['icon', 'logo', 'avatar']) and \
                   not src.endswith('.gif'):
                    images.append(full_url)
        
        return images
    
    def save_data(self):
        """Guarda los datos en CSV y JSON"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Guardar en JSON
        json_filename = f"noticias_losandes_{timestamp}.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(self.news_data, f, ensure_ascii=False, indent=2)
        
        # Guardar en CSV
        csv_filename = f"noticias_losandes_{timestamp}.csv"
        if self.news_data:
            with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
                fieldnames = self.news_data[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for row in self.news_data:
                    # Convertir listas a strings para CSV
                    csv_row = row.copy()
                    if isinstance(csv_row['tags'], list):
                        csv_row['tags'] = ', '.join(csv_row['tags'])
                    if isinstance(csv_row['link_imagenes'], list):
                        csv_row['link_imagenes'] = ', '.join(csv_row['link_imagenes'])
                    writer.writerow(csv_row)
        
        logger.info(f"Datos guardados en {json_filename} y {csv_filename}")
        return json_filename, csv_filename
    
    def run_scraping(self):
        """Ejecuta el scraping completo"""
        start_time = datetime.now()
        logger.info("Iniciando scraping de Los Andes...")
        
        # Obtener todas las URLs de artículos
        article_urls = self.get_all_article_urls()
        
        # Filtrar URLs ya scrapeadas para procesamiento incremental
        new_urls = [url for url in article_urls if url not in self.scraped_urls]
        logger.info(f"URLs nuevas para scrapear: {len(new_urls)}")
        logger.info(f"URLs ya scrapeadas anteriormente: {len(self.scraped_urls)}")
        
        if not new_urls:
            logger.info("No hay nuevas noticias para scrapear.")
            return
        
        # Procesar URLs con ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {executor.submit(self.extract_article_data, url): url 
                           for url in new_urls}
            
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    article_data = future.result()
                    if article_data:
                        self.news_data.append(article_data)
                        
                        # Progreso cada 50 artículos
                        if len(self.news_data) % 50 == 0:
                            logger.info(f"Procesados {len(self.news_data)} artículos...")
                            
                except Exception as e:
                    logger.error(f"Error procesando {url}: {str(e)}")
                
                # Pequeña pausa entre requests
                time.sleep(self.delay_between_requests)
        
        # Guardar datos
        if self.news_data:
            json_file, csv_file = self.save_data()
            
            # Guardar URLs scrapeadas
            self.save_scraped_urls()
            
            end_time = datetime.now()
            duration = end_time - start_time
            
            logger.info(f"""
            ========== SCRAPING COMPLETADO ==========
            Tiempo total: {duration}
            Artículos nuevos extraídos: {len(self.news_data)}
            Total artículos en base: {len(self.scraped_urls)}
            Archivos generados: {json_file}, {csv_file}
            =========================================
            """)
        else:
            logger.info("No se extrajeron nuevos artículos.")

# Función principal para ejecutar
def main():
    scraper = LosAndesScraper()
    scraper.run_scraping()

if __name__ == "__main__":
    main()