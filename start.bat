@echo off
set SCRIPT_DIR=%~dp0
set DATA_DIR=%SCRIPT_DIR%data
set LOG_FILE=%DATA_DIR%service.log

REM ==================== 参数处理 ====================
set MODE=hidden
for %%a in (%*) do (
    if "%%a"=="--tray" set MODE=tray
    if "%%a"=="--normal" set MODE=normal
)

REM Check if Python is in PATH
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python not found in PATH
    echo [!] Please install Python 3.11+ or add Python to PATH
    pause
    exit /b 1
)

REM Check data directory
if not exist "%DATA_DIR%" mkdir "%DATA_DIR%"

REM ==================== 启动模式 ====================
if "%MODE%"=="tray" (
    cd /d "%SCRIPT_DIR%backend"
    python tray_manager.py
    goto :end
)

if "%MODE%"=="normal" (
    echo [*] Starting service...
    cd /d "%SCRIPT_DIR%backend"
    start "Move Hermes Server" python main.py
    
    timeout /t 5 /nobreak >nul
    
    curl -s http://localhost:8080/health >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo [!] Service failed to start!
        echo [!] Check the new window for errors
        pause
        exit /b 1
    )
    
    start "" "http://localhost:8080"
    
    echo.
    echo ========================================
    echo   Service started
    echo   Visit: http://localhost:8080
    echo   Data dir: %DATA_DIR%
    echo ========================================
    echo.
    echo Tip: Close this window to stop the service
    pause
    goto :end
)

REM Hidden mode (default)
cd /d "%SCRIPT_DIR%backend"
start /B python main.py > "%LOG_FILE%" 2>&1

REM Wait for server to start
timeout /t 5 /nobreak >nul

REM Check if server is running
curl -s http://localhost:8080/health >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Service failed to start!
    echo [!] Check log file: %LOG_FILE%
    pause
    exit /b 1
)

REM Auto open browser
start "" "http://localhost:8080"

:end
