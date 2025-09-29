#!/bin/bash
echo "🚀 INICIANDO SCRAPING SIMPLE"
echo "============================"

# Detener todo
sudo docker-compose down

# Arreglar permisos
sudo chown -R 1000:1000 /opt/news-scraper/logs
sudo chown -R 1000:1000 /opt/news-scraper/data
sudo chmod -R 755 /opt/news-scraper/logs
sudo chmod -R 755 /opt/news-scraper/data

# Iniciar solo lo necesario
echo "🔄 Iniciando Redis y PostgreSQL..."
sudo docker-compose up -d redis postgres

# Esperar
sleep 10

echo "🔄 Iniciando Celery Worker..."
sudo docker-compose up -d celery-worker

# Esperar
sleep 5

echo "🔄 Iniciando Celery Beat (Scheduler)..."
sudo docker-compose up -d celery-beat

echo "✅ Sistema iniciado!"
echo ""
echo "📊 VER LOGS EN TIEMPO REAL:"
echo "sudo docker-compose logs -f celery-worker"
echo ""
echo "📊 VER TODOS LOS LOGS:"
echo "sudo docker-compose logs -f"
echo ""
echo "📊 EJECUTAR SCRAPING MANUAL:"
echo "sudo docker-compose exec celery-worker celery -A celery_tasks call celery_tasks.scheduled_scraping"
