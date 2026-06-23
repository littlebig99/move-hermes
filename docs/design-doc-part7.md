## 8. U盘自启动机制

### 8.1 start.bat

```batch
@echo off
chcp 65001 >nul
set SCRIPT_DIR=%~dp0
set DATA_DIR=%SCRIPT_DIR%data
set LOG_FILE=%DATA_DIR%service.log

echo ========================================
echo   Move Hermes - 智能订单管理系统
echo ========================================
echo.

REM 检查Python是否在PATH中
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] 未检测到Python，正在安装...
    echo [!] 请从 %SCRIPT_DIR%installer\ 目录运行安装程序
    pause
    exit /b 1
)

REM 检查数据目录
if not exist "%DATA_DIR%" mkdir "%DATA_DIR%"

REM 检查API配置
if not exist "%DATA_DIR%api_config.json" (
    echo [*] 首次启动，正在打开配置页面...
    start "" "%SCRIPT_DIR%frontend\config.html"
) else (
    echo [*] 加载已有配置...
)

REM 启动服务
echo [*] 正在启动服务...
cd /d "%SCRIPT_DIR%backend"
python main.py >"%LOG_FILE%" 2>&1

REM 自动打开浏览器
timeout /t 3 /nobreak >nul
start "" "http://localhost:8080"

echo.
echo ========================================
echo   服务已启动，浏览器应已自动打开
echo   端口: 8080
echo   数据目录: %DATA_DIR%
echo ========================================
echo.
echo 提示: 关闭此窗口将停止服务
echo 安全弹出U盘前请先关闭服务
pause
```

### 8.2 服务生命周期

```
U盘插入 → Windows自动运行autorun.inf → 执行start.bat
    ↓
检测Python → 安装/跳过
    ↓
检测API配置 → 首次则打开配置页
    ↓
启动FastAPI服务 (端口8080)
    ↓
等待用户操作
    ↓
关闭窗口/手动停止 → 清理进程 → 安全弹出
```
