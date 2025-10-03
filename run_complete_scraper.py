#!/usr/bin/env python3
"""
Script para ejecutar el scraping completo de todas las fuentes
y guardar los archivos en la carpeta data/
"""

import json
import logging
import os
import sys
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def ensure_data_directory():
    """Asegurar que existe el directorio data/"""
    if not os.path.exists('data'):
        os.makedirs('data')
        print("📁 Directorio 'data/' creado")
    else:
        print("📁 Directorio 'data/' ya existe")

def run_individual_scrapers():
    """Ejecutar scrapers individuales y cargar a BD"""
    print("🚀 EJECUTANDO SCRAPERS INDIVIDUALES")
    print("=" * 50)
    
    # Lista de scrapers disponibles (nuevos)
    scrapers = [
        {
            'name': 'pachamama',
            'file': 'scrapers/pachamama_scraper.py',
            'class': 'PachamamaRadioScraper'
        },
        {
            'name': 'los_andes', 
            'file': 'scrapers/los_andes_scraper.py',
            'class': 'LosAndesScraper'
        },
        {
            'name': 'puno_noticias',
            'file': 'scrapers/puno_noticias_scraper.py', 
            'class': 'PunoNoticiasScraper'
        },
        {
            'name': 'diario_sin_fronteras',
            'file': 'scrapers/diario_sin_fronteras_scraper.py',
            'class': 'DiarioSinFronterasScraper'
        }
    ]
    
    total_noticias = 0
    
    for scraper_info in scrapers:
        if not os.path.exists(scraper_info['file']):
            print(f"⚠️ {scraper_info['name']}: Archivo no encontrado")
            continue
            
        print(f"\n📰 Procesando: {scraper_info['name']}")
        print("-" * 30)
        
        try:
            # Importar y ejecutar scraper
            sys.path.append(os.path.dirname(scraper_info['file']))
            
            if scraper_info['name'] == 'pachamama':
                from scrapers.pachamama_scraper import PachamamaRadioScraper
                scraper = PachamamaRadioScraper()
                scraper.scrape_noticias(max_noticias=50)
                
                # Cargar noticias a BD
                noticias = load_noticias_from_scraper(scraper, scraper_info['name'])
                
            elif scraper_info['name'] == 'los_andes':
                from scrapers.los_andes_scraper import LosAndesScraper
                scraper = LosAndesScraper()
                scraper.scrape_noticias(max_noticias=50)
                
                # Cargar noticias a BD
                noticias = load_noticias_from_scraper(scraper, scraper_info['name'])
                
            elif scraper_info['name'] == 'puno_noticias':
                from scrapers.puno_noticias_scraper import PunoNoticiasScraper
                scraper = PunoNoticiasScraper()
                scraper.scrape_noticias(max_noticias=50)
                
                # Cargar noticias a BD
                noticias = load_noticias_from_scraper(scraper, scraper_info['name'])
                
            elif scraper_info['name'] == 'diario_sin_fronteras':
                from scrapers.diario_sin_fronteras_scraper import \
                    DiarioSinFronterasScraper
                scraper = DiarioSinFronterasScraper()
                scraper.scrape_noticias(max_noticias=50)
                
                # Cargar noticias a BD
                noticias = load_noticias_from_scraper(scraper, scraper_info['name'])
            
            total_noticias += len(noticias) if noticias else 0
            print(f"✅ {scraper_info['name']}: {len(noticias) if noticias else 0} noticias")
            
        except Exception as e:
            print(f"❌ Error en {scraper_info['name']}: {e}")
            continue
    
    return total_noticias

def load_noticias_from_file(json_file, fuente):
    """Cargar noticias desde archivo JSON a la base de datos"""
    if not os.path.exists(json_file):
        return []
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            noticias = json.load(f)
        
        # Mover archivo a carpeta data/
        move_file_to_data(json_file)
        
        # Cargar a base de datos
        return load_noticias_to_database(noticias, fuente)
        
    except Exception as e:
        print(f"❌ Error cargando {json_file}: {e}")
        return []

def load_noticias_from_scraper(scraper, fuente):
    """Cargar noticias desde objeto scraper a la base de datos"""
    try:
        noticias = []
        
        if hasattr(scraper, 'news_data'):
            noticias = scraper.news_data
        elif hasattr(scraper, 'json_file') and os.path.exists(scraper.json_file):
            with open(scraper.json_file, 'r', encoding='utf-8') as f:
                noticias = json.load(f)
        
        # Mover archivos a carpeta data/
        if hasattr(scraper, 'csv_file') and os.path.exists(scraper.csv_file):
            move_file_to_data(scraper.csv_file)
        if hasattr(scraper, 'json_file') and os.path.exists(scraper.json_file):
            move_file_to_data(scraper.json_file)
        
        # Cargar a base de datos
        return load_noticias_to_database(noticias, fuente)
        
    except Exception as e:
        print(f"❌ Error cargando noticias del scraper: {e}")
        return []

def move_file_to_data(filename):
    """Mover archivo a la carpeta data/"""
    try:
        if os.path.exists(filename):
            new_path = os.path.join('data', os.path.basename(filename))
            os.rename(filename, new_path)
            print(f"📁 Movido: {filename} → {new_path}")
    except Exception as e:
        print(f"⚠️ Error moviendo {filename}: {e}")

def load_noticias_to_database(noticias, fuente):
    """Cargar noticias a la base de datos"""
    if not noticias:
        return []
    
    try:
        from database import DatabaseManager
        
        with DatabaseManager() as db:
            if not db.connection:
                print("❌ Error conectando a la base de datos")
                return []
            
            noticias_cargadas = 0
            for noticia in noticias:
                # Normalizar datos
                noticia_normalizada = {
                    'titulo': noticia.get('titulo', ''),
                    'fecha': noticia.get('fecha', ''),
                    'hora': noticia.get('hora', ''),
                    'resumen': noticia.get('resumen', ''),
                    'contenido': noticia.get('contenido', ''),
                    'categoria': noticia.get('categoria', ''),
                    'autor': noticia.get('autor', ''),
                    'tags': noticia.get('tags', ''),
                    'url': noticia.get('url', ''),
                    'link_imagenes': noticia.get('link_imagenes', ''),
                    'fuente': fuente,
                    'fecha_extraccion': noticia.get('fecha_extraccion', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                }
                
                # Insertar en base de datos
                if db.insert_noticia(noticia_normalizada):
                    noticias_cargadas += 1
            
            print(f"💾 {noticias_cargadas} noticias cargadas a BD")
            return noticias_cargadas
            
    except Exception as e:
        print(f"❌ Error cargando a BD: {e}")
        return []

def show_final_stats():
    """Mostrar estadísticas finales"""
    print("\n📊 ESTADÍSTICAS FINALES")
    print("=" * 50)
    
    try:
        from database import DatabaseManager
        
        with DatabaseManager() as db:
            stats = db.get_estadisticas()
            print(f"Total noticias en BD: {stats.get('total_noticias', 0)}")
            print("Por fuente:")
            for fuente, cantidad in stats.get('noticias_por_fuente', {}).items():
                print(f"  {fuente}: {cantidad}")
            
            # Mostrar archivos en data/
            print(f"\n📁 Archivos en carpeta data/:")
            if os.path.exists('data'):
                files = os.listdir('data')
                for file in files:
                    print(f"  - {file}")
            else:
                print("  (carpeta vacía)")
    
    except Exception as e:
        print(f"❌ Error obteniendo estadísticas: {e}")

def main():
    print("🚀 SCRAPER COMPLETO - TODAS LAS FUENTES")
    print("=" * 60)
    print("Este script ejecutará el scraping de todas las fuentes")
    print("y guardará los archivos en la carpeta data/")
    print("=" * 60)
    
    # Asegurar directorio data/
    ensure_data_directory()
    
    # Ejecutar scrapers
    total_noticias = run_individual_scrapers()
    
    # Mostrar estadísticas
    show_final_stats()
    
    print(f"\n🎉 SCRAPING COMPLETADO")
    print(f"📰 Total noticias procesadas: {total_noticias}")
    print(f"📁 Archivos guardados en: data/")
    print(f"💾 Base de datos: PostgreSQL")

if __name__ == "__main__":
    main()
