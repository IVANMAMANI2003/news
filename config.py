"""
Configuración centralizada para el sistema de scraping de noticias
"""
import os

from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class DatabaseConfig:
    """Configuración de la base de datos PostgreSQL"""
    HOST = os.getenv('DB_HOST', 'localhost')
    PORT = os.getenv('DB_PORT', '5432')
    DATABASE = os.getenv('DB_NAME', 'news_scraping')
    USER = os.getenv('DB_USER', 'postgres')
    PASSWORD = os.getenv('DB_PASSWORD', '123456')
    
    @classmethod
    def get_connection_string(cls):
        return f"postgresql://{cls.USER}:{cls.PASSWORD}@{cls.HOST}:{cls.PORT}/{cls.DATABASE}"

class CeleryConfig:
    """Configuración de Celery/Redis"""
    REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
    REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
    REDIS_DB = int(os.getenv('REDIS_DB', '0'))
    BROKER_URL = os.getenv('CELERY_BROKER_URL', f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")
    RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', BROKER_URL)
    TIMEZONE = os.getenv('CELERY_TIMEZONE', 'America/Lima')
    CONCURRENCY = int(os.getenv('CELERY_CONCURRENCY', '2'))

class ScrapingConfig:
    """Configuración general del scraping"""
    # Delays entre requests (segundos)
    DELAY_BETWEEN_REQUESTS = int(os.getenv('DELAY_BETWEEN_REQUESTS', '2'))
    DELAY_BETWEEN_SOURCES = int(os.getenv('DELAY_BETWEEN_SOURCES', '5'))
    
    # Configuración de threading
    MAX_WORKERS = int(os.getenv('MAX_WORKERS', '3'))
    
    # Timeouts
    REQUEST_TIMEOUT = 30
    MAX_RETRIES = 3
    
    # Límites
    MAX_IMAGES_PER_ARTICLE = 2
    MAX_TAGS_PER_ARTICLE = 10
    
    # Archivos de salida
    OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'data')
    LOG_FILE = os.getenv('LOG_FILE', 'scraper.log')
    
    # Configuración de ejecución recursiva
    EXECUTION_INTERVAL_HOURS = int(os.getenv('EXECUTION_INTERVAL_HOURS', '1'))

class NewsSources:
    """Configuración de las fuentes de noticias"""
    SOURCES = {
        'diario_sin_fronteras': {
            'name': 'Diario Sin Fronteras',
            'base_url': 'https://diariosinfronteras.com.pe/',
            'enabled': True,
            'delay': 2
        },
        'los_andes': {
            'name': 'Los Andes',
            'base_url': 'https://losandes.com.pe',
            'enabled': True,
            'delay': 1
        },
        'pachamama': {
            'name': 'Pachamama Radio',
            'base_url': 'https://pachamamaradio.org/',
            'enabled': True,
            'delay': 2
        },
        'puno_noticias': {
            'name': 'Puno Noticias',
            'base_url': 'https://punonoticias.pe/',
            'enabled': True,
            'delay': 1
        }
    }

class DatabaseSchema:
    """Esquema de la base de datos"""
    CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS noticias (
        id SERIAL PRIMARY KEY,
        titulo TEXT,
        fecha TIMESTAMP,
        hora TIME,
        resumen TEXT,
        contenido TEXT,
        categoria VARCHAR(100),
        autor VARCHAR(200),
        tags TEXT,
        url TEXT UNIQUE,
        fecha_extraccion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        link_imagenes TEXT,
        fuente VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    CREATE_INDEXES_SQL = [
        "CREATE INDEX IF NOT EXISTS idx_noticias_fuente ON noticias(fuente);",
        "CREATE INDEX IF NOT EXISTS idx_noticias_fecha ON noticias(fecha);",
        "CREATE INDEX IF NOT EXISTS idx_noticias_categoria ON noticias(categoria);",
        "CREATE INDEX IF NOT EXISTS idx_noticias_fecha_extraccion ON noticias(fecha_extraccion);"
    ]

class LoggingConfig:
    """Configuración de logging"""
    LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    FILE_HANDLER = True
    CONSOLE_HANDLER = True
