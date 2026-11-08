@echo off
setlocal EnableExtensions
title FitPlate - one-time setup
cd /d "%~dp0"

echo ============================================================
echo   FitPlate (AI Fitness ^& Nutrition Platform) - one-time setup
echo ============================================================
echo.

rem ---------- 1. Check Python ----------
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (where python >nul 2>nul && set "PY=python")
if not defined PY (
  echo [X] Python was not found. Install Python 3.12 from https://www.python.org/downloads/
  echo     and tick "Add python.exe to PATH" during installation. Then run this file again.
  goto :fail
)
echo [OK] Python found:
%PY% --version

rem ---------- 2. Check Node.js ----------
where npm >nul 2>nul
if errorlevel 1 (
  echo [X] Node.js was not found. Install the LTS version from https://nodejs.org/ and run this file again.
  goto :fail
)
echo [OK] Node.js found:
call node --version

rem ---------- 3. Find PostgreSQL ----------
set "PSQL="
for /f "delims=" %%i in ('where psql 2^>nul') do if not defined PSQL set "PSQL=%%i"
if not defined PSQL (
  for /d %%d in ("C:\Program Files\PostgreSQL\*") do if exist "%%d\bin\psql.exe" set "PSQL=%%d\bin\psql.exe"
)
if not defined PSQL (
  echo [X] PostgreSQL was not found. Install it from https://www.postgresql.org/download/windows/
  echo     Remember the password you choose for the "postgres" user. Then run this file again.
  goto :fail
)
echo [OK] PostgreSQL found: "%PSQL%"
echo.

rem ---------- 4. Create the database user and database ----------
echo Creating the database. Type the password you chose for the "postgres" user
echo when you installed PostgreSQL (the text will be visible), then press Enter.
set /p "PGPASSWORD=postgres password: "
"%PSQL%" -w -U postgres -h localhost -c "CREATE USER fitness WITH PASSWORD 'fitness' CREATEDB;" 2>nul
"%PSQL%" -w -U postgres -h localhost -c "CREATE DATABASE fitness_db OWNER fitness;" 2>nul
"%PSQL%" -w -U postgres -h localhost -c "CREATE DATABASE fitness_test OWNER fitness;" 2>nul
set "PGPASSWORD=fitness"
"%PSQL%" -w -U fitness -h localhost -d fitness_db -c "SELECT 1;" >nul 2>nul
if errorlevel 1 (
  echo [X] Could not connect to the database. The postgres password may be wrong,
  echo     or the PostgreSQL service is not running. Run this file again and retype the password.
  goto :fail
)
set "PGPASSWORD="
echo [OK] Database fitness_db is ready.
echo.

rem ---------- 5. Backend ----------
echo Setting up the backend (this can take a few minutes the first time)...
cd /d "%~dp0backend"
if not exist venv (
  %PY% -m venv venv
  if errorlevel 1 goto :fail
)
venv\Scripts\python.exe -m pip install --upgrade pip >nul
venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
  echo [X] Installing Python packages failed. Check your internet connection and try again.
  goto :fail
)
if not exist .env (
  copy .env.example .env >nul
  venv\Scripts\python.exe -c "import secrets,pathlib; p=pathlib.Path('.env'); p.write_text(p.read_text().replace('change-me-to-a-long-random-string', secrets.token_hex(32)))"
  echo [OK] Created backend\.env with a new secret key.
)
echo Loading foods, meals, exercises and the demo account...
venv\Scripts\python.exe seed.py
if errorlevel 1 goto :fail
echo.

rem ---------- 6. Frontend ----------
echo Setting up the frontend...
cd /d "%~dp0frontend"
if not exist .env copy .env.example .env >nul
call npm install
if errorlevel 1 (
  echo [X] npm install failed. Check your internet connection and try again.
  goto :fail
)

echo.
echo ============================================================
echo   Setup complete. Double-click start-windows.bat to run the app.
echo   Demo login:  demo@fitness.app  /  Demo@1234
echo ============================================================
pause
exit /b 0

:fail
echo.
echo Setup stopped. Read the message above, fix it, then run setup-windows.bat again.
pause
exit /b 1
