#!/usr/bin/env python3
"""
Script de prueba para verificar que todo el sistema funcione correctamente
"""

import os
import sys


def test_imports():
    """Probar todas las importaciones"""
    print("🔍 Probando importaciones...")
    
    try:
        from database import DatabaseManager
        print("✅ DatabaseManager importado correctamente")
    except Exception as e:
        print(f"❌ Error importando DatabaseManager: {e}")
        return False
    
    try:
        from unified_scraper import normalize_news_data, save_news_files
        print("✅ Funciones de unified_scraper importadas correctamente")
    except Exception as e:
        print(f"❌ Error importando funciones de unified_scraper: {e}")
        return False
    
    try:
        from celery_config import celery_app
        print("✅ Celery app importado correctamente")
    except Exception as e:
        print(f"❌ Error importando Celery app: {e}")
        return False
    
    try:
        from celery_tasks import scheduled_scraping, scrape_source
        print("✅ Tareas de Celery importadas correctamente")
    except Exception as e:
        print(f"❌ Error importando tareas de Celery: {e}")
        return False
    
    # Probar scrapers individuales
    scrapers = [
        ('scrapers.pachamama_scraper', 'PachamamaRadioScraper'),
        ('scrapers.los_andes_scraper', 'LosAndesScraper'),
        ('scrapers.puno_noticias_scraper', 'PunoNoticiasScraper'),
        ('scrapers.diario_sin_fronteras_scraper', 'DiarioSinFronterasScraper')
    ]
    
    for module_name, class_name in scrapers:
        try:
            module = __import__(module_name, fromlist=[class_name])
            scraper_class = getattr(module, class_name)
            print(f"✅ {class_name} importado correctamente")
        except Exception as e:
            print(f"❌ Error importando {class_name}: {e}")
            return False
    
    return True

def test_scrapers():
    """Probar que los scrapers tengan el método scrape_noticias"""
    print("\n🔍 Probando scrapers...")
    
    scrapers = [
        ('scrapers.pachamama_scraper', 'PachamamaRadioScraper'),
        ('scrapers.los_andes_scraper', 'LosAndesScraper'),
        ('scrapers.puno_noticias_scraper', 'PunoNoticiasScraper'),
        ('scrapers.diario_sin_fronteras_scraper', 'DiarioSinFronterasScraper')
    ]
    
    for module_name, class_name in scrapers:
        try:
            module = __import__(module_name, fromlist=[class_name])
            scraper_class = getattr(module, class_name)
            
            # Verificar que tenga el método scrape_noticias
            if hasattr(scraper_class, 'scrape_noticias'):
                print(f"✅ {class_name} tiene método scrape_noticias")
            else:
                print(f"❌ {class_name} NO tiene método scrape_noticias")
                return False
                
        except Exception as e:
            print(f"❌ Error probando {class_name}: {e}")
            return False
    
    return True

def test_celery_tasks():
    """Probar que las tareas de Celery estén configuradas correctamente"""
    print("\n🔍 Probando tareas de Celery...")
    
    try:
        from celery_tasks import celery_app

        # Verificar que las tareas estén registradas
        registered_tasks = list(celery_app.tasks.keys())
        expected_tasks = [
            'news_scraper.tasks.scheduled_scraping',
            'news_scraper.tasks.scrape_source',
            'news_scraper.tasks.save_to_database',
            'news_scraper.tasks.process_news_batch',
            'news_scraper.tasks.cleanup_old_data'
        ]
        
        for task in expected_tasks:
            if task in registered_tasks:
                print(f"✅ Tarea {task} registrada")
            else:
                print(f"❌ Tarea {task} NO registrada")
                return False
        
        # Verificar configuración de beat
        beat_schedule = celery_app.conf.beat_schedule
        if 'scrape-news-every-hour' in beat_schedule:
            print("✅ Tarea programada 'scrape-news-every-hour' configurada")
        else:
            print("❌ Tarea programada 'scrape-news-every-hour' NO configurada")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error probando tareas de Celery: {e}")
        return False

def test_database_connection():
    """Probar conexión a la base de datos"""
    print("\n🔍 Probando conexión a base de datos...")
    
    try:
        from database import DatabaseManager

        # Crear instancia del manager
        db_manager = DatabaseManager()
        
        # Probar conexión
        if db_manager.health_check():
            print("✅ Conexión a base de datos exitosa")
            return True
        else:
            print("❌ Error en conexión a base de datos")
            return False
            
    except Exception as e:
        print(f"❌ Error probando base de datos: {e}")
        return False

def main():
    """Función principal de prueba"""
    print("🚀 INICIANDO PRUEBAS DEL SISTEMA DE SCRAPING")
    print("=" * 50)
    
    tests = [
        ("Importaciones", test_imports),
        ("Scrapers", test_scrapers),
        ("Tareas de Celery", test_celery_tasks),
        ("Base de datos", test_database_connection)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Ejecutando: {test_name}")
        if test_func():
            passed += 1
            print(f"✅ {test_name}: PASÓ")
        else:
            print(f"❌ {test_name}: FALLÓ")
    
    print("\n" + "=" * 50)
    print(f"📊 RESULTADOS: {passed}/{total} pruebas pasaron")
    
    if passed == total:
        print("🎉 ¡TODAS LAS PRUEBAS PASARON! El sistema está listo.")
        return True
    else:
        print("⚠️  Algunas pruebas fallaron. Revisar errores arriba.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

