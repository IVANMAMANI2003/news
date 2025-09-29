#!/usr/bin/env python3
"""
Sistema de monitoreo para el scraping de noticias
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests

from database import DatabaseManager

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ScrapingMonitor:
    def __init__(self):
        self.sources = {
            'pachamama': {
                'url': 'https://pachamamaradio.org/',
                'name': 'Pachamama Radio',
                'enabled': True
            },
            'los_andes': {
                'url': 'https://losandes.com.pe',
                'name': 'Los Andes',
                'enabled': True
            },
            'puno_noticias': {
                'url': 'https://punonoticias.pe/',
                'name': 'Puno Noticias',
                'enabled': True
            },
            'diario_sin_fronteras': {
                'url': 'https://diariosinfronteras.com.pe/',
                'name': 'Diario Sin Fronteras',
                'enabled': True
            }
        }
        
        self.monitoring_data = {
            'last_check': None,
            'sources_status': {},
            'database_status': False,
            'system_health': 'unknown'
        }
    
    def check_website_availability(self, url: str, timeout: int = 10) -> Dict:
        """Verificar disponibilidad de un sitio web"""
        try:
            response = requests.get(url, timeout=timeout, allow_redirects=True)
            
            return {
                'available': True,
                'status_code': response.status_code,
                'response_time': response.elapsed.total_seconds(),
                'content_length': len(response.content),
                'last_modified': response.headers.get('last-modified', 'N/A'),
                'server': response.headers.get('server', 'N/A')
            }
        except requests.exceptions.Timeout:
            return {
                'available': False,
                'error': 'Timeout',
                'response_time': timeout
            }
        except requests.exceptions.ConnectionError:
            return {
                'available': False,
                'error': 'Connection Error'
            }
        except Exception as e:
            return {
                'available': False,
                'error': str(e)
            }
    
    def check_database_health(self) -> bool:
        """Verificar salud de la base de datos"""
        try:
            with DatabaseManager() as db:
                return db.health_check()
        except Exception as e:
            logger.error(f"Error verificando base de datos: {e}")
            return False
    
    def check_scraping_progress(self) -> Dict:
        """Verificar progreso del scraping"""
        try:
            with DatabaseManager() as db:
                if not db.connection:
                    return {'error': 'No database connection'}
                
                # Obtener estadísticas de las últimas 24 horas
                cursor = db.connection.cursor()
                cursor.execute("""
                    SELECT 
                        fuente,
                        COUNT(*) as total_noticias,
                        MAX(fecha_extraccion) as ultima_extraccion,
                        MIN(fecha_extraccion) as primera_extraccion
                    FROM noticias 
                    WHERE fecha_extraccion >= NOW() - INTERVAL '24 hours'
                    GROUP BY fuente
                    ORDER BY total_noticias DESC
                """)
                
                results = cursor.fetchall()
                cursor.close()
                
                progress = {}
                for row in results:
                    fuente, total, ultima, primera = row
                    progress[fuente] = {
                        'total_noticias': total,
                        'ultima_extraccion': ultima.isoformat() if ultima else None,
                        'primera_extraccion': primera.isoformat() if primera else None,
                        'activo': ultima and (datetime.now() - ultima).total_seconds() < 3600  # Última hora
                    }
                
                return progress
        except Exception as e:
            logger.error(f"Error verificando progreso: {e}")
            return {'error': str(e)}
    
    def check_system_resources(self) -> Dict:
        """Verificar recursos del sistema"""
        try:
            import psutil
            
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
                'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
            }
        except ImportError:
            logger.warning("psutil no está instalado, no se pueden obtener métricas del sistema")
            return {'error': 'psutil not available'}
        except Exception as e:
            logger.error(f"Error obteniendo métricas del sistema: {e}")
            return {'error': str(e)}
    
    def run_monitoring_cycle(self) -> Dict:
        """Ejecutar un ciclo completo de monitoreo"""
        logger.info("🔍 Iniciando ciclo de monitoreo...")
        
        # Verificar sitios web
        sources_status = {}
        for source_id, source_info in self.sources.items():
            if source_info['enabled']:
                logger.info(f"Verificando {source_info['name']}...")
                status = self.check_website_availability(source_info['url'])
                sources_status[source_id] = {
                    'name': source_info['name'],
                    'url': source_info['url'],
                    'status': status
                }
        
        # Verificar base de datos
        logger.info("Verificando base de datos...")
        database_status = self.check_database_health()
        
        # Verificar progreso de scraping
        logger.info("Verificando progreso de scraping...")
        scraping_progress = self.check_scraping_progress()
        
        # Verificar recursos del sistema
        logger.info("Verificando recursos del sistema...")
        system_resources = self.check_system_resources()
        
        # Determinar salud general del sistema
        system_health = self.determine_system_health(sources_status, database_status, system_resources)
        
        # Actualizar datos de monitoreo
        self.monitoring_data = {
            'last_check': datetime.now().isoformat(),
            'sources_status': sources_status,
            'database_status': database_status,
            'scraping_progress': scraping_progress,
            'system_resources': system_resources,
            'system_health': system_health
        }
        
        # Guardar datos de monitoreo
        self.save_monitoring_data()
        
        logger.info(f"✅ Ciclo de monitoreo completado - Salud: {system_health}")
        return self.monitoring_data
    
    def determine_system_health(self, sources_status: Dict, database_status: bool, system_resources: Dict) -> str:
        """Determinar la salud general del sistema"""
        # Verificar sitios web
        available_sites = sum(1 for status in sources_status.values() if status['status']['available'])
        total_sites = len(sources_status)
        
        # Verificar base de datos
        db_ok = database_status
        
        # Verificar recursos del sistema
        resources_ok = True
        if 'error' not in system_resources:
            cpu_ok = system_resources.get('cpu_percent', 0) < 90
            memory_ok = system_resources.get('memory_percent', 0) < 90
            disk_ok = system_resources.get('disk_percent', 0) < 90
            resources_ok = cpu_ok and memory_ok and disk_ok
        
        # Determinar salud
        if available_sites == total_sites and db_ok and resources_ok:
            return 'excellent'
        elif available_sites >= total_sites * 0.75 and db_ok:
            return 'good'
        elif available_sites >= total_sites * 0.5:
            return 'warning'
        else:
            return 'critical'
    
    def save_monitoring_data(self):
        """Guardar datos de monitoreo en archivo JSON"""
        try:
            os.makedirs('data', exist_ok=True)
            
            with open('data/monitoring_data.json', 'w', encoding='utf-8') as f:
                json.dump(self.monitoring_data, f, ensure_ascii=False, indent=2)
            
            logger.info("📊 Datos de monitoreo guardados")
        except Exception as e:
            logger.error(f"Error guardando datos de monitoreo: {e}")
    
    def load_monitoring_data(self) -> Dict:
        """Cargar datos de monitoreo desde archivo JSON"""
        try:
            if os.path.exists('data/monitoring_data.json'):
                with open('data/monitoring_data.json', 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error cargando datos de monitoreo: {e}")
        
        return {}
    
    def generate_status_report(self) -> str:
        """Generar reporte de estado en formato HTML"""
        data = self.monitoring_data
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Sistema de Scraping de Noticias - Monitoreo</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .status {{ display: inline-block; padding: 5px 15px; border-radius: 20px; color: white; font-weight: bold; }}
                .excellent {{ background-color: #28a745; }}
                .good {{ background-color: #17a2b8; }}
                .warning {{ background-color: #ffc107; color: black; }}
                .critical {{ background-color: #dc3545; }}
                .section {{ margin-bottom: 30px; }}
                .section h3 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
                .source {{ margin-bottom: 15px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
                .source.available {{ border-left: 5px solid #28a745; }}
                .source.unavailable {{ border-left: 5px solid #dc3545; }}
                .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
                .metric {{ text-align: center; padding: 15px; background: #f8f9fa; border-radius: 5px; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #007bff; }}
                .metric-label {{ color: #666; margin-top: 5px; }}
                .timestamp {{ text-align: center; color: #666; font-size: 14px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📰 Sistema de Scraping de Noticias</h1>
                    <div class="status {data.get('system_health', 'unknown')}">
                        Estado: {data.get('system_health', 'unknown').upper()}
                    </div>
                </div>
                
                <div class="section">
                    <h3>🌐 Estado de Sitios Web</h3>
        """
        
        for source_id, source_data in data.get('sources_status', {}).items():
            status = source_data['status']
            available = status['available']
            html += f"""
                    <div class="source {'available' if available else 'unavailable'}">
                        <h4>{source_data['name']}</h4>
                        <p><strong>URL:</strong> {source_data['url']}</p>
                        <p><strong>Estado:</strong> {'✅ Disponible' if available else '❌ No disponible'}</p>
            """
            
            if available:
                html += f"""
                        <p><strong>Código de respuesta:</strong> {status['status_code']}</p>
                        <p><strong>Tiempo de respuesta:</strong> {status['response_time']:.2f}s</p>
                        <p><strong>Tamaño del contenido:</strong> {status['content_length']:,} bytes</p>
                """
            else:
                html += f"""
                        <p><strong>Error:</strong> {status.get('error', 'Desconocido')}</p>
                """
            
            html += "</div>"
        
        html += """
                </div>
                
                <div class="section">
                    <h3>💾 Base de Datos</h3>
                    <div class="source">
        """
        
        db_status = data.get('database_status', False)
        html += f"""
                        <p><strong>Estado:</strong> {'✅ Conectada' if db_status else '❌ Desconectada'}</p>
        """
        
        # Mostrar progreso de scraping
        scraping_progress = data.get('scraping_progress', {})
        if scraping_progress and 'error' not in scraping_progress:
            html += """
                        <h4>Progreso de Scraping (últimas 24h)</h4>
            """
            for fuente, progress in scraping_progress.items():
                html += f"""
                        <p><strong>{fuente}:</strong> {progress['total_noticias']} noticias 
                        {'✅ Activo' if progress['activo'] else '⚠️ Inactivo'}</p>
                """
        
        html += """
                    </div>
                </div>
                
                <div class="section">
                    <h3>📊 Recursos del Sistema</h3>
                    <div class="metrics">
        """
        
        resources = data.get('system_resources', {})
        if 'error' not in resources:
            html += f"""
                        <div class="metric">
                            <div class="metric-value">{resources.get('cpu_percent', 0):.1f}%</div>
                            <div class="metric-label">CPU</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{resources.get('memory_percent', 0):.1f}%</div>
                            <div class="metric-label">Memoria</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{resources.get('disk_percent', 0):.1f}%</div>
                            <div class="metric-label">Disco</div>
                        </div>
            """
        else:
            html += f"""
                        <div class="metric">
                            <div class="metric-value">N/A</div>
                            <div class="metric-label">Recursos no disponibles</div>
                        </div>
            """
        
        html += """
                    </div>
                </div>
                
                <div class="timestamp">
                    Última actualización: {data.get('last_check', 'N/A')}
                </div>
            </div>
        </body>
        </html>
        """.format(data=data)
        
        return html
    
    def save_status_report(self):
        """Guardar reporte de estado en archivo HTML"""
        try:
            os.makedirs('data', exist_ok=True)
            
            html_content = self.generate_status_report()
            
            with open('data/status_report.html', 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info("📄 Reporte de estado guardado en data/status_report.html")
        except Exception as e:
            logger.error(f"Error guardando reporte de estado: {e}")

def main():
    """Función principal para ejecutar el monitoreo"""
    print("🔍 SISTEMA DE MONITOREO DE SCRAPING")
    print("=" * 50)
    
    monitor = ScrapingMonitor()
    
    print("Opciones:")
    print("1. Ejecutar monitoreo completo")
    print("2. Verificar solo sitios web")
    print("3. Verificar solo base de datos")
    print("4. Generar reporte de estado")
    print("5. Monitoreo continuo (cada 5 minutos)")
    
    opcion = input("\nSelecciona una opción (1-5): ").strip()
    
    if opcion == "1":
        print("\n🔍 Ejecutando monitoreo completo...")
        data = monitor.run_monitoring_cycle()
        monitor.save_status_report()
        
        print(f"\n📊 RESULTADOS:")
        print(f"Salud del sistema: {data['system_health'].upper()}")
        print(f"Base de datos: {'✅ OK' if data['database_status'] else '❌ Error'}")
        
        print("\nSitios web:")
        for source_id, source_data in data['sources_status'].items():
            status = source_data['status']
            print(f"  {source_data['name']}: {'✅' if status['available'] else '❌'}")
    
    elif opcion == "2":
        print("\n🌐 Verificando sitios web...")
        for source_id, source_info in monitor.sources.items():
            if source_info['enabled']:
                print(f"Verificando {source_info['name']}...")
                status = monitor.check_website_availability(source_info['url'])
                print(f"  Estado: {'✅ Disponible' if status['available'] else '❌ No disponible'}")
                if status['available']:
                    print(f"  Tiempo de respuesta: {status['response_time']:.2f}s")
    
    elif opcion == "3":
        print("\n💾 Verificando base de datos...")
        status = monitor.check_database_health()
        print(f"Estado: {'✅ Conectada' if status else '❌ Desconectada'}")
    
    elif opcion == "4":
        print("\n📄 Generando reporte de estado...")
        monitor.run_monitoring_cycle()
        monitor.save_status_report()
        print("✅ Reporte generado en data/status_report.html")
    
    elif opcion == "5":
        print("\n🔄 Iniciando monitoreo continuo (Ctrl+C para detener)...")
        try:
            while True:
                monitor.run_monitoring_cycle()
                monitor.save_status_report()
                print(f"⏰ Próxima verificación en 5 minutos...")
                time.sleep(300)  # 5 minutos
        except KeyboardInterrupt:
            print("\n🛑 Monitoreo detenido")
    
    else:
        print("❌ Opción no válida")

if __name__ == "__main__":
    main()
