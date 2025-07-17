#!/bin/bash

# Frontend Startup Script for PCAP Reporter
# This script starts the Next.js frontend server

set -e

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_DIR="$PROJECT_DIR/frontend"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Log function
log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case "$level" in
        "INFO")
            echo -e "${GREEN}[INFO]${NC} $message"
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN]${NC} $message"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $message"
            ;;
        *)
            echo -e "${BLUE}[$level]${NC} $message"
            ;;
    esac
}

# Check if Node.js is installed
check_nodejs() {
    if ! command -v node &> /dev/null; then
        log "ERROR" "Node.js is not installed. Please install Node.js first."
        exit 1
    fi
    
    if ! command -v npm &> /dev/null; then
        log "ERROR" "npm is not installed. Please install npm first."
        exit 1
    fi
    
    log "INFO" "Node.js version: $(node --version)"
    log "INFO" "npm version: $(npm --version)"
}

# Install dependencies
install_dependencies() {
    log "INFO" "Installing frontend dependencies..."
    cd "$FRONTEND_DIR"
    npm ci --only=production
    log "INFO" "Dependencies installed successfully"
}

# Build the frontend
build_frontend() {
    log "INFO" "Building frontend application..."
    "$SCRIPT_DIR/build-frontend.sh"
    log "INFO" "Frontend build completed successfully"
}

# Start the frontend server
start_frontend() {
    log "INFO" "Starting frontend server..."
    cd "$FRONTEND_DIR"
    
    # Check if build exists
    if [ ! -d ".next/standalone" ]; then
        log "WARN" "Frontend build not found. Building now..."
        build_frontend
    fi
    
    # Start the server
    log "INFO" "Frontend server starting on http://localhost:3000"
    node .next/standalone/server.js
}

# Stop the frontend server
stop_frontend() {
    log "INFO" "Stopping frontend server..."
    pkill -f "node .next/standalone/server.js" || true
    log "INFO" "Frontend server stopped"
}

# Check frontend status
check_status() {
    if pgrep -f "node .next/standalone/server.js" > /dev/null; then
        log "INFO" "Frontend server is running"
        
        # Test health endpoint
        if curl -sf http://localhost:3000/health > /dev/null; then
            log "INFO" "Frontend health check: PASSED"
        else
            log "WARN" "Frontend health check: FAILED"
        fi
    else
        log "WARN" "Frontend server is not running"
    fi
}

# Main function
main() {
    local command="${1:-help}"
    
    case "$command" in
        "install")
            check_nodejs
            install_dependencies
            ;;
        "build")
            check_nodejs
            build_frontend
            ;;
        "start")
            check_nodejs
            start_frontend
            ;;
        "stop")
            stop_frontend
            ;;
        "restart")
            stop_frontend
            sleep 2
            start_frontend
            ;;
        "status")
            check_status
            ;;
        "help"|*)
            echo "Usage: $0 {install|build|start|stop|restart|status|help}"
            echo ""
            echo "Commands:"
            echo "  install  - Install frontend dependencies"
            echo "  build    - Build the frontend application"
            echo "  start    - Start the frontend server"
            echo "  stop     - Stop the frontend server"
            echo "  restart  - Restart the frontend server"
            echo "  status   - Check frontend server status"
            echo "  help     - Show this help message"
            ;;
    esac
}

# Run main function
main "$@"