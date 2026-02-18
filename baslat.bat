@echo off
echo PDF Ceviri Backend baslatiliyor...
echo.

:: Python kurulu mu kontrol et
python --version >nul 2>&1
if errorlevel 1 (
    echo HATA: Python bulunamadi!
    echo https://python.org adresinden Python indirip kurun.
    pause
    exit /b
)

:: pip ile degil, python -m pip ile yukle (dogru Python'a yukler)
echo Gereksinimler yukleniyor...
python -m pip install fastapi uvicorn pymupdf python-multipart

echo.
echo ================================================
echo  Backend calisiyor: http://localhost:8000
echo  Durdurmak icin: CTRL+C
echo ================================================
echo.

ipconfig | findstr "IPv4"

echo.
echo Yukardaki IP'yi pdfService.js dosyasindaki
echo BACKEND_URL satirina yazmayi unutmayin!
echo.

python main.py
pause
