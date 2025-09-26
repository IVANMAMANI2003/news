import csv
import hashlib
import json
import logging
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List, Set
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


class NewsScraper:
    def __init__(self, config_file="scraper_config.json"):
        self.config = self.load_config(config_file)
        self.base_url = "https://diariosinfronteras.com.pe/"
        self.visited_urls = set()
        self.scraped_articles = set()
        self.news_data = []
        self.lock = threading.Lock()
        
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
        
        # Headers para evitar bloqueos
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Cargar URLs ya procesadas si existe el archivo
        self.load_processed_urls()

    def load_config(self, config_file):
        """Cargar configuración del scraping"""
        default_config = {
            "delay_between_requests": 2,
            "max_workers": 5,
            "timeout": 30,
            "max_retries": 3,
            "output_csv": "noticias.csv",
            "output_json": "noticias.json",
            "processed_urls_file": "processed_urls.json",
            "enable_recursive": True,
            "max_pages_per_category": None,
            "categories_to_scrape": "all",
            "extract_images": True,
            "max_images_per_article": 2
        }
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                print(f"Error cargando configuración: {e}. Usando configuración por defecto.")
        else:
            # Crear archivo de configuración por defecto
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
            print(f"Archivo de configuración creado: {config_file}")
        
        return default_config

    def load_processed_urls(self):
        """Cargar URLs ya procesadas"""
        if os.path.exists(self.config["processed_urls_file"]):
            try:
                with open(self.config["processed_urls_file"], 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.scraped_articles = set(data.get("scraped_articles", []))
                    self.visited_urls = set(data.get("visited_urls", []))
                self.logger.info(f"Cargadas {len(self.scraped_articles)} noticias ya procesadas")
            except Exception as e:
                self.logger.error(f"Error cargando URLs procesadas: {e}")

    def save_processed_urls(self):
        """Guardar URLs procesadas"""
        try:
            data = {
                "scraped_articles": list(self.scraped_articles),
                "visited_urls": list(self.visited_urls),
                "last_update": datetime.now().isoformat()
            }
            with open(self.config["processed_urls_file"], 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Error guardando URLs procesadas: {e}")

    def get_page(self, url, retries=None):
        """Obtener página web con reintentos"""
        if retries is None:
            retries = self.config["max_retries"]
        
        for attempt in range(retries + 1):
            try:
                response = requests.get(
                    url, 
                    headers=self.headers, 
                    timeout=self.config["timeout"]
                )
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                if attempt == retries:
                    self.logger.error(f"Error obteniendo {url} después de {retries} intentos: {e}")
                    return None
                time.sleep(2 ** attempt)  # Backoff exponencial
        return None

    def extract_article_urls(self, soup, base_url):
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
                    # Filtrar solo URLs que parecen artículos de noticias
                    if self.is_article_url(full_url):
                        article_urls.add(full_url)
        
        return article_urls

    def is_article_url(self, url):
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

    def extract_pagination_urls(self, soup, base_url):
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
        
        return pagination_urls

    def extract_category_urls(self, soup, base_url):
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
        
        return category_urls

    def extract_images(self, soup, article_url):
        """Extraer imágenes del artículo"""
        images = []
        max_images = self.config.get("max_images_per_article", 2)
        
        if not self.config.get("extract_images", True):
            return images
        
        # Selectores para imágenes
        img_selectors = [
            'article img',
            '.content img',
            '.entry-content img',
            '.post-content img',
            '.featured-image img',
            'img[src]'
        ]
        
        seen_images = set()
        
        for selector in img_selectors:
            img_tags = soup.select(selector)
            for img in img_tags:
                src = img.get('src') or img.get('data-src')
                if src and len(images) < max_images:
                    full_img_url = urljoin(article_url, src)
                    if full_img_url not in seen_images:
                        # Filtrar imágenes muy pequeñas o iconos
                        width = img.get('width', '0')
                        height = img.get('height', '0')
                        if width.isdigit() and height.isdigit():
                            if int(width) < 100 or int(height) < 100:
                                continue
                        
                        images.append(full_img_url)
                        seen_images.add(full_img_url)
        
        return images[:max_images]

    def extract_article_data(self, url):
        """Extraer datos de un artículo específico"""
        try:
            # Verificar si ya fue procesado
            url_hash = hashlib.md5(url.encode()).hexdigest()
            if url_hash in self.scraped_articles:
                return None
            
            response = self.get_page(url)
            if not response:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extraer título
            title_selectors = [
                'h1.entry-title',
                'h1.post-title',
                'h1.article-title',
                '.title h1',
                'h1',
                '.entry-header h1',
                'article h1'
            ]
            title = self.extract_by_selectors(soup, title_selectors, get_text=True)
            
            # Extraer fecha y hora
            date_selectors = [
                '.entry-date',
                '.post-date',
                '.published',
                'time[datetime]',
                '.date',
                '.entry-meta time',
                'meta[property="article:published_time"]'
            ]
            fecha_hora = self.extract_date_time(soup, date_selectors)
            
            # Extraer contenido
            content_selectors = [
                '.entry-content',
                '.post-content',
                '.article-content',
                '.content',
                'article .text',
                '.single-content'
            ]
            contenido = self.extract_by_selectors(soup, content_selectors, get_text=True, clean=True)
            
            # Extraer resumen (meta description o primer párrafo)
            resumen = self.extract_summary(soup, contenido)
            
            # Extraer categoría
            category_selectors = [
                '.entry-categories a',
                '.post-categories a',
                '.categories a',
                '.category a',
                'meta[property="article:section"]'
            ]
            categoria = self.extract_by_selectors(soup, category_selectors, get_text=True)
            
            # Extraer autor
            author_selectors = [
                '.author',
                '.entry-author',
                '.post-author',
                '.by-author',
                'meta[name="author"]',
                'meta[property="article:author"]'
            ]
            autor = self.extract_by_selectors(soup, author_selectors, get_text=True)
            
            # Extraer tags
            tag_selectors = [
                '.entry-tags a',
                '.post-tags a',
                '.tags a',
                'meta[property="article:tag"]'
            ]
            tags = self.extract_tags(soup, tag_selectors)
            
            # Extraer imágenes
            imagenes = self.extract_images(soup, url)
            
            article_data = {
                'titulo': title or 'Sin título',
                'fecha': fecha_hora.get('fecha', ''),
                'hora': fecha_hora.get('hora', ''),
                'resumen': resumen or '',
                'contenido': contenido or '',
                'categoria': categoria or '',
                'autor': autor or '',
                'tags': tags,
                'url': url,
                'fecha_extraccion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'link_imagenes': imagenes
            }
            
            # Marcar como procesado
            with self.lock:
                self.scraped_articles.add(url_hash)
                self.news_data.append(article_data)
            
            self.logger.info(f"Extraído artículo: {title[:50]}...")
            return article_data
            
        except Exception as e:
            self.logger.error(f"Error extrayendo artículo de {url}: {e}")
            return None

    def extract_by_selectors(self, soup, selectors, get_text=False, clean=False):
        """Extraer contenido usando múltiples selectores"""
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                element = elements[0]
                if get_text:
                    text = element.get_text(strip=True)
                    if clean:
                        text = self.clean_text(text)
                    return text
                else:
                    return element.get('content', '') if element.name == 'meta' else str(element)
        return ''

    def extract_date_time(self, soup, selectors):
        """Extraer fecha y hora"""
        fecha_hora = {'fecha': '', 'hora': ''}
        
        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                datetime_attr = element.get('datetime')
                if datetime_attr:
                    try:
                        dt = datetime.fromisoformat(datetime_attr.replace('Z', '+00:00'))
                        fecha_hora['fecha'] = dt.strftime('%Y-%m-%d')
                        fecha_hora['hora'] = dt.strftime('%H:%M:%S')
                        return fecha_hora
                    except:
                        pass
                
                # Intentar extraer del texto
                text = element.get_text(strip=True)
                if text:
                    date_match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', text)
                    if date_match:
                        day, month, year = date_match.groups()
                        fecha_hora['fecha'] = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    
                    time_match = re.search(r'(\d{1,2}):(\d{2})', text)
                    if time_match:
                        hour, minute = time_match.groups()
                        fecha_hora['hora'] = f"{hour.zfill(2)}:{minute}:00"
                    
                    if fecha_hora['fecha'] or fecha_hora['hora']:
                        return fecha_hora
        
        return fecha_hora

    def extract_summary(self, soup, content):
        """Extraer resumen del artículo"""
        # Intentar meta description primero
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc:
            return meta_desc.get('content', '').strip()
        
        # Si no hay meta description, usar el primer párrafo del contenido
        if content:
            paragraphs = content.split('\n\n')
            for p in paragraphs:
                p = p.strip()
                if len(p) > 50:  # Párrafo significativo
                    return p[:300] + '...' if len(p) > 300 else p
        
        return ''

    def extract_tags(self, soup, selectors):
        """Extraer tags"""
        tags = []
        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                tag_text = element.get_text(strip=True) if element.name != 'meta' else element.get('content', '')
                if tag_text:
                    tags.append(tag_text)
        return ', '.join(tags) if tags else ''

    def clean_text(self, text):
        """Limpiar texto eliminando espacios extra y caracteres especiales"""
        if not text:
            return ''
        
        # Eliminar múltiples espacios y saltos de línea
        text = re.sub(r'\s+', ' ', text)
        # Eliminar caracteres de control
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        return text.strip()

    def discover_all_urls(self):
        """Descubrir todas las URLs del sitio de forma recursiva"""
        self.logger.info("Iniciando descubrimiento de URLs...")
        
        urls_to_visit = {self.base_url}
        all_article_urls = set()
        
        while urls_to_visit:
            current_urls = urls_to_visit.copy()
            urls_to_visit.clear()
            
            for url in current_urls:
                if url in self.visited_urls:
                    continue
                
                self.logger.info(f"Explorando: {url}")
                response = self.get_page(url)
                if not response:
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extraer URLs de artículos
                article_urls = self.extract_article_urls(soup, url)
                all_article_urls.update(article_urls)
                
                # Extraer URLs de paginación y categorías para continuar explorando
                if self.config.get("enable_recursive", True):
                    pagination_urls = self.extract_pagination_urls(soup, url)
                    category_urls = self.extract_category_urls(soup, url)
                    
                    new_urls = pagination_urls.union(category_urls)
                    for new_url in new_urls:
                        if new_url not in self.visited_urls:
                            urls_to_visit.add(new_url)
                
                self.visited_urls.add(url)
                time.sleep(self.config["delay_between_requests"])
        
        self.logger.info(f"Descubrimiento completado. Encontradas {len(all_article_urls)} URLs de artículos")
        return all_article_urls

    def scrape_articles(self, article_urls):
        """Hacer scraping de todos los artículos usando threading"""
        total_articles = len(article_urls)
        self.logger.info(f"Iniciando scraping de {total_articles} artículos...")
        
        with ThreadPoolExecutor(max_workers=self.config["max_workers"]) as executor:
            future_to_url = {executor.submit(self.extract_article_data, url): url for url in article_urls}
            
            completed = 0
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    completed += 1
                    if completed % 10 == 0:
                        self.logger.info(f"Progreso: {completed}/{total_articles} artículos procesados")
                        # Guardar progreso periódicamente
                        self.save_data()
                        self.save_processed_urls()
                except Exception as e:
                    self.logger.error(f"Error procesando {url}: {e}")
                
                time.sleep(self.config["delay_between_requests"] / self.config["max_workers"])

    def save_data(self):
        """Guardar datos en CSV y JSON"""
        if not self.news_data:
            self.logger.warning("No hay datos para guardar")
            return
        
        # Guardar CSV
        try:
            with open(self.config["output_csv"], 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'titulo', 'fecha', 'hora', 'resumen', 'contenido', 
                    'categoria', 'autor', 'tags', 'url', 'fecha_extraccion', 'link_imagenes'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for article in self.news_data:
                    # Convertir lista de imágenes a string
                    article_copy = article.copy()
                    article_copy['link_imagenes'] = '; '.join(article['link_imagenes'])
                    writer.writerow(article_copy)
            
            self.logger.info(f"Datos guardados en CSV: {self.config['output_csv']}")
        except Exception as e:
            self.logger.error(f"Error guardando CSV: {e}")
        
        # Guardar JSON
        try:
            with open(self.config["output_json"], 'w', encoding='utf-8') as jsonfile:
                json.dump(self.news_data, jsonfile, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Datos guardados en JSON: {self.config['output_json']}")
        except Exception as e:
            self.logger.error(f"Error guardando JSON: {e}")

    def run(self):
        """Ejecutar el scraping completo"""
        start_time = datetime.now()
        self.logger.info("=== INICIANDO SCRAPING DE DIARIOS SIN FRONTERAS ===")
        
        try:
            # Descubrir todas las URLs
            article_urls = self.discover_all_urls()
            
            # Filtrar URLs ya procesadas
            url_hashes = {hashlib.md5(url.encode()).hexdigest() for url in article_urls}
            new_urls = [url for url in article_urls if hashlib.md5(url.encode()).hexdigest() not in self.scraped_articles]
            
            self.logger.info(f"URLs nuevas por procesar: {len(new_urls)}")
            
            if new_urls:
                # Hacer scraping de artículos
                self.scrape_articles(new_urls)
                
                # Guardar datos finales
                self.save_data()
                self.save_processed_urls()
            else:
                self.logger.info("No hay artículos nuevos para procesar")
            
            end_time = datetime.now()
            duration = end_time - start_time
            
            self.logger.info(f"=== SCRAPING COMPLETADO ===")
            self.logger.info(f"Total de artículos extraídos: {len(self.news_data)}")
            self.logger.info(f"Tiempo total: {duration}")
            
        except KeyboardInterrupt:
            self.logger.info("Scraping interrumpido por el usuario")
            self.save_data()
            self.save_processed_urls()
        except Exception as e:
            self.logger.error(f"Error durante el scraping: {e}")
            self.save_data()
            self.save_processed_urls()

if __name__ == "__main__":
    scraper = NewsScraper()
    scraper.run()