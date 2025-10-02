@echo off
setlocal enabledelayedexpansion

echo ===========================================
echo   French Novel Tool Development Setup
echo ===========================================
echo.

REM Check if .env.dev exists
if not exist .env.dev (
    echo Creating .env.dev file from template...
    copy .env.dev.example .env.dev
    echo Please edit .env.dev with your API keys and settings
    echo Setup paused: Edit .env.dev first, then run this script again
    exit /b 1
)

REM Check Docker is installed and running
docker info > NUL 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: Docker is not running or not installed.
    echo Please install Docker Desktop and start it.
    exit /b 1
)

echo Creating development environment...

REM Build and start containers
echo Building and starting containers...
docker-compose -f docker-compose.dev.yml up -d --build

REM Initialize the database
echo Initializing database...
docker-compose -f docker-compose.dev.yml exec backend flask db upgrade

echo.
echo Development environment is ready!
echo Backend API: http://localhost:5000
echo Frontend: http://localhost:3000
echo Redis: localhost:6379
echo.
echo Use these commands to manage the environment:
echo   Start: docker-compose -f docker-compose.dev.yml up -d
echo   Stop: docker-compose -f docker-compose.dev.yml down
echo   View logs: docker-compose -f docker-compose.dev.yml logs -f
echo   Shell access:
echo     - Backend: docker-compose -f docker-compose.dev.yml exec backend bash
echo     - Frontend: docker-compose -f docker-compose.dev.yml exec frontend sh