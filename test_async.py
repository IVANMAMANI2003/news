#!/usr/bin/env python3
"""
Script de prueba para el sistema asíncrono sin Redis
"""

import logging
import os
import sys
import time
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_async_scraping():
    """Probar scraping asíncrono simulado"""
    print("🚀 PROBANDO SISTEMA ASÍNCRONO SIMULADO")
    print("=" * 50)
    
    # Simular tareas asíncronas
    sources = ['pachamama', 'los_andes', 'puno_noticias', 'diario_sin_fronteras']
    
    print(f"📰 Iniciando scraping de {len(sources)} fuentes en paralelo...")
    
    start_time = time.time()
    
    # Simular procesamiento paralelo
    for i, source in enumerate(sources):
        print(f"🔄 Procesando {source}...")
        
        # Simular tiempo de scraping
        time.sleep(2)  # Simular 2 segundos por fuente
        
        # Simular resultados
        noticias_count = 10 + (i * 5)  # Simular diferentes cantidades
        print(f"✅ {source}: {noticias_count} noticias extraídas")
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"\n📊 RESULTADOS:")
    print(f"⏱️ Tiempo total: {duration:.2f} segundos")
    print(f"📰 Total noticias: {sum(10 + (i * 5) for i in range(len(sources)))}")
    print(f"🚀 Velocidad: {len(sources) / duration:.2f} fuentes/segundo")
    
    # Comparar con sistema secuencial
    sequential_time = len(sources) * 2  # 2 segundos por fuente
    improvement = (sequential_time - duration) / sequential_time * 100
    
    print(f"\n📈 MEJORA DE RENDIMIENTO:")
    print(f"🔄 Secuencial: {sequential_time:.2f} segundos")
    print(f"⚡ Asíncrono: {duration:.2f} segundos")
    print(f"📊 Mejora: {improvement:.1f}% más rápido")

def test_file_organization():
    """Probar organización de archivos en carpeta data/"""
    print("\n📁 PROBANDO ORGANIZACIÓN DE ARCHIVOS")
    print("=" * 50)
    
    # Crear directorio data si no existe
    if not os.path.exists('data'):
        os.makedirs('data')
        print("✅ Directorio 'data/' creado")
    else:
        print("✅ Directorio 'data/' ya existe")
    
    # Verificar archivos existentes
    if os.path.exists('data/noticias_pachamama.csv'):
        print("✅ Archivos de Pachamama encontrados en data/")
        
        # Mostrar tamaño de archivos
        csv_size = os.path.getsize('data/noticias_pachamama.csv')
        json_size = os.path.getsize('data/noticias_pachamama.json')
        
        print(f"📄 CSV: {csv_size:,} bytes")
        print(f"📄 JSON: {json_size:,} bytes")
    else:
        print("⚠️ No se encontraron archivos en data/")
    
    # Listar archivos en data/
    files = os.listdir('data')
    if files:
        print(f"\n📁 Archivos en data/ ({len(files)}):")
        for file in files:
            file_path = os.path.join('data', file)
            size = os.path.getsize(file_path)
            print(f"  - {file} ({size:,} bytes)")
    else:
        print("📁 Carpeta data/ está vacía")

def test_database_performance():
    """Probar rendimiento de la base de datos"""
    print("\n💾 PROBANDO RENDIMIENTO DE BASE DE DATOS")
    print("=" * 50)
    
    try:
        from database import DatabaseManager
        
        with DatabaseManager() as db:
            if not db.connection:
                print("❌ No se pudo conectar a la base de datos")
                return
            
            # Obtener estadísticas
            stats = db.get_estadisticas()
            
            print(f"📊 Total noticias: {stats.get('total_noticias', 0)}")
            print("📰 Por fuente:")
            for fuente, cantidad in stats.get('noticias_por_fuente', {}).items():
                print(f"  - {fuente}: {cantidad}")
            
            # Probar consulta rápida
            start_time = time.time()
            noticias = db.get_noticias_recientes(10)
            query_time = time.time() - start_time
            
            print(f"⚡ Tiempo de consulta: {query_time:.4f} segundos")
            print(f"📄 Noticias obtenidas: {len(noticias)}")
            
    except Exception as e:
        print(f"❌ Error probando base de datos: {e}")

def main():
    """Función principal"""
    print("🧪 PRUEBAS DEL SISTEMA ASÍNCRONO")
    print("=" * 60)
    
    # Probar scraping asíncrono simulado
    test_async_scraping()
    
    # Probar organización de archivos
    test_file_organization()
    
    # Probar rendimiento de base de datos
    test_database_performance()
    
    print("\n🎉 PRUEBAS COMPLETADAS")
    print("=" * 60)
    print("📝 Próximos pasos:")
    print("1. Instalar Redis para sistema completo")
    print("2. Ejecutar: python start_local.py")
    print("3. O usar Docker: docker-compose up -d")
    print("4. Monitorear en: http://localhost:5555")

if __name__ == "__main__":
    main()
