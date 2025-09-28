#!/usr/bin/env python3
"""
Script de prueba para el sistema de scraping local
"""

import logging
import os
import sys
from datetime import datetime

# Configurar logging básico
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_database_connection():
    """Probar conexión a la base de datos"""
    try:
        from database import DatabaseManager
        
        logger.info("Probando conexión a PostgreSQL...")
        
        # Intentar conectar
        db = DatabaseManager()
        
        # Crear base de datos si no existe
        if db.create_database_if_not_exists():
            logger.info("✅ Base de datos creada/verificada")
        else:
            logger.error("❌ Error creando base de datos")
            return False
        
        # Conectar
        if db.connect():
            logger.info("✅ Conexión a PostgreSQL exitosa")
            
            # Crear tablas
            if db.create_tables():
                logger.info("✅ Tablas creadas exitosamente")
                
                # Probar inserción
                test_noticia = {
                    'titulo': 'Noticia de prueba',
                    'fecha': '2024-01-01',
                    'hora': '12:00:00',
                    'resumen': 'Resumen de prueba',
                    'contenido': 'Contenido de prueba',
                    'categoria': 'General',
                    'autor': 'Sistema',
                    'tags': 'prueba,test',
                    'url': 'https://ejemplo.com/prueba',
                    'link_imagenes': '',
                    'fuente': 'sistema',
                    'fecha_extraccion': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                if db.insert_noticia(test_noticia):
                    logger.info("✅ Inserción de prueba exitosa")
                else:
                    logger.info("ℹ️ Noticia de prueba ya existe (normal)")
                
                # Obtener estadísticas
                stats = db.get_estadisticas()
                logger.info(f"📊 Estadísticas: {stats.get('total_noticias', 0)} noticias en BD")
                
                db.close()
                return True
            else:
                logger.error("❌ Error creando tablas")
                return False
        else:
            logger.error("❌ Error conectando a PostgreSQL")
            return False
            
    except ImportError as e:
        logger.error(f"❌ Error importando módulos: {e}")
        logger.info("💡 Instala las dependencias: pip install -r requirements.txt")
        return False
    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}")
        return False

def test_scrapers():
    """Probar los scrapers individuales"""
    logger.info("Probando scrapers individuales...")
    
    # Verificar que existen los archivos de scrapers
    scraper_files = [
        'codigos-claude/diario-sinfronteras/sin-fronteras.py',
        'codigos-claude/los-andes/los-andes.py', 
        'codigos-claude/pachamama/pachamama.py',
        'codigos-claude/puno-noticias/puno-noticias.py'
    ]
    
    for file_path in scraper_files:
        if os.path.exists(file_path):
            logger.info(f"✅ {file_path} existe")
        else:
            logger.warning(f"⚠️ {file_path} no encontrado")
    
    return True

def test_unified_scraper():
    """Probar el scraper unificado"""
    try:
        logger.info("Probando scraper unificado...")
        
        # Importar el scraper unificado
        from unified_scraper import UnifiedNewsScraper

        # Crear instancia
        scraper = UnifiedNewsScraper()
        logger.info("✅ Scraper unificado creado exitosamente")
        
        # Probar normalización de datos
        test_data = {
            'titulo': 'Noticia de prueba',
            'fecha': '01/01/2024',
            'hora': '12:00',
            'resumen': 'Resumen de prueba',
            'contenido': 'Contenido de prueba',
            'categoria': 'General',
            'autor': 'Autor de prueba',
            'tags': ['prueba', 'test'],
            'url': 'https://ejemplo.com/prueba',
            'link_imagenes': ['https://ejemplo.com/imagen.jpg']
        }
        
        normalized = scraper.normalize_news_data(test_data, 'test_source')
        logger.info("✅ Normalización de datos exitosa")
        logger.info(f"📝 Datos normalizados: {normalized['titulo']}")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Error importando scraper unificado: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error probando scraper unificado: {e}")
        return False

def test_scheduler():
    """Probar el scheduler"""
    try:
        logger.info("Probando scheduler...")
        
        from scheduler import NewsScrapingScheduler

        # Crear instancia
        scheduler = NewsScrapingScheduler()
        logger.info("✅ Scheduler creado exitosamente")
        
        # Obtener estado
        status = scheduler.get_scheduler_status()
        logger.info(f"📊 Estado del scheduler: {status['running']}")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Error importando scheduler: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error probando scheduler: {e}")
        return False

def main():
    """Función principal de prueba"""
    print("=" * 60)
    print("🧪 PRUEBAS DEL SISTEMA DE SCRAPING LOCAL")
    print("=" * 60)
    
    tests = [
        ("Base de datos PostgreSQL", test_database_connection),
        ("Scrapers individuales", test_scrapers),
        ("Scraper unificado", test_unified_scraper),
        ("Scheduler", test_scheduler)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔍 Probando: {test_name}")
        print("-" * 40)
        
        try:
            result = test_func()
            results.append((test_name, result))
            
            if result:
                print(f"✅ {test_name}: EXITOSO")
            else:
                print(f"❌ {test_name}: FALLÓ")
                
        except Exception as e:
            print(f"💥 {test_name}: ERROR - {e}")
            results.append((test_name, False))
    
    # Resumen final
    print("\n" + "=" * 60)
    print("📋 RESUMEN DE PRUEBAS")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ EXITOSO" if result else "❌ FALLÓ"
        print(f"{test_name}: {status}")
    
    print(f"\n🎯 Resultado: {passed}/{total} pruebas exitosas")
    
    if passed == total:
        print("🎉 ¡Todas las pruebas pasaron! El sistema está listo.")
        print("\n📝 Próximos pasos:")
        print("1. Ejecutar: python unified_scraper.py")
        print("2. O ejecutar: python scheduler.py")
    else:
        print("⚠️ Algunas pruebas fallaron. Revisa los errores arriba.")
        print("\n🔧 Soluciones comunes:")
        print("1. Instalar PostgreSQL y crear usuario 'postgres' con password '123456'")
        print("2. Instalar dependencias: pip install -r requirements.txt")
        print("3. Verificar que los archivos de scrapers existan en codigos-claude/")

if __name__ == "__main__":
    main()
