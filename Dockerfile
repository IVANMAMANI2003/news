# Dockerfile para el sistema de scraping de noticias
FROM python:3.9-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Establecer directorio de trabajo
WORKDIR /app

# Copiar archivos de dependencias
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY . .

# Crear directorio para datos
RUN mkdir -p data logs

# Usuario no-root
RUN useradd -m -u 1000 scraper && chown -R scraper:scraper /app
USER scraper

# Variables de entorno
ENV DB_HOST=localhost \
    DB_PORT=5432 \
    DB_NAME=news_scraping \
    DB_USER=postgres \
    DB_PASSWORD=123456 \
    LOG_LEVEL=INFO \
    REDIS_HOST=redis \
    REDIS_PORT=6379 \
    REDIS_DB=0

# Comando por defecto
CMD ["python", "main.py"]
