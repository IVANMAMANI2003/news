# 🚀 Despliegue en AWS - Sistema de Scraping de Noticias

## 📋 Requisitos Previos

### 1. Instancia EC2
- **Tipo**: t3.medium o superior (mínimo 2GB RAM)
- **Sistema Operativo**: Ubuntu 20.04 LTS o superior
- **Almacenamiento**: 20GB mínimo
- **Puertos abiertos**: 22 (SSH), 80 (HTTP), 443 (HTTPS), 5555 (Flower)

### 2. Configuración de Seguridad
```bash
# Grupo de seguridad debe permitir:
- SSH (22) desde tu IP
- HTTP (80) desde cualquier lugar
- HTTPS (443) desde cualquier lugar
- Flower (5555) desde cualquier lugar (opcional)
```

## 🚀 Despliegue Automático

### Opción 1: Script Automático (Recomendado)

```bash
# 1. Conectar a la instancia EC2
ssh -i tu-key.pem ubuntu@tu-ip-publica

# 2. Ejecutar script de despliegue
sudo wget https://raw.githubusercontent.com/IVANMAMANI2003/news/main/deploy_to_aws.sh
sudo chmod +x deploy_to_aws.sh
sudo ./deploy_to_aws.sh
```

### Opción 2: Despliegue Manual

```bash
# 1. Conectar a la instancia
ssh -i tu-key.pem ubuntu@tu-ip-publica

# 2. Actualizar sistema
sudo apt update && sudo apt upgrade -y

# 3. Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# 4. Instalar Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 5. Clonar repositorio
git clone https://github.com/IVANMAMANI2003/news.git
cd news

# 6. Iniciar servicios
sudo docker-compose up -d --build
```

## 📊 Verificación del Despliegue

### 1. Verificar Servicios
```bash
# Ver estado de contenedores
sudo docker-compose ps

# Ver logs
sudo docker-compose logs -f

# Ver uso de recursos
sudo docker stats
```

### 2. Acceder a Servicios Web
- **Flower (Monitoreo)**: `http://tu-ip-publica:5555`
- **Archivos de Datos**: `http://tu-ip-publica/data/`
- **Estado del Sistema**: `http://tu-ip-publica/`

### 3. Verificar Base de Datos
```bash
# Conectar a PostgreSQL
sudo docker-compose exec postgres psql -U postgres -d news_scraper

# Ver estadísticas
SELECT COUNT(*) FROM noticias;
SELECT fuente, COUNT(*) FROM noticias GROUP BY fuente;
```

## 🔧 Comandos de Administración

### Gestión del Sistema
```bash
# Iniciar sistema
news-scraper-start

# Detener sistema
news-scraper-stop

# Monitorear sistema
news-scraper-monitor

# Crear backup
news-scraper-backup
```

### Escalado de Workers
```bash
# Escalar a 4 workers
news-scraper-scale 4

# Escalar a 8 workers
news-scraper-scale 8
```

### Logs y Monitoreo
```bash
# Ver logs en tiempo real
sudo docker-compose logs -f

# Ver logs de un servicio específico
sudo docker-compose logs -f celery-worker

# Ver logs de base de datos
sudo docker-compose logs -f postgres
```

## 📈 Optimización de Rendimiento

### 1. Configuración de Instancia
- **t3.medium**: Para desarrollo y pruebas
- **t3.large**: Para producción pequeña
- **t3.xlarge**: Para producción media
- **c5.xlarge**: Para alta performance

### 2. Escalado de Workers
```bash
# Para instancia t3.medium (2 vCPU)
news-scraper-scale 2

# Para instancia t3.large (2 vCPU)
news-scraper-scale 4

# Para instancia t3.xlarge (4 vCPU)
news-scraper-scale 8
```

### 3. Configuración de Memoria
```bash
# Ajustar límites de memoria en docker-compose.yml
services:
  celery-worker:
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M
```

## 🔒 Seguridad

### 1. Configurar SSL (Opcional)
```bash
# Instalar certificado SSL
sudo certbot --nginx -d tu-dominio.com

# Renovar certificados automáticamente
sudo crontab -e
# Agregar: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 2. Firewall
```bash
# Verificar reglas de firewall
sudo ufw status

# Bloquear acceso a Flower desde internet (opcional)
sudo ufw deny 5555
```

### 3. Backup Automático
```bash
# Crear backup diario
sudo crontab -e
# Agregar: 0 2 * * * /opt/news-scraper/backup.sh
```

## 🐛 Solución de Problemas

### Error de Memoria
```bash
# Verificar uso de memoria
free -h
sudo docker stats

# Limpiar contenedores no utilizados
sudo docker system prune -f
```

### Error de Conexión a Base de Datos
```bash
# Verificar estado de PostgreSQL
sudo docker-compose exec postgres pg_isready -U postgres

# Reiniciar base de datos
sudo docker-compose restart postgres
```

### Error de Redis
```bash
# Verificar estado de Redis
sudo docker-compose exec redis redis-cli ping

# Reiniciar Redis
sudo docker-compose restart redis
```

### Error de Workers
```bash
# Ver logs de workers
sudo docker-compose logs celery-worker

# Reiniciar workers
sudo docker-compose restart celery-worker
```

## 📊 Monitoreo y Alertas

### 1. Métricas Importantes
- **CPU**: < 80%
- **Memoria**: < 80%
- **Disco**: < 85%
- **Workers activos**: > 0
- **Tareas completadas**: Verificar en Flower

### 2. Alertas Recomendadas
```bash
# Script de monitoreo básico
#!/bin/bash
CPU=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
MEM=$(free | grep Mem | awk '{printf("%.2f", $3/$2 * 100.0)}')

if (( $(echo "$CPU > 80" | bc -l) )); then
    echo "ALERTA: CPU alto: $CPU%"
fi

if (( $(echo "$MEM > 80" | bc -l) )); then
    echo "ALERTA: Memoria alta: $MEM%"
fi
```

## 💰 Optimización de Costos

### 1. Instancias Spot
- Usar instancias spot para desarrollo
- Ahorro del 50-90% en costos

### 2. Auto-scaling
```bash
# Script para auto-scaling basado en carga
#!/bin/bash
LOAD=$(uptime | awk -F'load average:' '{print $2}' | cut -d',' -f1 | tr -d ' ')

if (( $(echo "$LOAD > 2" | bc -l) )); then
    news-scraper-scale 8
elif (( $(echo "$LOAD < 0.5" | bc -l) )); then
    news-scraper-scale 2
fi
```

### 3. Programación de Instancias
- Apagar instancias en horarios no laborales
- Usar AWS Lambda para tareas programadas

## 📞 Soporte

### Logs Importantes
```bash
# Logs del sistema
journalctl -u news-scraper -f

# Logs de Docker
sudo docker-compose logs -f

# Logs de aplicación
tail -f /opt/news-scraper/logs/unified_scraper.log
```

### Información del Sistema
```bash
# Ver información del despliegue
cat /opt/news-scraper/DEPLOYMENT_INFO.txt

# Ver estado de servicios
news-scraper-monitor
```

---

**¡Sistema listo para producción en AWS! 🎉**

Para más información, consulta el [README.md](README.md) o el [QUICK_START.md](QUICK_START.md).
