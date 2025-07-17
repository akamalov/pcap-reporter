#!/bin/bash

# Frontend Build Script with Static File Fix
# This script builds the frontend and ensures static files are properly copied

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

# Check if we're in the right directory
if [ ! -f "$FRONTEND_DIR/package.json" ]; then
    log "ERROR" "Frontend directory not found: $FRONTEND_DIR"
    exit 1
fi

log "INFO" "Building frontend application..."

# Navigate to frontend directory
cd "$FRONTEND_DIR"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    log "INFO" "Installing dependencies..."
    npm ci
fi

# Build the application
log "INFO" "Running Next.js build..."
npm run build

# Check if build was successful
if [ ! -d ".next/standalone" ]; then
    log "ERROR" "Build failed - standalone directory not found"
    exit 1
fi

# Copy static files to standalone build
log "INFO" "Copying static files to standalone build..."
cp -r .next/static .next/standalone/.next/

# Copy public folder if it exists
if [ -d "public" ]; then
    log "INFO" "Copying public folder to standalone build..."
    cp -r public .next/standalone/
else
    log "WARN" "No public folder found - skipping"
fi

# Create a simple health check
log "INFO" "Creating health check..."
cat > .next/standalone/health-check.js << 'EOF'
const http = require('http');

const options = {
  hostname: 'localhost',
  port: 3000,
  path: '/health',
  method: 'GET',
  timeout: 5000
};

const req = http.request(options, (res) => {
  if (res.statusCode === 200) {
    console.log('✅ Frontend is healthy');
    process.exit(0);
  } else {
    console.log('❌ Frontend health check failed');
    process.exit(1);
  }
});

req.on('error', (err) => {
  console.log('❌ Frontend health check error:', err.message);
  process.exit(1);
});

req.on('timeout', () => {
  console.log('❌ Frontend health check timeout');
  req.abort();
  process.exit(1);
});

req.end();
EOF

log "INFO" "Build completed successfully!"
log "INFO" "To start the frontend server: node .next/standalone/server.js"
log "INFO" "To check health: node .next/standalone/health-check.js"