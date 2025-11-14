@echo off
REM Frontend Startup Script for Resume AI Project
REM This script starts the React development server

echo.
echo ====================================
echo Resume AI Frontend - Startup Script
echo ====================================
echo.

echo [1/2] Checking Node.js installation...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js not found in PATH
    echo Please install Node.js from https://nodejs.org/
    exit /b 1
)
echo OK: Node.js is available

echo.
echo [2/2] Starting React development server...
echo.
echo Frontend will start on: http://localhost:3000
echo Make sure backend is running on: http://localhost:8000
echo.

npm start
