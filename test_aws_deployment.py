#!/usr/bin/env python3
"""
Script de prueba para verificar el despliegue en AWS
"""

import logging
import os
import sys
import time
from datetime import datetime

import requests

from database import DatabaseManager
from monitoring import ScrapingMonitor

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_database_connection():
    """Probar conexión a la base de datos"""
    print("🔍 Probando conexión a la base de datos...")
    
    try:
        with DatabaseManager() as db:
            if db.connection:
                print("✅ Base de datos: Conectada")
                
                # Probar health check
                if db.health_check():
                    print("✅ Base de datos: Salud OK")
                else:
                    print("❌ Base de datos: Problemas de salud")
                
                # Obtener estadísticas
                stats = db.get_estadisticas()
                print(f"📊 Total noticias: {stats.get('total_noticias', 0)}")
                
                return True
            else:
                print("❌ Base de datos: Sin conexión")
                return False
    except Exception as e:
        print(f"❌ Base de datos: Error - {e}")
        return False

def test_website_monitoring():
    """Probar monitoreo de sitios web"""
    print("\n🔍 Probando monitoreo de sitios web...")
    
    try:
        monitor = ScrapingMonitor()
        
        # Probar un sitio web
        test_url = "https://pachamamaradio.org/"
        print(f"Verificando {test_url}...")
        
        status = monitor.check_website_availability(test_url)
        
        if status['available']:
            print(f"✅ Sitio web: Disponible ({status['response_time']:.2f}s)")
        else:
            print(f"❌ Sitio web: No disponible - {status.get('error', 'Error desconocido')}")
        
        return status['available']
    except Exception as e:
        print(f"❌ Monitoreo: Error - {e}")
        return False

def test_system_resources():
    """Probar recursos del sistema"""
    print("\n🔍 Probando recursos del sistema...")
    
    try:
        monitor = ScrapingMonitor()
        resources = monitor.check_system_resources()
        
        if 'error' not in resources:
            cpu = resources.get('cpu_percent', 0)
            memory = resources.get('memory_percent', 0)
            disk = resources.get('disk_percent', 0)
            
            print(f"📊 CPU: {cpu:.1f}%")
            print(f"📊 Memoria: {memory:.1f}%")
            print(f"📊 Disco: {disk:.1f}%")
            
            # Verificar si los recursos están en niveles normales
            if cpu < 90 and memory < 90 and disk < 90:
                print("✅ Recursos del sistema: OK")
                return True
            else:
                print("⚠️ Recursos del sistema: Niveles altos")
                return False
        else:
            print(f"❌ Recursos del sistema: {resources['error']}")
            return False
    except Exception as e:
        print(f"❌ Recursos del sistema: Error - {e}")
        return False

def test_web_services():
    """Probar servicios web"""
    print("\n🔍 Probando servicios web...")
    
    # Obtener IP pública
    try:
        public_ip = requests.get('http://169.254.169.254/latest/meta-data/public-ipv4', timeout=5).text
    except:
        public_ip = "localhost"
    
    services = [
        {"name": "Nginx", "url": f"http://{public_ip}:8080", "expected_status": 200},
        {"name": "API de estado", "url": f"http://{public_ip}:8080/api/stats", "expected_status": 200},
        {"name": "Flower", "url": f"http://{public_ip}:5555", "expected_status": 200},
    ]
    
    results = []
    
    for service in services:
        try:
            print(f"Verificando {service['name']}...")
            response = requests.get(service['url'], timeout=10)
            
            if response.status_code == service['expected_status']:
                print(f"✅ {service['name']}: OK ({response.status_code})")
                results.append(True)
            else:
                print(f"❌ {service['name']}: Error ({response.status_code})")
                results.append(False)
        except Exception as e:
            print(f"❌ {service['name']}: Error - {e}")
            results.append(False)
    
    return all(results)

def test_file_structure():
    """Probar estructura de archivos"""
    print("\n🔍 Probando estructura de archivos...")
    
    required_dirs = ['data', 'logs']
    required_files = [
        'docker-compose.yml',
        'requirements.txt',
        'database.py',
        'unified_scraper.py',
        'monitoring.py',
        'nginx.conf'
    ]
    
    # Verificar directorios
    for dir_name in required_dirs:
        if os.path.exists(dir_name):
            print(f"✅ Directorio {dir_name}/: Existe")
        else:
            print(f"❌ Directorio {dir_name}/: No existe")
            os.makedirs(dir_name, exist_ok=True)
            print(f"✅ Directorio {dir_name}/: Creado")
    
    # Verificar archivos
    for file_name in required_files:
        if os.path.exists(file_name):
            print(f"✅ Archivo {file_name}: Existe")
        else:
            print(f"❌ Archivo {file_name}: No existe")
    
    return True

def test_docker_services():
    """Probar servicios de Docker"""
    print("\n🔍 Probando servicios de Docker...")
    
    try:
        import subprocess

        # Verificar si Docker está ejecutándose
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Docker: Ejecutándose")
            
            # Verificar contenedores
            result = subprocess.run(['docker-compose', 'ps'], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Docker Compose: OK")
                print("Contenedores:")
                print(result.stdout)
            else:
                print("❌ Docker Compose: Error")
                print(result.stderr)
        else:
            print("❌ Docker: No está ejecutándose")
            print(result.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Docker: Error - {e}")
        return False

def generate_test_report(results):
    """Generar reporte de pruebas"""
    print("\n" + "="*60)
    print("📊 REPORTE DE PRUEBAS")
    print("="*60)
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    print(f"Total de pruebas: {total_tests}")
    print(f"Pruebas exitosas: {passed_tests}")
    print(f"Pruebas fallidas: {total_tests - passed_tests}")
    print(f"Porcentaje de éxito: {(passed_tests/total_tests)*100:.1f}%")
    
    print("\nDetalles:")
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    if passed_tests == total_tests:
        print("\n🎉 ¡TODAS LAS PRUEBAS PASARON!")
        print("El sistema está listo para producción en AWS")
    else:
        print(f"\n⚠️ {total_tests - passed_tests} pruebas fallaron")
        print("Revisa los errores antes de desplegar en producción")
    
    return passed_tests == total_tests

def main():
    """Función principal"""
    print("🧪 PRUEBAS DE DESPLIEGUE EN AWS")
    print("="*60)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Ejecutar pruebas
    results = {}
    
    results['Base de datos'] = test_database_connection()
    results['Monitoreo de sitios web'] = test_website_monitoring()
    results['Recursos del sistema'] = test_system_resources()
    results['Servicios web'] = test_web_services()
    results['Estructura de archivos'] = test_file_structure()
    results['Servicios de Docker'] = test_docker_services()
    
    # Generar reporte
    all_passed = generate_test_report(results)
    
    # Guardar reporte
    try:
        os.makedirs('data', exist_ok=True)
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'results': results,
            'all_passed': all_passed,
            'total_tests': len(results),
            'passed_tests': sum(results.values())
        }
        
        import json
        with open('data/test_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 Reporte guardado en: data/test_report.json")
    except Exception as e:
        print(f"\n❌ Error guardando reporte: {e}")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
