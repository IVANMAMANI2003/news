#!/usr/bin/env python3
"""
Script de limpieza del proyecto
"""

import glob
import os
import shutil
import time
from datetime import datetime, timedelta


def cleanup_logs():
    """Limpiar archivos de log antiguos"""
    print("🧹 Limpiando logs antiguos...")
    
    log_files = glob.glob("*.log")
    for log_file in log_files:
        try:
            os.remove(log_file)
            print(f"  ✅ Eliminado: {log_file}")
        except Exception as e:
            print(f"  ❌ Error eliminando {log_file}: {e}")

def cleanup_data_files():
    """Limpiar archivos de datos antiguos"""
    print("🧹 Limpiando archivos de datos antiguos...")
    
    if not os.path.exists('data'):
        print("  📁 Directorio 'data/' no existe")
        return
    
    # Limpiar archivos CSV y JSON antiguos (más de 7 días)
    cutoff_time = time.time() - (7 * 24 * 60 * 60)
    
    patterns = ['data/*.csv', 'data/*.json']
    for pattern in patterns:
        for file_path in glob.glob(pattern):
            try:
                if os.path.getmtime(file_path) < cutoff_time:
                    os.remove(file_path)
                    print(f"  ✅ Eliminado: {file_path}")
            except Exception as e:
                print(f"  ❌ Error eliminando {file_path}: {e}")

def cleanup_cache():
    """Limpiar archivos de cache"""
    print("🧹 Limpiando archivos de cache...")
    
    cache_dirs = ['__pycache__', '.pytest_cache', 'htmlcov']
    for cache_dir in cache_dirs:
        if os.path.exists(cache_dir):
            try:
                shutil.rmtree(cache_dir)
                print(f"  ✅ Eliminado: {cache_dir}/")
            except Exception as e:
                print(f"  ❌ Error eliminando {cache_dir}/: {e}")

def cleanup_temp_files():
    """Limpiar archivos temporales"""
    print("🧹 Limpiando archivos temporales...")
    
    temp_patterns = ['*.tmp', '*.temp', '*.bak', '*.backup', '*.pyc', '*.pyo']
    for pattern in temp_patterns:
        for file_path in glob.glob(pattern):
            try:
                os.remove(file_path)
                print(f"  ✅ Eliminado: {file_path}")
            except Exception as e:
                print(f"  ❌ Error eliminando {file_path}: {e}")

def cleanup_scraped_files():
    """Limpiar archivos de scraping en la raíz"""
    print("🧹 Limpiando archivos de scraping en la raíz...")
    
    root_patterns = ['noticias_*.csv', 'noticias_*.json', 'urls_procesadas.txt']
    for pattern in root_patterns:
        for file_path in glob.glob(pattern):
            try:
                os.remove(file_path)
                print(f"  ✅ Eliminado: {file_path}")
            except Exception as e:
                print(f"  ❌ Error eliminando {file_path}: {e}")

def show_project_stats():
    """Mostrar estadísticas del proyecto"""
    print("\n📊 ESTADÍSTICAS DEL PROYECTO")
    print("=" * 50)
    
    # Contar archivos por tipo
    file_counts = {}
    total_size = 0
    
    for root, dirs, files in os.walk('.'):
        # Ignorar directorios de git y cache
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        
        for file in files:
            if file.startswith('.'):
                continue
                
            file_path = os.path.join(root, file)
            try:
                size = os.path.getsize(file_path)
                total_size += size
                
                ext = os.path.splitext(file)[1] or 'sin_extension'
                file_counts[ext] = file_counts.get(ext, 0) + 1
            except:
                pass
    
    print(f"📁 Total de archivos: {sum(file_counts.values())}")
    print(f"💾 Tamaño total: {total_size / 1024 / 1024:.2f} MB")
    print("\n📄 Archivos por tipo:")
    for ext, count in sorted(file_counts.items()):
        print(f"  {ext}: {count}")

def main():
    """Función principal"""
    print("🧹 LIMPIEZA DEL PROYECTO")
    print("=" * 50)
    
    # Ejecutar limpieza
    cleanup_logs()
    cleanup_data_files()
    cleanup_cache()
    cleanup_temp_files()
    cleanup_scraped_files()
    
    # Mostrar estadísticas
    show_project_stats()
    
    print("\n✅ LIMPIEZA COMPLETADA")
    print("=" * 50)
    print("📝 El proyecto está listo para:")
    print("  1. Subir a GitHub")
    print("  2. Desplegar en AWS")
    print("  3. Compartir con otros desarrolladores")

if __name__ == "__main__":
    main()
