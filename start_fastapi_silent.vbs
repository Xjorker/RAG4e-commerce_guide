' 后台启动FastAPI - 真正脱离任何终端/VBS独立运行
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd.exe /c cd /d d:\RAG导购 && python start_fastapi_9000.py > d:\RAG导购\fastapi_log.txt 2>&1", 0, False
