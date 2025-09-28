#!/bin/bash

# Script final para desplegar el sistema de scraping en AWS
# Este script automatiza todo el proceso de despliegue

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

print_header "=== DESPLIEGUE AUTOMÁTICO EN AWS ==="
print_header "Sistema de Scraping de Noticias con Redis y Celery"

# Verificar que se ejecute como root o con sudo
if [ "$EUID" -ne 0 ]; then
    print_error "Este script debe ejecutarse como root o con sudo"
    exit 1
fi

# Verificar que estamos en una instancia EC2
if ! curl -s http://169.254.169.254/latest/meta-data/instance-id > /dev/null 2>&1; then
    print_warning "No se detectó una instancia EC2. Continuando de todas formas..."
fi

# Obtener información de la instancia
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id 2>/dev/null || echo "local")
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "localhost")
PRIVATE_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4 2>/dev/null || echo "127.0.0.1")
REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region 2>/dev/null || echo "us-east-1")
INSTANCE_TYPE=$(curl -s http://169.254.169.254/latest/meta-data/instance-type 2>/dev/null || echo "t3.medium")

print_message "Información de la instancia:"
print_message "  - ID: $INSTANCE_ID"
print_message "  - IP Pública: $PUBLIC_IP"
print_message "  - IP Privada: $PRIVATE_IP"
print_message "  - Región: $REGION"
print_message "  - Tipo: $INSTANCE_TYPE"

# Actualizar sistema
print_message "Actualizando sistema..."
apt-get update -y
apt-get upgrade -y

# Instalar dependencias del sistema
print_message "Instalando dependencias del sistema..."
apt-get install -y \
    curl \
    wget \
    git \
    htop \
    nginx \
    certbot \
    python3-certbot-nginx \
    postgresql-client \
    redis-tools \
    unzip

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

# Crear directorio del proyecto
PROJECT_DIR="/opt/news-scraper"
print_message "Creando directorio del proyecto: $PROJECT_DIR"
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# Clonar repositorio desde GitHub
print_message "Clonando repositorio desde GitHub..."
if [ -d ".git" ]; then
    print_message "Repositorio ya existe, actualizando..."
    git pull origin main
else
    git clone https://github.com/IVANMAMANI2003/news.git .
fi

# Crear estructura de directorios
mkdir -p data logs

# Configurar firewall
print_message "Configurando firewall..."
ufw allow 22/tcp   # SSH
ufw allow 80/tcp   # HTTP
ufw allow 443/tcp  # HTTPS
ufw allow 5555/tcp # Flower (monitoreo)
ufw --force enable

# Crear archivo de variables de entorno
print_message "Creando archivo de variables de entorno..."
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

# AWS
AWS_REGION=$REGION
AWS_INSTANCE_ID=$INSTANCE_ID
EOF

# Configurar Nginx
print_message "Configurando Nginx..."
cat > /etc/nginx/sites-available/news-scraper << EOF
server {
    listen 80;
    server_name _;
    
    # Servir archivos de datos
    location /data/ {
        alias $PROJECT_DIR/data/;
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
        return 200 'Sistema de Scraping de Noticias - OK\nIP: $PUBLIC_IP\nInstancia: $INSTANCE_ID\nRegión: $REGION';
        add_header Content-Type text/plain;
    }
}
EOF

ln -sf /etc/nginx/sites-available/news-scraper /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx

# Crear servicio systemd
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
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable news-scraper.service

# Construir y ejecutar contenedores
print_message "Construyendo contenedores Docker..."
docker-compose build --parallel

print_message "Iniciando servicios..."
docker-compose up -d

# Esperar a que los servicios estén listos
print_message "Esperando a que los servicios estén listos..."
sleep 60

# Verificar estado
print_message "Verificando estado de los servicios..."
docker-compose ps

# Crear scripts de utilidad
print_message "Creando scripts de utilidad..."

# Script de inicio
cat > $PROJECT_DIR/start.sh << 'EOF'
#!/bin/bash
cd /opt/news-scraper
docker-compose up -d
echo "✅ Sistema iniciado"
EOF

# Script de parada
cat > $PROJECT_DIR/stop.sh << 'EOF'
#!/bin/bash
cd /opt/news-scraper
docker-compose down
echo "✅ Sistema detenido"
EOF

# Script de monitoreo
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
EOF

# Script de escalado
cat > $PROJECT_DIR/scale_workers.sh << 'EOF'
#!/bin/bash
cd /opt/news-scraper

WORKERS=${1:-4}
echo "🔧 Escalando workers a $WORKERS instancias..."

docker-compose up -d --scale celery-worker=$WORKERS

echo "✅ Workers escalados a $WORKERS instancias"
docker-compose ps
EOF

# Script de backup
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

# Hacer scripts ejecutables
chmod +x $PROJECT_DIR/*.sh

# Crear enlaces simbólicos
ln -sf $PROJECT_DIR/start.sh /usr/local/bin/news-scraper-start
ln -sf $PROJECT_DIR/stop.sh /usr/local/bin/news-scraper-stop
ln -sf $PROJECT_DIR/monitor.sh /usr/local/bin/news-scraper-monitor
ln -sf $PROJECT_DIR/backup.sh /usr/local/bin/news-scraper-backup
ln -sf $PROJECT_DIR/scale_workers.sh /usr/local/bin/news-scraper-scale

# Mostrar información final
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
print_message "  - Escalar workers: news-scraper-scale [número]"
print_message "  - Ver logs: cd $PROJECT_DIR && docker-compose logs -f"
print_message ""
print_message "El sistema ejecutará scraping automáticamente cada hora"
print_message "con procesamiento asíncrono usando Redis y Celery"
print_message ""
print_message "Para escalar workers:"
print_message "  docker-compose up -d --scale celery-worker=4"

# Crear archivo de información del despliegue
cat > $PROJECT_DIR/DEPLOYMENT_INFO.txt << EOF
=== INFORMACIÓN DEL DESPLIEGUE ===
Fecha: $(date)
Instancia: $INSTANCE_ID
IP Pública: $PUBLIC_IP
IP Privada: $PRIVATE_IP
Región: $REGION
Tipo: $INSTANCE_TYPE

=== SERVICIOS ===
- PostgreSQL: $PRIVATE_IP:5432
- Redis: $PRIVATE_IP:6379
- Flower: http://$PUBLIC_IP:5555
- Nginx: http://$PUBLIC_IP

=== COMANDOS ===
- Iniciar: news-scraper-start
- Detener: news-scraper-stop
- Monitorear: news-scraper-monitor
- Backup: news-scraper-backup
- Escalar: news-scraper-scale [número]

=== LOGS ===
- Ver logs: cd $PROJECT_DIR && docker-compose logs -f
- Logs específicos: docker-compose logs -f [servicio]

=== MANTENIMIENTO ===
- Reiniciar: docker-compose restart
- Actualizar: git pull && docker-compose up -d --build
- Limpiar: docker system prune -f
EOF

print_message "Información del despliegue guardada en: $PROJECT_DIR/DEPLOYMENT_INFO.txt"

print_header "🎉 DESPLIEGUE COMPLETADO EXITOSAMENTE"
print_message "El sistema de scraping está listo para usar en AWS"
