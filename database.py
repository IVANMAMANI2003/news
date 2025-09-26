"""
Módulo para manejo de la base de datos PostgreSQL
"""
import logging
from typing import Dict, List, Optional

import psycopg2
import psycopg2.extras

from config import DatabaseConfig, DatabaseSchema

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manejador de la base de datos PostgreSQL"""
    
    def __init__(self):
        self.connection = None
        self.cursor = None
        
    def connect(self):
        """Establecer conexión con la base de datos"""
        try:
            self.connection = psycopg2.connect(
                host=DatabaseConfig.HOST,
                port=DatabaseConfig.PORT,
                database=DatabaseConfig.DATABASE,
                user=DatabaseConfig.USER,
                password=DatabaseConfig.PASSWORD
            )
            self.cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            logger.info("Conexión a PostgreSQL establecida correctamente")
            return True
        except Exception as e:
            logger.error(f"Error conectando a PostgreSQL: {e}")
            return False
    
    def create_database_if_not_exists(self):
        """Crear la base de datos si no existe"""
        try:
            # Conectar a la base de datos 'postgres' para crear la nueva BD
            temp_conn = psycopg2.connect(
                host=DatabaseConfig.HOST,
                port=DatabaseConfig.PORT,
                database='postgres',
                user=DatabaseConfig.USER,
                password=DatabaseConfig.PASSWORD
            )
            temp_conn.autocommit = True
            temp_cursor = temp_conn.cursor()
            
            # Verificar si la base de datos existe
            temp_cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (DatabaseConfig.DATABASE,)
            )
            
            if not temp_cursor.fetchone():
                # Crear la base de datos
                temp_cursor.execute(f'CREATE DATABASE "{DatabaseConfig.DATABASE}"')
                logger.info(f"Base de datos '{DatabaseConfig.DATABASE}' creada exitosamente")
            else:
                logger.info(f"Base de datos '{DatabaseConfig.DATABASE}' ya existe")
            
            temp_cursor.close()
            temp_conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error creando base de datos: {e}")
            return False
    
    def create_tables(self):
        """Crear las tablas necesarias"""
        try:
            if not self.connection:
                self.connect()
            
            # Crear tabla principal
            self.cursor.execute(DatabaseSchema.CREATE_TABLE_SQL)
            logger.info("Tabla 'noticias' creada/verificada correctamente")
            
            # Crear índices
            for index_sql in DatabaseSchema.CREATE_INDEXES_SQL:
                self.cursor.execute(index_sql)
            
            self.connection.commit()
            logger.info("Índices creados correctamente")
            return True
            
        except Exception as e:
            logger.error(f"Error creando tablas: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def insert_news(self, news_data: Dict) -> bool:
        """Insertar una noticia en la base de datos"""
        try:
            if not self.connection:
                self.connect()
            
            insert_sql = """
            INSERT INTO noticias (
                titulo, fecha, hora, resumen, contenido, categoria, 
                autor, tags, url, link_imagenes, fuente
            ) VALUES (
                %(titulo)s, %(fecha)s, %(hora)s, %(resumen)s, %(contenido)s, 
                %(categoria)s, %(autor)s, %(tags)s, %(url)s, %(link_imagenes)s, %(fuente)s
            ) ON CONFLICT (url) DO NOTHING
            """
            
            self.cursor.execute(insert_sql, news_data)
            self.connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error insertando noticia: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def insert_multiple_news(self, news_list: List[Dict]) -> int:
        """Insertar múltiples noticias en lote"""
        try:
            if not self.connection:
                self.connect()
            
            insert_sql = """
            INSERT INTO noticias (
                titulo, fecha, hora, resumen, contenido, categoria, 
                autor, tags, url, link_imagenes, fuente
            ) VALUES (
                %(titulo)s, %(fecha)s, %(hora)s, %(resumen)s, %(contenido)s, 
                %(categoria)s, %(autor)s, %(tags)s, %(url)s, %(link_imagenes)s, %(fuente)s
            ) ON CONFLICT (url) DO NOTHING
            """
            
            inserted_count = 0
            for news_data in news_list:
                try:
                    self.cursor.execute(insert_sql, news_data)
                    if self.cursor.rowcount > 0:
                        inserted_count += 1
                except Exception as e:
                    logger.warning(f"Error insertando noticia individual: {e}")
                    continue
            
            self.connection.commit()
            logger.info(f"Insertadas {inserted_count} noticias nuevas")
            return inserted_count
            
        except Exception as e:
            logger.error(f"Error insertando noticias en lote: {e}")
            if self.connection:
                self.connection.rollback()
            return 0
    
    def get_news_by_source(self, source: str, limit: int = 100) -> List[Dict]:
        """Obtener noticias por fuente"""
        try:
            if not self.connection:
                self.connect()
            
            query = """
            SELECT * FROM noticias 
            WHERE fuente = %s 
            ORDER BY fecha_extraccion DESC 
            LIMIT %s
            """
            
            self.cursor.execute(query, (source, limit))
            return self.cursor.fetchall()
            
        except Exception as e:
            logger.error(f"Error obteniendo noticias por fuente: {e}")
            return []
    
    def get_recent_news(self, hours: int = 24) -> List[Dict]:
        """Obtener noticias recientes"""
        try:
            if not self.connection:
                self.connect()
            
            query = """
            SELECT * FROM noticias 
            WHERE fecha_extraccion >= NOW() - INTERVAL '%s hours'
            ORDER BY fecha_extraccion DESC
            """
            
            self.cursor.execute(query, (hours,))
            return self.cursor.fetchall()
            
        except Exception as e:
            logger.error(f"Error obteniendo noticias recientes: {e}")
            return []
    
    def get_statistics(self) -> Dict:
        """Obtener estadísticas de la base de datos"""
        try:
            if not self.connection:
                self.connect()
            
            stats = {}
            
            # Total de noticias
            self.cursor.execute("SELECT COUNT(*) as total FROM noticias")
            stats['total_noticias'] = self.cursor.fetchone()['total']
            
            # Por fuente
            self.cursor.execute("""
                SELECT fuente, COUNT(*) as count 
                FROM noticias 
                GROUP BY fuente 
                ORDER BY count DESC
            """)
            stats['por_fuente'] = dict(self.cursor.fetchall())
            
            # Últimas 24 horas
            self.cursor.execute("""
                SELECT COUNT(*) as count 
                FROM noticias 
                WHERE fecha_extraccion >= NOW() - INTERVAL '24 hours'
            """)
            stats['ultimas_24h'] = self.cursor.fetchone()['count']
            
            return stats
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {}
    
    def close(self):
        """Cerrar conexión a la base de datos"""
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()
            logger.info("Conexión a PostgreSQL cerrada")
        except Exception as e:
            logger.error(f"Error cerrando conexión: {e}")
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
