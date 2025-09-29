#!/bin/bash

# Configurar cron para ejecutar scraping cada hora

echo "⏰ Configurando cron para scraping automático..."

# Crear script de scraping
cat > /opt/news-scraper/run_hourly_scraping.sh << 'EOF'
#!/bin/bash
cd /opt/news-scraper
docker-compose exec celery-worker python aws_scraping.py >> /opt/news-scraper/logs/cron_scraping.log 2>&1
EOF

chmod +x /opt/news-scraper/run_hourly_scraping.sh

# Agregar a crontab
(crontab -l 2>/dev/null; echo "0 * * * * /opt/news-scraper/run_hourly_scraping.sh") | crontab -

echo "✅ Cron configurado para ejecutar cada hora"
echo "📝 Logs en: /opt/news-scraper/logs/cron_scraping.log"
