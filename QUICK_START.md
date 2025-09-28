# 🚀 Inicio Rápido - Sistema de Scraping de Noticias

## ⚡ Instalación en 5 minutos

### 1. Clonar el repositorio
```bash
git clone https://github.com/IVANMAMANI2003/news.git
cd news
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Configurar PostgreSQL
```bash
# Crear base de datos
sudo -u postgres psql
CREATE DATABASE news_scraper;
CREATE USER postgres WITH PASSWORD '123456';
GRANT ALL PRIVILEGES ON DATABASE news_scraper TO postgres;
\q
```

### 4. Probar el sistema
```bash
python test_db.py
```

### 5. Ejecutar scraping
```bash
python run_complete_scraper.py
```

## 🐳 Con Docker (Recomendado)

```bash
# Iniciar todos los servicios
sudo docker-compose up -d

# Ver logs
sudo docker-compose logs -f

# Monitorear en: http://localhost:5555
```

## ☁️ Despliegue en AWS

```bash
# En instancia EC2
sudo ./deploy_aws_optimized.sh
```

## 📊 Monitoreo

- **Flower UI**: http://localhost:5555
- **Archivos**: http://localhost/data/
- **Logs**: `docker-compose logs -f`

## 🆘 Solución de Problemas

### Error de PostgreSQL
```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### Error de Redis
```bash
# Ubuntu/Debian
sudo apt install redis-server
sudo systemctl start redis-server

# Windows: Descargar desde https://github.com/microsoftarchive/redis/releases
```

### Error de permisos
```bash
chmod +x *.sh
```

## 📁 Estructura del Proyecto

```
news/
├── 📁 codigos-claude/          # Scrapers individuales
├── 📁 data/                    # Archivos generados
├── 🐳 docker-compose.yml       # Orquestación de servicios
├── 🚀 deploy_aws_optimized.sh  # Script de despliegue AWS
├── ⚙️ celery_config.py         # Configuración de Celery
├── 🔄 celery_tasks.py          # Tareas asíncronas
├── 🖥️ celery_client.py         # Cliente para ejecutar tareas
├── 🗄️ database.py              # Gestión de PostgreSQL
├── 📊 unified_scraper.py       # Scraper unificado
├── ⏰ scheduler.py             # Programador de tareas
└── 🧪 test_*.py               # Scripts de prueba
```

## 🎯 Comandos Útiles

```bash
# Probar sistema completo
python test_local.py

# Scraping asíncrono
python start_local.py

# Scraping manual
python run_complete_scraper.py

# Ver estadísticas de BD
python -c "from database import DatabaseManager; db = DatabaseManager(); db.connect(); print(db.get_estadisticas())"

# Escalar workers
sudo docker-compose up -d --scale celery-worker=4
```

## 📈 Rendimiento

- **Sistema tradicional**: 30-60 minutos para 4 fuentes
- **Sistema optimizado**: 5-10 minutos para 4 fuentes
- **Mejora**: 80-90% más rápido

## 🔗 Enlaces Útiles

- [Repositorio GitHub](https://github.com/IVANMAMANI2003/news)
- [Documentación completa](README.md)
- [Configuración avanzada](config.py)

---

**¡Listo para usar! 🎉**
