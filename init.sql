-- Script de inicialización de la base de datos
-- Este archivo se ejecuta automáticamente al crear el contenedor PostgreSQL

-- Crear la base de datos si no existe
CREATE DATABASE IF NOT EXISTS news_scraping;

-- Conectar a la base de datos
\c news_scraping;

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
CREATE INDEX IF NOT EXISTS idx_noticias_fuente ON noticias(fuente);
CREATE INDEX IF NOT EXISTS idx_noticias_fecha ON noticias(fecha);
CREATE INDEX IF NOT EXISTS idx_noticias_categoria ON noticias(categoria);
CREATE INDEX IF NOT EXISTS idx_noticias_fecha_extraccion ON noticias(fecha_extraccion);
CREATE INDEX IF NOT EXISTS idx_noticias_url ON noticias(url);

-- Crear tabla de logs del sistema
CREATE TABLE IF NOT EXISTS scraping_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    level VARCHAR(20),
    source VARCHAR(100),
    message TEXT,
    details TEXT
);

-- Crear tabla de estadísticas
CREATE TABLE IF NOT EXISTS scraping_stats (
    id SERIAL PRIMARY KEY,
    date DATE DEFAULT CURRENT_DATE,
    source VARCHAR(100),
    total_articles INTEGER DEFAULT 0,
    new_articles INTEGER DEFAULT 0,
    execution_time INTEGER, -- en segundos
    status VARCHAR(20) DEFAULT 'success'
);

-- Insertar datos de ejemplo (opcional)
-- INSERT INTO noticias (titulo, fecha, resumen, fuente) VALUES 
-- ('Noticia de ejemplo', CURRENT_TIMESTAMP, 'Esta es una noticia de ejemplo', 'Sistema');
