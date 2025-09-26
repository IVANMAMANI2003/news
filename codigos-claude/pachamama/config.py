# config.py
import os


class Config:
    # Configuraciones del scraper
    BASE_URL = "https://pachamamaradio.org/"
    DELAY_BETWEEN_REQUESTS = 2  # segundos
    MAX_DEPTH = 15  # niveles de profundidad
    TIMEOUT = 30  # segundos para requests
    
    # Archivos de salida
    CSV_FILE = "noticias_pachamama.csv"
    JSON_FILE = "noticias_pachamama.json"
    URLS_PROCESADAS_FILE = "urls_procesadas.txt"
    LOG_FILE = "scraping.log"
    
    # Headers HTTP
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    # Configuraciones de filtrado
    EXCLUDED_EXTENSIONS = ['.jpg', '.png', '.gif', '.pdf', '.doc', '.docx', '.zip']
    EXCLUDED_PATHS = ['wp-admin', 'wp-content', 'wp-includes', 'feed', 'rss']
    
    # Límites
    MAX_IMAGES_PER_NEWS = 2
    SUMMARY_LENGTH = 300