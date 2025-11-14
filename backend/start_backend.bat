@echo off
REM Backend Startup Script for Resume AI Project
REM This script initializes and starts the FastAPI backend server

echo.
echo ====================================
echo Resume AI Backend - Startup Script
echo ====================================
echo.

REM Check if .env file exists
if not exist .env (
    echo ERROR: .env file not found!
    echo Please create a .env file with required environment variables:
    echo   - DATABASE_URL
    echo   - SECRET_KEY
    echo   - ALGORITHM
    echo   - ACCESS_TOKEN_EXPIRE_MINUTES
    echo.
    exit /b 1
)

echo [1/3] Checking Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found in PATH
    exit /b 1
)
echo OK: Python is available

echo.
echo [2/3] Installing/Updating dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    exit /b 1
)
echo OK: Dependencies installed

echo.
echo [3/3] Starting FastAPI server...
echo.
echo Backend will start on: http://0.0.0.0:8000
echo API Documentation: http://localhost:8000/docs
echo.

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
