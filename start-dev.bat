@echo off
echo Starting CronScheduler in development mode (backend + frontend)...
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo API docs: http://localhost:8000/api/v1/docs
echo.

start "CronScheduler Backend" cmd /k "cd /d %~dp0backend && E:\MC\anaconda3\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
timeout /t 2 /nobreak >nul
start "CronScheduler Frontend" cmd /k "cd /d %~dp0frontend && set PATH=D:\Program Files\nodejs;%PATH% && npm run dev"
