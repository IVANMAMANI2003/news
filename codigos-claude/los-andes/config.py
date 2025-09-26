# config.py - Archivo de configuración
class ScrapingConfig:
    """Configuración centralizada para el scraper"""
    
    # Configuración de scraping
    BASE_URL = "https://losandes.com.pe"
    DELAY_BETWEEN_REQUESTS = 1  # segundos
    MAX_WORKERS = 5  # hilos concurrentes
    REQUEST_TIMEOUT = 30
    MAX_RETRIES = 3
    
    # Configuración de archivos
    SCRAPED_URLS_FILE = "scraped_urls.json"
    DATA_DIR = "data_noticias"
    
    # Configuración de logging
    LOG_LEVEL = "INFO"
    LOG_FILE = "scraper.log"
    
    # Límites de seguridad
    MAX_PAGES_PER_SECTION = 100
    MAX_IMAGES_PER_ARTICLE = 2
    MAX_TAGS_PER_ARTICLE = 10
    
    # Patrones de URLs
    ARTICLE_PATTERNS = [
        r'/\d{4}/',  # Contiene año
        r'/noticia/',
        r'/news/',
        r'/articulo/',
        r'/post/',
    ]
    
    EXCLUDE_PATTERNS = [
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
    
    # Secciones principales del sitio
    MAIN_SECTIONS = [
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