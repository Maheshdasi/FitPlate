@echo off
title FitPlate - starting
cd /d "%~dp0"

if not exist "backend\venv\Scripts\python.exe" (
  echo Run setup-windows.bat first.
  pause
  exit /b 1
)

rem Backend API in its own window (keep it open)
start "FitPlate BACKEND - keep this window open" /D "%~dp0backend" cmd /k venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

rem Frontend website in its own window (keep it open)
start "FitPlate FRONTEND - keep this window open" /D "%~dp0frontend" cmd /k npm run dev

echo Starting the backend and the website... the browser will open in a few seconds.
timeout /t 8 /nobreak >nul
start "" http://localhost:5173
start "" http://localhost:8000/docs
echo.
echo The app is running at http://localhost:5173
echo API documentation is at http://localhost:8000/docs
echo To stop the app, close the two black windows titled "FitPlate BACKEND" and "FitPlate FRONTEND".
timeout /t 10 >nul
