@echo off
rem The project folder is two levels above this script (scripts\windows)
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI\"
title FitPlate - refresh demo data
cd /d "%ROOT%backend"
echo This regenerates the demo account's 4 months of history so it ends TODAY.
echo Run it on the morning of your project review.
echo (Accounts you created yourself are not touched.)
echo.
venv\Scripts\python.exe seed.py
echo.
echo Done. Demo login:  demo@fitness.app  /  Demo@1234
pause
