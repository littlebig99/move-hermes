@echo off
set SCRIPT_DIR=%~dp0
set DATA_DIR=%SCRIPT_DIR%data
set LOG_FILE=%DATA_DIR%service.log

REM Check if Python is in PATH
python --version >nul 2>&1
if %errorlevel% neq 0 (
    exit /b 1
)

REM Check data directory
if not exist "%DATA_DIR%" mkdir "%DATA_DIR%"

REM Start service in background
cd /d "%SCRIPT_DIR%backend"
start /B python main.py > "%LOG_FILE%" 2>&1

REM Wait for server to start
timeout /t 5 /nobreak >nul

REM Check if server is running
curl -s http://localhost:8080/health >nul 2>&1
if %errorlevel% neq 0 (
    exit /b 1
)

REM Auto open browser
start "" "http://localhost:8080"
