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
ufw --force enable

# No configurar Nginx - solo usar Docker

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

# Limpiar contenedores existentes
print "Limpiando contenedores existentes..."
sudo docker-compose down -v 2>/dev/null || true
sudo docker system prune -a -f 2>/dev/null || true
sudo docker volume prune -f 2>/dev/null || true

# Deshabilitar BuildKit (usar Docker clásico)
print "Configurando Docker clásico (sin BuildKit)..."
export DOCKER_BUILDKIT=0
echo 'export DOCKER_BUILDKIT=0' >> ~/.bashrc

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

# Verificar que todos los servicios estén corriendo
print "Verificando que todos los servicios estén corriendo..."
for i in {1..10}; do
    if sudo docker-compose ps | grep -q "Up"; then
        print "Servicios funcionando correctamente"
        break
    else
        print "Esperando servicios... intento $i/10"
        sleep 10
    fi
done

# Verificar estado final
print "Estado final de contenedores:"
sudo docker-compose ps

# Configurar Celery Beat para tareas programadas
print "Configurando tareas programadas de Celery Beat..."
sudo docker-compose stop celery-beat 2>/dev/null || true
sudo docker-compose exec redis redis-cli DEL celerybeat-schedule 2>/dev/null || true
sudo docker-compose up -d celery-beat

# Esperar a que Celery Beat se inicie
print "Esperando a que Celery Beat se configure..."
sleep 10

# Verificar tareas programadas
print "Verificando tareas programadas..."
sudo docker-compose exec celery-worker celery -A celery_tasks inspect scheduled

# Ejecutar scraping manual inmediato para probar
print "Ejecutando scraping manual de prueba..."
sudo docker-compose exec celery-worker celery -A celery_tasks call news_scraper.tasks.scheduled_scraping &

# Ejecutar scraping completo automáticamente
print "Ejecutando scraping completo de las 4 páginas..."
if sudo docker-compose exec -T celery-worker python -c "
import sys
sys.path.append('/app')
from unified_scraper import UnifiedNewsScraper
scraper = UnifiedNewsScraper()
scraper.run_complete_scraping()
print('Scraping completo finalizado')
" 2>/dev/null; then
    print "✅ Scraping ejecutado correctamente"
else
    print "⚠️  Error en scraping automático, pero el sistema está listo"
    print "Puedes ejecutar manualmente: sudo docker-compose exec celery-worker python unified_scraper.py"
fi

# Esperar un poco para que se procese
print "Esperando procesamiento inicial..."
sleep 60

# Verificar que se hayan procesado noticias
print "Verificando noticias en base de datos..."
sudo docker-compose exec -T postgres psql -U postgres -d news_scraper -c "SELECT COUNT(*) as total_noticias FROM noticias;"

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
    scrape)
        echo "Ejecutando scraping completo de las 4 páginas..."
        sudo docker-compose exec celery-worker python -c "
import sys
sys.path.append('/app')
from unified_scraper import UnifiedNewsScraper
scraper = UnifiedNewsScraper()
scraper.run_complete_scraping()
print('Scraping completo finalizado')
"
        ;;
    stats)
        echo "Estadísticas de la base de datos:"
        sudo docker-compose exec postgres psql -U postgres -d news_scraper -c "SELECT fuente, COUNT(*) as noticias FROM noticias GROUP BY fuente;"
        ;;
    *)
        echo "Uso: $0 {start|stop|restart|status|logs|scale|monitor|scrape|stats}"
        echo "  start    - Iniciar sistema"
        echo "  stop     - Detener sistema"
        echo "  restart  - Reiniciar sistema"
        echo "  status   - Ver estado"
        echo "  logs     - Ver logs"
        echo "  scale N  - Escalar workers"
        echo "  monitor  - Ver URL de monitoreo"
        echo "  scrape   - Ejecutar scraping manual"
        echo "  stats    - Ver estadísticas"
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
print "  - Ubicación: $PROJECT_DIR"
print ""
print "Estado actual:"
sudo docker-compose ps
print ""
print "Comandos de gestión:"
print "  news-scraper start     # Iniciar"
print "  news-scraper stop      # Detener"
print "  news-scraper restart   # Reiniciar"
print "  news-scraper status    # Ver estado"
print "  news-scraper logs      # Ver logs"
print "  news-scraper scrape    # Ejecutar scraping manual"
print "  news-scraper stats     # Ver estadísticas de BD"
print "  news-scraper scale 4   # Escalar workers"
print ""
print "Comandos de Celery:"
print "  sudo docker-compose exec celery-worker celery -A celery_tasks inspect scheduled"
print "  sudo docker-compose exec celery-worker celery -A celery_tasks call news_scraper.tasks.scheduled_scraping"
print "  sudo docker-compose logs -f celery-beat"
print ""
print "Diagnóstico rápido:"
print "  sudo docker-compose ps"
print "  sudo docker-compose logs celery-worker"
print "  sudo docker-compose exec postgres psql -U postgres -d news_scraper -c 'SELECT COUNT(*) FROM noticias;'"
print ""
print_header "✅ SISTEMA LISTO PARA USAR"
