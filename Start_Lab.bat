@echo off
setlocal
cd /d "%~dp0"

:: تشغيل السيرفر في الخلفية
start /min "" "venv\Scripts\python.exe" -m uvicorn lab_app:app --app-dir "%~dp0." --host 127.0.0.1 --port 8000

:: الانتظار الصامت حتى يستجيب السيرفر
:loop
curl -s http://127.0.0.1:8000/login >nul
if %errorlevel% neq 0 (
    timeout /t 1 >nul
    goto loop
)

:: فتح واجهة التطبيق
start chrome --app=http://127.0.0.1:8000/login --window-size=1200,800
exit