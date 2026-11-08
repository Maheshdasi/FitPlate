@echo off
rem The project folder is two levels above this script (scripts\windows)
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI\"
title FitPlate - automated tests
cd /d "%ROOT%backend"
echo Running the 57 automated backend tests (uses a separate test database)...
echo.
venv\Scripts\python.exe -m pytest -v
echo.
pause
