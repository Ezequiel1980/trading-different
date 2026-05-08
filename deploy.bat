@echo off
echo === Trading Different — Deploy a Vercel ===
echo.

REM Verificar Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js no esta instalado. Descargarlo de https://nodejs.org
    pause
    exit /b 1
)

REM Instalar Vercel CLI si no está
vercel --version >nul 2>&1
if errorlevel 1 (
    echo Instalando Vercel CLI...
    npm install -g vercel
)

echo.
echo Iniciando deploy...
vercel --prod --yes --name trading-different
pause
