#!/bin/bash

# Script de inicio automático para AWS

echo "🚀 INICIANDO SISTEMA DE SCRAPING EN AWS"
echo "========================================"

# Ir al directorio del proyecto
cd /opt/news-scraper

# Actualizar código
echo "📥 Actualizando código..."
git pull origin main

# Reiniciar contenedores
echo "🔄 Reiniciando contenedores..."
docker-compose down
docker-compose up -d --build

# Esperar a que los servicios estén listos
echo "⏳ Esperando servicios..."
sleep 30

# Verificar estado
echo "📊 Verificando estado..."
docker-compose ps

# Ejecutar scraping
echo "🚀 Ejecutando scraping..."
docker-compose exec celery-worker python aws_scraping.py

echo "✅ Sistema iniciado correctamente"
echo "📊 Monitoreo: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):5555"
echo "📁 Archivos: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8080/data/"
