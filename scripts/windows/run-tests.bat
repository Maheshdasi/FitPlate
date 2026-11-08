@echo off
title FitPlate - automated tests
cd /d "%~dp0backend"
echo Running the 26 automated backend tests (uses a separate test database)...
echo.
venv\Scripts\python.exe -m pytest -v
echo.
pause
