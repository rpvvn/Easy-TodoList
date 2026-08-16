@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================
echo   Easy-TodoList - Build Windows EXE
echo ============================================
echo.

set "PY=python"
%PY% --version >nul 2>nul
if errorlevel 1 set "PY=py -3"
%PY% --version >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+ first.
    pause
    exit /b 1
)

%PY% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
    echo [ERROR] Python 3.10 or newer is required.
    pause
    exit /b 1
)

echo [1/4] Installing dependencies...
%PY% -m pip install --upgrade pip
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo [2/4] Generating app icon...
if exist app.ico del /f /q app.ico
%PY% make_icon.py
if errorlevel 1 (
    echo [ERROR] Failed to generate app.ico.
    pause
    exit /b 1
)

echo [3/4] Building EXE with PyInstaller...
%PY% -m PyInstaller --noconfirm --clean --onefile --windowed --name Easy-TodoList --icon app.ico main.py
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed.
    pause
    exit /b 1
)

echo [4/4] Done!
echo.
echo Output: %cd%\dist\Easy-TodoList.exe
echo.
pause
