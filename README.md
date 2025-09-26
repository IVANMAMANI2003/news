# 📰 Sistema de Scraping de Noticias Automatizado

Sistema completo de recolección automática de noticias de múltiples fuentes peruanas con almacenamiento en PostgreSQL y ejecución recursiva.

## 🎯 Características

- **Scraping de 4 fuentes de noticias**:
  - Diario Sin Fronteras
  - Los Andes
  - Pachamama Radio
  - Puno Noticias
- **Base de datos PostgreSQL** con esquema optimizado
- **Ejecución recursiva** cada hora automáticamente (Celery Beat)
- **Colas de tareas** con Celery + Redis (worker y beat)
- **Monitoreo de tareas** con Flower
- **Generación de archivos** CSV y JSON por fuente y consolidados
- **Sistema de logging** completo
- **Preparado para AWS** con Docker y scripts de despliegue
- **Interfaz web** para monitoreo

## ☁️ Repositorio

- GitHub: [`IVANMAMANI2003/news`](https://github.com/IVANMAMANI2003/news.git)

## 🐳 Ejecución en Docker (recomendada)

```bash
# Construir e iniciar todos los servicios (usar sudo en AWS)
sudo docker-compose up -d --build

# Ver estado de contenedores
sudo docker ps

# Logs del worker Celery
sudo docker logs -f news_celery_worker | sed -u 's/^/[CELERY-WORKER] /'

# Logs del beat Celery
sudo docker logs -f news_celery_beat | sed -u 's/^/[CELERY-BEAT] /'

# Logs del scraper (ejecución one-shot)
sudo docker logs -f news_scraper | sed -u 's/^/[SCRAPER] /'

# Monitoreo Flower
# URL: http://<IP-SERVIDOR>:5555
```

Servicios incluidos en `docker-compose.yml`:
- `postgres`: Base de datos
- `redis`: Broker/Backend Celery
- `scraper`: ejecución única de scraping (útil para pruebas)
- `celery_worker`: procesador de tareas
- `celery_beat`: programador (cada hora)
- `flower`: monitoreo de tareas en `:5555`

## 🔁 Programación con Celery

- Tarea periódica cada hora: `tasks.scrape_all_sources`
- Ejecutar manualmente dentro de contenedor worker:
```bash
sudo docker exec -it news_celery_worker bash -lc "python - <<'PY'
from tasks import scrape_all_sources
r = scrape_all_sources.delay()
print('Task sent:', r.id)
PY"
```

## 🗄️ Base de datos y verificación

```bash
# Ingresar a PostgreSQL en contenedor
echo "SELECT fuente, COUNT(*), MAX(fecha_extraccion) FROM noticias GROUP BY fuente ORDER BY 2 DESC;" \
  | sudo docker exec -i news_postgres psql -U postgres -d news_scraping
```

## 🧪 Pruebas rápidas

```bash
# Ejecutar scraping one-shot (fuera del schedule)
sudo docker run --rm --network host -v $(pwd)/data:/app/data -v $(pwd)/logs:/app/logs \
  -e DB_HOST=localhost -e DB_USER=postgres -e DB_PASSWORD=123456 \
  $(sudo docker build -q .) python scheduler.py --mode once
```

## 🔐 Recomendaciones AWS

- Anteponer `sudo` a todos los comandos del sistema: `sudo docker ...`, `sudo systemctl ...`
- Abrir puertos: 22, 80, 5432, 5555
- Monitorear logs en tiempo real:
```bash
sudo docker logs -f news_celery_worker
sudo docker logs -f news_celery_beat
sudo docker logs -f news_scraper
```
- Ver tareas en Flower: `http://<ip>:5555`

## 📜 Tareas Celery

Archivo: `tasks.py`
- `scrape_all_sources`: ejecuta scraping y guarda en PostgreSQL
- `scrape_single_source(<source_key>)`: procesa una sola fuente

## 📁 Archivos relevantes

- `docker-compose.yml`: orquestación (Postgres, Redis, Worker, Beat, Flower)
- `tasks.py`: tareas Celery + beat schedule
- `news_scraper_manager.py`: orquesta scrapers + BD + files
- `database.py`: conexión/DDL/insert en PostgreSQL
- `base_scraper.py` y `scrapers/*`: scrapers por sitio

## 🗄️ Esquema de Base de Datos

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

## 🧭 Operaciones comunes (AWS)

```bash
# Construir y levantar todo
sudo docker-compose up -d --build

# Verificar que Beat esté programando
sudo docker logs -f news_celery_beat | grep -E "Scheduler|scrape_all_sources"

# Verificar inserciones en BD
echo "SELECT COUNT(*) FROM noticias;" | sudo docker exec -i news_postgres psql -U postgres -d news_scraping

# Reiniciar servicios
sudo docker-compose restart
```

## 📋 Requisitos

- Python 3.9+
- PostgreSQL 13+
- Docker (opcional)
- Ubuntu/Debian (para despliegue AWS)

## 🚀 Instalación Local

### 1. Clonar el repositorio
```bash
git clone <repository-url>
cd news-scraping
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Configurar PostgreSQL
```bash
# Instalar PostgreSQL
sudo apt-get install postgresql postgresql-contrib

# Crear base de datos
sudo -u postgres psql
CREATE DATABASE news_scraping;
CREATE USER postgres WITH PASSWORD '123456';
GRANT ALL PRIVILEGES ON DATABASE news_scraping TO postgres;
\q
```

### 4. Configurar variables de entorno
```bash
cp .env.example .env
# Editar .env con sus configuraciones
```

### 5. Ejecutar el sistema
```bash
# Modo interactivo
python main.py

# Modo programado (cada hora)
python scheduler.py --mode schedule --interval 1

# Una sola ejecución
python scheduler.py --mode once
```

## 🐳 Instalación con Docker

### 1. Usar Docker Compose
```bash
# Iniciar todos los servicios
docker-compose up -d

# Ver logs
docker-compose logs -f

# Detener servicios
docker-compose down
```

### 2. Usar Docker individual
```bash
# Construir imagen
docker build -t news-scraper .

# Ejecutar con PostgreSQL externo
docker run -d \
  --name news-scraper \
  -e DB_HOST=host.docker.internal \
  -e DB_PASSWORD=123456 \
  -v $(pwd)/data:/app/data \
  news-scraper
```

## ☁️ Despliegue en AWS

### 1. Preparar instancia EC2
- Instancia Ubuntu 20.04 LTS o superior
- Mínimo 2GB RAM, 20GB almacenamiento
- Puertos abiertos: 22 (SSH), 80 (HTTP), 5432 (PostgreSQL)

### 2. Ejecutar script de despliegue
```bash
# Subir archivos a la instancia
scp -r . ubuntu@your-instance-ip:/home/ubuntu/

# Conectar a la instancia
ssh ubuntu@your-instance-ip

# Ejecutar script de despliegue
chmod +x deploy_aws.sh
./deploy_aws.sh
```

### 3. Verificar instalación
```bash
# Ver estado de servicios
sudo systemctl status news-scraper

# Ver logs
journalctl -u news-scraper -f

# Monitorear sistema
./monitor.sh
```

## 📊 Uso del Sistema

### Modo Interactivo
```bash
python main.py
```

Menú disponible:
1. Ejecutar scraping completo
2. Ejecutar fuente específica
3. Generar archivos consolidados
4. Mostrar estadísticas
5. Iniciar modo programado
6. Salir

### Modo Programado
```bash
# Cada hora
python scheduler.py --mode schedule --interval 1

# Cada 6 horas
python scheduler.py --mode schedule --interval 6

# Una sola ejecución
python scheduler.py --mode once
```

### Fuente Específica
```bash
python scheduler.py --mode once --source diario_sin_fronteras
```

## 📁 Estructura de Archivos

```
news-scraping/
├── main.py                          # Script principal
├── scheduler.py                     # Programador de tareas
├── news_scraper_manager.py          # Gestor principal
├── database.py                      # Manejador de BD
├── base_scraper.py                  # Clase base para scrapers
├── config.py                        # Configuración
├── requirements.txt                 # Dependencias
├── scrapers/                        # Scrapers específicos
│   ├── __init__.py
│   ├── diario_sin_fronteras_scraper.py
│   ├── los_andes_scraper.py
│   ├── pachamama_scraper.py
│   └── puno_noticias_scraper.py
├── data/                           # Archivos generados
├── Dockerfile                      # Imagen Docker
├── docker-compose.yml              # Orquestación
├── deploy_aws.sh                   # Script de despliegue AWS
├── nginx.conf                      # Configuración web
└── README.md                       # Este archivo
```

## 🗄️ Esquema de Base de Datos

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

## 📈 Monitoreo

### Logs del Sistema
```bash
# Ver logs en tiempo real
tail -f scraper.log

# Ver logs del servicio
journalctl -u news-scraper -f

# Ver logs de Docker
docker-compose logs -f scraper
```

### Estadísticas
```bash
# Script de monitoreo
./monitor.sh

# Consultas SQL directas
psql -h localhost -U postgres -d news_scraping
```

### Interfaz Web
- URL: `http://your-server-ip`
- Archivos de datos: `http://your-server-ip/data/`
- API de estado: `http://your-server-ip/api/stats`

## 🔧 Configuración

### Variables de Entorno
```bash
# Base de datos
DB_HOST=localhost
DB_PORT=5432
DB_NAME=news_scraping
DB_USER=postgres
DB_PASSWORD=123456

# Logging
LOG_LEVEL=INFO

# AWS (para despliegue)
AWS_REGION=us-east-1
AWS_INSTANCE_ID=your-instance-id
```

### Configuración de Scraping
Editar `config.py` para ajustar:
- Delays entre requests
- Número de workers
- Límites de páginas
- Patrones de URLs

## 🛠️ Mantenimiento

### Respaldos Automáticos
```bash
# Ejecutar respaldo manual
./backup.sh

# Los respaldos se ejecutan automáticamente cada día a las 2 AM
```

### Limpieza de Archivos
```bash
# Limpiar archivos antiguos (más de 30 días)
find data/ -name "*.csv" -mtime +30 -delete
find data/ -name "*.json" -mtime +30 -delete
```

### Actualización del Sistema
```bash
# Detener servicios
sudo systemctl stop news-scraper

# Actualizar código
git pull origin main

# Reiniciar servicios
sudo systemctl start news-scraper
```

## 🐛 Solución de Problemas

### Error de Conexión a BD
```bash
# Verificar PostgreSQL
sudo systemctl status postgresql

# Verificar conexión
psql -h localhost -U postgres -d news_scraping
```

### Error de Permisos
```bash
# Dar permisos al usuario
sudo chown -R $USER:$USER /opt/news_scraping
chmod +x *.sh
```

### Error de Memoria
```bash
# Verificar uso de memoria
free -h
htop

# Ajustar límites en config.py
```

## 📞 Soporte

Para problemas o preguntas:
1. Revisar logs del sistema
2. Verificar configuración de red
3. Comprobar estado de servicios
4. Consultar este README

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver archivo LICENSE para más detalles.

---

**Desarrollado para la recolección automatizada de noticias peruanas** 🇵🇪
