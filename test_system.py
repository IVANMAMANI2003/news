"""
Script de prueba para verificar el funcionamiento del sistema
"""
import logging
import sys
from datetime import datetime

from news_scraper_manager import NewsScraperManager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_database_connection():
    """Probar conexión a la base de datos"""
    print("🔍 Probando conexión a la base de datos...")
    
    try:
        manager = NewsScraperManager()
        
        # Crear base de datos si no existe
        if not manager.db_manager.create_database_if_not_exists():
            print("❌ Error creando base de datos")
            return False
        
        # Conectar
        if not manager.db_manager.connect():
            print("❌ Error conectando a la base de datos")
            return False
        
        # Crear tablas
        if not manager.db_manager.create_tables():
            print("❌ Error creando tablas")
            return False
        
        print("✅ Conexión a base de datos exitosa")
        manager.close()
        return True
        
    except Exception as e:
        print(f"❌ Error en prueba de base de datos: {e}")
        return False

def test_scrapers_initialization():
    """Probar inicialización de scrapers"""
    print("🔍 Probando inicialización de scrapers...")
    
    try:
        manager = NewsScraperManager()
        
        if not manager.scrapers:
            print("❌ No se pudieron inicializar scrapers")
            return False
        
        print(f"✅ {len(manager.scrapers)} scrapers inicializados:")
        for key, scraper in manager.scrapers.items():
            print(f"   - {scraper.source_name}")
        
        manager.close()
        return True
        
    except Exception as e:
        print(f"❌ Error en prueba de scrapers: {e}")
        return False

def test_single_scraper():
    """Probar un scraper individual"""
    print("🔍 Probando scraper individual...")
    
    try:
        manager = NewsScraperManager()
        
        if not manager.setup_database():
            print("❌ Error configurando base de datos")
            return False
        
        # Probar con Los Andes (generalmente más estable)
        if 'los_andes' in manager.scrapers:
            print("   Probando Los Andes...")
            results = manager.scrape_single_source('los_andes')
            print(f"✅ Los Andes: {results} noticias extraídas")
        else:
            print("⚠️ Scraper de Los Andes no disponible")
        
        manager.close()
        return True
        
    except Exception as e:
        print(f"❌ Error en prueba de scraper individual: {e}")
        return False

def test_file_generation():
    """Probar generación de archivos"""
    print("🔍 Probando generación de archivos...")
    
    try:
        import json
        import os

        # Crear directorio de prueba
        test_dir = "test_data"
        os.makedirs(test_dir, exist_ok=True)
        
        # Datos de prueba
        test_data = [
            {
                'titulo': 'Noticia de prueba',
                'fecha': '2024-01-01',
                'hora': '12:00:00',
                'resumen': 'Esta es una noticia de prueba',
                'contenido': 'Contenido completo de la noticia de prueba',
                'categoria': 'Prueba',
                'autor': 'Sistema',
                'tags': 'prueba, test',
                'url': 'https://example.com/test',
                'link_imagenes': '',
                'fuente': 'Sistema de Prueba'
            }
        ]
        
        # Generar archivos
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # JSON
        json_file = os.path.join(test_dir, f"test_{timestamp}.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)
        
        # CSV
        import csv
        csv_file = os.path.join(test_dir, f"test_{timestamp}.csv")
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            if test_data:
                fieldnames = test_data[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(test_data)
        
        # Verificar archivos
        if os.path.exists(json_file) and os.path.exists(csv_file):
            print("✅ Archivos generados correctamente")
            print(f"   - JSON: {json_file}")
            print(f"   - CSV: {csv_file}")
            
            # Limpiar archivos de prueba
            os.remove(json_file)
            os.remove(csv_file)
            os.rmdir(test_dir)
            
            return True
        else:
            print("❌ Error generando archivos")
            return False
        
    except Exception as e:
        print(f"❌ Error en prueba de generación de archivos: {e}")
        return False

def main():
    """Función principal de pruebas"""
    print("=" * 60)
    print("🧪 SISTEMA DE PRUEBAS - SCRAPING DE NOTICIAS")
    print("=" * 60)
    print(f"Iniciado en: {datetime.now()}")
    print()
    
    tests = [
        ("Conexión a Base de Datos", test_database_connection),
        ("Inicialización de Scrapers", test_scrapers_initialization),
        ("Generación de Archivos", test_file_generation),
        ("Scraper Individual", test_single_scraper),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: EXITOSO")
            else:
                print(f"❌ {test_name}: FALLÓ")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE PRUEBAS")
    print("=" * 60)
    print(f"Pruebas pasadas: {passed}/{total}")
    print(f"Porcentaje de éxito: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 ¡Todas las pruebas pasaron! El sistema está listo.")
        return 0
    else:
        print("⚠️ Algunas pruebas fallaron. Revisar configuración.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
