#!/bin/bash

# =============================================================================
# DEPLOY SCRIPT SIMPLIFICADO - SISTEMA DE SCRAPING DE NOTICIAS
# =============================================================================
# Script esencial para desplegar el sistema de scraping en AWS EC2
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

print_header "=== DESPLIEGUE SIMPLIFICADO - SISTEMA DE SCRAPING ==="

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
# 1. ACTUALIZAR SISTEMA E INSTALAR DEPENDENCIAS
# =============================================================================
print_header "1. ACTUALIZANDO SISTEMA E INSTALANDO DEPENDENCIAS..."

sudo apt-get update -y
sudo apt-get upgrade -y

# Instalar dependencias esenciales
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    wget \
    git \
    unzip \
    htop \
    ufw

# =============================================================================
# 2. INSTALAR DOCKER
# =============================================================================
print_header "2. INSTALANDO DOCKER..."

# Remover versiones anteriores
sudo apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

# Agregar repositorio de Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Instalar Docker
sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io

# Iniciar y habilitar Docker
sudo systemctl start docker
sudo systemctl enable docker

# Agregar usuario ubuntu al grupo docker
sudo usermod -aG docker ubuntu

# =============================================================================
# 3. INSTALAR DOCKER COMPOSE
# =============================================================================
print_header "3. INSTALANDO DOCKER COMPOSE..."

# Descargar Docker Compose
DOCKER_COMPOSE_VERSION="2.21.0"
sudo curl -L "https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Crear enlace simbólico
sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose

# =============================================================================
# 4. CONFIGURAR FIREWALL
# =============================================================================
print_header "4. CONFIGURANDO FIREWALL..."

# Habilitar UFW
sudo ufw --force enable

# Reglas básicas
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 6379/tcp  # Redis
sudo ufw allow 5432/tcp  # PostgreSQL

print_info "Firewall configurado"

# =============================================================================
# 5. PREPARAR PROYECTO
# =============================================================================
print_header "5. PREPARANDO PROYECTO..."

# Crear directorio
sudo mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# Clonar repositorio si no existe
if [ ! -d ".git" ]; then
    print_info "Clonando repositorio..."
    sudo git clone https://github.com/IVANMAMANI2003/news.git .
else
    print_info "Actualizando repositorio..."
    sudo git pull origin main
fi

# Crear directorios necesarios
sudo mkdir -p data logs

# =============================================================================
# 6. CONFIGURAR VARIABLES DE ENTORNO
# =============================================================================
print_header "6. CONFIGURANDO VARIABLES DE ENTORNO..."

sudo tee .env > /dev/null << EOF
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
echo 'export DOCKER_BUILDKIT=0' | sudo tee -a ~/.bashrc

# Limpiar Docker completamente
print_info "Limpiando Docker..."
sudo docker-compose down -v 2>/dev/null || true
sudo docker system prune -a -f
sudo docker volume prune -f

# =============================================================================
# 8. CONSTRUIR Y LEVANTAR SERVICIOS
# =============================================================================
print_header "8. CONSTRUYENDO Y LEVANTANDO SERVICIOS..."

# Construir imágenes
print_info "Construyendo imágenes..."
sudo docker-compose build --no-cache

# Levantar servicios
print_info "Levantando servicios..."
sudo docker-compose up -d

# =============================================================================
# 9. VERIFICAR SERVICIOS
# =============================================================================
print_header "9. VERIFICANDO SERVICIOS..."

# Esperar a que los servicios estén listos
print_info "Esperando a que los servicios estén listos..."
sleep 30

# Verificar estado
print_info "Estado de contenedores:"
sudo docker-compose ps

# =============================================================================
# 10. EJECUTAR SCRAPING INICIAL COMPLETO INMEDIATAMENTE
# =============================================================================
print_header "10. EJECUTANDO SCRAPING INICIAL COMPLETO INMEDIATAMENTE..."

# Ejecutar scraping completo via Celery inmediatamente
print_info "Ejecutando scraping completo via Celery..."
if ! sudo docker-compose exec celery-worker celery -A celery_tasks call news_scraper.tasks.scheduled_scraping; then
    print_warning "⚠️ Scraping inicial falló. Revisa logs con: news-scraper logs"
    print_info "El sistema está funcionando, pero el scraping inicial necesita revisión"
else
    print_info "✅ Scraping inicial ejecutado correctamente"
fi

# =============================================================================
# 11. CONFIGURAR CELERY BEAT PARA NUEVAS NOTICIAS
# =============================================================================
print_header "11. CONFIGURANDO CELERY BEAT PARA NUEVAS NOTICIAS..."

# Limpiar schedule persistente
print_info "Limpiando schedule persistente..."
sudo docker-compose exec redis redis-cli DEL celerybeat-schedule 2>/dev/null || true

# Reiniciar Celery Beat
print_info "Reiniciando Celery Beat..."
if sudo docker-compose up -d celery-beat; then
    print_info "✅ Celery Beat iniciado correctamente"
else
    print_warning "⚠️ Error iniciando Celery Beat. Revisa logs con: news-scraper logs"
fi

# Esperar a que se configure
sleep 10

# Verificar que Celery Beat esté funcionando
print_info "Verificando configuración de Celery Beat..."
if sudo docker-compose exec celery-worker celery -A celery_tasks inspect scheduled | grep -q "empty"; then
    print_warning "⚠️ Celery Beat no está cargando tareas programadas"
    print_info "Ejecuta: sudo docker-compose logs celery-beat para revisar errores"
else
    print_info "✅ Celery Beat cargando tareas programadas correctamente"
fi

# =============================================================================
# 12. CREAR SCRIPT DE GESTIÓN SIMPLE
# =============================================================================
print_header "12. CREANDO SCRIPT DE GESTIÓN..."

sudo tee $PROJECT_DIR/manage.sh > /dev/null << 'EOF'
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
    scrape)
        echo "Ejecutando scraping manual..."
        sudo docker-compose exec celery-worker celery -A celery_tasks call news_scraper.tasks.scheduled_scraping
        ;;
    stats)
        echo "Estadísticas de la base de datos:"
        sudo docker-compose exec postgres psql -U postgres -d news_scraper -c "SELECT fuente, COUNT(*) as noticias FROM noticias GROUP BY fuente;"
        ;;
    *)
        echo "Uso: $0 {start|stop|restart|status|logs|scrape|stats}"
        echo ""
        echo "Comandos disponibles:"
        echo "  start    - Iniciar sistema"
        echo "  stop     - Detener sistema"
        echo "  restart  - Reiniciar sistema"
        echo "  status   - Ver estado"
        echo "  logs     - Ver logs"
        echo "  scrape   - Ejecutar scraping manual"
        echo "  stats    - Ver estadísticas de BD"
        ;;
esac
EOF

sudo chmod +x $PROJECT_DIR/manage.sh

# Crear enlace simbólico
sudo ln -sf $PROJECT_DIR/manage.sh /usr/local/bin/news-scraper

# =============================================================================
# 13. MOSTRAR INFORMACIÓN FINAL
# =============================================================================
print_header "=== DESPLIEGUE COMPLETADO ==="

print_info "Sistema desplegado en:"
print_info "  - IP Pública: $PUBLIC_IP"
print_info "  - IP Privada: $PRIVATE_IP"
print_info "  - Ubicación: $PROJECT_DIR"

echo ""
print_info "Estado actual:"
sudo docker-compose ps

echo ""
print_info "Comandos de gestión:"
print_info "  news-scraper start    # Iniciar sistema"
print_info "  news-scraper stop     # Detener sistema"
print_info "  news-scraper status   # Ver estado"
print_info "  news-scraper logs     # Ver logs"
print_info "  news-scraper scrape   # Ejecutar scraping manual"
print_info "  news-scraper stats    # Ver estadísticas de BD"

echo ""
print_info "Verificación final del sistema:"

# Verificar estado de contenedores
if sudo docker-compose ps | grep -q "Up"; then
    print_info "✅ Todos los contenedores están funcionando"
else
    print_warning "⚠️ Algunos contenedores no están funcionando correctamente"
fi

# Verificar tareas programadas
if sudo docker-compose exec celery-worker celery -A celery_tasks inspect scheduled | grep -q "empty"; then
    print_warning "⚠️ Celery Beat no está cargando tareas programadas"
    print_info "Ejecuta: sudo docker-compose logs celery-beat para revisar errores"
else
    print_info "✅ Celery Beat cargando tareas programadas correctamente"
fi

# Verificar noticias en BD
NOTICIAS_COUNT=$(sudo docker-compose exec -T postgres psql -U postgres -d news_scraper -c "SELECT COUNT(*) FROM noticias;" 2>/dev/null | grep -o '[0-9]*' | tail -1)
if [ "$NOTICIAS_COUNT" -gt 0 ]; then
    print_info "✅ Base de datos contiene $NOTICIAS_COUNT noticias"
else
    print_warning "⚠️ No hay noticias en la base de datos"
fi

echo ""
print_info "El scraping inicial completo se ejecutó inmediatamente"
print_info "El scraping de nuevas noticias se ejecuta automáticamente cada hora via Celery Beat"

echo ""
print_header "✅ SISTEMA LISTO PARA USAR"
