#!/bin/bash

echo "🔍 DIAGNÓSTICO DEL SISTEMA DE SCRAPING"
echo "======================================"

# Verificar Docker
echo "1. Verificando Docker..."
if command -v docker &> /dev/null; then
    echo "✅ Docker instalado"
    echo "Versión: $(docker --version)"
else
    echo "❌ Docker no instalado"
    exit 1
fi

# Verificar Docker Compose
echo -e "\n2. Verificando Docker Compose..."
if command -v docker-compose &> /dev/null; then
    echo "✅ Docker Compose instalado"
    echo "Versión: $(docker-compose --version)"
else
    echo "❌ Docker Compose no instalado"
    exit 1
fi

# Verificar contenedores
echo -e "\n3. Estado de contenedores..."
sudo docker-compose ps

# Verificar logs de errores
echo -e "\n4. Verificando logs de errores..."
echo "--- Logs de Redis ---"
sudo docker-compose logs redis | tail -5

echo -e "\n--- Logs de PostgreSQL ---"
sudo docker-compose logs postgres | tail -5

echo -e "\n--- Logs de Celery Worker ---"
sudo docker-compose logs celery-worker | tail -10

echo -e "\n--- Logs de Celery Beat ---"
sudo docker-compose logs celery-beat | tail -5

# Verificar conectividad de base de datos
echo -e "\n5. Verificando base de datos..."
if sudo docker-compose exec -T postgres psql -U postgres -d news_scraper -c "SELECT 1;" &>/dev/null; then
    echo "✅ Base de datos conectada"
    
    # Contar noticias
    echo "Contando noticias en BD:"
    sudo docker-compose exec -T postgres psql -U postgres -d news_scraper -c "SELECT fuente, COUNT(*) as noticias FROM noticias GROUP BY fuente;"
else
    echo "❌ No se puede conectar a la base de datos"
fi

# Verificar Redis
echo -e "\n6. Verificando Redis..."
if sudo docker-compose exec -T redis redis-cli ping &>/dev/null; then
    echo "✅ Redis conectado"
else
    echo "❌ Redis no conectado"
fi

# Verificar archivos de datos
echo -e "\n7. Verificando archivos generados..."
if [ -d "data" ]; then
    echo "✅ Directorio data existe"
    echo "Archivos CSV: $(ls -la data/*.csv 2>/dev/null | wc -l)"
    echo "Archivos JSON: $(ls -la data/*.json 2>/dev/null | wc -l)"
else
    echo "❌ Directorio data no existe"
fi

# Verificar logs
echo -e "\n8. Verificando logs..."
if [ -d "logs" ]; then
    echo "✅ Directorio logs existe"
    echo "Archivos de log: $(ls -la logs/*.log 2>/dev/null | wc -l)"
else
    echo "❌ Directorio logs no existe"
fi

# Verificar comandos de gestión
echo -e "\n9. Verificando comandos de gestión..."
if command -v news-scraper &> /dev/null; then
    echo "✅ Comando news-scraper disponible"
else
    echo "❌ Comando news-scraper no disponible"
    echo "Crear enlace: sudo ln -sf $(pwd)/manage.sh /usr/local/bin/news-scraper"
fi

echo -e "\n======================================"
echo "🔧 COMANDOS DE REPARACIÓN:"
echo "======================================"
echo "Si hay problemas, ejecuta:"
echo "1. sudo docker-compose down -v"
echo "2. sudo docker system prune -f"
echo "3. sudo docker-compose up -d"
echo "4. sudo docker-compose logs -f"
echo ""
echo "Para ejecutar scraping manual:"
echo "sudo docker-compose exec celery-worker python unified_scraper.py"
echo ""
echo "Para ver logs en tiempo real:"
echo "sudo docker-compose logs -f celery-worker"
