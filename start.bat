@echo off
set SCRIPT_DIR=%~dp0
set DATA_DIR=%SCRIPT_DIR%data
set LOG_FILE=%DATA_DIR%service.log

REM ==================== 参数处理 ====================
set MODE=normal
for %%a in (%*) do (
    if "%%a"=="--tray" set MODE=tray
    if "%%a"=="--hidden" set MODE=hidden
)

echo ========================================
echo   Move Hermes - Smart Order Management
echo ========================================
echo.

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

REM Check API config
if not exist "%DATA_DIR%api_config.json" (
    echo [*] First launch, opening config page...
) else (
    echo [*] Loading existing configuration...
)

REM ==================== 启动模式 ====================
if "%MODE%"=="tray" (
    echo [*] Starting in tray mode...
    cd /d "%SCRIPT_DIR%backend"
    python tray_manager.py
    goto :end
)

if "%MODE%"=="hidden" (
    echo [*] Starting in hidden mode...
    cd /d "%SCRIPT_DIR%backend"
    start /B python main.py > "%LOG_FILE%" 2>&1
    
    REM Wait for server to start
    timeout /t 10 /nobreak >nul
    
    REM Check if server is running
    curl -s http://localhost:8080/health >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo [!] Service failed to start!
        echo [!] Check log file: %LOG_FILE%
        pause
        exit /b 1
    )
    
    REM Auto open browser
    start "" "http://localhost:8080"
    
    echo.
    echo ========================================
    echo   Service started (hidden mode)
    echo   Visit: http://localhost:8080
    echo   Log: %LOG_FILE%
    echo ========================================
    echo.
    echo Tip: To stop, run: taskkill /F /IM python.exe
    goto :end
)

REM Normal mode (default)
echo [*] Starting service...
cd /d "%SCRIPT_DIR%backend"
start "Move Hermes Server" python main.py

REM Wait for server to start
timeout /t 5 /nobreak >nul

REM Check if server is running
curl -s http://localhost:8080/health >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [!] Service failed to start!
    echo [!] Check the new window for errors
    pause
    exit /b 1
)

REM Auto open browser
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

:end
echo.
echo Thanks for using Move Hermes!
