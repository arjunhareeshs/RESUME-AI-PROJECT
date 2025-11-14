@echo off
setlocal
cd /d "%~dp0"

set "BACKEND_DIR=%~dp0backend"
set "FRONTEND_DIR=%~dp0frontend"

where python >nul 2>nul || (echo [Error] Python not found in PATH.& pause & exit /b 1)
where npm >nul 2>nul || (echo [Error] npm not found in PATH.& pause & exit /b 1)

REM Backend
start "Backend" cmd /k "cd /d \"%BACKEND_DIR%\" && python -m pip install -r requirements.txt && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

REM Frontend (ensure deps)
start "Frontend" cmd /k "cd /d \"%FRONTEND_DIR%\" && npm install && set PORT=3000 && npm start"

REM Open frontend after a longer wait
timeout /t 12 /nobreak >nul
start "" "http://localhost:3001"
endlocal
exit /b 0