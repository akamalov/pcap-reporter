@echo off
REM PCAP Reporter - Windows Environment Management Script
REM Usage: pcap-reporter.bat [start|stop|restart|status|logs] [options]

setlocal enabledelayedexpansion

REM Script configuration
set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..
set COMPOSE_FILE=%PROJECT_DIR%\docker-compose.yml
set COMPOSE_PROD_FILE=%PROJECT_DIR%\docker-compose.prod.yml
set LOG_DIR=%PROJECT_DIR%\logs

REM Colors (limited support in Windows)
set RED=[31m
set GREEN=[32m
set YELLOW=[33m
set BLUE=[34m
set CYAN=[36m
set NC=[0m

REM Default values
set COMMAND=
set ENV_TYPE=dev
set CLEANUP=false
set SERVICE_NAME=
set FOLLOW=false

REM Parse command line arguments
:parse_args
if "%~1"=="" goto end_parse
if "%~1"=="start" (
    set COMMAND=start
    shift
    goto parse_args
)
if "%~1"=="stop" (
    set COMMAND=stop
    shift
    goto parse_args
)
if "%~1"=="restart" (
    set COMMAND=restart
    shift
    goto parse_args
)
if "%~1"=="status" (
    set COMMAND=status
    shift
    goto parse_args
)
if "%~1"=="-s" (
    set COMMAND=status
    shift
    goto parse_args
)
if "%~1"=="--status" (
    set COMMAND=status
    shift
    goto parse_args
)
if "%~1"=="logs" (
    set COMMAND=logs
    shift
    goto parse_args
)
if "%~1"=="-l" (
    set COMMAND=logs
    shift
    goto parse_args
)
if "%~1"=="--logs" (
    set COMMAND=logs
    shift
    goto parse_args
)
if "%~1"=="--prod" (
    set ENV_TYPE=prod
    shift
    goto parse_args
)
if "%~1"=="--cleanup" (
    set CLEANUP=true
    shift
    goto parse_args
)
if "%~1"=="--service" (
    set SERVICE_NAME=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--follow" (
    set FOLLOW=true
    shift
    goto parse_args
)
if "%~1"=="help" (
    set COMMAND=help
    shift
    goto parse_args
)
if "%~1"=="-h" (
    set COMMAND=help
    shift
    goto parse_args
)
if "%~1"=="--help" (
    set COMMAND=help
    shift
    goto parse_args
)
echo Unknown option: %~1
goto show_help

:end_parse

REM Set default command if none provided
if "%COMMAND%"=="" set COMMAND=help

REM Check dependencies
call :check_dependencies
if errorlevel 1 exit /b 1

REM Execute command
if "%COMMAND%"=="start" goto start_services
if "%COMMAND%"=="stop" goto stop_services
if "%COMMAND%"=="restart" goto restart_services
if "%COMMAND%"=="status" goto get_service_status
if "%COMMAND%"=="logs" goto show_service_logs
if "%COMMAND%"=="help" goto show_help

echo Unknown command: %COMMAND%
goto show_help

:check_dependencies
echo [INFO] Checking dependencies...

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not installed. Please install Docker Desktop first.
    exit /b 1
)

REM Check if Docker Compose is installed
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Compose is not installed. Please install Docker Compose first.
    exit /b 1
)

REM Check if Docker daemon is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker daemon is not running. Please start Docker Desktop first.
    exit /b 1
)

echo [INFO] Dependencies check passed
goto :eof

:start_services
echo [INFO] Starting PCAP Reporter services (%ENV_TYPE% environment)...

REM Create necessary directories
if not exist "%PROJECT_DIR%\uploads" mkdir "%PROJECT_DIR%\uploads"
if not exist "%PROJECT_DIR%\logs" mkdir "%PROJECT_DIR%\logs"
if not exist "%PROJECT_DIR%\mongodb\data" mkdir "%PROJECT_DIR%\mongodb\data"

REM Start services
if "%ENV_TYPE%"=="prod" (
    docker-compose -f "%COMPOSE_PROD_FILE%" up -d --build
) else (
    docker-compose -f "%COMPOSE_FILE%" up -d --build
)

echo [INFO] Waiting for services to be ready...
timeout /t 10 /nobreak >nul

echo [INFO] PCAP Reporter services started successfully!
echo [INFO] Web interface: http://localhost:3000
echo [INFO] API documentation: http://localhost:8000/docs
echo [INFO] Health check: http://localhost:8000/api/health
goto :eof

:stop_services
echo [INFO] Stopping PCAP Reporter services (%ENV_TYPE% environment)...

if "%ENV_TYPE%"=="prod" (
    docker-compose -f "%COMPOSE_PROD_FILE%" down
) else (
    docker-compose -f "%COMPOSE_FILE%" down
)

if "%CLEANUP%"=="true" (
    echo [INFO] Performing cleanup...
    if "%ENV_TYPE%"=="prod" (
        docker-compose -f "%COMPOSE_PROD_FILE%" down -v
    ) else (
        docker-compose -f "%COMPOSE_FILE%" down -v
    )
    docker container prune -f
    docker network prune -f
    echo [INFO] Cleanup completed
)

echo [INFO] PCAP Reporter services stopped
goto :eof

:restart_services
echo [INFO] Restarting PCAP Reporter services...
call :stop_services
timeout /t 5 /nobreak >nul
call :start_services
goto :eof

:get_service_status
echo PCAP Reporter Service Status
echo ==============================

if "%ENV_TYPE%"=="prod" (
    if not exist "%COMPOSE_PROD_FILE%" (
        echo [ERROR] Production compose file not found: %COMPOSE_PROD_FILE%
        goto :eof
    )
    docker-compose -f "%COMPOSE_PROD_FILE%" ps
) else (
    if not exist "%COMPOSE_FILE%" (
        echo [ERROR] Development compose file not found: %COMPOSE_FILE%
        goto :eof
    )
    docker-compose -f "%COMPOSE_FILE%" ps
)

echo.
echo Service Health:
echo   Frontend: http://localhost:3000
echo   Backend API: http://localhost:8000/api/health
echo   API Docs: http://localhost:8000/docs
goto :eof

:show_service_logs
if "%SERVICE_NAME%"=="" (
    echo Available services:
    echo   nginx - Reverse proxy
    echo   frontend - Web interface
    echo   backend - API server
    echo   celery-worker - Task processor
    echo   mongodb - Database
    echo   redis - Cache and queue
    goto :eof
)

echo [INFO] Showing logs for service: %SERVICE_NAME%

if "%ENV_TYPE%"=="prod" (
    if "%FOLLOW%"=="true" (
        docker-compose -f "%COMPOSE_PROD_FILE%" logs -f "%SERVICE_NAME%"
    ) else (
        docker-compose -f "%COMPOSE_PROD_FILE%" logs --tail=100 "%SERVICE_NAME%"
    )
) else (
    if "%FOLLOW%"=="true" (
        docker-compose -f "%COMPOSE_FILE%" logs -f "%SERVICE_NAME%"
    ) else (
        docker-compose -f "%COMPOSE_FILE%" logs --tail=100 "%SERVICE_NAME%"
    )
)
goto :eof

:show_help
echo PCAP Reporter Environment Management Script
echo.
echo Usage:
echo     pcap-reporter.bat ^<command^> [options]
echo.
echo Commands:
echo     start       Start all services
echo     stop        Stop all services
echo     restart     Restart all services
echo     status      Show service status
echo     logs        Show service logs
echo     help        Show this help message
echo.
echo Options:
echo     --prod                Use production environment
echo     --cleanup             Clean up volumes and images when stopping
echo     --service ^<name^>      Target specific service (for logs)
echo     --follow              Follow logs in real-time
echo     -s, --status          Show service status
echo     -l, --logs            Show service logs
echo.
echo Examples:
echo     pcap-reporter.bat start                    # Start development environment
echo     pcap-reporter.bat start --prod             # Start production environment
echo     pcap-reporter.bat stop --cleanup           # Stop and cleanup
echo     pcap-reporter.bat status                   # Show service status
echo     pcap-reporter.bat logs --service backend   # Show backend logs
echo.
echo Available Services:
echo     nginx - Reverse proxy
echo     frontend - Web interface
echo     backend - API server
echo     celery-worker - Task processor
echo     mongodb - Database
echo     redis - Cache and queue
echo.
echo Service URLs:
echo     Frontend: http://localhost:3000
echo     Backend API: http://localhost:8000
echo     API Docs: http://localhost:8000/docs
echo     Health Check: http://localhost:8000/api/health
goto :eof