# Sistema de Scraping de Noticias con Redis y Celery

Sistema automatizado y asíncrono para extraer noticias de 4 fuentes peruanas con procesamiento paralelo, cache Redis y colas de tareas Celery.

## 🚀 Características Principales

- **Procesamiento Asíncrono**: Redis + Celery para scraping paralelo
- **Alta Performance**: Workers múltiples y cache inteligente
- **Monitoreo en Tiempo Real**: Flower web UI para supervisión
- **Escalabilidad**: Fácil escalado horizontal de workers
- **Base de Datos**: PostgreSQL con índices optimizados
- **Archivos**: CSV y JSON automáticos en carpeta `data/`

## 📰 Fuentes de Noticias

- **Diario Sin Fronteras**: https://diariosinfronteras.com.pe/
- **Los Andes**: https://losandes.com.pe
- **Pachamama Radio**: https://pachamamaradio.org/
- **Puno Noticias**: https://punonoticias.pe/

## Instalación Rápida (Windows)

1. **Instalar Python** (si no lo tienes):
   - Descarga desde: https://python.org
   - Asegúrate de marcar "Add Python to PATH"

2. **Instalar PostgreSQL**:
   - Descarga desde: https://postgresql.org/download/windows/
   - Usuario: `postgres`
   - Password: `123456`
   - Puerto: `5432`

3. **Ejecutar instalación automática**:
   ```cmd
   install_windows.bat
   ```

## Instalación Manual

1. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configurar PostgreSQL**:
   - Crear usuario `postgres` con password `123456`
   - Crear base de datos `news_scraper`

3. **Probar conexión**:
   ```bash
   python test_db.py
   ```

## 🚀 Uso

### Sistema Local con Redis y Celery
```bash
# Instalar dependencias
pip install -r requirements.txt

# Iniciar sistema completo (Redis + Celery + Workers)
python start_local.py

# Ejecutar scraping asíncrono
python celery_client.py
```

### Sistema Tradicional (Sin Redis)
```bash
# Probar el sistema
python test_local.py

# Ejecutar scraping una vez
python unified_scraper.py

# Ejecutar scheduler (cada hora)
python scheduler.py
```

### Docker Compose (Recomendado)
```bash
# Iniciar todos los servicios
sudo docker-compose up -d

# Ver logs
sudo docker-compose logs -f

# Escalar workers
sudo docker-compose up -d --scale celery-worker=4
```

## Estructura de Datos

Las noticias se almacenan con la siguiente estructura:

```sql
CREATE TABLE noticias (
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
```

## 📁 Archivos Generados

- **CSV**: `data/noticias_[fuente]_[timestamp].csv`
- **JSON**: `data/noticias_[fuente]_[timestamp].json`
- **Logs**: `unified_scraper.log`, `celery_worker.log`, `celery_beat.log`
- **Estadísticas**: `data/scraping_stats.json`

## Configuración

Edita `config.py` para modificar:
- Intervalo de scraping (por defecto: 1 hora)
- Fuentes habilitadas
- Configuración de base de datos
- Configuración de logging

## Solución de Problemas

### Error de Conexión a PostgreSQL
1. Verifica que PostgreSQL esté ejecutándose
2. Confirma usuario: `postgres`, password: `123456`
3. Verifica puerto: `5432`

### Error de Importación
```bash
pip install -r requirements.txt
```

### Error de Permisos
Ejecuta como administrador en Windows

## Comandos Útiles

```bash
# Ver estado de la base de datos
python -c "from database import DatabaseManager; db = DatabaseManager(); db.connect(); print(db.get_estadisticas())"

# Limpiar logs antiguos
del *.log

# Ver logs en tiempo real
python scheduler.py
```

## Estructura del Proyecto

```
news/
├── database.py              # Gestión de PostgreSQL
├── unified_scraper.py       # Scraper unificado
├── scheduler.py            # Scheduler recursivo
├── config.py               # Configuración
├── test_local.py           # Pruebas del sistema
├── test_db.py              # Prueba de base de datos
├── requirements.txt        # Dependencias
├── install_windows.bat     # Instalación automática
├── codigos-claude/         # Scrapers individuales
│   ├── diario-sinfronteras/
│   ├── los-andes/
│   ├── pachamama/
│   └── puno-noticias/
└── output/                 # Archivos generados
```

## 🌐 Despliegue en AWS

### Despliegue Optimizado (Recomendado)
```bash
# En instancia EC2
sudo ./deploy_aws_optimized.sh
```

### Servicios Desplegados
- **Redis**: Cache y colas de tareas
- **PostgreSQL**: Base de datos
- **Celery Workers**: Procesamiento asíncrono
- **Celery Beat**: Scheduler automático
- **Flower**: Monitoreo web (puerto 5555)
- **Nginx**: Servidor web para archivos

### Monitoreo
- **Flower UI**: `http://[IP_PUBLICA]:5555`
- **Archivos**: `http://[IP_PUBLICA]/data/`
- **Logs**: `docker-compose logs -f`

## 📊 Rendimiento

### Antes (Sistema Tradicional)
- ⏱️ Tiempo: ~30-60 minutos para 4 fuentes
- 🔄 Procesamiento: Secuencial
- 📊 Workers: 1

### Después (Redis + Celery)
- ⏱️ Tiempo: ~5-10 minutos para 4 fuentes
- 🔄 Procesamiento: Paralelo asíncrono
- 📊 Workers: 4-8 (escalable)

## 🚀 Próximos Pasos

1. **Probar localmente**: `python test_local.py`
2. **Sistema asíncrono**: `python start_local.py`
3. **Docker Compose**: `docker-compose up -d`
4. **Desplegar en AWS**: `./deploy_aws_optimized.sh`
