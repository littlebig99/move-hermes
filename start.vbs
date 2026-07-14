' Move Hermes — 隐藏启动脚本
' 双击此文件可完全静默启动服务器，不显示任何窗口
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run chr(34) & "E:\project\move-hermes\start.bat" & chr(34), 0, False
