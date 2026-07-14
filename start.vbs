' Move Hermes — 隐藏启动脚本
' 双击此文件可完全静默启动服务器，不显示任何窗口
Set WshShell = CreateObject("WScript.Shell")

scriptDir = "E:\project\move-hermes"
dataDir = scriptDir & "\data"

' 确保数据目录存在
Set fso = CreateObject("Scripting.FileSystemObject")
If Not fso.FolderExists(dataDir) Then
    fso.CreateFolder(dataDir)
End If

' 使用 PowerShell 隐藏启动 pythonw.exe
psCmd = "powershell -WindowStyle Hidden -Command ""Start-Process 'pythonw.exe' -ArgumentList '" & scriptDir & "\backend\main.py'" & " -WorkingDirectory '" & scriptDir & "\backend' -NoNewWindow"""
WshShell.Run psCmd, 0, False

' 等待服务器启动
WScript.Sleep 6000

' 自动打开浏览器
WshShell.Run "http://localhost:8080", 1, False
