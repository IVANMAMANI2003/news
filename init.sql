-- Script de inicialización de la base de datos PostgreSQL
-- Este archivo se ejecuta automáticamente cuando se crea el contenedor

-- Crear la base de datos si no existe (ya se crea automáticamente por la variable POSTGRES_DB)
-- CREATE DATABASE IF NOT EXISTS news_scraper;

-- Conectar a la base de datos
\c news_scraper;

-- Crear tabla de noticias
CREATE TABLE IF NOT EXISTS noticias (
    id SERIAL PRIMARY KEY,
    titulo TEXT,
    fecha TIMESTAMP,
    hora TIME,
    resumen TEXT,
    contenido TEXT,
    categoria VARCHAR(100),
    autor VARCHAR(200),
    tags TEXT,
    url TEXT UNIQUE,
    fecha_extraccion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    link_imagenes TEXT,
    fuente VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Crear índices para mejorar el rendimiento
CREATE INDEX IF NOT EXISTS idx_noticias_fecha ON noticias(fecha);
CREATE INDEX IF NOT EXISTS idx_noticias_fuente ON noticias(fuente);
CREATE INDEX IF NOT EXISTS idx_noticias_categoria ON noticias(categoria);
CREATE INDEX IF NOT EXISTS idx_noticias_fecha_extraccion ON noticias(fecha_extraccion);
CREATE INDEX IF NOT EXISTS idx_noticias_url ON noticias(url);
CREATE INDEX IF NOT EXISTS idx_noticias_created_at ON noticias(created_at);

-- Crear tabla de logs del sistema (opcional)
CREATE TABLE IF NOT EXISTS system_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    level VARCHAR(20),
    source VARCHAR(100),
    message TEXT,
    details JSONB
);

-- Crear tabla de estadísticas (opcional)
CREATE TABLE IF NOT EXISTS scraping_stats (
    id SERIAL PRIMARY KEY,
    fecha DATE DEFAULT CURRENT_DATE,
    fuente VARCHAR(100),
    noticias_extraidas INTEGER DEFAULT 0,
    errores INTEGER DEFAULT 0,
    tiempo_ejecucion INTEGER, -- en segundos
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Crear índices para las tablas adicionales
CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level);
CREATE INDEX IF NOT EXISTS idx_scraping_stats_fecha ON scraping_stats(fecha);
CREATE INDEX IF NOT EXISTS idx_scraping_stats_fuente ON scraping_stats(fuente);

-- Insertar datos de ejemplo (opcional)
-- INSERT INTO noticias (titulo, fecha, hora, resumen, contenido, categoria, autor, tags, url, link_imagenes, fuente) 
-- VALUES ('Noticia de ejemplo', '2024-01-01', '12:00:00', 'Resumen de ejemplo', 'Contenido de ejemplo', 'General', 'Sistema', 'ejemplo,test', 'https://ejemplo.com/noticia', '', 'sistema');

-- Crear usuario adicional para la aplicación (opcional)
-- CREATE USER scraper_user WITH PASSWORD 'scraper_password';
-- GRANT CONNECT ON DATABASE news_scraper TO scraper_user;
-- GRANT USAGE ON SCHEMA public TO scraper_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO scraper_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO scraper_user;

-- Configuraciones adicionales
-- Configurar timezone
SET timezone = 'America/Lima';

-- Mostrar información de la base de datos
SELECT 'Base de datos inicializada correctamente' as status;
SELECT current_database() as database_name;
SELECT current_user as current_user;
SELECT version() as postgresql_version;
