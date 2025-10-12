@echo off
setlocal enabledelayedexpansion

:: Title
title French Novel Tool - Startup Script

:: Color codes
set "GREEN=[32m"
set "RED=[31m"
set "YELLOW=[33m"
set "BLUE=[36m"
set "NC=[0m"

echo.
echo %BLUE%=========================================%NC%
echo %BLUE%  French Novel Tool - Starting...%NC%
echo %BLUE%=========================================%NC%
echo.

:: Check if Python is installed
echo %BLUE%[1/10]%NC% Checking Python installation...
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo %RED%[ERROR] Python is not installed or not in PATH!%NC%
    echo Please install Python 3.10+ and try again.
    pause
    exit /b 1
)
echo %GREEN%✓ Python found%NC%

:: Check if Node.js is installed
echo %BLUE%[2/10]%NC% Checking Node.js installation...
node --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo %RED%[ERROR] Node.js is not installed or not in PATH!%NC%
    echo Please install Node.js 18+ and try again.
    pause
    exit /b 1
)
echo %GREEN%✓ Node.js found%NC%

:: Check if virtual environment exists
echo %BLUE%[3/10]%NC% Checking virtual environment...
IF NOT EXIST ".venv\Scripts\activate.bat" (
    echo %YELLOW%[WARNING] Virtual environment not found. Creating...%NC%
    python -m venv .venv
    IF %ERRORLEVEL% NEQ 0 (
        echo %RED%[ERROR] Failed to create virtual environment!%NC%
        pause
        exit /b 1
    )
    echo %GREEN%✓ Virtual environment created%NC%
) ELSE (
    echo %GREEN%✓ Virtual environment found%NC%
)

:: Activate the virtual environment
echo %BLUE%[4/10]%NC% Activating virtual environment...
call .venv\Scripts\activate
IF %ERRORLEVEL% NEQ 0 (
    echo %RED%[ERROR] Failed to activate virtual environment!%NC%
    pause
    exit /b 1
)
echo %GREEN%✓ Virtual environment activated%NC%

:: Set PYTHONPATH
set "PYTHONPATH=%CD%\backend"

:: Check if backend dependencies are installed
echo %BLUE%[5/10]%NC% Checking backend dependencies...
python -c "import flask_limiter" >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo %YELLOW%[WARNING] Backend dependencies not found. Installing...%NC%
    pip install -r backend\requirements.txt
    IF %ERRORLEVEL% NEQ 0 (
        echo %RED%[ERROR] Failed to install backend dependencies!%NC%
        pause
        exit /b 1
    )
    echo %GREEN%✓ Backend dependencies installed%NC%
) ELSE (
    echo %GREEN%✓ Backend dependencies found%NC%
)

:: Check if frontend dependencies are installed
echo %BLUE%[6/10]%NC% Checking frontend dependencies...
IF NOT EXIST "frontend\node_modules" (
    echo %YELLOW%[WARNING] Frontend dependencies not found. Installing...%NC%
    cd frontend
    call npm install
    IF %ERRORLEVEL% NEQ 0 (
        echo %RED%[ERROR] Failed to install frontend dependencies!%NC%
        cd ..
        pause
        exit /b 1
    )
    cd ..
    echo %GREEN%✓ Frontend dependencies installed%NC%
) ELSE (
    echo %GREEN%✓ Frontend dependencies found%NC%
)

:: Check if .env file exists
echo %BLUE%[7/10]%NC% Checking backend configuration...
IF NOT EXIST "backend\.env" (
    echo %YELLOW%[WARNING] backend\.env not found!%NC%
    IF EXIST "backend\.env.example" (
        echo Creating backend\.env from template...
        copy "backend\.env.example" "backend\.env" >nul
        echo %YELLOW%Please edit backend\.env with your API keys before continuing.%NC%
        pause
    ) ELSE (
        echo %RED%[ERROR] backend\.env.example not found!%NC%
        pause
        exit /b 1
    )
) ELSE (
    echo %GREEN%✓ Backend configuration found%NC%
)

:: Run backend tests
echo %BLUE%[8/10]%NC% Running backend tests...
.venv\Scripts\pytest backend\tests -q
IF %ERRORLEVEL% NEQ 0 (
    echo %RED%[ERROR] Backend tests failed!%NC%
    echo.
    set /p "continue=Continue anyway? (y/N): "
    if /i not "!continue!"=="y" (
        echo Aborting startup.
        pause
        exit /b %ERRORLEVEL%
    )
) ELSE (
    echo %GREEN%✓ Backend tests passed%NC%
)

:: Check if ports are available
echo %BLUE%[9/10]%NC% Checking port availability...
netstat -ano | findstr ":5000" | findstr "LISTENING" >nul
IF %ERRORLEVEL% EQU 0 (
    echo %YELLOW%[WARNING] Port 5000 is already in use!%NC%
    echo Please close the application using it or change the backend port.
    pause
)
netstat -ano | findstr ":3000" | findstr "LISTENING" >nul
IF %ERRORLEVEL% EQU 0 (
    echo %YELLOW%[WARNING] Port 3000 is already in use!%NC%
    echo Please close the application using it or change the frontend port.
    pause
)
echo %GREEN%✓ Ports available%NC%

:: Start the backend server in a new window
echo %BLUE%[10/10]%NC% Starting servers...
echo.
echo %GREEN%Starting backend server on http://localhost:5000...%NC%
start "French Novel Tool - Backend" cmd /k "cd /d %CD% && call .venv\Scripts\activate && set PYTHONPATH=%CD%\backend && python backend\run.py"

:: Wait a moment for backend to start
timeout /t 3 /nobreak >nul

:: Start the frontend server in a new window
echo %GREEN%Starting frontend server on http://localhost:3000...%NC%
start "French Novel Tool - Frontend" cmd /k "cd /d %CD%\frontend && npm run dev"

:: Wait for the servers to start
echo.
echo %YELLOW%Waiting for servers to initialize...%NC%
timeout /t 8 /nobreak >nul

:: Check if backend is responding
echo Checking backend health...
curl -s http://localhost:5000/api/v1/health >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    echo %GREEN%✓ Backend is responding%NC%
) ELSE (
    echo %YELLOW%[WARNING] Backend may not be ready yet%NC%
)

:: Open the browser
echo.
echo %GREEN%Opening browser...%NC%
start http://localhost:3000/

echo.
echo %GREEN%=========================================%NC%
echo %GREEN%  Application is running!%NC%
echo %GREEN%=========================================%NC%
echo.
echo %BLUE%Frontend:%NC% http://localhost:3000
echo %BLUE%Backend API:%NC% http://localhost:5000/api/v1
echo.
echo %YELLOW%Press any key to stop all servers and exit...%NC%
pause >nul

:: Cleanup: Kill the server windows
echo.
echo %YELLOW%Shutting down servers...%NC%
taskkill /FI "WINDOWTITLE eq French Novel Tool - Backend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq French Novel Tool - Frontend*" /T /F >nul 2>&1
echo %GREEN%✓ Servers stopped%NC%
echo.
echo %BLUE%Goodbye!%NC%
timeout /t 2 /nobreak >nul