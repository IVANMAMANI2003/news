#!/bin/bash

# =============================================================================
# DEPLOY SCRIPT - SISTEMA DE SCRAPING DE NOTICIAS
# =============================================================================
# Script para desplegar el sistema de scraping en AWS EC2
# Incluye: Docker, PostgreSQL, Redis, Celery, Scraping automático
# =============================================================================

set -e  # Salir si hay errores

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funciones de utilidad
print_header() {
    echo -e "${BLUE}[HEADER] $1${NC}"
}

print_info() {
    echo -e "${GREEN}[INFO] $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

print_error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

# Verificar que se ejecute con sudo
if [ "$EUID" -ne 0 ]; then
    print_error "Ejecuta con: sudo ./deploy.sh"
    exit 1
fi

print_header "=== DESPLIEGUE EN AWS - SISTEMA DE SCRAPING ==="

# Obtener información del sistema
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "localhost")
PRIVATE_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4 2>/dev/null || echo "127.0.0.1")
REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region 2>/dev/null || echo "us-east-1")

print_info "IP Pública: $PUBLIC_IP"
print_info "IP Privada: $PRIVATE_IP"
print_info "Región: $REGION"

# Directorio del proyecto
PROJECT_DIR="/opt/news-scraper"

# =============================================================================
# 1. ACTUALIZAR SISTEMA
# =============================================================================
print_header "1. ACTUALIZANDO SISTEMA..."

apt-get update -y
apt-get upgrade -y

# Instalar dependencias del sistema
apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    wget \
    git \
    unzip \
    htop \
    tree

# =============================================================================
# 2. INSTALAR DOCKER
# =============================================================================
print_header "2. INSTALANDO DOCKER..."

# Remover versiones anteriores
apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

# Agregar repositorio de Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Instalar Docker
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io

# Iniciar y habilitar Docker
systemctl start docker
systemctl enable docker

# Agregar usuario ubuntu al grupo docker
usermod -aG docker ubuntu

# =============================================================================
# 3. INSTALAR DOCKER COMPOSE
# =============================================================================
print_header "3. INSTALANDO DOCKER COMPOSE..."

# Descargar Docker Compose
DOCKER_COMPOSE_VERSION="2.21.0"
curl -L "https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Crear enlace simbólico
ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose

# =============================================================================
# 4. CONFIGURAR FIREWALL
# =============================================================================
print_header "4. CONFIGURANDO FIREWALL..."

# Habilitar UFW
ufw --force enable

# Reglas básicas
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 6379/tcp  # Redis
ufw allow 5432/tcp  # PostgreSQL

print_info "Firewall configurado"

# =============================================================================
# 5. PREPARAR PROYECTO
# =============================================================================
print_header "5. PREPARANDO PROYECTO..."

# Crear directorio
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# Clonar repositorio si no existe
if [ ! -d ".git" ]; then
    print_info "Clonando repositorio..."
    git clone https://github.com/IVANMAMANI2003/news.git .
else
    print_info "Actualizando repositorio..."
    git pull origin main
fi

# Crear directorios necesarios
mkdir -p data logs

# =============================================================================
# 6. CONFIGURAR VARIABLES DE ENTORNO
# =============================================================================
print_header "6. CONFIGURANDO VARIABLES DE ENTORNO..."

cat > .env << EOF
# Base de datos
DB_HOST=postgres
DB_PORT=5432
DB_NAME=news_scraper
DB_USER=postgres
DB_PASSWORD=123456

# Redis
REDIS_URL=redis://redis:6379/0

# AWS
AWS_REGION=$REGION
EOF

print_info "Variables de entorno configuradas"

# =============================================================================
# 7. CONFIGURAR DOCKER
# =============================================================================
print_header "7. CONFIGURANDO DOCKER..."

# Deshabilitar BuildKit (usar Docker clásico)
export DOCKER_BUILDKIT=0
echo 'export DOCKER_BUILDKIT=0' >> ~/.bashrc

# Limpiar Docker completamente
print_info "Limpiando Docker..."
docker-compose down -v 2>/dev/null || true
docker system prune -a -f
docker volume prune -f

# =============================================================================
# 8. CONSTRUIR Y LEVANTAR SERVICIOS
# =============================================================================
print_header "8. CONSTRUYENDO Y LEVANTANDO SERVICIOS..."

# Construir imágenes
print_info "Construyendo imágenes..."
docker-compose build --no-cache

# Levantar servicios
print_info "Levantando servicios..."
docker-compose up -d

# =============================================================================
# 9. VERIFICAR SERVICIOS
# =============================================================================
print_header "9. VERIFICANDO SERVICIOS..."

# Esperar a que los servicios estén listos
print_info "Esperando a que los servicios estén listos..."
sleep 30

# Verificar estado
print_info "Estado de contenedores:"
docker-compose ps

# Verificar que todos estén corriendo
print_info "Verificando que todos los servicios estén corriendo..."
for i in {1..10}; do
    if docker-compose ps | grep -q "Up"; then
        print_info "✅ Servicios funcionando correctamente"
        break
    else
        print_warning "Esperando servicios... intento $i/10"
        sleep 10
    fi
done

# =============================================================================
# 10. CONFIGURAR CELERY BEAT
# =============================================================================
print_header "10. CONFIGURANDO CELERY BEAT..."

# Limpiar schedule persistente
print_info "Limpiando schedule persistente..."
docker-compose exec redis redis-cli DEL celerybeat-schedule 2>/dev/null || true

# Reiniciar Celery Beat si no está corriendo
if ! docker-compose ps | grep -q "celery-beat.*Up"; then
    print_info "Reiniciando Celery Beat..."
    docker-compose up -d celery-beat
fi

# Esperar a que se configure
sleep 10

# Verificar tareas programadas
print_info "Verificando tareas programadas..."
docker-compose exec celery-worker celery -A celery_tasks inspect scheduled

# =============================================================================
# 11. EJECUTAR SCRAPING INICIAL
# =============================================================================
print_header "11. EJECUTANDO SCRAPING INICIAL..."

# Ejecutar scraping via Celery
print_info "Ejecutando scraping via Celery..."
docker-compose exec celery-worker celery -A celery_tasks call news_scraper.tasks.scheduled_scraping &

# Ejecutar scraping directo
print_info "Ejecutando scraping directo..."
if docker-compose exec -T celery-worker python -c "
import sys
sys.path.append('/app')
from unified_scraper import UnifiedNewsScraper
scraper = UnifiedNewsScraper()
scraper.run_complete_scraping()
print('Scraping completo finalizado')
" 2>/dev/null; then
    print_info "✅ Scraping ejecutado correctamente"
else
    print_warning "⚠️  Error en scraping automático, pero el sistema está listo"
fi

# =============================================================================
# 12. VERIFICAR RESULTADOS
# =============================================================================
print_header "12. VERIFICANDO RESULTADOS..."

# Esperar procesamiento
print_info "Esperando procesamiento inicial..."
sleep 30

# Verificar contenedores
print_info "Estado final de contenedores:"
docker-compose ps

# Verificar base de datos
print_info "Verificando noticias en base de datos..."
docker-compose exec -T postgres psql -U postgres -d news_scraper -c "SELECT COUNT(*) as total_noticias FROM noticias;"

# =============================================================================
# 13. CREAR SCRIPT DE GESTIÓN
# =============================================================================
print_header "13. CREANDO SCRIPT DE GESTIÓN..."

cat > $PROJECT_DIR/manage.sh << 'EOF'
#!/bin/bash
cd /opt/news-scraper

case "$1" in
    start)
        echo "Iniciando sistema..."
        docker-compose up -d
        ;;
    stop)
        echo "Deteniendo sistema..."
        docker-compose down
        ;;
    restart)
        echo "Reiniciando sistema..."
        docker-compose restart
        ;;
    status)
        echo "Estado del sistema:"
        docker-compose ps
        ;;
    logs)
        echo "Mostrando logs:"
        docker-compose logs -f
        ;;
    worker-logs)
        echo "Mostrando logs del worker:"
        docker-compose logs -f celery-worker
        ;;
    beat-logs)
        echo "Mostrando logs de Celery Beat:"
        docker-compose logs -f celery-beat
        ;;
    scrape)
        echo "Ejecutando scraping manual..."
        docker-compose exec celery-worker python unified_scraper.py
        ;;
    celery-scrape)
        echo "Ejecutando scraping via Celery..."
        docker-compose exec celery-worker celery -A celery_tasks call news_scraper.tasks.scheduled_scraping
        ;;
    stats)
        echo "Estadísticas de la base de datos:"
        docker-compose exec postgres psql -U postgres -d news_scraper -c "SELECT fuente, COUNT(*) as noticias FROM noticias GROUP BY fuente;"
        ;;
    scheduled)
        echo "Tareas programadas:"
        docker-compose exec celery-worker celery -A celery_tasks inspect scheduled
        ;;
    active)
        echo "Tareas activas:"
        docker-compose exec celery-worker celery -A celery_tasks inspect active
        ;;
    scale)
        WORKERS=${2:-2}
        echo "Escalando workers a $WORKERS..."
        docker-compose up -d --scale celery-worker=$WORKERS
        ;;
    clean)
        echo "Limpiando Docker..."
        docker-compose down -v
        docker system prune -f
        ;;
    *)
        echo "Uso: $0 {start|stop|restart|status|logs|worker-logs|beat-logs|scrape|celery-scrape|stats|scheduled|active|scale|clean}"
        echo ""
        echo "Comandos disponibles:"
        echo "  start         - Iniciar sistema"
        echo "  stop          - Detener sistema"
        echo "  restart       - Reiniciar sistema"
        echo "  status        - Ver estado"
        echo "  logs          - Ver todos los logs"
        echo "  worker-logs   - Ver logs del worker"
        echo "  beat-logs     - Ver logs de Celery Beat"
        echo "  scrape        - Ejecutar scraping manual"
        echo "  celery-scrape - Ejecutar scraping via Celery"
        echo "  stats         - Ver estadísticas de BD"
        echo "  scheduled     - Ver tareas programadas"
        echo "  active        - Ver tareas activas"
        echo "  scale N       - Escalar workers"
        echo "  clean         - Limpiar Docker"
        ;;
esac
EOF

chmod +x $PROJECT_DIR/manage.sh

# Crear enlaces simbólicos
ln -sf $PROJECT_DIR/manage.sh /usr/local/bin/news-scraper

# =============================================================================
# 14. CREAR SCRIPT DE ACTUALIZACIÓN
# =============================================================================
print_header "14. CREANDO SCRIPT DE ACTUALIZACIÓN..."

cat > $PROJECT_DIR/update.sh << 'EOF'
#!/bin/bash
cd /opt/news-scraper

echo "Actualizando sistema de scraping..."
git pull origin main

echo "Reconstruyendo contenedores..."
docker-compose down
docker-compose build --no-cache
docker-compose up -d

echo "Verificando servicios..."
docker-compose ps

echo "✅ Sistema actualizado"
EOF

chmod +x $PROJECT_DIR/update.sh
ln -sf $PROJECT_DIR/update.sh /usr/local/bin/news-update

# =============================================================================
# 15. MOSTRAR INFORMACIÓN FINAL
# =============================================================================
print_header "=== DESPLIEGUE COMPLETADO ==="

print_info "Sistema desplegado en:"
print_info "  - IP Pública: $PUBLIC_IP"
print_info "  - IP Privada: $PRIVATE_IP"
print_info "  - Ubicación: $PROJECT_DIR"

echo ""
print_info "Estado actual:"
docker-compose ps

echo ""
print_info "Comandos de gestión:"
print_info "  news-scraper start         # Iniciar sistema"
print_info "  news-scraper stop          # Detener sistema"
print_info "  news-scraper status        # Ver estado"
print_info "  news-scraper logs          # Ver logs"
print_info "  news-scraper worker-logs   # Ver logs del worker"
print_info "  news-scraper beat-logs     # Ver logs de Celery Beat"
print_info "  news-scraper scrape        # Ejecutar scraping manual"
print_info "  news-scraper celery-scrape # Ejecutar scraping via Celery"
print_info "  news-scraper stats         # Ver estadísticas de BD"
print_info "  news-scraper scheduled     # Ver tareas programadas"
print_info "  news-scraper active        # Ver tareas activas"
print_info "  news-scraper scale 4       # Escalar workers"
print_info "  news-scraper clean         # Limpiar Docker"
print_info "  news-update                # Actualizar desde GitHub"

echo ""
print_info "Diagnóstico rápido:"
print_info "  docker-compose ps"
print_info "  docker-compose logs celery-worker"
print_info "  docker-compose exec postgres psql -U postgres -d news_scraper -c 'SELECT COUNT(*) FROM noticias;'"

echo ""
print_header "✅ SISTEMA LISTO PARA USAR"
print_info "El scraping se ejecuta automáticamente cada hora via Celery Beat"
print_info "Puedes ejecutar scraping manual en cualquier momento con: news-scraper scrape"
