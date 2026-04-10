@echo off
setlocal
title Report Generator - Launcher
cd /d "%~dp0"

echo ============================================
echo   Report Generator - Starting services
echo ============================================

REM --- 1. Start PostgreSQL (Windows service) ---
echo.
echo [1/3] Starting PostgreSQL service...
net start postgresql-x64-18 1>nul 2>nul
echo [OK]   PostgreSQL running.

REM --- 2. Start Backend (FastAPI) ---
echo.
echo [2/3] Starting Backend on http://127.0.0.1:8000 ...
start "Backend - FastAPI" cmd /k "conda activate rgenerator && python -m backend.api"

REM --- 3. Start Frontend (Vite/React) ---
echo.
echo [3/3] Starting Frontend on http://localhost:5173 ...
start "Frontend - Vite" cmd /k "cd frontend && npm run dev"

echo.
echo ============================================
echo   All services launched.
echo   - PostgreSQL : WSL (Ubuntu)
echo   - Backend    : http://127.0.0.1:8000
echo   - Frontend   : http://localhost:5173
echo ============================================
echo.
echo Close this window or press any key to exit the launcher.
pause >nul
