@echo off
title NORTHSTAR - AI Agent Long-Horizon Goal Tracking System
color 0B
echo =======================================================================
echo          NORTHSTAR - AI AGENT LONG-HORIZON GOAL TRACKING SYSTEM
echo =======================================================================
echo.
echo [1/2] Launching Northstar FastAPI Backend on http://127.0.0.1:8000 ...
start "Northstar Backend (FastAPI)" cmd /k "python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload"

echo [2/2] Launching Northstar prebuilt Frontend on http://localhost:5173 ...
cd frontend
start "Northstar Frontend (Vite Preview)" cmd /k "npm.cmd run preview -- --host 127.0.0.1 --port 5173"

echo.
echo Waiting 3 seconds for services to initialize...
timeout /t 3 >nul

echo Opening Northstar Mission Control in default browser...
start http://localhost:5173

echo.
echo =======================================================================
echo Northstar is running!
echo - Frontend: http://localhost:5173
echo - Backend:  http://127.0.0.1:8000
echo - Swagger:  http://127.0.0.1:8000/docs
echo =======================================================================
pause
