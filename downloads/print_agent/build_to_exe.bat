@echo off
TITLE Compile Nuvia Print Agent to EXE
color 0B

:: Fix working directory
cd /d "%~dp0"

echo =======================================================
echo       NUVIA PRINT AGENT - EXE COMPILER WIZARD
echo =======================================================
echo.

echo [1] Checking for Python...
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    color 4F
    echo [ERROR] Python is missing! Install Python and add it to PATH.
    pause
    exit /b 1
)

echo [2] Installing libraries and PyInstaller...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

echo [3] Compiling to EXE...
:: Clean old builds
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

python -m PyInstaller --onefile --noconsole --name NuviaPrintAgent --hidden-import win32timezone main.py

echo.
IF %ERRORLEVEL% EQU 0 (
    echo =======================================================
    echo                     COMPILATION SUCCESS!
    echo =======================================================
    echo Your EXE file has been created successfully!
    echo File Location: \dist\NuviaPrintAgent.exe
    echo.
    echo You can now copy "NuviaPrintAgent.exe" and "config.json"
    echo anywhere on your computer and run it without Python.
    echo =======================================================
) ELSE (
    color 4F
    echo [ERROR] Compilation failed.
)
pause
