#!/bin/bash

# Script de despliegue optimizado en AWS para el sistema de scraping con Redis y Celery
# Este script configura una instancia EC2 con Docker y ejecuta el sistema completo

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir mensajes
print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[HEADER]${NC} $1"
}

# Verificar que se ejecute como root o con sudo
if [ "$EUID" -ne 0 ]; then
    print_error "Este script debe ejecutarse como root o con sudo"
    exit 1
fi

print_header "=== DESPLIEGUE OPTIMIZADO EN AWS - SISTEMA DE SCRAPING ==="
print_header "Con Redis, Celery y procesamiento asíncrono"

# Actualizar sistema
print_message "Actualizando sistema..."
apt-get update -y
apt-get upgrade -y

# Instalar Docker
print_message "Instalando Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    systemctl start docker
    systemctl enable docker
    usermod -aG docker ubuntu
    print_message "Docker instalado correctamente"
else
    print_message "Docker ya está instalado"
fi

# Instalar Docker Compose
print_message "Instalando Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    print_message "Docker Compose instalado correctamente"
else
    print_message "Docker Compose ya está instalado"
fi

# Instalar dependencias adicionales
print_message "Instalando dependencias adicionales..."
apt-get install -y \
    postgresql-client \
    redis-tools \
    htop \
    nginx \
    certbot \
    python3-certbot-nginx

# Crear directorio del proyecto
PROJECT_DIR="/opt/news-scraper"
print_message "Creando directorio del proyecto: $PROJECT_DIR"
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# Crear estructura de directorios
mkdir -p data logs codigos-claude

# Copiar archivos del proyecto
print_message "Copiando archivos del proyecto..."
cp requirements.txt $PROJECT_DIR/
cp database.py $PROJECT_DIR/
cp unified_scraper.py $PROJECT_DIR/
cp scheduler.py $PROJECT_DIR/
cp config.py $PROJECT_DIR/
cp Dockerfile $PROJECT_DIR/
cp docker-compose.yml $PROJECT_DIR/
cp init.sql $PROJECT_DIR/
cp nginx.conf $PROJECT_DIR/

# Copiar archivos de Celery
cp celery_config.py $PROJECT_DIR/
cp celery_tasks.py $PROJECT_DIR/
cp celery_client.py $PROJECT_DIR/
cp start_local.py $PROJECT_DIR/

# Copiar directorio de scrapers
if [ -d "codigos-claude" ]; then
    cp -r codigos-claude/* $PROJECT_DIR/codigos-claude/
    print_message "Scrapers copiados correctamente"
else
    print_warning "Directorio codigos-claude no encontrado, creando estructura básica..."
    mkdir -p $PROJECT_DIR/codigos-claude/{diario-sinfronteras,los-andes,pachamama,puno-noticias}
fi

# Configurar firewall
print_message "Configurando firewall..."
ufw allow 22/tcp   # SSH
ufw allow 80/tcp   # HTTP
ufw allow 443/tcp  # HTTPS
ufw allow 5555/tcp # Flower (monitoreo)
ufw --force enable

# Crear archivo de variables de entorno optimizado
print_message "Creando archivo de variables de entorno optimizado..."
cat > $PROJECT_DIR/.env << EOF
# Configuración de Redis
REDIS_URL=redis://redis:6379/0

# Configuración de base de datos
DB_HOST=postgres
DB_PORT=5432
DB_NAME=news_scraper
DB_USER=postgres
DB_PASSWORD=123456

# Configuración de scraping optimizada
SCRAPING_DELAY=1
SCRAPING_WORKERS=10
SCRAPING_TIMEOUT=30
SCRAPING_RETRIES=3
SCRAPING_INCREMENTAL=true
SCRAPING_MAX_ARTICLES=2000

# Configuración de Celery
CELERY_WORKER_CONCURRENCY=4
CELERY_WORKER_PREFETCH_MULTIPLIER=1
CELERY_TASK_ACKS_LATE=true
CELERY_WORKER_MAX_TASKS_PER_CHILD=1000

# Fuentes
SOURCE_SIN_FRONTERAS=true
SOURCE_LOS_ANDES=true
SOURCE_PACHAMAMA=true
SOURCE_PUNO_NOTICIAS=true

# Salida
OUTPUT_CSV=true
OUTPUT_JSON=true
OUTPUT_DIR=/app/data
OUTPUT_TIMESTAMP=true

# Logging
LOG_LEVEL=INFO
LOG_FILE=/app/logs/unified_scraper.log
LOG_MAX_SIZE_MB=50
LOG_BACKUP_COUNT=10

# Notificaciones
NOTIFICATIONS_ENABLED=false

# Mantenimiento
MAINTENANCE_CLEANUP_LOGS_DAYS=30
MAINTENANCE_CLEANUP_FILES_DAYS=7
MAINTENANCE_DB_BACKUP=false
MAINTENANCE_BACKUP_INTERVAL=24

# AWS (opcional)
AWS_REGION=us-east-1
EOF

# Crear script de inicio optimizado
print_message "Creando script de inicio optimizado..."
cat > $PROJECT_DIR/start.sh << 'EOF'
#!/bin/bash
cd /opt/news-scraper

echo "🚀 Iniciando sistema de scraping optimizado..."

# Detener contenedores existentes
docker-compose down

# Construir imágenes
echo "🔨 Construyendo imágenes Docker..."
docker-compose build --parallel

# Iniciar servicios
echo "🚀 Iniciando servicios..."
docker-compose up -d

# Esperar a que los servicios estén listos
echo "⏳ Esperando a que los servicios estén listos..."
sleep 30

# Verificar estado
echo "📊 Estado de los servicios:"
docker-compose ps

# Mostrar logs iniciales
echo "📋 Logs iniciales:"
docker-compose logs --tail=20

echo "✅ Sistema iniciado correctamente"
echo "📊 Monitoreo: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):5555"
echo "📁 Archivos: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)/data/"
EOF

chmod +x $PROJECT_DIR/start.sh

# Crear script de parada
print_message "Creando script de parada..."
cat > $PROJECT_DIR/stop.sh << 'EOF'
#!/bin/bash
cd /opt/news-scraper
docker-compose down
echo "✅ Sistema detenido"
EOF

chmod +x $PROJECT_DIR/stop.sh

# Crear script de monitoreo
print_message "Creando script de monitoreo..."
cat > $PROJECT_DIR/monitor.sh << 'EOF'
#!/bin/bash
cd /opt/news-scraper

echo "=== ESTADO DEL SISTEMA ==="
echo "Contenedores:"
docker-compose ps

echo ""
echo "Uso de recursos:"
docker stats --no-stream

echo ""
echo "Logs recientes:"
docker-compose logs --tail=20

echo ""
echo "Uso de disco:"
df -h

echo ""
echo "Uso de memoria:"
free -h

echo ""
echo "Estado de Redis:"
docker-compose exec redis redis-cli ping

echo ""
echo "Estado de PostgreSQL:"
docker-compose exec postgres pg_isready -U postgres
EOF

chmod +x $PROJECT_DIR/monitor.sh

# Crear script de backup
print_message "Creando script de backup..."
cat > $PROJECT_DIR/backup.sh << 'EOF'
#!/bin/bash
cd /opt/news-scraper

BACKUP_DIR="/opt/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

echo "📦 Creando backup en $BACKUP_DIR..."

# Backup de base de datos
docker-compose exec -T postgres pg_dump -U postgres news_scraper > $BACKUP_DIR/database.sql

# Backup de archivos de datos
cp -r data/ $BACKUP_DIR/

# Backup de logs
cp -r logs/ $BACKUP_DIR/

# Backup de configuración
cp docker-compose.yml $BACKUP_DIR/
cp .env $BACKUP_DIR/

echo "✅ Backup completado en $BACKUP_DIR"
EOF

chmod +x $PROJECT_DIR/backup.sh

# Configurar Nginx para servir archivos
print_message "Configurando Nginx..."
cat > /etc/nginx/sites-available/news-scraper << EOF
server {
    listen 80;
    server_name _;
    
    # Servir archivos de datos
    location /data/ {
        alias /opt/news-scraper/data/;
        autoindex on;
        autoindex_exact_size off;
        autoindex_localtime on;
    }
    
    # Proxy para Flower
    location /flower/ {
        proxy_pass http://localhost:5555/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # Página de estado
    location / {
        return 200 'Sistema de Scraping de Noticias - OK';
        add_header Content-Type text/plain;
    }
}
EOF

ln -sf /etc/nginx/sites-available/news-scraper /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx

# Crear servicio systemd para auto-inicio
print_message "Creando servicio systemd..."
cat > /etc/systemd/system/news-scraper.service << EOF
[Unit]
Description=News Scraper System with Redis and Celery
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/start.sh
ExecStop=$PROJECT_DIR/stop.sh
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable news-scraper.service

# Construir y ejecutar contenedores
print_message "Construyendo contenedores Docker..."
cd $PROJECT_DIR
docker-compose build --parallel

print_message "Iniciando servicios..."
docker-compose up -d

# Esperar a que los servicios estén listos
print_message "Esperando a que los servicios estén listos..."
sleep 60

# Verificar estado
print_message "Verificando estado de los servicios..."
docker-compose ps

# Mostrar logs iniciales
print_message "Mostrando logs iniciales..."
docker-compose logs --tail=20

# Crear enlaces simbólicos para fácil acceso
ln -sf $PROJECT_DIR/start.sh /usr/local/bin/news-scraper-start
ln -sf $PROJECT_DIR/stop.sh /usr/local/bin/news-scraper-stop
ln -sf $PROJECT_DIR/monitor.sh /usr/local/bin/news-scraper-monitor
ln -sf $PROJECT_DIR/backup.sh /usr/local/bin/news-scraper-backup

# Obtener información de la instancia
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
PRIVATE_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)
REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)
INSTANCE_TYPE=$(curl -s http://169.254.169.254/latest/meta-data/instance-type)

print_header "=== DESPLIEGUE COMPLETADO ==="
print_message "El sistema está ejecutándose en:"
print_message "  - IP Pública: $PUBLIC_IP"
print_message "  - IP Privada: $PRIVATE_IP"
print_message "  - Región: $REGION"
print_message "  - Tipo de instancia: $INSTANCE_TYPE"
print_message ""
print_message "Servicios disponibles:"
print_message "  - Monitoreo (Flower): http://$PUBLIC_IP:5555"
print_message "  - Archivos de datos: http://$PUBLIC_IP/data/"
print_message "  - Base de datos: $PRIVATE_IP:5432"
print_message "  - Redis: $PRIVATE_IP:6379"
print_message ""
print_message "Comandos útiles:"
print_message "  - Iniciar: news-scraper-start"
print_message "  - Detener: news-scraper-stop"
print_message "  - Monitorear: news-scraper-monitor"
print_message "  - Backup: news-scraper-backup"
print_message "  - Ver logs: cd $PROJECT_DIR && docker-compose logs -f"
print_message ""
print_message "El sistema ejecutará scraping automáticamente cada hora"
print_message "con procesamiento asíncrono usando Redis y Celery"
print_message ""
print_message "Para escalar workers:"
print_message "  docker-compose up -d --scale celery-worker=4"

# Crear script de escalado
cat > $PROJECT_DIR/scale_workers.sh << 'EOF'
#!/bin/bash
cd /opt/news-scraper

WORKERS=${1:-4}
echo "🔧 Escalando workers a $WORKERS instancias..."

docker-compose up -d --scale celery-worker=$WORKERS

echo "✅ Workers escalados a $WORKERS instancias"
docker-compose ps
EOF

chmod +x $PROJECT_DIR/scale_workers.sh
ln -sf $PROJECT_DIR/scale_workers.sh /usr/local/bin/news-scraper-scale

print_message "Para escalar workers: news-scraper-scale [número]"
