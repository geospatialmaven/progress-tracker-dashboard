@echo off
title Geospatial Maven — Progress Tracker Dashboard
echo.
echo  ================================================
echo   GEOSPATIAL MAVEN — Progress Tracker Dashboard
echo  ================================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python not found. Please install Python 3.8+
    pause
    exit /b
)

:: Install dependencies
echo  Installing dependencies...
pip install -r requirements.txt --quiet

echo.
echo  Starting server...
echo  Open http://localhost:5000 in your browser
echo.
echo  Login credentials:
echo    Super Admin : admin@geospatialmaven.com / admin123
echo    Developer   : sarah@geospatialmaven.com / dev123
echo    Client      : client@undp.org / client123
echo.
echo  Press Ctrl+C to stop the server.
echo.

python app.py
pause
