@echo off
setlocal
cd /d C:\DIENGIN

echo ==================================================>> C:\DIENGIN\logs\task_scheduler.log
echo [%date% %time%] DIENGIN scheduled run START>> C:\DIENGIN\logs\task_scheduler.log

"C:\DIENGIN\.venv\Scripts\python.exe" "C:\DIENGIN\main.py" >> C:\DIENGIN\logs\task_scheduler.log 2>&1
set EXITCODE=%ERRORLEVEL%

echo [%date% %time%] DIENGIN scheduled run END exit=%EXITCODE%>> C:\DIENGIN\logs\task_scheduler.log
exit /b %EXITCODE%
