# 🚀 Inicio Rápido - Sistema de Scraping de Noticias

## ⚡ Instalación en 3 Pasos

### 1. Instalar dependencias del sistema
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3 python3-pip python3-venv postgresql postgresql-contrib

# Configurar PostgreSQL
sudo systemctl start postgresql
sudo -u postgres psql -c "CREATE DATABASE news_scraping;"
sudo -u postgres psql -c "CREATE USER postgres WITH PASSWORD '123456';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE news_scraping TO postgres;"
```

### 2. Instalar el sistema
```bash
# Hacer ejecutables los scripts
chmod +x *.sh

# Instalación automática
./install.sh
```

### 3. Ejecutar el sistema
```bash
# Inicio rápido con menú
./start.sh

# O directamente
python main.py
```

## 🐳 Con Docker (Más Fácil)

```bash
# Iniciar todo con Docker Compose
docker-compose up -d

# Ver logs
docker-compose logs -f

# Detener
docker-compose down
```

## ☁️ En AWS EC2

```bash
# 1. Subir archivos a la instancia
scp -r . ubuntu@your-instance-ip:/home/ubuntu/

# 2. Conectar y ejecutar
ssh ubuntu@your-instance-ip
chmod +x deploy_aws.sh
./deploy_aws.sh
```

## 📊 Uso Básico

### Modo Interactivo
```bash
python main.py
# Seleccionar opción 1 para scraping completo
```

### Modo Programado (Automático)
```bash
python scheduler.py --mode schedule --interval 1
# Ejecuta cada hora automáticamente
```

### Una Sola Ejecución
```bash
python scheduler.py --mode once
```

## 📁 Archivos Generados

- **CSV y JSON por fuente**: `data/noticias_[fuente]_[timestamp].csv/json`
- **Archivos consolidados**: `data/noticias_consolidadas_[timestamp].csv/json`
- **Base de datos**: PostgreSQL con tabla `noticias`
- **Logs**: `scraper.log`

## 🔧 Configuración

### Variables de Entorno
```bash
# Editar .env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=news_scraping
DB_USER=postgres
DB_PASSWORD=123456
```

### Fuentes de Noticias
- ✅ Diario Sin Fronteras
- ✅ Los Andes  
- ✅ Pachamama Radio
- ✅ Puno Noticias

## 📈 Monitoreo

### Ver Estado
```bash
# Script de monitoreo
./monitor.sh

# Logs en tiempo real
tail -f scraper.log

# Estado de servicios
sudo systemctl status postgresql
```

### Interfaz Web (con Docker)
- URL: `http://localhost`
- Archivos: `http://localhost/data/`

## 🆘 Solución Rápida de Problemas

### Error de Base de Datos
```bash
sudo systemctl restart postgresql
psql -h localhost -U postgres -d news_scraping
```

### Error de Permisos
```bash
chmod +x *.sh
sudo chown -R $USER:$USER .
```

### Error de Memoria
```bash
# Verificar uso
free -h
htop

# Ajustar en config.py
MAX_WORKERS = 2  # Reducir workers
```

## 📞 Comandos Útiles

```bash
# Ejecutar pruebas
python test_system.py

# Ver estadísticas
python -c "from news_scraper_manager import NewsScraperManager; m=NewsScraperManager(); m.setup_database(); print(m.get_statistics())"

# Respaldar datos
./backup.sh

# Ver logs
journalctl -u news-scraper -f  # Con systemd
```

## 🎯 Resultados Esperados

- **Noticias por hora**: 50-200 (dependiendo de la fuente)
- **Archivos generados**: CSV y JSON automáticamente
- **Base de datos**: Almacenamiento persistente en PostgreSQL
- **Ejecución**: Automática cada hora
- **Monitoreo**: Logs y estadísticas disponibles

---

**¡El sistema está listo para recopilar noticias automáticamente!** 🎉
