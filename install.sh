#!/bin/bash

# Script de instalación rápida para el sistema de scraping
# Compatible con Ubuntu/Debian

set -e

echo "🚀 Instalando Sistema de Scraping de Noticias..."
echo "================================================"

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
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

# Verificar si es Ubuntu/Debian
if ! command -v apt-get &> /dev/null; then
    print_error "Este script está diseñado para Ubuntu/Debian"
    exit 1
fi

# Actualizar sistema
print_status "Actualizando sistema..."
sudo apt-get update

# Instalar Python y dependencias
print_status "Instalando Python y dependencias..."
sudo apt-get install -y python3 python3-pip python3-venv

# Instalar PostgreSQL
print_status "Instalando PostgreSQL..."
sudo apt-get install -y postgresql postgresql-contrib

# Configurar PostgreSQL
print_status "Configurando PostgreSQL..."
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Crear base de datos
sudo -u postgres psql -c "CREATE DATABASE news_scraping;" 2>/dev/null || true
sudo -u postgres psql -c "CREATE USER postgres WITH PASSWORD '123456';" 2>/dev/null || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE news_scraping TO postgres;" 2>/dev/null || true

# Crear entorno virtual
print_status "Creando entorno virtual..."
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias de Python
print_status "Instalando dependencias de Python..."
pip install --upgrade pip
pip install -r requirements.txt

# Crear directorio de datos
print_status "Creando directorios..."
mkdir -p data logs

# Crear archivo de configuración
print_status "Creando archivo de configuración..."
cat > .env << EOF
# Configuración de la base de datos PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=news_scraping
DB_USER=postgres
DB_PASSWORD=123456

# Configuración de logging
LOG_LEVEL=INFO
EOF

# Ejecutar prueba del sistema
print_status "Ejecutando pruebas del sistema..."
python test_system.py

if [ $? -eq 0 ]; then
    print_status "✅ Instalación completada exitosamente!"
    echo
    echo "=== COMANDOS DISPONIBLES ==="
    echo "Ejecutar sistema: python main.py"
    echo "Modo programado: python scheduler.py --mode schedule --interval 1"
    echo "Ejecutar pruebas: python test_system.py"
    echo
    echo "=== CONFIGURACIÓN ==="
    echo "Base de datos: localhost:5432 (usuario: postgres, contraseña: 123456)"
    echo "Archivos de datos: ./data/"
    echo "Logs: ./scraper.log"
    echo
    print_warning "IMPORTANTE: Asegúrese de que PostgreSQL esté ejecutándose antes de usar el sistema"
else
    print_error "❌ La instalación falló. Revisar errores arriba."
    exit 1
fi
