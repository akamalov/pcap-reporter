#!/bin/bash

# Frontend Diagnostics Script
# Provides detailed frontend health information and troubleshooting

set -e

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get Docker Compose command
get_compose_cmd() {
    echo "docker-compose -f $COMPOSE_FILE"
}

# Log function with colors
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
        "DEBUG")
            echo -e "${BLUE}[DEBUG]${NC} $message"
            ;;
        *)
            echo -e "${CYAN}[$level]${NC} $message"
            ;;
    esac
}

# Check frontend container status
check_container_status() {
    local compose_cmd=$(get_compose_cmd)
    
    echo -e "${CYAN}===========================================${NC}"
    echo -e "${CYAN}Frontend Container Status${NC}"
    echo -e "${CYAN}===========================================${NC}"
    
    # Check if container exists
    local container_info=$($compose_cmd ps frontend 2>/dev/null || echo "")
    
    if [[ -z "$container_info" ]]; then
        log "ERROR" "Frontend container not found"
        return 1
    fi
    
    # Display container information
    echo -e "${BLUE}Container Information:${NC}"
    $compose_cmd ps frontend
    echo
    
    # Check container health
    local health_status=$(docker inspect pcap-reporter-frontend --format='{{.State.Health.Status}}' 2>/dev/null || echo "No health check")
    echo -e "${BLUE}Health Status:${NC} $health_status"
    
    # Check container logs for errors
    local error_count=$($compose_cmd logs frontend 2>/dev/null | grep -i "error" | wc -l)
    local warn_count=$($compose_cmd logs frontend 2>/dev/null | grep -i "warn" | wc -l)
    
    echo -e "${BLUE}Log Summary:${NC}"
    echo -e "  Errors: $error_count"
    echo -e "  Warnings: $warn_count"
    echo
}

# Check frontend logs for specific issues
check_frontend_logs() {
    local compose_cmd=$(get_compose_cmd)
    
    echo -e "${CYAN}===========================================${NC}"
    echo -e "${CYAN}Frontend Log Analysis${NC}"
    echo -e "${CYAN}===========================================${NC}"
    
    local logs=$($compose_cmd logs --tail=100 frontend 2>/dev/null || echo "No logs available")
    
    if [[ -z "$logs" ]]; then
        log "WARN" "No frontend logs available"
        return 1
    fi
    
    # Check for common issues
    local issues=()
    
    if echo "$logs" | grep -qi "ENOENT.*node_modules"; then
        issues+=("Missing node_modules")
    fi
    
    if echo "$logs" | grep -qi "EADDRINUSE.*3000"; then
        issues+=("Port 3000 in use")
    fi
    
    if echo "$logs" | grep -qi "permission denied"; then
        issues+=("Permission denied")
    fi
    
    if echo "$logs" | grep -qi "npm ERR"; then
        issues+=("NPM errors")
    fi
    
    if echo "$logs" | grep -qi "Module not found"; then
        issues+=("Module not found")
    fi
    
    if echo "$logs" | grep -qi "ECONNREFUSED.*8000"; then
        issues+=("Backend connection refused")
    fi
    
    if echo "$logs" | grep -qi "failed to compile"; then
        issues+=("Compilation failed")
    fi
    
    if echo "$logs" | grep -qi "webpack"; then
        issues+=("Webpack issues")
    fi
    
    if [[ ${#issues[@]} -gt 0 ]]; then
        echo -e "${RED}Issues Detected:${NC}"
        for issue in "${issues[@]}"; do
            echo -e "  ${YELLOW}●${NC} $issue"
        done
        echo
    else
        log "INFO" "No common issues detected in logs"
    fi
    
    # Show recent error messages
    local recent_errors=$(echo "$logs" | grep -i "error" | tail -5)
    if [[ -n "$recent_errors" ]]; then
        echo -e "${RED}Recent Error Messages:${NC}"
        echo "$recent_errors"
        echo
    fi
}

# Check network connectivity
check_network_connectivity() {
    local compose_cmd=$(get_compose_cmd)
    
    echo -e "${CYAN}===========================================${NC}"
    echo -e "${CYAN}Network Connectivity${NC}"
    echo -e "${CYAN}===========================================${NC}"
    
    # Check if frontend can reach backend
    local backend_reachable=$($compose_cmd exec -T frontend curl -s http://api:8000/health 2>/dev/null || echo "failed")
    
    if [[ "$backend_reachable" == "failed" ]]; then
        log "ERROR" "Frontend cannot reach backend API"
    else
        log "INFO" "Frontend can reach backend API"
    fi
    
    # Check external connectivity
    local external_reachable=$($compose_cmd exec -T frontend curl -s https://www.google.com 2>/dev/null || echo "failed")
    
    if [[ "$external_reachable" == "failed" ]]; then
        log "WARN" "Frontend cannot reach external networks"
    else
        log "INFO" "Frontend has external network access"
    fi
    
    # Check port availability
    local port_3000_available=$(netstat -tlnp 2>/dev/null | grep ":3000" || echo "")
    
    if [[ -n "$port_3000_available" ]]; then
        echo -e "${BLUE}Port 3000 Usage:${NC}"
        echo "$port_3000_available"
    else
        log "INFO" "Port 3000 is available"
    fi
    echo
}

# Check frontend dependencies
check_frontend_dependencies() {
    local compose_cmd=$(get_compose_cmd)
    
    echo -e "${CYAN}===========================================${NC}"
    echo -e "${CYAN}Frontend Dependencies${NC}"
    echo -e "${CYAN}===========================================${NC}"
    
    # Check if node_modules exists
    local node_modules_exists=$($compose_cmd exec -T frontend test -d node_modules 2>/dev/null && echo "exists" || echo "missing")
    
    if [[ "$node_modules_exists" == "missing" ]]; then
        log "ERROR" "node_modules directory is missing"
    else
        log "INFO" "node_modules directory exists"
        
        # Check node_modules size
        local node_modules_size=$($compose_cmd exec -T frontend du -sh node_modules 2>/dev/null | cut -f1 || echo "unknown")
        echo -e "${BLUE}node_modules size:${NC} $node_modules_size"
    fi
    
    # Check package.json
    local package_json_exists=$($compose_cmd exec -T frontend test -f package.json 2>/dev/null && echo "exists" || echo "missing")
    
    if [[ "$package_json_exists" == "missing" ]]; then
        log "ERROR" "package.json is missing"
    else
        log "INFO" "package.json exists"
    fi
    
    # Check package-lock.json
    local package_lock_exists=$($compose_cmd exec -T frontend test -f package-lock.json 2>/dev/null && echo "exists" || echo "missing")
    
    if [[ "$package_lock_exists" == "missing" ]]; then
        log "WARN" "package-lock.json is missing"
    else
        log "INFO" "package-lock.json exists"
    fi
    
    # Check Node.js version
    local node_version=$($compose_cmd exec -T frontend node --version 2>/dev/null || echo "unknown")
    echo -e "${BLUE}Node.js version:${NC} $node_version"
    
    # Check npm version
    local npm_version=$($compose_cmd exec -T frontend npm --version 2>/dev/null || echo "unknown")
    echo -e "${BLUE}npm version:${NC} $npm_version"
    echo
}

# Check system resources
check_system_resources() {
    echo -e "${CYAN}===========================================${NC}"
    echo -e "${CYAN}System Resources${NC}"
    echo -e "${CYAN}===========================================${NC}"
    
    # Check disk space
    local disk_usage=$(df -h "$PROJECT_DIR" | tail -1 | awk '{print $5}' | tr -d '%')
    echo -e "${BLUE}Disk usage:${NC} ${disk_usage}%"
    
    if [[ $disk_usage -gt 90 ]]; then
        log "ERROR" "Disk space is critically low"
    elif [[ $disk_usage -gt 80 ]]; then
        log "WARN" "Disk space is running low"
    else
        log "INFO" "Disk space is adequate"
    fi
    
    # Check memory usage
    local memory_usage=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
    echo -e "${BLUE}Memory usage:${NC} ${memory_usage}%"
    
    if [[ $memory_usage -gt 90 ]]; then
        log "ERROR" "Memory usage is critically high"
    elif [[ $memory_usage -gt 80 ]]; then
        log "WARN" "Memory usage is high"
    else
        log "INFO" "Memory usage is normal"
    fi
    
    # Check Docker stats for frontend container
    local docker_stats=$(docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep frontend || echo "")
    
    if [[ -n "$docker_stats" ]]; then
        echo -e "${BLUE}Container resources:${NC}"
        echo "$docker_stats"
    fi
    echo
}

# Generate remediation suggestions
generate_remediation_suggestions() {
    echo -e "${CYAN}===========================================${NC}"
    echo -e "${CYAN}Remediation Suggestions${NC}"
    echo -e "${CYAN}===========================================${NC}"
    
    echo -e "${YELLOW}Common Frontend Issues and Solutions:${NC}"
    echo
    echo -e "${BLUE}1. Container not running:${NC}"
    echo "   ./scripts/pcap-reporter.sh start"
    echo
    echo -e "${BLUE}2. Missing dependencies:${NC}"
    echo "   docker-compose exec frontend npm install"
    echo "   docker-compose restart frontend"
    echo
    echo -e "${BLUE}3. Port conflicts:${NC}"
    echo "   lsof -ti:3000 | xargs kill -9"
    echo "   docker-compose restart frontend"
    echo
    echo -e "${BLUE}4. Permission issues:${NC}"
    echo "   sudo chown -R \$USER:\$USER ./frontend"
    echo "   docker-compose restart frontend"
    echo
    echo -e "${BLUE}5. Clear cache and rebuild:${NC}"
    echo "   docker-compose stop frontend"
    echo "   docker-compose rm -f frontend"
    echo "   docker-compose build --no-cache frontend"
    echo "   docker-compose up -d frontend"
    echo
    echo -e "${BLUE}6. Full remediation:${NC}"
    echo "   ./scripts/pcap-reporter.sh fix-frontend"
    echo
}

# Main function
main() {
    echo -e "${PURPLE}PCAP Reporter - Frontend Diagnostics${NC}"
    echo -e "${PURPLE}====================================${NC}"
    echo
    
    # Check if Docker is available
    if ! command -v docker &> /dev/null; then
        log "ERROR" "Docker is not installed"
        exit 1
    fi
    
    # Check if Docker Compose is available
    if ! command -v docker-compose &> /dev/null; then
        log "ERROR" "Docker Compose is not installed"
        exit 1
    fi
    
    # Run diagnostics
    check_container_status
    check_frontend_logs
    check_network_connectivity
    check_frontend_dependencies
    check_system_resources
    generate_remediation_suggestions
    
    echo -e "${PURPLE}Diagnostics complete!${NC}"
    echo -e "${PURPLE}For automated fixes, run: ./scripts/pcap-reporter.sh fix-frontend${NC}"
}

# Run main function
main "$@"