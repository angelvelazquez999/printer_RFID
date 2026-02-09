@echo off
echo ========================================
echo Compilando RFID Printer API a EXE
echo ========================================
echo.

:: Instalar pyinstaller si no está instalado
echo Verificando PyInstaller...
poetry add pyinstaller --group dev

echo.
echo Compilando con PyInstaller...
poetry run pyinstaller rfid-printer.spec --clean

echo.
echo ========================================
echo Compilacion completada!
echo ========================================
echo El ejecutable esta en: dist\rfid-printer-api.exe
echo.
echo Para ejecutar: dist\rfid-printer-api.exe [puerto]
echo Ejemplo: dist\rfid-printer-api.exe 8090
echo.
pause
