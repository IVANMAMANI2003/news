import csv
import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime
from typing import Dict, List, Set
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


class PunoNoticiasScraper:
    def __init__(self, base_url="https://punonoticias.pe/", delay=1):
        self.base_url = base_url
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Configurar logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('scraper.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Archivos de estado
        self.scraped_urls_file = "scraped_urls.txt"
        self.news_data_file = "noticias_data.json"
        self.csv_file = "noticias_completas.csv"
        
        # Sets para tracking
        self.scraped_urls: Set[str] = self.load_scraped_urls()
        self.news_data: List[Dict] = self.load_existing_data()

    def load_scraped_urls(self) -> Set[str]:
        """Cargar URLs ya scrapeadas desde archivo"""
        if os.path.exists(self.scraped_urls_file):
            with open(self.scraped_urls_file, 'r', encoding='utf-8') as f:
                return set(line.strip() for line in f)
        return set()

    def save_scraped_url(self, url: str):
        """Guardar URL scrapeada"""
        with open(self.scraped_urls_file, 'a', encoding='utf-8') as f:
            f.write(url + '\n')
        self.scraped_urls.add(url)

    def load_existing_data(self) -> List[Dict]:
        """Cargar datos existentes"""
        if os.path.exists(self.news_data_file):
            try:
                with open(self.news_data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []

    def get_page(self, url: str) -> BeautifulSoup:
        """Obtener y parsear página"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            self.logger.error(f"Error obteniendo {url}: {e}")
            return None

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

    def extract_news_data(self, url: str) -> Dict:
        """Extraer datos de una noticia específica"""
        soup = self.get_page(url)
        if not soup:
            return None

        data = {
            'url': url,
            'fecha_extraccion': datetime.now().isoformat(),
            'titulo': '',
            'fecha': '',
            'hora': '',
            'resumen': '',
            'contenido': '',
            'categoria': '',
            'autor': '',
            'tags': [],
            'link_imagenes': []
        }

        try:
            # Título
            title_selectors = [
                'h1.entry-title',
                'h1.post-title', 
                'h1.news-title',
                'h1.article-title',
                '.title h1',
                'h1',
                '.post-header h1'
            ]
            
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem and title_elem.get_text(strip=True):
                    data['titulo'] = title_elem.get_text(strip=True)
                    break

            # Fecha y hora
            date_selectors = [
                '.post-date',
                '.entry-date', 
                '.news-date',
                '.article-date',
                'time',
                '.date',
                '.published'
            ]
            
            for selector in date_selectors:
                date_elem = soup.select_one(selector)
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    # Extraer fecha y hora si están juntas
                    if re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{4}', date_text):
                        data['fecha'] = date_text
                    if re.search(r'\d{1,2}:\d{2}', date_text):
                        data['hora'] = date_text
                    break

            # Contenido
            content_selectors = [
                '.entry-content',
                '.post-content',
                '.news-content', 
                '.article-content',
                '.content',
                '.post-body',
                'article'
            ]
            
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    # Remover elementos no deseados
                    for unwanted in content_elem.select('script, style, .ad, .advertisement'):
                        unwanted.decompose()
                    data['contenido'] = content_elem.get_text(strip=True)
                    break

            # Resumen (meta description o primer párrafo)
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                data['resumen'] = meta_desc.get('content', '')
            elif data['contenido']:
                # Usar primeras 200 palabras como resumen
                words = data['contenido'].split()[:200]
                data['resumen'] = ' '.join(words) + '...' if len(words) == 200 else ' '.join(words)

            # Autor
            author_selectors = [
                '.author',
                '.post-author',
                '.by-author', 
                '.writer',
                'span.author'
            ]
            
            for selector in author_selectors:
                author_elem = soup.select_one(selector)
                if author_elem:
                    data['autor'] = author_elem.get_text(strip=True)
                    break

            # Categoría
            category_selectors = [
                '.category',
                '.post-category',
                '.news-category',
                '.breadcrumb a',
                '.cat-links a'
            ]
            
            for selector in category_selectors:
                cat_elem = soup.select_one(selector)
                if cat_elem:
                    data['categoria'] = cat_elem.get_text(strip=True)
                    break

            # Tags
            tag_selectors = [
                '.tags a',
                '.post-tags a',
                '.tag-links a'
            ]
            
            for selector in tag_selectors:
                tag_elems = soup.select(selector)
                if tag_elems:
                    data['tags'] = [tag.get_text(strip=True) for tag in tag_elems]
                    break

            # Imágenes (máximo 2)
            img_selectors = [
                '.entry-content img',
                '.post-content img',
                '.news-content img',
                'article img',
                '.featured-image img'
            ]
            
            images = []
            for selector in img_selectors:
                img_elems = soup.select(selector)
                for img in img_elems:
                    src = img.get('src') or img.get('data-src')
                    if src:
                        full_img_url = urljoin(url, src)
                        images.append(full_img_url)
                        if len(images) >= 2:
                            break
                if len(images) >= 2:
                    break
            
            data['link_imagenes'] = images

        except Exception as e:
            self.logger.error(f"Error extrayendo datos de {url}: {e}")

        return data

    def discover_all_urls(self) -> Set[str]:
        """Descubrir todas las URLs del sitio"""
        discovered_urls = set()
        to_visit = [self.base_url]
        visited = set()

        self.logger.info("Iniciando descubrimiento de URLs...")

        while to_visit:
            current_url = to_visit.pop(0)
            
            if current_url in visited:
                continue
                
            visited.add(current_url)
            self.logger.info(f"Explorando: {current_url}")
            
            soup = self.get_page(current_url)
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
            
            time.sleep(self.delay)

        self.logger.info(f"Descubiertas {len(discovered_urls)} URLs de noticias")
        return discovered_urls

    def scrape_all_news(self):
        """Scraper principal"""
        self.logger.info("Iniciando scraping completo...")
        
        # Descubrir todas las URLs
        all_news_urls = self.discover_all_urls()
        
        # Filtrar URLs ya scrapeadas
        new_urls = [url for url in all_news_urls if url not in self.scraped_urls]
        
        self.logger.info(f"Encontradas {len(new_urls)} noticias nuevas para scrapear")
        
        for i, url in enumerate(new_urls, 1):
            self.logger.info(f"Scrapeando {i}/{len(new_urls)}: {url}")
            
            news_data = self.extract_news_data(url)
            if news_data and news_data.get('titulo'):
                self.news_data.append(news_data)
                self.save_scraped_url(url)
                
                # Guardar progreso cada 10 noticias
                if i % 10 == 0:
                    self.save_data()
                    
            time.sleep(self.delay)
        
        # Guardar datos finales
        self.save_data()
        self.logger.info(f"Scraping completado. Total noticias: {len(self.news_data)}")

    def save_data(self):
        """Guardar datos en JSON y CSV"""
        # Guardar JSON
        with open(self.news_data_file, 'w', encoding='utf-8') as f:
            json.dump(self.news_data, f, ensure_ascii=False, indent=2)
        
        # Guardar CSV
        if self.news_data:
            fieldnames = [
                'titulo', 'fecha', 'hora', 'resumen', 'contenido', 
                'categoria', 'autor', 'tags', 'url', 'fecha_extraccion', 
                'link_imagenes'
            ]
            
            with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for item in self.news_data:
                    row = item.copy()
                    # Convertir listas a strings
                    row['tags'] = ', '.join(row.get('tags', []))
                    row['link_imagenes'] = ', '.join(row.get('link_imagenes', []))
                    writer.writerow(row)

    def run_incremental(self):
        """Ejecutar scraping incremental"""
        self.logger.info("Ejecutando scraping incremental...")
        self.scrape_all_news()

if __name__ == "__main__":
    # Configuración
    scraper = PunoNoticiasScraper(
        base_url="https://punonoticias.pe/",
        delay=1  # Delay entre requests
    )
    
    # Para primera ejecución completa
    print("Iniciando scraping completo de PunoNoticias.pe...")
    scraper.scrape_all_news()
    
    # Para ejecuciones incrementales posteriores, usar:
    # scraper.run_incremental()