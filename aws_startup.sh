#!/bin/bash

# Script completo de despliegue en AWS EC2 para el sistema de scraping de noticias
# Incluye Docker, PostgreSQL, Redis, Celery y monitoreo

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

# Verificar si estamos en Ubuntu/Debian
if ! command -v apt-get &> /dev/null; then
    print_error "Este script está diseñado para Ubuntu/Debian. Por favor adapte para su distribución."
    exit 1
fi

print_header "🚀 DESPLIEGUE COMPLETO EN AWS EC2"
print_status "Iniciando despliegue del sistema de scraping de noticias..."

# 1. Actualizar sistema
print_header "📦 ACTUALIZANDO SISTEMA"
print_status "Actualizando paquetes del sistema..."
sudo apt-get update -y
sudo apt-get upgrade -y

# 2. Instalar dependencias básicas
print_header "🔧 INSTALANDO DEPENDENCIAS"
print_status "Instalando dependencias del sistema..."
sudo apt-get install -y \
    curl \
    wget \
    git \
    unzip \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release

# 3. Instalar Docker
print_header "🐳 INSTALANDO DOCKER"
print_status "Instalando Docker..."
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Agregar usuario actual al grupo docker
sudo usermod -aG docker $USER

# Iniciar y habilitar Docker
sudo systemctl start docker
sudo systemctl enable docker

# 4. Instalar Docker Compose
print_header "🔗 INSTALANDO DOCKER COMPOSE"
print_status "Instalando Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose

# 5. Configurar firewall
print_header "🔥 CONFIGURANDO FIREWALL"
print_status "Configurando reglas de firewall..."
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 5432/tcp  # PostgreSQL
sudo ufw allow 6379/tcp  # Redis
sudo ufw allow 5555/tcp  # Flower
sudo ufw --force enable

# 6. Crear directorio del proyecto
print_header "📁 PREPARANDO DIRECTORIO"
PROJECT_DIR="/opt/news_scraping"
sudo mkdir -p $PROJECT_DIR
sudo chown $USER:$USER $PROJECT_DIR
cd $PROJECT_DIR

# 7. Clonar repositorio
print_status "Clonando repositorio desde GitHub..."
git clone https://github.com/IVANMAMANI2003/news.git .
cd news

# 8. Crear archivo de configuración para AWS
print_header "⚙️ CONFIGURANDO VARIABLES"
print_status "Creando archivo de configuración para AWS..."
cat > .env << EOF
# Configuración de la base de datos PostgreSQL
DB_HOST=postgres
DB_PORT=5432
DB_NAME=news_scraping
DB_USER=postgres
DB_PASSWORD=123456

# Configuración de Redis/Celery
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
CELERY_TIMEZONE=America/Lima
CELERY_CONCURRENCY=2

# Configuración de scraping
DELAY_BETWEEN_REQUESTS=2
MAX_WORKERS=3
EXECUTION_INTERVAL_HOURS=1
OUTPUT_DIR=data
LOG_LEVEL=INFO

# Configuración de AWS
AWS_REGION=us-east-1
AWS_INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id 2>/dev/null || echo "local")
EOF

# 9. Crear directorios necesarios
print_status "Creando directorios necesarios..."
mkdir -p data logs

# 10. Construir y levantar servicios
print_header "🚀 DESPLEGANDO SERVICIOS"
print_status "Construyendo imágenes Docker..."
sudo docker-compose build

print_status "Iniciando todos los servicios..."
sudo docker-compose up -d

# 11. Esperar a que los servicios estén listos
print_status "Esperando a que los servicios estén listos..."
sleep 30

# 12. Verificar servicios
print_header "✅ VERIFICANDO SERVICIOS"
print_status "Verificando estado de los contenedores..."
sudo docker ps

# Verificar PostgreSQL
print_status "Verificando PostgreSQL..."
if sudo docker exec news_postgres pg_isready -U postgres; then
    print_status "✅ PostgreSQL está funcionando"
else
    print_error "❌ PostgreSQL no está funcionando"
fi

# Verificar Redis
print_status "Verificando Redis..."
if sudo docker exec news_redis redis-cli ping | grep -q PONG; then
    print_status "✅ Redis está funcionando"
else
    print_error "❌ Redis no está funcionando"
fi

# Verificar Celery Worker
print_status "Verificando Celery Worker..."
if sudo docker ps | grep -q news_celery_worker; then
    print_status "✅ Celery Worker está funcionando"
else
    print_error "❌ Celery Worker no está funcionando"
fi

# Verificar Celery Beat
print_status "Verificando Celery Beat..."
if sudo docker ps | grep -q news_celery_beat; then
    print_status "✅ Celery Beat está funcionando"
else
    print_error "❌ Celery Beat no está funcionando"
fi

# 13. Crear scripts de monitoreo
print_header "📊 CREANDO SCRIPTS DE MONITOREO"
cat > monitor.sh << 'EOF'
#!/bin/bash
echo "=== ESTADO DEL SISTEMA DE SCRAPING ==="
echo "Fecha: $(date)"
echo

echo "=== CONTENEDORES ==="
sudo docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo
echo "=== ESTADÍSTICAS DE LA BASE DE DATOS ==="
sudo docker exec news_postgres psql -U postgres -d news_scraping -c "
SELECT 
    fuente,
    COUNT(*) as total_noticias,
    MAX(fecha_extraccion) as ultima_extraccion
FROM noticias 
GROUP BY fuente 
ORDER BY total_noticias DESC;
"

echo
echo "=== ARCHIVOS GENERADOS ==="
ls -la data/ | head -10

echo
echo "=== LOGS RECIENTES CELERY WORKER ==="
sudo docker logs --tail=10 news_celery_worker

echo
echo "=== LOGS RECIENTES CELERY BEAT ==="
sudo docker logs --tail=10 news_celery_beat
EOF

chmod +x monitor.sh

# Crear script de respaldo
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/backups/news_scraping"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Respaldar base de datos
sudo docker exec news_postgres pg_dump -U postgres -d news_scraping > $BACKUP_DIR/database_$DATE.sql

# Respaldar archivos de datos
tar -czf $BACKUP_DIR/data_$DATE.tar.gz data/

# Respaldar logs
tar -czf $BACKUP_DIR/logs_$DATE.tar.gz logs/

# Limpiar respaldos antiguos (mantener solo últimos 7 días)
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Respaldo completado: $BACKUP_DIR"
EOF

chmod +x backup.sh

# 14. Configurar cron para respaldos
print_status "Configurando respaldos automáticos..."
(crontab -l 2>/dev/null; echo "0 2 * * * $PROJECT_DIR/backup.sh") | crontab -

# 15. Ejecutar primera tarea de scraping
print_header "🔄 EJECUTANDO PRIMERA TAREA"
print_status "Ejecutando scraping inicial..."
sudo docker exec news_celery_worker python -c "
from tasks import scrape_all_sources
result = scrape_all_sources.delay()
print('Tarea enviada:', result.id)
"

# 16. Mostrar información final
print_header "🎉 DESPLIEGUE COMPLETADO"
print_status "Sistema de scraping desplegado exitosamente!"

echo
echo "=== INFORMACIÓN IMPORTANTE ==="
echo "🌐 Panel de monitoreo Flower: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):5555"
echo "🗄️ Base de datos: localhost:5432 (usuario: postgres, contraseña: 123456)"
echo "📁 Archivos de datos: $PROJECT_DIR/data/"
echo "📋 Logs: $PROJECT_DIR/logs/"
echo "🔧 Monitoreo: $PROJECT_DIR/monitor.sh"
echo "💾 Respaldo: $PROJECT_DIR/backup.sh"
echo

echo "=== COMANDOS ÚTILES ==="
echo "Ver estado: sudo docker ps"
echo "Ver logs worker: sudo docker logs -f news_celery_worker"
echo "Ver logs beat: sudo docker logs -f news_celery_beat"
echo "Monitorear sistema: $PROJECT_DIR/monitor.sh"
echo "Reiniciar servicios: sudo docker-compose restart"
echo "Detener servicios: sudo docker-compose down"
echo "Iniciar servicios: sudo docker-compose up -d"
echo

echo "=== VERIFICACIÓN RÁPIDA ==="
echo "Ejecutando verificación..."
$PROJECT_DIR/monitor.sh

print_status "¡Despliegue completado! El sistema está ejecutándose automáticamente cada hora."
