#!/bin/bash

# Script de inicio robusto para AWS
set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

print_header "=== INICIANDO SISTEMA DE SCRAPING EN AWS ==="

# Verificar que estamos en el directorio correcto
if [ ! -f "docker-compose.yml" ]; then
    print_error "docker-compose.yml no encontrado. Ejecuta desde el directorio del proyecto."
    exit 1
fi

# Crear directorios necesarios
print_message "Creando directorios necesarios..."
mkdir -p data logs
chmod 755 data logs

# Verificar Docker
print_message "Verificando Docker..."
if ! command -v docker &> /dev/null; then
    print_error "Docker no está instalado"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose no está instalado"
    exit 1
fi

# Verificar permisos
print_message "Verificando permisos..."
if [ ! -w "." ]; then
    print_error "Sin permisos de escritura en el directorio actual"
    exit 1
fi

# Detener contenedores existentes
print_message "Deteniendo contenedores existentes..."
sudo docker-compose down 2>/dev/null || true

# Limpiar contenedores huérfanos
print_message "Limpiando contenedores huérfanos..."
sudo docker-compose down --remove-orphans 2>/dev/null || true

# Construir imágenes
print_message "Construyendo imágenes Docker..."
if ! sudo docker-compose build --no-cache; then
    print_error "Error construyendo imágenes Docker"
    exit 1
fi

# Iniciar servicios base primero
print_message "Iniciando servicios base (Redis y PostgreSQL)..."
sudo docker-compose up -d redis postgres

# Esperar a que los servicios base estén listos
print_message "Esperando a que los servicios base estén listos..."
sleep 30

# Verificar Redis
print_message "Verificando Redis..."
if ! sudo docker-compose exec -T redis redis-cli ping | grep -q "PONG"; then
    print_error "Redis no está respondiendo"
    exit 1
fi
print_message "✅ Redis OK"

# Verificar PostgreSQL
print_message "Verificando PostgreSQL..."
if ! sudo docker-compose exec -T postgres pg_isready -U postgres; then
    print_error "PostgreSQL no está respondiendo"
    exit 1
fi
print_message "✅ PostgreSQL OK"

# Iniciar servicios de aplicación
print_message "Iniciando servicios de aplicación..."
sudo docker-compose up -d celery-beat celery-flower monitoring nginx

# Esperar un poco más
sleep 10

# Iniciar workers de Celery
print_message "Iniciando workers de Celery..."
sudo docker-compose up -d celery-worker

# Esperar a que todo esté listo
print_message "Esperando a que todos los servicios estén listos..."
sleep 20

# Verificar estado de todos los servicios
print_message "Verificando estado de los servicios..."
sudo docker-compose ps

# Verificar que los servicios estén ejecutándose
print_message "Verificando servicios críticos..."

# Verificar Redis
if sudo docker-compose exec -T redis redis-cli ping | grep -q "PONG"; then
    print_message "✅ Redis: OK"
else
    print_error "❌ Redis: Error"
fi

# Verificar PostgreSQL
if sudo docker-compose exec -T postgres pg_isready -U postgres >/dev/null 2>&1; then
    print_message "✅ PostgreSQL: OK"
else
    print_error "❌ PostgreSQL: Error"
fi

# Verificar Nginx
if curl -s http://localhost:8080 >/dev/null 2>&1; then
    print_message "✅ Nginx: OK"
else
    print_warning "⚠️ Nginx: No responde en localhost:8080"
fi

# Verificar Flower
if curl -s http://localhost:5555 >/dev/null 2>&1; then
    print_message "✅ Flower: OK"
else
    print_warning "⚠️ Flower: No responde en localhost:5555"
fi

# Obtener información de la instancia
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "localhost")
PRIVATE_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4 2>/dev/null || echo "127.0.0.1")

print_header "=== SISTEMA INICIADO ==="
print_message "Servicios disponibles:"
print_message "  - Nginx (Web): http://$PUBLIC_IP:8080"
print_message "  - Monitoreo (Flower): http://$PUBLIC_IP:5555"
print_message "  - Archivos de datos: http://$PUBLIC_IP:8080/data/"
print_message "  - Logs del sistema: http://$PUBLIC_IP:8080/logs/"
print_message "  - Página de monitoreo: http://$PUBLIC_IP:8080/monitor"
print_message "  - API de estado: http://$PUBLIC_IP:8080/api/stats"

print_message ""
print_message "Comandos útiles:"
print_message "  - Ver logs: sudo docker-compose logs -f"
print_message "  - Ver estado: sudo docker-compose ps"
print_message "  - Detener: sudo docker-compose down"
print_message "  - Reiniciar: sudo docker-compose restart"
print_message "  - Escalar workers: sudo docker-compose up -d --scale celery-worker=4"

print_header "✅ SISTEMA INICIADO EXITOSAMENTE"
