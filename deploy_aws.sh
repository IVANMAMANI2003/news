#!/bin/bash

# Script de despliegue para AWS EC2
# Este script configura el sistema de scraping en una instancia EC2

set -e

echo "🚀 Iniciando despliegue en AWS EC2..."

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para imprimir mensajes con color
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar si estamos en Ubuntu/Debian
if ! command -v apt-get &> /dev/null; then
    print_error "Este script está diseñado para Ubuntu/Debian. Por favor adapte para su distribución."
    exit 1
fi

print_status "Actualizando sistema..."
sudo apt-get update

print_status "Instalando dependencias del sistema..."
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    postgresql \
    postgresql-contrib \
    nginx \
    docker.io \
    docker-compose \
    git \
    curl \
    wget \
    unzip

print_status "Configurando PostgreSQL..."
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Configurar PostgreSQL
sudo -u postgres psql -c "CREATE USER postgres WITH PASSWORD '123456';"
sudo -u postgres psql -c "CREATE DATABASE news_scraping OWNER postgres;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE news_scraping TO postgres;"

# Configurar PostgreSQL para conexiones remotas
sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" /etc/postgresql/*/main/postgresql.conf
sudo sed -i "s/local   all             all                                     peer/local   all             all                                     md5/" /etc/postgresql/*/main/pg_hba.conf
echo "host    all             all             0.0.0.0/0               md5" | sudo tee -a /etc/postgresql/*/main/pg_hba.conf

sudo systemctl restart postgresql

print_status "Configurando Docker..."
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

print_status "Creando directorio del proyecto..."
PROJECT_DIR="/opt/news_scraping"
sudo mkdir -p $PROJECT_DIR
sudo chown $USER:$USER $PROJECT_DIR

print_status "Copiando archivos del proyecto..."
# Asumiendo que los archivos están en el directorio actual
cp -r . $PROJECT_DIR/
cd $PROJECT_DIR

print_status "Creando entorno virtual de Python..."
python3 -m venv venv
source venv/bin/activate

print_status "Instalando dependencias de Python..."
pip install --upgrade pip
pip install -r requirements.txt

print_status "Configurando variables de entorno..."
cat > .env << EOF
# Configuración de la base de datos PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=news_scraping
DB_USER=postgres
DB_PASSWORD=123456

# Configuración de AWS
AWS_REGION=us-east-1
AWS_INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)

# Configuración de logging
LOG_LEVEL=INFO
EOF

print_status "Configurando Nginx..."
sudo cp nginx.conf /etc/nginx/nginx.conf
sudo systemctl restart nginx
sudo systemctl enable nginx

print_status "Creando servicio systemd para el scraper..."
sudo tee /etc/systemd/system/news-scraper.service > /dev/null << EOF
[Unit]
Description=News Scraping Service
After=network.target postgresql.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin
ExecStart=$PROJECT_DIR/venv/bin/python scheduler.py --mode schedule --interval 1
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

print_status "Habilitando y iniciando servicios..."
sudo systemctl daemon-reload
sudo systemctl enable news-scraper
sudo systemctl start news-scraper

print_status "Configurando firewall..."
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 5432/tcp
sudo ufw --force enable

print_status "Creando script de monitoreo..."
cat > monitor.sh << 'EOF'
#!/bin/bash
echo "=== ESTADO DEL SISTEMA DE SCRAPING ==="
echo "Fecha: $(date)"
echo

echo "=== SERVICIOS ==="
systemctl is-active postgresql
systemctl is-active nginx
systemctl is-active news-scraper

echo
echo "=== ESTADÍSTICAS DE LA BASE DE DATOS ==="
sudo -u postgres psql -d news_scraping -c "
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
echo "=== LOGS RECIENTES ==="
tail -20 scraper.log
EOF

chmod +x monitor.sh

print_status "Creando script de respaldo..."
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/backups/news_scraping"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Respaldar base de datos
pg_dump -h localhost -U postgres -d news_scraping > $BACKUP_DIR/database_$DATE.sql

# Respaldar archivos de datos
tar -czf $BACKUP_DIR/data_$DATE.tar.gz data/

# Respaldar logs
tar -czf $BACKUP_DIR/logs_$DATE.tar.gz *.log

# Limpiar respaldos antiguos (mantener solo últimos 7 días)
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Respaldo completado: $BACKUP_DIR"
EOF

chmod +x backup.sh

print_status "Configurando cron para respaldos diarios..."
(crontab -l 2>/dev/null; echo "0 2 * * * $PROJECT_DIR/backup.sh") | crontab -

print_status "Verificando instalación..."
sleep 5

# Verificar servicios
if systemctl is-active --quiet postgresql; then
    print_status "✅ PostgreSQL está funcionando"
else
    print_error "❌ PostgreSQL no está funcionando"
fi

if systemctl is-active --quiet nginx; then
    print_status "✅ Nginx está funcionando"
else
    print_error "❌ Nginx no está funcionando"
fi

if systemctl is-active --quiet news-scraper; then
    print_status "✅ Servicio de scraping está funcionando"
else
    print_error "❌ Servicio de scraping no está funcionando"
fi

print_status "🎉 Despliegue completado!"
echo
echo "=== INFORMACIÓN IMPORTANTE ==="
echo "📊 Panel web: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
echo "🗄️ Base de datos: localhost:5432 (usuario: postgres, contraseña: 123456)"
echo "📁 Archivos de datos: $PROJECT_DIR/data/"
echo "📋 Logs: $PROJECT_DIR/scraper.log"
echo "🔧 Monitoreo: $PROJECT_DIR/monitor.sh"
echo "💾 Respaldo: $PROJECT_DIR/backup.sh"
echo
echo "=== COMANDOS ÚTILES ==="
echo "Ver estado: sudo systemctl status news-scraper"
echo "Ver logs: journalctl -u news-scraper -f"
echo "Reiniciar servicio: sudo systemctl restart news-scraper"
echo "Monitorear: $PROJECT_DIR/monitor.sh"
echo
print_warning "IMPORTANTE: Configure las reglas de seguridad de AWS para permitir tráfico en los puertos 80 y 5432"
