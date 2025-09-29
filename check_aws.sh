#!/bin/bash

echo "🔍 VERIFICANDO SISTEMA EN AWS"
echo "============================="

# Verificar contenedores
echo "📦 Estado de contenedores:"
docker-compose ps

echo ""
echo "📊 Base de datos:"
docker-compose exec postgres psql -U postgres -d news_scraper -c "SELECT COUNT(*) as total_noticias FROM noticias;"

echo ""
echo "📁 Archivos generados:"
ls -la /opt/news-scraper/data/

echo ""
echo "📝 Logs recientes:"
docker-compose logs --tail=20 celery-worker

echo ""
echo "🌐 URLs de acceso:"
echo "Flower: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):5555"
echo "Archivos: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8080/data/"
