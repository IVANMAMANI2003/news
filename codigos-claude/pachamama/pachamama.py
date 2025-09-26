import requests
from bs4 import BeautifulSoup
import json
import csv
import os
from datetime import datetime
import time
import re
from urllib.parse import urljoin, urlparse
import logging
from typing import Dict, List, Set
import hashlib

class PachamamaRadioScraper:
    def __init__(self, base_url="https://pachamamaradio.org/", delay=2):
        self.base_url = base_url
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        # Configurar logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('scraping.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Archivos de datos
        self.csv_file = 'noticias_pachamama.csv'
        self.json_file = 'noticias_pachamama.json'
        self.urls_procesadas_file = 'urls_procesadas.txt'
        
        # Cargar URLs ya procesadas
        self.urls_procesadas = self.cargar_urls_procesadas()
        
        # Inicializar archivos si no existen
        self.inicializar_archivos()

    def cargar_urls_procesadas(self) -> Set[str]:
        """Carga las URLs ya procesadas para evitar duplicados"""
        if os.path.exists(self.urls_procesadas_file):
            with open(self.urls_procesadas_file, 'r', encoding='utf-8') as f:
                return set(line.strip() for line in f)
        return set()

    def guardar_url_procesada(self, url: str):
        """Guarda una URL como procesada"""
        self.urls_procesadas.add(url)
        with open(self.urls_procesadas_file, 'a', encoding='utf-8') as f:
            f.write(f"{url}\n")

    def inicializar_archivos(self):
        """Inicializa los archivos CSV y JSON si no existen"""
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'titulo', 'fecha', 'hora', 'resumen', 'contenido', 
                    'categoria', 'autor', 'tags', 'url', 'fecha_extraccion', 
                    'link_imagenes', 'hash_contenido'
                ])
                writer.writeheader()
        
        if not os.path.exists(self.json_file):
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)

    def hacer_request(self, url: str) -> BeautifulSoup:
        """Realiza una petición HTTP con manejo de errores"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            response.encoding = response.apparent_encoding or 'utf-8'
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            self.logger.error(f"Error al acceder a {url}: {e}")
            return None

    def extraer_fechas(self, soup: BeautifulSoup, url: str) -> tuple:
        """Extrae fecha y hora de una noticia"""
        fecha, hora = "", ""
        
        # Múltiples selectores para fechas
        selectores_fecha = [
            '.entry-date', '.post-date', '.date', '.published',
            'time[datetime]', '.entry-meta time', '.post-meta .date',
            '[class*="date"]', '[class*="time"]'
        ]
        
        for selector in selectores_fecha:
            elemento = soup.select_one(selector)
            if elemento:
                # Si tiene atributo datetime
                if elemento.get('datetime'):
                    fecha_completa = elemento['datetime']
                else:
                    fecha_completa = elemento.get_text().strip()
                
                # Procesar la fecha
                if fecha_completa:
                    try:
                        # Intentar extraer fecha y hora
                        if 'T' in fecha_completa:
                            partes = fecha_completa.split('T')
                            fecha = partes[0]
                            hora = partes[1].split('+')[0] if '+' in partes[1] else partes[1]
                        else:
                            # Usar regex para extraer fecha
                            match_fecha = re.search(r'\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}', fecha_completa)
                            if match_fecha:
                                fecha = match_fecha.group()
                            
                            match_hora = re.search(r'\d{1,2}:\d{2}(?::\d{2})?', fecha_completa)
                            if match_hora:
                                hora = match_hora.group()
                    except:
                        pass
                
                if fecha:
                    break
        
        return fecha, hora

    def extraer_imagenes(self, soup: BeautifulSoup, url: str) -> List[str]:
        """Extrae hasta 2 imágenes principales de la noticia"""
        imagenes = []
        base_domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        
        # Selectores para imágenes principales
        selectores_img = [
            '.entry-content img', '.post-content img', '.article-content img',
            '.featured-image img', '.post-thumbnail img', '.wp-post-image',
            'article img', '.content img', 'img[src*="wp-content"]'
        ]
        
        for selector in selectores_img:
            imgs = soup.select(selector)
            for img in imgs:
                src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                if src and len(imagenes) < 2:
                    # Convertir a URL absoluta
                    if src.startswith('//'):
                        src = f"https:{src}"
                    elif src.startswith('/'):
                        src = f"{base_domain}{src}"
                    elif not src.startswith('http'):
                        src = urljoin(url, src)
                    
                    # Filtrar imágenes pequeñas o iconos
                    if not any(x in src.lower() for x in ['icon', 'logo', 'avatar', 'emoji']):
                        if src not in imagenes:
                            imagenes.append(src)
                
                if len(imagenes) >= 2:
                    break
            
            if len(imagenes) >= 2:
                break
        
        return imagenes

    def limpiar_texto(self, texto: str) -> str:
        """Limpia y formatea texto"""
        if not texto:
            return ""
        
        # Eliminar etiquetas HTML residuales
        texto = re.sub(r'<[^>]+>', '', texto)
        # Normalizar espacios
        texto = re.sub(r'\s+', ' ', texto)
        # Eliminar caracteres especiales problemáticos
        texto = texto.replace('\u00a0', ' ').replace('\r', '').replace('\n', ' ')
        return texto.strip()

    def extraer_noticia(self, url: str) -> Dict:
        """Extrae todos los datos de una noticia individual"""
        soup = self.hacer_request(url)
        if not soup:
            return None
        
        # Título
        titulo_selectors = ['h1.entry-title', 'h1.post-title', 'h1', '.entry-title', '.post-title', 'title']
        titulo = ""
        for selector in titulo_selectors:
            elemento = soup.select_one(selector)
            if elemento:
                titulo = self.limpiar_texto(elemento.get_text())
                break
        
        # Contenido principal
        contenido_selectors = [
            '.entry-content', '.post-content', '.article-content',
            '.content', 'article .content', '.post-body', '.entry-body'
        ]
        contenido = ""
        for selector in contenido_selectors:
            elemento = soup.select_one(selector)
            if elemento:
                contenido = self.limpiar_texto(elemento.get_text())
                break
        
        # Resumen (excerpt o primeros párrafos)
        resumen = ""
        resumen_selectors = ['.entry-excerpt', '.post-excerpt', '.excerpt', '.summary']
        for selector in resumen_selectors:
            elemento = soup.select_one(selector)
            if elemento:
                resumen = self.limpiar_texto(elemento.get_text())
                break
        
        # Si no hay resumen, usar primeros 300 caracteres del contenido
        if not resumen and contenido:
            resumen = contenido[:300] + "..." if len(contenido) > 300 else contenido
        
        # Fecha y hora
        fecha, hora = self.extraer_fechas(soup, url)
        
        # Autor
        autor_selectors = ['.author', '.post-author', '.entry-author', '.by-author', '[rel="author"]']
        autor = ""
        for selector in autor_selectors:
            elemento = soup.select_one(selector)
            if elemento:
                autor = self.limpiar_texto(elemento.get_text())
                break
        
        # Categoría
        categoria_selectors = ['.category', '.post-category', '.entry-category', '.categories']
        categoria = ""
        for selector in categoria_selectors:
            elemento = soup.select_one(selector)
            if elemento:
                categoria = self.limpiar_texto(elemento.get_text())
                break
        
        # Tags
        tags_selectors = ['.tags', '.post-tags', '.entry-tags', '.tag-links']
        tags = ""
        for selector in tags_selectors:
            elementos = soup.select(selector + ' a, ' + selector)
            if elementos:
                tags = ", ".join([self.limpiar_texto(tag.get_text()) for tag in elementos])
                break
        
        # Imágenes
        imagenes = self.extraer_imagenes(soup, url)
        
        # Crear hash del contenido para evitar duplicados
        hash_contenido = hashlib.md5((titulo + contenido).encode('utf-8')).hexdigest()
        
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
            'fecha_extraccion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'link_imagenes': "; ".join(imagenes),
            'hash_contenido': hash_contenido
        }

    def encontrar_enlaces_noticias(self, soup: BeautifulSoup, base_url: str) -> Set[str]:
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
        
        return enlaces

    def encontrar_paginas_navegacion(self, soup: BeautifulSoup, base_url: str) -> Set[str]:
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
        
        return paginas

    def guardar_noticia(self, noticia: Dict):
        """Guarda una noticia en CSV y JSON"""
        # Guardar en CSV
        with open(self.csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=noticia.keys())
            writer.writerow(noticia)
        
        # Guardar en JSON
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                noticias = json.load(f)
        except:
            noticias = []
        
        noticias.append(noticia)
        
        with open(self.json_file, 'w', encoding='utf-8') as f:
            json.dump(noticias, f, ensure_ascii=False, indent=2)

    def scrape_recursivo(self, max_depth=10):
        """Ejecuta scraping recursivo completo"""
        self.logger.info("Iniciando scraping recursivo de Pachamama Radio")
        
        urls_por_procesar = {self.base_url}
        urls_visitadas = set()
        depth = 0
        total_noticias = 0
        
        while urls_por_procesar and depth < max_depth:
            self.logger.info(f"Procesando nivel {depth + 1}, URLs pendientes: {len(urls_por_procesar)}")
            
            urls_nivel_actual = urls_por_procesar.copy()
            urls_por_procesar.clear()
            
            for url in urls_nivel_actual:
                if url in urls_visitadas:
                    continue
                
                self.logger.info(f"Procesando: {url}")
                urls_visitadas.add(url)
                
                soup = self.hacer_request(url)
                if not soup:
                    continue
                
                # Si parece ser una noticia individual, extraerla
                if self.es_noticia_individual(soup, url):
                    if url not in self.urls_procesadas:
                        noticia = self.extraer_noticia(url)
                        if noticia and noticia['titulo']:
                            self.guardar_noticia(noticia)
                            self.guardar_url_procesada(url)
                            total_noticias += 1
                            self.logger.info(f"Noticia extraída: {noticia['titulo'][:50]}...")
                
                # Buscar más enlaces
                enlaces_noticias = self.encontrar_enlaces_noticias(soup, url)
                enlaces_paginas = self.encontrar_paginas_navegacion(soup, url)
                
                # Añadir enlaces no visitados
                for enlace in enlaces_noticias | enlaces_paginas:
                    if enlace not in urls_visitadas and enlace not in self.urls_procesadas:
                        urls_por_procesar.add(enlace)
                
                # Delay entre peticiones
                time.sleep(self.delay)
            
            depth += 1
            self.logger.info(f"Nivel {depth} completado. Noticias extraídas hasta ahora: {total_noticias}")
        
        self.logger.info(f"Scraping completado. Total de noticias extraídas: {total_noticias}")

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

    def ejecutar_scraping_incremental(self):
        """Ejecuta scraping incremental (para ejecuciones posteriores)"""
        self.logger.info("Ejecutando scraping incremental")
        
        # Buscar nuevas noticias desde la página principal y páginas recientes
        urls_base = [
            self.base_url,
            f"{self.base_url}noticias/",
            f"{self.base_url}blog/",
        ]
        
        # Añadir páginas de fechas recientes
        fecha_actual = datetime.now()
        for i in range(5):  # Últimos 5 días
            fecha = fecha_actual.strftime('%Y/%m/%d')
            urls_base.append(f"{self.base_url}{fecha}/")
        
        nuevas_noticias = 0
        
        for url_base in urls_base:
            soup = self.hacer_request(url_base)
            if not soup:
                continue
            
            enlaces = self.encontrar_enlaces_noticias(soup, url_base)
            
            for enlace in enlaces:
                if enlace not in self.urls_procesadas:
                    noticia = self.extraer_noticia(enlace)
                    if noticia and noticia['titulo']:
                        self.guardar_noticia(noticia)
                        self.guardar_url_procesada(enlace)
                        nuevas_noticias += 1
                        self.logger.info(f"Nueva noticia: {noticia['titulo'][:50]}...")
                    
                    time.sleep(self.delay)
        
        self.logger.info(f"Scraping incremental completado. Nuevas noticias: {nuevas_noticias}")


def main():
    """Función principal"""
    scraper = PachamamaRadioScraper(delay=2)  # 2 segundos entre peticiones
    
    print("=== SCRAPER PACHAMAMA RADIO ===")
    print("1. Scraping completo (primera vez)")
    print("2. Scraping incremental (solo nuevas noticias)")
    
    opcion = input("Selecciona una opción (1 o 2): ").strip()
    
    if opcion == "1":
        print("Iniciando scraping completo...")
        scraper.scrape_recursivo(max_depth=15)
    elif opcion == "2":
        print("Iniciando scraping incremental...")
        scraper.ejecutar_scraping_incremental()
    else:
        print("Opción no válida")
        return
    
    print(f"\nScraping completado!")
    print(f"Datos guardados en:")
    print(f"- CSV: {scraper.csv_file}")
    print(f"- JSON: {scraper.json_file}")
    print(f"- Log: scraping.log")


if __name__ == "__main__":
    main()