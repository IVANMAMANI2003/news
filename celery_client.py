#!/usr/bin/env python3
"""
Cliente para ejecutar tareas de Celery de forma asíncrona
"""

import logging
import time
from datetime import datetime
from typing import Dict, List

from celery_tasks import (process_news_batch, save_to_database,
                          scheduled_scraping, scrape_source)

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CeleryScrapingClient:
    def __init__(self):
        self.active_tasks = []
    
    def start_scraping_all_sources(self) -> List[str]:
        """
        Iniciar scraping de todas las fuentes en paralelo
        """
        logger.info("🚀 Iniciando scraping asíncrono de todas las fuentes")
        
        sources = [
            'pachamama',
            'los_andes', 
            'puno_noticias',
            'diario_sin_fronteras'
        ]
        
        task_ids = []
        
        for source in sources:
            try:
                logger.info(f"📰 Iniciando scraping de {source}")
                task = scrape_source.delay(source, {})
                task_ids.append(task.id)
                self.active_tasks.append({
                    'task_id': task.id,
                    'source': source,
                    'task': task,
                    'started_at': datetime.now()
                })
                logger.info(f"✅ Tarea iniciada para {source}: {task.id}")
                
            except Exception as e:
                logger.error(f"❌ Error iniciando tarea para {source}: {e}")
        
        return task_ids
    
    def monitor_tasks(self, timeout: int = 1800) -> Dict:
        """
        Monitorear el progreso de las tareas activas
        """
        logger.info(f"👀 Monitoreando {len(self.active_tasks)} tareas (timeout: {timeout}s)")
        
        start_time = time.time()
        completed_tasks = []
        failed_tasks = []
        
        while self.active_tasks and (time.time() - start_time) < timeout:
            for task_info in self.active_tasks[:]:  # Copia para poder modificar
                task = task_info['task']
                source = task_info['source']
                
                try:
                    if task.ready():
                        if task.successful():
                            result = task.result
                            completed_tasks.append({
                                'source': source,
                                'result': result,
                                'duration': (datetime.now() - task_info['started_at']).total_seconds()
                            })
                            logger.info(f"✅ {source} completado: {result.get('noticias_count', 0)} noticias")
                        else:
                            error = task.result
                            failed_tasks.append({
                                'source': source,
                                'error': str(error),
                                'duration': (datetime.now() - task_info['started_at']).total_seconds()
                            })
                            logger.error(f"❌ {source} falló: {error}")
                        
                        self.active_tasks.remove(task_info)
                    else:
                        # Mostrar progreso
                        try:
                            progress = task.info
                            if isinstance(progress, dict) and 'current' in progress:
                                current = progress.get('current', 0)
                                total = progress.get('total', 100)
                                status = progress.get('status', 'Procesando...')
                                logger.info(f"🔄 {source}: {current}/{total} - {status}")
                        except:
                            pass
                            
                except Exception as e:
                    logger.error(f"❌ Error monitoreando {source}: {e}")
                    failed_tasks.append({
                        'source': source,
                        'error': str(e),
                        'duration': (datetime.now() - task_info['started_at']).total_seconds()
                    })
                    self.active_tasks.remove(task_info)
            
            if self.active_tasks:
                time.sleep(5)  # Esperar 5 segundos antes de verificar de nuevo
        
        # Procesar tareas que no terminaron
        for task_info in self.active_tasks:
            failed_tasks.append({
                'source': task_info['source'],
                'error': 'Timeout',
                'duration': (datetime.now() - task_info['started_at']).total_seconds()
            })
        
        return {
            'completed': completed_tasks,
            'failed': failed_tasks,
            'total_duration': time.time() - start_time
        }
    
    def get_task_status(self, task_id: str) -> Dict:
        """
        Obtener estado de una tarea específica
        """
        try:
            from celery_tasks import celery_app
            task = celery_app.AsyncResult(task_id)
            
            return {
                'task_id': task_id,
                'status': task.status,
                'result': task.result if task.ready() else None,
                'info': task.info if not task.ready() else None
            }
        except Exception as e:
            return {
                'task_id': task_id,
                'status': 'ERROR',
                'error': str(e)
            }
    
    def start_scheduled_scraping(self):
        """
        Iniciar scraping programado
        """
        logger.info("⏰ Iniciando scraping programado")
        
        try:
            task = scheduled_scraping.delay()
            logger.info(f"✅ Scraping programado iniciado: {task.id}")
            return task.id
        except Exception as e:
            logger.error(f"❌ Error iniciando scraping programado: {e}")
            return None

def main():
    """
    Función principal para ejecutar el cliente
    """
    print("🚀 CLIENTE DE SCRAPING ASÍNCRONO CON CELERY")
    print("=" * 60)
    
    client = CeleryScrapingClient()
    
    print("Opciones:")
    print("1. Scraping completo (todas las fuentes)")
    print("2. Scraping programado")
    print("3. Monitorear tareas activas")
    print("4. Estado de tarea específica")
    
    opcion = input("\nSelecciona una opción (1-4): ").strip()
    
    if opcion == "1":
        print("\n🚀 Iniciando scraping completo...")
        task_ids = client.start_scraping_all_sources()
        
        if task_ids:
            print(f"✅ {len(task_ids)} tareas iniciadas")
            print("👀 Monitoreando progreso...")
            
            results = client.monitor_tasks(timeout=1800)  # 30 minutos
            
            print(f"\n📊 RESULTADOS:")
            print(f"✅ Completadas: {len(results['completed'])}")
            print(f"❌ Fallidas: {len(results['failed'])}")
            print(f"⏱️ Duración total: {results['total_duration']:.2f} segundos")
            
            if results['completed']:
                print("\n📰 Fuentes completadas:")
                for task in results['completed']:
                    print(f"  - {task['source']}: {task['result'].get('noticias_count', 0)} noticias ({task['duration']:.2f}s)")
            
            if results['failed']:
                print("\n❌ Fuentes fallidas:")
                for task in results['failed']:
                    print(f"  - {task['source']}: {task['error']}")
        else:
            print("❌ No se pudieron iniciar tareas")
    
    elif opcion == "2":
        task_id = client.start_scheduled_scraping()
        if task_id:
            print(f"✅ Scraping programado iniciado: {task_id}")
        else:
            print("❌ Error iniciando scraping programado")
    
    elif opcion == "3":
        print("👀 Monitoreando tareas activas...")
        results = client.monitor_tasks(timeout=300)  # 5 minutos
        print(f"Resultados: {results}")
    
    elif opcion == "4":
        task_id = input("Ingresa el ID de la tarea: ").strip()
        status = client.get_task_status(task_id)
        print(f"Estado de la tarea: {status}")
    
    else:
        print("❌ Opción no válida")

if __name__ == "__main__":
    main()
