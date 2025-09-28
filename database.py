import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

import psycopg2
import psycopg2.extras


class DatabaseManager:
    def __init__(self, host='localhost', port=5432, database='news_scraper', 
                 user='postgres', password='123456'):
        """
        Inicializar el gestor de base de datos PostgreSQL
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.connection = None
        
        # Configurar logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def connect(self):
        """Establecer conexión con PostgreSQL"""
        try:
            self.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            self.connection.autocommit = True
            self.logger.info("Conexión a PostgreSQL establecida exitosamente")
            return True
        except psycopg2.Error as e:
            self.logger.error(f"Error conectando a PostgreSQL: {e}")
            return False
    
    def create_database_if_not_exists(self):
        """Crear la base de datos si no existe"""
        try:
            # Conectar a la base de datos por defecto 'postgres'
            temp_conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database='postgres',
                user=self.user,
                password=self.password
            )
            temp_conn.autocommit = True
            cursor = temp_conn.cursor()
            
            # Verificar si la base de datos existe
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (self.database,))
            exists = cursor.fetchone()
            
            if not exists:
                cursor.execute(f"CREATE DATABASE {self.database}")
                self.logger.info(f"Base de datos '{self.database}' creada exitosamente")
            else:
                self.logger.info(f"Base de datos '{self.database}' ya existe")
            
            cursor.close()
            temp_conn.close()
            return True
            
        except psycopg2.Error as e:
            self.logger.error(f"Error creando base de datos: {e}")
            return False
    
    def create_tables(self):
        """Crear las tablas necesarias"""
        if not self.connection:
            self.logger.error("No hay conexión a la base de datos")
            return False
        
        try:
            cursor = self.connection.cursor()
            
            # Crear tabla de noticias
            create_table_query = """
            CREATE TABLE IF NOT EXISTS noticias (
                id SERIAL PRIMARY KEY,
                titulo TEXT,
                fecha TIMESTAMP,
                hora TIME,
                resumen TEXT,
                contenido TEXT,
                categoria VARCHAR(100),
                autor VARCHAR(200),
                tags TEXT,
                url TEXT UNIQUE,
                fecha_extraccion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                link_imagenes TEXT,
                fuente VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            
            cursor.execute(create_table_query)
            
            # Crear índices para mejorar el rendimiento
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_noticias_fecha ON noticias(fecha);",
                "CREATE INDEX IF NOT EXISTS idx_noticias_fuente ON noticias(fuente);",
                "CREATE INDEX IF NOT EXISTS idx_noticias_categoria ON noticias(categoria);",
                "CREATE INDEX IF NOT EXISTS idx_noticias_fecha_extraccion ON noticias(fecha_extraccion);",
                "CREATE INDEX IF NOT EXISTS idx_noticias_url ON noticias(url);"
            ]
            
            for index_query in indexes:
                cursor.execute(index_query)
            
            cursor.close()
            self.logger.info("Tablas e índices creados exitosamente")
            return True
            
        except psycopg2.Error as e:
            self.logger.error(f"Error creando tablas: {e}")
            return False
    
    def insert_noticia(self, noticia_data: Dict) -> bool:
        """Insertar una noticia en la base de datos"""
        if not self.connection:
            self.logger.error("No hay conexión a la base de datos")
            return False
        
        try:
            cursor = self.connection.cursor()
            
            # Verificar si la URL ya existe
            cursor.execute("SELECT id FROM noticias WHERE url = %s", (noticia_data['url'],))
            if cursor.fetchone():
                self.logger.info(f"Noticia ya existe: {noticia_data['url']}")
                cursor.close()
                return False
            
            # Insertar nueva noticia
            insert_query = """
            INSERT INTO noticias (
                titulo, fecha, hora, resumen, contenido, categoria, 
                autor, tags, url, link_imagenes, fuente, fecha_extraccion
            ) VALUES (
                %(titulo)s, %(fecha)s, %(hora)s, %(resumen)s, %(contenido)s, 
                %(categoria)s, %(autor)s, %(tags)s, %(url)s, %(link_imagenes)s, 
                %(fuente)s, %(fecha_extraccion)s
            )
            """
            
            cursor.execute(insert_query, noticia_data)
            cursor.close()
            
            self.logger.info(f"Noticia insertada: {noticia_data['titulo'][:50]}...")
            return True
            
        except psycopg2.Error as e:
            self.logger.error(f"Error insertando noticia: {e}")
            return False
    
    def insert_noticias_batch(self, noticias_data: List[Dict]) -> int:
        """Insertar múltiples noticias en lote"""
        if not self.connection:
            self.logger.error("No hay conexión a la base de datos")
            return 0
        
        inserted_count = 0
        
        try:
            cursor = self.connection.cursor()
            
            for noticia_data in noticias_data:
                # Verificar si la URL ya existe
                cursor.execute("SELECT id FROM noticias WHERE url = %s", (noticia_data['url'],))
                if cursor.fetchone():
                    continue
                
                # Insertar nueva noticia
                insert_query = """
                INSERT INTO noticias (
                    titulo, fecha, hora, resumen, contenido, categoria, 
                    autor, tags, url, link_imagenes, fuente, fecha_extraccion
                ) VALUES (
                    %(titulo)s, %(fecha)s, %(hora)s, %(resumen)s, %(contenido)s, 
                    %(categoria)s, %(autor)s, %(tags)s, %(url)s, %(link_imagenes)s, 
                    %(fuente)s, %(fecha_extraccion)s
                )
                """
                
                cursor.execute(insert_query, noticia_data)
                inserted_count += 1
            
            cursor.close()
            self.logger.info(f"Insertadas {inserted_count} noticias nuevas")
            return inserted_count
            
        except psycopg2.Error as e:
            self.logger.error(f"Error insertando noticias en lote: {e}")
            return 0
    
    def get_noticias_by_fuente(self, fuente: str, limit: int = 100) -> List[Dict]:
        """Obtener noticias por fuente"""
        if not self.connection:
            self.logger.error("No hay conexión a la base de datos")
            return []
        
        try:
            cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            query = """
            SELECT * FROM noticias 
            WHERE fuente = %s 
            ORDER BY fecha_extraccion DESC 
            LIMIT %s
            """
            
            cursor.execute(query, (fuente, limit))
            results = cursor.fetchall()
            cursor.close()
            
            return [dict(row) for row in results]
            
        except psycopg2.Error as e:
            self.logger.error(f"Error obteniendo noticias por fuente: {e}")
            return []
    
    def get_noticias_recientes(self, limit: int = 100) -> List[Dict]:
        """Obtener noticias más recientes"""
        if not self.connection:
            self.logger.error("No hay conexión a la base de datos")
            return []
        
        try:
            cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            query = """
            SELECT * FROM noticias 
            ORDER BY fecha_extraccion DESC 
            LIMIT %s
            """
            
            cursor.execute(query, (limit,))
            results = cursor.fetchall()
            cursor.close()
            
            return [dict(row) for row in results]
            
        except psycopg2.Error as e:
            self.logger.error(f"Error obteniendo noticias recientes: {e}")
            return []
    
    def get_estadisticas(self) -> Dict:
        """Obtener estadísticas de la base de datos"""
        if not self.connection:
            self.logger.error("No hay conexión a la base de datos")
            return {}
        
        try:
            cursor = self.connection.cursor()
            
            # Total de noticias
            cursor.execute("SELECT COUNT(*) FROM noticias")
            total_noticias = cursor.fetchone()[0]
            
            # Noticias por fuente
            cursor.execute("""
                SELECT fuente, COUNT(*) as cantidad 
                FROM noticias 
                GROUP BY fuente 
                ORDER BY cantidad DESC
            """)
            noticias_por_fuente = dict(cursor.fetchall())
            
            # Noticias por categoría
            cursor.execute("""
                SELECT categoria, COUNT(*) as cantidad 
                FROM noticias 
                WHERE categoria IS NOT NULL AND categoria != ''
                GROUP BY categoria 
                ORDER BY cantidad DESC 
                LIMIT 10
            """)
            noticias_por_categoria = dict(cursor.fetchall())
            
            # Última extracción
            cursor.execute("""
                SELECT MAX(fecha_extraccion) as ultima_extraccion 
                FROM noticias
            """)
            ultima_extraccion = cursor.fetchone()[0]
            
            cursor.close()
            
            return {
                'total_noticias': total_noticias,
                'noticias_por_fuente': noticias_por_fuente,
                'noticias_por_categoria': noticias_por_categoria,
                'ultima_extraccion': ultima_extraccion
            }
            
        except psycopg2.Error as e:
            self.logger.error(f"Error obteniendo estadísticas: {e}")
            return {}
    
    def close(self):
        """Cerrar conexión a la base de datos"""
        if self.connection:
            self.connection.close()
            self.logger.info("Conexión a PostgreSQL cerrada")
    
    def __enter__(self):
        """Context manager entry"""
        self.create_database_if_not_exists()
        self.connect()
        self.create_tables()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

# Función de utilidad para inicializar la base de datos
def initialize_database():
    """Inicializar la base de datos con todas las tablas necesarias"""
    with DatabaseManager() as db:
        if db.connection:
            print("✅ Base de datos inicializada correctamente")
            return True
        else:
            print("❌ Error inicializando la base de datos")
            return False

if __name__ == "__main__":
    # Probar la conexión y creación de tablas
    initialize_database()
