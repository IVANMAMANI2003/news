"""
Script principal para ejecutar el sistema de scraping de noticias
"""
import logging
import sys
from datetime import datetime

from news_scraper_manager import NewsScraperManager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Función principal"""
    print("=" * 60)
    print("SISTEMA DE SCRAPING DE NOTICIAS AUTOMATIZADO")
    print("=" * 60)
    print(f"Iniciado en: {datetime.now()}")
    print()
    
    # Crear gestor de scraping
    manager = NewsScraperManager()
    
    try:
        # Configurar base de datos
        print("Configurando base de datos...")
        if not manager.setup_database():
            print("❌ Error configurando base de datos")
            return 1
        
        print("✅ Base de datos configurada correctamente")
        print()
        
        # Mostrar menú de opciones
        while True:
            print("\n" + "=" * 40)
            print("MENÚ PRINCIPAL")
            print("=" * 40)
            print("1. Ejecutar scraping completo (todas las fuentes)")
            print("2. Ejecutar scraping de una fuente específica")
            print("3. Generar archivos consolidados")
            print("4. Mostrar estadísticas")
            print("5. Iniciar modo programado (cada hora)")
            print("6. Salir")
            print()
            
            try:
                opcion = input("Seleccione una opción (1-6): ").strip()
                
                if opcion == "1":
                    print("\n🔄 Ejecutando scraping completo...")
                    results = manager.scrape_all_sources()
                    print(f"✅ Scraping completado. Resultados: {results}")
                    
                elif opcion == "2":
                    print("\nFuentes disponibles:")
                    for i, (key, source) in enumerate(manager.scrapers.items(), 1):
                        print(f"{i}. {source.source_name}")
                    
                    try:
                        fuente_idx = int(input("Seleccione una fuente (número): ")) - 1
                        fuente_keys = list(manager.scrapers.keys())
                        if 0 <= fuente_idx < len(fuente_keys):
                            fuente_key = fuente_keys[fuente_idx]
                            print(f"\n🔄 Ejecutando scraping de {manager.scrapers[fuente_key].source_name}...")
                            results = manager.scrape_single_source(fuente_key)
                            print(f"✅ Scraping completado. Noticias extraídas: {results}")
                        else:
                            print("❌ Opción inválida")
                    except ValueError:
                        print("❌ Por favor ingrese un número válido")
                
                elif opcion == "3":
                    print("\n🔄 Generando archivos consolidados...")
                    manager.generate_consolidated_files()
                    print("✅ Archivos consolidados generados")
                
                elif opcion == "4":
                    print("\n📊 Obteniendo estadísticas...")
                    stats = manager.get_statistics()
                    if stats:
                        print("\nESTADÍSTICAS DEL SISTEMA:")
                        print(f"Total de noticias: {stats.get('total_noticias', 0)}")
                        print(f"Noticias últimas 24h: {stats.get('ultimas_24h', 0)}")
                        print("\nPor fuente:")
                        for fuente, count in stats.get('por_fuente', {}).items():
                            print(f"  - {fuente}: {count}")
                    else:
                        print("❌ No se pudieron obtener estadísticas")
                
                elif opcion == "5":
                    print("\n⏰ Iniciando modo programado (cada hora)...")
                    print("Presione Ctrl+C para detener")
                    try:
                        from scheduler import NewsScrapingScheduler
                        scheduler = NewsScrapingScheduler()
                        scheduler.start_scheduler(interval_hours=1)
                    except KeyboardInterrupt:
                        print("\n⏹️ Modo programado detenido")
                
                elif opcion == "6":
                    print("\n👋 Saliendo del sistema...")
                    break
                
                else:
                    print("❌ Opción no válida. Por favor seleccione 1-6.")
                
            except KeyboardInterrupt:
                print("\n\n👋 Saliendo del sistema...")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                logger.error(f"Error en menú principal: {e}")
    
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        logger.error(f"Error crítico: {e}")
        return 1
    
    finally:
        manager.close()
        print("✅ Sistema cerrado correctamente")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
