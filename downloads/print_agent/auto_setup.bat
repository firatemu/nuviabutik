@echo off
TITLE Nuvia Local Print Agent - Automatic Setup
color 0A

:: Fix working directory when running as Administrator
cd /d "%~dp0"

echo =======================================================
echo     NUVIA LOCAL PRINT AGENT - INSTALLATION WIZARD
echo =======================================================
echo.

:: Check Admin Rights
NET SESSION >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    color 4F
    echo [ERROR] This script requires Administrator privileges!
    echo Please right-click "auto_setup.bat" and select "Run as Administrator".
    echo.
    pause
    exit /b 1
)

:: Check Python
echo [1] Checking Python installation...
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    color 4F
    echo [ERROR] Python is not installed or not added to PATH!
    echo Please install Python (3.10 or newer) from https://www.python.org/downloads/
    echo CRITICAL: Ensure you check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)
python --version

echo.
echo [2] Upgrading PIP and installing required libraries...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
IF %ERRORLEVEL% NEQ 0 (
    color 4F
    echo [ERROR] Failed to install requirements. Please check your internet connection.
    pause
    exit /b 1
)

echo.
echo [3] Installing Windows Service (NuviaPrintAgent)...
:: Stop service if it already exists
python install_service.py stop >nul 2>&1
python install_service.py remove >nul 2>&1

:: Install and start
python install_service.py install
IF %ERRORLEVEL% NEQ 0 (
    color 4F
    echo [ERROR] Failed to install Windows Service.
    pause
    exit /b 1
)

python install_service.py start
echo.
echo =======================================================
echo                      SUCCESS!
echo =======================================================
echo Nuvia Local Print Agent has been successfully installed
echo and is now running quietly in the background.
echo.
echo The agent will automatically start every time you turn
echo on this computer.
echo.
echo Local API Address: http://localhost:3210/health
echo Logs are saved to: C:\PrintAgent\logs\agent.log
echo =======================================================
pause
