@echo off
echo ========================================
echo INSTALACION DEL SISTEMA DE SCRAPING
echo ========================================
echo.

echo [1/4] Verificando Python...
python --version
if %errorlevel% neq 0 (
    echo ERROR: Python no esta instalado
    echo Descarga Python desde: https://python.org
    pause
    exit /b 1
)
echo Python encontrado
echo.

echo [2/4] Instalando dependencias...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: No se pudieron instalar las dependencias
    pause
    exit /b 1
)
echo Dependencias instaladas
echo.

echo [3/4] Verificando PostgreSQL...
echo Verifica que PostgreSQL este instalado y ejecutandose
echo Usuario: postgres
echo Password: 123456
echo Puerto: 5432
echo.
echo Si no tienes PostgreSQL instalado:
echo 1. Descarga desde: https://postgresql.org/download/windows/
echo 2. Instala con usuario 'postgres' y password '123456'
echo 3. Asegurate que el servicio este ejecutandose
echo.
pause

echo [4/4] Probando conexion a base de datos...
python test_db.py
if %errorlevel% neq 0 (
    echo ERROR: No se pudo conectar a PostgreSQL
    echo Verifica la instalacion y configuracion
    pause
    exit /b 1
)

echo.
echo ========================================
echo INSTALACION COMPLETADA
echo ========================================
echo.
echo Para ejecutar el sistema:
echo 1. python test_local.py    - Probar todo el sistema
echo 2. python unified_scraper.py - Ejecutar scraping una vez
echo 3. python scheduler.py     - Ejecutar scheduler continuo
echo.
pause
