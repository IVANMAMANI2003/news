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
RUN mkdir -p data

# Crear usuario no-root para seguridad
RUN useradd -m -u 1000 scraper && chown -R scraper:scraper /app
USER scraper

# Variables de entorno por defecto
ENV DB_HOST=localhost
ENV DB_PORT=5432
ENV DB_NAME=news_scraping
ENV DB_USER=postgres
ENV DB_PASSWORD=123456
ENV LOG_LEVEL=INFO

# Comando por defecto
CMD ["python", "main.py"]
