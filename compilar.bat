@echo off
REM Compila RETRO LEGACY a un .exe con su icono. Doble clic o desde la consola: compilar.bat
cd /d "%~dp0"

if not exist "icono\retro_legacy.ico" (
  echo FALTA icono\retro_legacy.ico. Ejecuta primero: git pull origin main
  pause
  exit /b 1
)
if not exist "portraits" (
  echo FALTA la carpeta portraits. Ejecuta primero: git pull origin main
  pause
  exit /b 1
)

echo [1/4] Instalando PyInstaller...
python --version
python -m pip install --quiet --upgrade pyinstaller pefile
if errorlevel 1 ( echo No se pudo instalar PyInstaller & pause & exit /b 1 )

echo [2/4] Limpiando compilaciones anteriores...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist RetroLegacy.spec del /q RetroLegacy.spec

echo [3/4] Compilando...
python -m PyInstaller --clean --noconsole --onedir --name RetroLegacy --collect-all imageio_ffmpeg --add-data "videos;videos" --add-data "fonts;fonts" --add-data "portraits;portraits" --add-data "aviones;aviones" --add-data "barcos;barcos" --add-data "soldados;soldados" --add-data "musica;musica" --add-data "icono;icono" --icon "icono\retro_legacy.ico" retro_legacy.py
if errorlevel 1 ( echo La compilacion fallo. Revisa los mensajes de arriba. & pause & exit /b 1 )

python -m PyInstaller --version
echo [4/4] Refrescando la cache de iconos de Windows...
ie4uinit.exe -show >nul 2>&1
ie4uinit.exe -ClearIconCache >nul 2>&1

echo.
python verificar_icono.py
echo.
echo Listo: dist\RetroLegacy\RetroLegacy.exe
echo Si el Explorador todavia muestra el icono viejo, cierra y abre la carpeta o reinicia el Explorador de archivos.
pause
