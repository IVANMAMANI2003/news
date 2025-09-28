#!/usr/bin/env python3
"""
Script para cargar las noticias extraídas a la base de datos
"""

import json
import os
from datetime import datetime

from database import DatabaseManager


def load_pachamama_news():
    """Cargar noticias de Pachamama a la base de datos"""
    json_file = "noticias_pachamama.json"
    
    if not os.path.exists(json_file):
        print(f"❌ Archivo {json_file} no encontrado")
        return
    
    print(f"📖 Leyendo {json_file}...")
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            noticias = json.load(f)
        
        print(f"📰 Encontradas {len(noticias)} noticias")
        
        # Conectar a la base de datos
        with DatabaseManager() as db:
            if not db.connection:
                print("❌ Error conectando a la base de datos")
                return
            
            print("💾 Cargando noticias a la base de datos...")
            
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
                    'fuente': 'pachamama',
                    'fecha_extraccion': noticia.get('fecha_extraccion', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                }
                
                # Insertar en base de datos
                if db.insert_noticia(noticia_normalizada):
                    noticias_cargadas += 1
                    print(f"✅ {noticia_normalizada['titulo'][:50]}...")
            
            print(f"\n🎉 {noticias_cargadas} noticias cargadas exitosamente")
            
            # Mostrar estadísticas
            stats = db.get_estadisticas()
            print(f"\n📊 Estadísticas actuales:")
            print(f"Total noticias: {stats.get('total_noticias', 0)}")
            print("Por fuente:")
            for fuente, cantidad in stats.get('noticias_por_fuente', {}).items():
                print(f"  {fuente}: {cantidad}")
    
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    print("🔄 CARGANDO NOTICIAS A LA BASE DE DATOS")
    print("=" * 50)
    
    load_pachamama_news()
    
    print("\n✅ Proceso completado")

if __name__ == "__main__":
    main()
