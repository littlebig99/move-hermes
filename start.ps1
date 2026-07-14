# Move Hermes — 隐藏启动脚本
# 双击此文件可完全静默启动服务器，不显示任何窗口
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $scriptDir "backend"
$dataDir = Join-Path $scriptDir "data"
$logFile = Join-Path $dataDir "service.log"

# 确保数据目录存在
if (-not (Test-Path $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir | Out-Null
}

# 使用 pythonw.exe 启动（无控制台窗口）
Start-Process "pythonw.exe" -ArgumentList "`"$backendDir\main.py`"" -WorkingDirectory $backendDir -WindowStyle Hidden

# 等待服务器启动
Start-Sleep -Seconds 6

# 自动打开浏览器
Start-Process "http://localhost:8080"
