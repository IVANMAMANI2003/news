"""
Configuración central del sistema de scraping de noticias
"""

import os
from typing import Any, Dict


class Config:
    """Configuración central del sistema"""
    
    # Configuración de base de datos
    DATABASE = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'news_scraper'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', '123456')
    }
    
    # Configuración de scraping - SIN LIMITACIONES
    SCRAPING = {
        'delay_between_sources': int(os.getenv('SCRAPING_DELAY', 1)),  # Más rápido
        'max_workers_per_source': int(os.getenv('SCRAPING_WORKERS', 10)),  # Más workers
        'timeout': None,  # Sin límite de tiempo
        'max_retries': int(os.getenv('SCRAPING_RETRIES', 5)),  # Más reintentos
        'enable_incremental': os.getenv('SCRAPING_INCREMENTAL', 'true').lower() == 'true',
        'max_articles_per_source': None  # Sin límite de artículos
    }
    
    # Configuración de scheduler - SIN LIMITACIONES
    SCHEDULER = {
        'interval_hours': int(os.getenv('SCHEDULER_INTERVAL', 1)),  # Cada hora
        'max_concurrent_jobs': int(os.getenv('SCHEDULER_MAX_JOBS', 4)),  # Más trabajos concurrentes
        'timeout_minutes': None,  # Sin límite de tiempo
        'retry_failed_jobs': os.getenv('SCHEDULER_RETRY', 'true').lower() == 'true',
        'max_retries': int(os.getenv('SCHEDULER_MAX_RETRIES', 5)),  # Más reintentos
        'retry_delay_minutes': int(os.getenv('SCHEDULER_RETRY_DELAY', 15))  # Menos delay entre reintentos
    }
    
    # Configuración de fuentes
    SOURCES = {
        'pachamama': {
            'enabled': os.getenv('SOURCE_PACHAMAMA', 'true').lower() == 'true',
            'base_url': 'https://pachamamaradio.org/',
            'delay': int(os.getenv('SOURCE_PACHAMAMA_DELAY', 1))
        },
        'puno_noticias': {
            'enabled': os.getenv('SOURCE_PUNO_NOTICIAS', 'true').lower() == 'true',
            'base_url': 'https://punonoticias.pe/',
            'delay': int(os.getenv('SOURCE_PUNO_NOTICIAS_DELAY', 1))
        },
        'los_andes': {
            'enabled': os.getenv('SOURCE_LOS_ANDES', 'true').lower() == 'true',
            'base_url': 'https://losandes.com.pe',
            'delay': int(os.getenv('SOURCE_LOS_ANDES_DELAY', 1))
        },

        
        'diario_sin_fronteras': {
            'enabled': os.getenv('SOURCE_SIN_FRONTERAS', 'true').lower() == 'true',
            'base_url': 'https://diariosinfronteras.com.pe/',
            'delay': int(os.getenv('SOURCE_SIN_FRONTERAS_DELAY', 1))
        }
    }
    
    # Configuración de salida
    OUTPUT = {
        'save_csv': os.getenv('OUTPUT_CSV', 'true').lower() == 'true',
        'save_json': os.getenv('OUTPUT_JSON', 'true').lower() == 'true',
        'output_directory': os.getenv('OUTPUT_DIR', 'output'),
        'include_timestamp': os.getenv('OUTPUT_TIMESTAMP', 'true').lower() == 'true'
    }
    
    # Configuración de logging
    LOGGING = {
        'level': os.getenv('LOG_LEVEL', 'INFO'),
        'file': os.getenv('LOG_FILE', 'unified_scraper.log'),
        'max_size_mb': int(os.getenv('LOG_MAX_SIZE_MB', 10)),
        'backup_count': int(os.getenv('LOG_BACKUP_COUNT', 5))
    }
    
    # Configuración de notificaciones
    NOTIFICATIONS = {
        'enabled': os.getenv('NOTIFICATIONS_ENABLED', 'false').lower() == 'true',
        'email': {
            'smtp_server': os.getenv('EMAIL_SMTP_SERVER', ''),
            'smtp_port': int(os.getenv('EMAIL_SMTP_PORT', 587)),
            'username': os.getenv('EMAIL_USERNAME', ''),
            'password': os.getenv('EMAIL_PASSWORD', ''),
            'to_addresses': os.getenv('EMAIL_TO_ADDRESSES', '').split(',') if os.getenv('EMAIL_TO_ADDRESSES') else []
        },
        'webhook': {
            'url': os.getenv('WEBHOOK_URL', ''),
            'enabled': os.getenv('WEBHOOK_ENABLED', 'false').lower() == 'true'
        }
    }
    
    # Configuración de mantenimiento
    MAINTENANCE = {
        'cleanup_old_logs_days': int(os.getenv('MAINTENANCE_CLEANUP_LOGS_DAYS', 30)),
        'cleanup_old_files_days': int(os.getenv('MAINTENANCE_CLEANUP_FILES_DAYS', 7)),
        'database_backup_enabled': os.getenv('MAINTENANCE_DB_BACKUP', 'false').lower() == 'true',
        'backup_interval_hours': int(os.getenv('MAINTENANCE_BACKUP_INTERVAL', 24))
    }
    
    # Configuración de AWS (para despliegue)
    AWS = {
        'region': os.getenv('AWS_REGION', 'us-east-1'),
        'access_key_id': os.getenv('AWS_ACCESS_KEY_ID', ''),
        'secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY', ''),
        's3_bucket': os.getenv('AWS_S3_BUCKET', ''),
        'ec2_instance_id': os.getenv('AWS_EC2_INSTANCE_ID', '')
    }
    
    @classmethod
    def get_database_url(cls) -> str:
        """Obtener URL de conexión a la base de datos"""
        return f"postgresql://{cls.DATABASE['user']}:{cls.DATABASE['password']}@{cls.DATABASE['host']}:{cls.DATABASE['port']}/{cls.DATABASE['database']}"
    
    @classmethod
    def get_source_config(cls, source_name: str) -> Dict[str, Any]:
        """Obtener configuración de una fuente específica"""
        return cls.SOURCES.get(source_name, {})
    
    @classmethod
    def is_source_enabled(cls, source_name: str) -> bool:
        """Verificar si una fuente está habilitada"""
        source_config = cls.get_source_config(source_name)
        return source_config.get('enabled', False)
    
    @classmethod
    def get_enabled_sources(cls) -> list:
        """Obtener lista de fuentes habilitadas"""
        return [name for name, config in cls.SOURCES.items() if config.get('enabled', False)]
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validar configuración"""
        errors = []
        
        # Validar configuración de base de datos
        if not cls.DATABASE['host']:
            errors.append("DB_HOST no está configurado")
        if not cls.DATABASE['user']:
            errors.append("DB_USER no está configurado")
        if not cls.DATABASE['password']:
            errors.append("DB_PASSWORD no está configurado")
        
        # Validar que al menos una fuente esté habilitada
        if not cls.get_enabled_sources():
            errors.append("Ninguna fuente de noticias está habilitada")
        
        # Validar configuración de notificaciones si está habilitada
        if cls.NOTIFICATIONS['enabled']:
            if cls.NOTIFICATIONS['email']['smtp_server'] and not cls.NOTIFICATIONS['email']['username']:
                errors.append("EMAIL_USERNAME requerido cuando las notificaciones están habilitadas")
        
        if errors:
            print("Errores de configuración:")
            for error in errors:
                print(f"  - {error}")
            return False
        
        return True
    
    @classmethod
    def print_config(cls):
        """Imprimir configuración actual"""
        print("=== CONFIGURACIÓN ACTUAL ===")
        print(f"Base de datos: {cls.DATABASE['host']}:{cls.DATABASE['port']}/{cls.DATABASE['database']}")
        print(f"Usuario BD: {cls.DATABASE['user']}")
        print(f"Intervalo scheduler: {cls.SCHEDULER['interval_hours']} horas")
        print(f"Fuentes habilitadas: {', '.join(cls.get_enabled_sources())}")
        print(f"Modo incremental: {cls.SCRAPING['enable_incremental']}")
        print(f"Directorio salida: {cls.OUTPUT['output_directory']}")
        print(f"Nivel logging: {cls.LOGGING['level']}")
        print(f"Notificaciones: {'Habilitadas' if cls.NOTIFICATIONS['enabled'] else 'Deshabilitadas'}")

# Configuración por defecto para desarrollo local
DEFAULT_CONFIG = {
    'database': Config.DATABASE,
    'scraping': Config.SCRAPING,
    'scheduler': Config.SCHEDULER,
    'sources': Config.SOURCES,
    'output': Config.OUTPUT,
    'logging': Config.LOGGING,
    'notifications': Config.NOTIFICATIONS,
    'maintenance': Config.MAINTENANCE
}

if __name__ == "__main__":
    # Validar y mostrar configuración
    if Config.validate_config():
        print("✅ Configuración válida")
        Config.print_config()
    else:
        print("❌ Configuración inválida")
        exit(1)
