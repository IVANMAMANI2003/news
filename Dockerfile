# Dockerfile para el sistema de scraping de noticias
FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    postgresql-client \
    redis-tools \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar archivos de requirements
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY . .

# Crear directorios necesarios
RUN mkdir -p data logs

# Crear usuario no-root para seguridad
RUN useradd -m -u 1000 scraper && \
    chown -R scraper:scraper /app

# Cambiar a usuario no-root
USER scraper

# Variables de entorno por defecto
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Exponer puerto (opcional, para monitoreo)
EXPOSE 8080

# Comando por defecto
CMD ["python", "scheduler.py"]
