# config.py
class Config:
    # URLs y configuración del sitio
    BASE_URL = "https://punonoticias.pe/"
    
    # Configuración de scraping
    DELAY_BETWEEN_REQUESTS = 1  # segundos
    MAX_RETRIES = 3
    TIMEOUT = 30  # segundos
    
    # Archivos de salida
    CSV_OUTPUT = "noticias_completas.csv"
    JSON_OUTPUT = "noticias_data.json"
    SCRAPED_URLS_FILE = "scraped_urls.txt"
    
    # Configuración de programación
    SCRAPING_INTERVALS = [
        "06:00",  # 6 AM
        "12:00",  # 12 PM  
        "18:00"   # 6 PM
    ]
    
    # Headers para requests
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }

# setup.py - Script de instalación
import subprocess
import sys


def install_requirements():
    """Instalar requirements"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Requirements instalados correctamente")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error instalando requirements: {e}")

def setup_directories():
    """Crear directorios necesarios"""
    import os
    
    directories = [
        "logs",
        "data", 
        "exports"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"📁 Directorio '{directory}' creado")

if __name__ == "__main__":
    print("🚀 Configurando entorno de scraping...")
    install_requirements()
    setup_directories()
    print("✅ Configuración completada")