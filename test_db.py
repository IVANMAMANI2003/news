#!/usr/bin/env python3
"""
Script simple para probar solo la conexión a PostgreSQL
"""

import logging
import sys
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    print("🔍 Probando conexión a PostgreSQL...")
    
    try:
        # Importar el módulo de base de datos
        from database import DatabaseManager
        
        print("✅ Módulo database importado correctamente")
        
        # Crear instancia
        db = DatabaseManager()
        print("✅ DatabaseManager creado")
        
        # Crear base de datos si no existe
        print("📝 Creando/verificando base de datos...")
        if db.create_database_if_not_exists():
            print("✅ Base de datos creada/verificada")
        else:
            print("❌ Error creando base de datos")
            return False
        
        # Conectar
        print("🔌 Conectando a PostgreSQL...")
        if db.connect():
            print("✅ Conexión exitosa")
            
            # Crear tablas
            print("📋 Creando tablas...")
            if db.create_tables():
                print("✅ Tablas creadas")
                
                # Insertar noticia de prueba
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
                
                print("💾 Insertando noticia de prueba...")
                if db.insert_noticia(test_noticia):
                    print("✅ Noticia insertada")
                else:
                    print("ℹ️ Noticia ya existe (normal)")
                
                # Obtener estadísticas
                stats = db.get_estadisticas()
                print(f"📊 Total noticias en BD: {stats.get('total_noticias', 0)}")
                
                db.close()
                print("✅ Conexión cerrada")
                return True
            else:
                print("❌ Error creando tablas")
                return False
        else:
            print("❌ Error conectando a PostgreSQL")
            print("💡 Verifica que PostgreSQL esté ejecutándose y las credenciales sean correctas")
            return False
            
    except ImportError as e:
        print(f"❌ Error importando módulos: {e}")
        print("💡 Instala las dependencias: pip install psycopg2-binary")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 ¡Prueba de base de datos exitosa!")
        print("📝 Ahora puedes ejecutar: python test_local.py")
    else:
        print("\n💥 Prueba de base de datos falló")
        print("🔧 Verifica que PostgreSQL esté instalado y ejecutándose")
        print("   Usuario: postgres, Password: 123456")
