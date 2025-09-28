#!/bin/bash

# Script para verificar permisos y configurar el sistema correctamente

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

print_header "=== VERIFICACIÓN DE PERMISOS Y CONFIGURACIÓN ==="

# Verificar si se ejecuta como root
if [ "$EUID" -eq 0 ]; then
    print_message "✅ Ejecutándose como root"
else
    print_warning "⚠️ No se está ejecutando como root. Algunos comandos pueden fallar."
    print_message "💡 Para evitar problemas, ejecuta: sudo $0"
fi

# Verificar Docker
print_message "🔍 Verificando Docker..."
if command -v docker &> /dev/null; then
    print_message "✅ Docker está instalado"
    
    # Verificar permisos de Docker
    if docker ps &> /dev/null; then
        print_message "✅ Permisos de Docker OK"
    else
        print_warning "⚠️ Problemas con permisos de Docker"
        print_message "💡 Ejecuta: sudo usermod -aG docker $USER"
        print_message "💡 Luego cierra sesión y vuelve a entrar"
    fi
else
    print_error "❌ Docker no está instalado"
    print_message "💡 Instala Docker con: curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh"
fi

# Verificar Docker Compose
print_message "🔍 Verificando Docker Compose..."
if command -v docker-compose &> /dev/null; then
    print_message "✅ Docker Compose está instalado"
else
    print_error "❌ Docker Compose no está instalado"
    print_message "💡 Instala con: sudo curl -L \"https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)\" -o /usr/local/bin/docker-compose && sudo chmod +x /usr/local/bin/docker-compose"
fi

# Verificar PostgreSQL
print_message "🔍 Verificando PostgreSQL..."
if command -v psql &> /dev/null; then
    print_message "✅ PostgreSQL está instalado"
else
    print_warning "⚠️ PostgreSQL no está instalado localmente"
    print_message "💡 Se usará PostgreSQL en Docker"
fi

# Verificar Redis
print_message "🔍 Verificando Redis..."
if command -v redis-cli &> /dev/null; then
    print_message "✅ Redis está instalado"
else
    print_warning "⚠️ Redis no está instalado localmente"
    print_message "💡 Se usará Redis en Docker"
fi

# Verificar Python
print_message "🔍 Verificando Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    print_message "✅ Python $PYTHON_VERSION está instalado"
else
    print_error "❌ Python3 no está instalado"
    print_message "💡 Instala con: sudo apt update && sudo apt install python3 python3-pip"
fi

# Verificar pip
print_message "🔍 Verificando pip..."
if command -v pip3 &> /dev/null; then
    print_message "✅ pip3 está instalado"
else
    print_warning "⚠️ pip3 no está instalado"
    print_message "💡 Instala con: sudo apt install python3-pip"
fi

# Verificar permisos de directorio
print_message "🔍 Verificando permisos de directorio..."
CURRENT_DIR=$(pwd)
if [ -w "$CURRENT_DIR" ]; then
    print_message "✅ Permisos de escritura en directorio actual"
else
    print_error "❌ Sin permisos de escritura en directorio actual"
    print_message "💡 Ejecuta: sudo chown -R $USER:$USER $CURRENT_DIR"
fi

# Verificar archivos del proyecto
print_message "🔍 Verificando archivos del proyecto..."
REQUIRED_FILES=("docker-compose.yml" "requirements.txt" "database.py" "unified_scraper.py")
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        print_message "✅ $file existe"
    else
        print_error "❌ $file no encontrado"
    fi
done

# Verificar directorio data
print_message "🔍 Verificando directorio data..."
if [ -d "data" ]; then
    print_message "✅ Directorio data/ existe"
    if [ -w "data" ]; then
        print_message "✅ Permisos de escritura en data/"
    else
        print_warning "⚠️ Sin permisos de escritura en data/"
        print_message "💡 Ejecuta: sudo chmod 755 data/"
    fi
else
    print_warning "⚠️ Directorio data/ no existe"
    print_message "💡 Se creará automáticamente"
fi

# Verificar puertos
print_message "🔍 Verificando puertos..."
PORTS=(80 443 5432 6379 5555)
for port in "${PORTS[@]}"; do
    if netstat -tuln 2>/dev/null | grep -q ":$port "; then
        print_warning "⚠️ Puerto $port está en uso"
    else
        print_message "✅ Puerto $port está disponible"
    fi
done

# Verificar firewall
print_message "🔍 Verificando firewall..."
if command -v ufw &> /dev/null; then
    UFW_STATUS=$(sudo ufw status 2>/dev/null | head -1)
    if [[ $UFW_STATUS == *"active"* ]]; then
        print_message "✅ Firewall está activo"
        print_message "💡 Asegúrate de abrir los puertos necesarios:"
        print_message "   sudo ufw allow 22/tcp   # SSH"
        print_message "   sudo ufw allow 80/tcp   # HTTP"
        print_message "   sudo ufw allow 443/tcp  # HTTPS"
        print_message "   sudo ufw allow 5555/tcp # Flower"
    else
        print_warning "⚠️ Firewall no está activo"
    fi
else
    print_warning "⚠️ ufw no está instalado"
fi

# Verificar espacio en disco
print_message "🔍 Verificando espacio en disco..."
DISK_USAGE=$(df -h . | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -lt 80 ]; then
    print_message "✅ Espacio en disco OK ($DISK_USAGE% usado)"
else
    print_warning "⚠️ Poco espacio en disco ($DISK_USAGE% usado)"
fi

# Verificar memoria
print_message "🔍 Verificando memoria..."
TOTAL_MEM=$(free -m | awk 'NR==2{printf "%.0f", $2}')
if [ "$TOTAL_MEM" -ge 2048 ]; then
    print_message "✅ Memoria suficiente (${TOTAL_MEM}MB)"
else
    print_warning "⚠️ Poca memoria (${TOTAL_MEM}MB). Se recomienda al menos 2GB"
fi

# Resumen y recomendaciones
print_header "=== RESUMEN Y RECOMENDACIONES ==="

print_message "📋 Comandos recomendados para evitar problemas de permisos:"
print_message ""
print_message "🔧 Configuración inicial:"
print_message "   sudo apt update && sudo apt upgrade -y"
print_message "   sudo usermod -aG docker $USER"
print_message "   sudo chown -R $USER:$USER $CURRENT_DIR"
print_message ""
print_message "🐳 Docker:"
print_message "   sudo docker-compose up -d"
print_message "   sudo docker-compose logs -f"
print_message "   sudo docker-compose down"
print_message ""
print_message "🔍 Monitoreo:"
print_message "   sudo docker-compose ps"
print_message "   sudo docker stats"
print_message "   sudo docker-compose exec postgres psql -U postgres -d news_scraper"
print_message ""
print_message "🛠️ Mantenimiento:"
print_message "   sudo docker system prune -f"
print_message "   sudo docker-compose restart"
print_message "   sudo docker-compose up -d --scale celery-worker=4"

print_header "✅ VERIFICACIÓN COMPLETADA"
print_message "Revisa los mensajes anteriores para identificar posibles problemas"
print_message "Ejecuta los comandos recomendados si es necesario"
