#!/bin/bash

# SCRIPT ÚNICO DE DESPLIEGUE EN AWS
# Este es el ÚNICO script que necesitas para desplegar en AWS

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[HEADER]${NC} $1"
}

print_header "=== DESPLIEGUE EN AWS - SISTEMA DE SCRAPING ==="

# Verificar que se ejecute como root
if [ "$EUID" -ne 0 ]; then
    print_error "Ejecuta con: sudo ./deploy.sh"
    exit 1
fi

# Obtener información de la instancia
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "localhost")
PRIVATE_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4 2>/dev/null || echo "127.0.0.1")
REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region 2>/dev/null || echo "us-east-1")

print "IP Pública: $PUBLIC_IP"
print "IP Privada: $PRIVATE_IP"
print "Región: $REGION"

# Actualizar sistema
print "Actualizando sistema..."
apt-get update -y
apt-get upgrade -y

# Instalar dependencias
print "Instalando dependencias..."
apt-get install -y curl wget git htop nginx postgresql-client redis-tools

# Instalar Docker
print "Instalando Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    systemctl start docker
    systemctl enable docker
    usermod -aG docker ubuntu
fi

# Instalar Docker Compose
print "Instalando Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# Crear directorio del proyecto
PROJECT_DIR="/opt/news-scraper"
print "Creando directorio: $PROJECT_DIR"
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# Clonar repositorio
print "Clonando repositorio..."
if [ -d ".git" ]; then
    git pull origin main
else
    git clone https://github.com/IVANMAMANI2003/news.git .
fi

# Crear directorios
mkdir -p data logs
chmod 755 data logs

# Configurar firewall
print "Configurando firewall..."
ufw allow 22/tcp   # SSH
ufw allow 8081/tcp # HTTP
ufw allow 5555/tcp # Flower
ufw --force enable

# Configurar Nginx
print "Configurando Nginx..."
cat > /etc/nginx/sites-available/news-scraper << EOF
server {
    listen 8081;
    server_name _;
    
    location /data/ {
        alias $PROJECT_DIR/data/;
        autoindex on;
    }
    
    location /logs/ {
        alias $PROJECT_DIR/logs/;
        autoindex on;
    }
    
    location /monitor {
        alias $PROJECT_DIR/data/status_report.html;
        try_files \$uri =404;
    }
    
    location /flower/ {
        proxy_pass http://localhost:5555/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
    
    location /api/stats {
        return 200 '{"status": "ok", "ip": "$PUBLIC_IP"}';
        add_header Content-Type application/json;
    }
    
    location / {
        return 200 'Sistema de Scraping - OK\nIP: $PUBLIC_IP\nMonitoreo: http://$PUBLIC_IP:8081/monitor';
        add_header Content-Type text/plain;
    }
}
EOF

ln -sf /etc/nginx/sites-available/news-scraper /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx

# Crear archivo .env
print "Creando archivo de configuración..."
cat > $PROJECT_DIR/.env << EOF
# Base de datos
DB_HOST=postgres
DB_PORT=5432
DB_NAME=news_scraper
DB_USER=postgres
DB_PASSWORD=123456

# Redis
REDIS_URL=redis://redis:6379/0

# Scraping
SCRAPING_DELAY=1
SCRAPING_WORKERS=10
SCRAPING_TIMEOUT=30
SCRAPING_RETRIES=3
SCRAPING_INCREMENTAL=true
SCRAPING_MAX_ARTICLES=2000

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

# AWS
AWS_REGION=$REGION
EOF

# Construir y ejecutar contenedores
print "Construyendo contenedores..."
sudo docker-compose build --no-cache

print "Iniciando servicios..."
sudo docker-compose up -d

# Esperar a que estén listos
print "Esperando a que los servicios estén listos..."
sleep 60

# Verificar servicios
print "Verificando servicios..."
sudo docker-compose ps

# Crear script de gestión
print "Creando script de gestión..."
cat > $PROJECT_DIR/manage.sh << 'EOF'
#!/bin/bash
cd /opt/news-scraper

case "$1" in
    start)
        echo "Iniciando sistema..."
        sudo docker-compose up -d
        ;;
    stop)
        echo "Deteniendo sistema..."
        sudo docker-compose down
        ;;
    restart)
        echo "Reiniciando sistema..."
        sudo docker-compose restart
        ;;
    status)
        echo "Estado del sistema:"
        sudo docker-compose ps
        ;;
    logs)
        echo "Mostrando logs:"
        sudo docker-compose logs -f
        ;;
    scale)
        WORKERS=${2:-2}
        echo "Escalando workers a $WORKERS..."
        sudo docker-compose up -d --scale celery-worker=$WORKERS
        ;;
    monitor)
        echo "Monitoreo disponible en:"
        echo "http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8080/monitor"
        ;;
    *)
        echo "Uso: $0 {start|stop|restart|status|logs|scale|monitor}"
        echo "  start    - Iniciar sistema"
        echo "  stop     - Detener sistema"
        echo "  restart  - Reiniciar sistema"
        echo "  status   - Ver estado"
        echo "  logs     - Ver logs"
        echo "  scale N  - Escalar workers"
        echo "  monitor  - Ver URL de monitoreo"
        ;;
esac
EOF

chmod +x $PROJECT_DIR/manage.sh

# Crear enlaces simbólicos
ln -sf $PROJECT_DIR/manage.sh /usr/local/bin/news-scraper

# Mostrar información final
print_header "=== DESPLIEGUE COMPLETADO ==="
print "Sistema desplegado en:"
print "  - IP Pública: $PUBLIC_IP"
print "  - IP Privada: $PRIVATE_IP"
print ""
print "Servicios disponibles:"
print "  - Web: http://$PUBLIC_IP:8081"
print "  - Monitoreo: http://$PUBLIC_IP:8081/monitor"
print "  - Flower: http://$PUBLIC_IP:5555"
print "  - Archivos: http://$PUBLIC_IP:8081/data/"
print "  - Logs: http://$PUBLIC_IP:8081/logs/"
print ""
print "Comandos de gestión:"
print "  news-scraper start     # Iniciar"
print "  news-scraper stop      # Detener"
print "  news-scraper restart   # Reiniciar"
print "  news-scraper status    # Ver estado"
print "  news-scraper logs      # Ver logs"
print "  news-scraper scale 4   # Escalar workers"
print "  news-scraper monitor   # Ver URL de monitoreo"
print ""
print_header "✅ SISTEMA LISTO PARA USAR"
