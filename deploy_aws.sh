#!/bin/bash

# Script de despliegue en AWS para el sistema de scraping de noticias
# Este script configura una instancia EC2 con Docker y ejecuta el sistema

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Verificar que se ejecute como root o con sudo
if [ "$EUID" -ne 0 ]; then
    print_error "Este script debe ejecutarse como root o con sudo"
    exit 1
fi

print_message "=== DESPLIEGUE EN AWS - SISTEMA DE SCRAPING DE NOTICIAS ==="

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

# Instalar PostgreSQL client (para conexiones externas)
print_message "Instalando PostgreSQL client..."
apt-get install -y postgresql-client

# Crear directorio del proyecto
PROJECT_DIR="/opt/news-scraper"
print_message "Creando directorio del proyecto: $PROJECT_DIR"
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# Crear estructura de directorios
mkdir -p output logs codigos-claude

# Copiar archivos del proyecto (asumiendo que están en el directorio actual)
print_message "Copiando archivos del proyecto..."
if [ -f "requirements.txt" ]; then
    cp requirements.txt $PROJECT_DIR/
else
    print_error "Archivo requirements.txt no encontrado"
    exit 1
fi

if [ -f "database.py" ]; then
    cp database.py $PROJECT_DIR/
else
    print_error "Archivo database.py no encontrado"
    exit 1
fi

if [ -f "unified_scraper.py" ]; then
    cp unified_scraper.py $PROJECT_DIR/
else
    print_error "Archivo unified_scraper.py no encontrado"
    exit 1
fi

if [ -f "scheduler.py" ]; then
    cp scheduler.py $PROJECT_DIR/
else
    print_error "Archivo scheduler.py no encontrado"
    exit 1
fi

if [ -f "config.py" ]; then
    cp config.py $PROJECT_DIR/
else
    print_error "Archivo config.py no encontrado"
    exit 1
fi

if [ -f "Dockerfile" ]; then
    cp Dockerfile $PROJECT_DIR/
else
    print_error "Archivo Dockerfile no encontrado"
    exit 1
fi

if [ -f "docker-compose.yml" ]; then
    cp docker-compose.yml $PROJECT_DIR/
else
    print_error "Archivo docker-compose.yml no encontrado"
    exit 1
fi

if [ -f "init.sql" ]; then
    cp init.sql $PROJECT_DIR/
else
    print_error "Archivo init.sql no encontrado"
    exit 1
fi

if [ -f "nginx.conf" ]; then
    cp nginx.conf $PROJECT_DIR/
else
    print_error "Archivo nginx.conf no encontrado"
    exit 1
fi

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
ufw allow 5432/tcp # PostgreSQL (solo para desarrollo)
ufw --force enable

# Crear archivo de variables de entorno
print_message "Creando archivo de variables de entorno..."
cat > $PROJECT_DIR/.env << EOF
# Configuración de base de datos
DB_HOST=postgres
DB_PORT=5432
DB_NAME=news_scraper
DB_USER=postgres
DB_PASSWORD=123456

# Configuración de scraping
SCRAPING_DELAY=5
SCRAPING_WORKERS=3
SCRAPING_TIMEOUT=30
SCRAPING_RETRIES=3
SCRAPING_INCREMENTAL=true
SCRAPING_MAX_ARTICLES=1000

# Configuración de scheduler
SCHEDULER_INTERVAL=1
SCHEDULER_MAX_JOBS=1
SCHEDULER_TIMEOUT=120
SCHEDULER_RETRY=true
SCHEDULER_MAX_RETRIES=3
SCHEDULER_RETRY_DELAY=30

# Fuentes
SOURCE_SIN_FRONTERAS=true
SOURCE_LOS_ANDES=true
SOURCE_PACHAMAMA=true
SOURCE_PUNO_NOTICIAS=true

# Salida
OUTPUT_CSV=true
OUTPUT_JSON=true
OUTPUT_DIR=/app/output
OUTPUT_TIMESTAMP=true

# Logging
LOG_LEVEL=INFO
LOG_FILE=/app/logs/unified_scraper.log
LOG_MAX_SIZE_MB=10
LOG_BACKUP_COUNT=5

# Notificaciones
NOTIFICATIONS_ENABLED=false

# Mantenimiento
MAINTENANCE_CLEANUP_LOGS_DAYS=30
MAINTENANCE_CLEANUP_FILES_DAYS=7
MAINTENANCE_DB_BACKUP=false
MAINTENANCE_BACKUP_INTERVAL=24
EOF

# Crear script de inicio
print_message "Creando script de inicio..."
cat > $PROJECT_DIR/start.sh << 'EOF'
#!/bin/bash
cd /opt/news-scraper
docker-compose down
docker-compose up -d
echo "Sistema de scraping iniciado"
echo "Base de datos: http://localhost:5432"
echo "Archivos: http://localhost/output/"
docker-compose logs -f
EOF

chmod +x $PROJECT_DIR/start.sh

# Crear script de parada
print_message "Creando script de parada..."
cat > $PROJECT_DIR/stop.sh << 'EOF'
#!/bin/bash
cd /opt/news-scraper
docker-compose down
echo "Sistema de scraping detenido"
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
echo "Logs recientes:"
docker-compose logs --tail=20
echo ""
echo "Uso de disco:"
df -h
echo ""
echo "Uso de memoria:"
free -h
EOF

chmod +x $PROJECT_DIR/monitor.sh

# Crear servicio systemd para auto-inicio
print_message "Creando servicio systemd..."
cat > /etc/systemd/system/news-scraper.service << EOF
[Unit]
Description=News Scraper System
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
docker-compose build

print_message "Iniciando servicios..."
docker-compose up -d

# Esperar a que los servicios estén listos
print_message "Esperando a que los servicios estén listos..."
sleep 30

# Verificar estado
print_message "Verificando estado de los servicios..."
docker-compose ps

# Mostrar logs iniciales
print_message "Mostrando logs iniciales..."
docker-compose logs --tail=20

# Crear enlace simbólico para fácil acceso
ln -sf $PROJECT_DIR/start.sh /usr/local/bin/news-scraper-start
ln -sf $PROJECT_DIR/stop.sh /usr/local/bin/news-scraper-stop
ln -sf $PROJECT_DIR/monitor.sh /usr/local/bin/news-scraper-monitor

print_message "=== DESPLIEGUE COMPLETADO ==="
print_message "El sistema está ejecutándose en:"
print_message "  - Base de datos: localhost:5432"
print_message "  - Archivos de salida: http://localhost/output/"
print_message "  - Logs: $PROJECT_DIR/logs/"
print_message ""
print_message "Comandos útiles:"
print_message "  - Iniciar: news-scraper-start"
print_message "  - Detener: news-scraper-stop"
print_message "  - Monitorear: news-scraper-monitor"
print_message "  - Ver logs: cd $PROJECT_DIR && docker-compose logs -f"
print_message ""
print_message "El sistema se ejecutará automáticamente cada hora para extraer noticias."
print_message "Los archivos CSV y JSON se generarán en el directorio output/"

# Mostrar información de la instancia
print_message "=== INFORMACIÓN DE LA INSTANCIA ==="
echo "IP pública: $(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
echo "IP privada: $(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)"
echo "Región: $(curl -s http://169.254.169.254/latest/meta-data/placement/region)"
echo "Tipo de instancia: $(curl -s http://169.254.169.254/latest/meta-data/instance-type)"
