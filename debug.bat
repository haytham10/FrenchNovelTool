@echo off
setlocal enabledelayedexpansion

echo =========================================
echo   French Novel Tool Debug Environment
echo =========================================
echo.

if "%1" == "backend" (
  echo Starting backend debugger...
  echo Connect your IDE to port 5678
  
  rem Set environment variable to enable debugger
  set ENABLE_DEBUGGER=True
  
  rem Start backend with debugger
  docker-compose -f docker-compose.dev.yml stop backend
  docker-compose -f docker-compose.dev.yml up -d backend
  
  echo Backend debugger is ready!
  echo Attach your debugger to localhost:5678
  
  rem Show logs
  docker-compose -f docker-compose.dev.yml logs -f backend

) else if "%1" == "frontend" (
  echo Starting frontend debugger...
  echo Connect your IDE to port 9229
  
  rem Start frontend with debugger
  docker-compose -f docker-compose.dev.yml exec frontend node --inspect=0.0.0.0:9229 node_modules/.bin/next dev -p 3000 --hostname 0.0.0.0
  
  echo Frontend debugger is ready!
  echo Attach your debugger to localhost:9229

) else (
  echo Error: Please specify which component to debug:
  echo Usage: debug.bat [backend^|frontend]
  exit /b 1
)