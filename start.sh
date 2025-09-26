#!/bin/bash

# Script de inicio rápido para el sistema de scraping

echo "🚀 Iniciando Sistema de Scraping de Noticias..."
echo "=============================================="

# Verificar si existe el entorno virtual
if [ ! -d "venv" ]; then
    echo "❌ Entorno virtual no encontrado. Ejecute primero: ./install.sh"
    exit 1
fi

# Activar entorno virtual
source venv/bin/activate

# Verificar PostgreSQL
echo "🔍 Verificando PostgreSQL..."
if ! systemctl is-active --quiet postgresql; then
    echo "⚠️ PostgreSQL no está ejecutándose. Iniciando..."
    sudo systemctl start postgresql
fi

# Verificar base de datos
echo "🔍 Verificando base de datos..."
if ! psql -h localhost -U postgres -d news_scraping -c "SELECT 1;" &>/dev/null; then
    echo "⚠️ Base de datos no accesible. Verificando configuración..."
    sudo -u postgres psql -c "CREATE DATABASE news_scraping;" 2>/dev/null || true
fi

# Mostrar menú de opciones
echo
echo "=== OPCIONES DE INICIO ==="
echo "1. Modo interactivo (recomendado para primera vez)"
echo "2. Modo programado (cada hora)"
echo "3. Ejecutar una sola vez"
echo "4. Ejecutar pruebas del sistema"
echo "5. Ver estado del sistema"
echo

read -p "Seleccione una opción (1-5): " option

case $option in
    1)
        echo "🔄 Iniciando modo interactivo..."
        python main.py
        ;;
    2)
        echo "⏰ Iniciando modo programado (cada hora)..."
        echo "Presione Ctrl+C para detener"
        python scheduler.py --mode schedule --interval 1
        ;;
    3)
        echo "🔄 Ejecutando una sola vez..."
        python scheduler.py --mode once
        ;;
    4)
        echo "🧪 Ejecutando pruebas del sistema..."
        python test_system.py
        ;;
    5)
        echo "📊 Estado del sistema:"
        echo "====================="
        echo "PostgreSQL: $(systemctl is-active postgresql)"
        echo "Archivos de datos: $(ls -la data/ 2>/dev/null | wc -l) archivos"
        echo "Logs recientes:"
        tail -5 scraper.log 2>/dev/null || echo "No hay logs disponibles"
        ;;
    *)
        echo "❌ Opción no válida"
        exit 1
        ;;
esac
