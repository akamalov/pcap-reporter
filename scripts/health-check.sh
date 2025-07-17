#!/bin/bash

# PCAP Reporter Health Check Script
# Usage: ./health-check.sh [--detailed] [--json]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DETAILED=false
JSON_OUTPUT=false
TIMEOUT=10

# Service endpoints
FRONTEND_URL="http://localhost:3000"
BACKEND_URL="http://localhost:8000"
HEALTH_URL="http://localhost:8000/api/health"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --detailed)
            DETAILED=true
            shift
            ;;
        --json)
            JSON_OUTPUT=true
            shift
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Health check result structure
declare -A health_results
health_results["overall"]="unknown"
health_results["frontend"]="unknown"
health_results["backend"]="unknown"
health_results["database"]="unknown"
health_results["cache"]="unknown"
health_results["worker"]="unknown"

# Check if service is running
check_service() {
    local service_name="$1"
    local url="$2"
    local endpoint="${3:-/}"
    
    local full_url="$url$endpoint"
    
    if curl -sf --max-time "$TIMEOUT" "$full_url" > /dev/null 2>&1; then
        health_results["$service_name"]="healthy"
        return 0
    else
        health_results["$service_name"]="unhealthy"
        return 1
    fi
}

# Check Docker services
check_docker_services() {
    local compose_file="docker-compose.yml"
    
    if [[ -f "docker-compose.prod.yml" ]]; then
        compose_file="docker-compose.prod.yml"
    fi
    
    # Check if containers are running
    local containers=$(docker-compose -f "$compose_file" ps 2>/dev/null | grep "Up" | wc -l)
    
    if [[ $containers -eq 0 ]]; then
        health_results["overall"]="down"
        return 1
    fi
    
    return 0
}

# Detailed health check
detailed_health_check() {
    echo -e "${BLUE}Detailed Health Check${NC}"
    echo -e "${BLUE}====================${NC}"
    
    # Check Docker services
    if check_docker_services; then
        echo -e "${GREEN}✓${NC} Docker services are running"
    else
        echo -e "${RED}✗${NC} Docker services are not running"
        return 1
    fi
    
    # Check frontend
    echo -n "Frontend service... "
    if check_service "frontend" "$FRONTEND_URL"; then
        echo -e "${GREEN}✓ Healthy${NC}"
    else
        echo -e "${RED}✗ Unhealthy${NC}"
    fi
    
    # Check backend API
    echo -n "Backend API... "
    if check_service "backend" "$BACKEND_URL" "/docs"; then
        echo -e "${GREEN}✓ Healthy${NC}"
    else
        echo -e "${RED}✗ Unhealthy${NC}"
    fi
    
    # Check health endpoint
    echo -n "Health endpoint... "
    if check_service "health" "$HEALTH_URL"; then
        echo -e "${GREEN}✓ Healthy${NC}"
        
        # Get detailed health info
        local health_data=$(curl -sf --max-time "$TIMEOUT" "$HEALTH_URL" 2>/dev/null)
        
        if [[ -n "$health_data" ]]; then
            echo -e "${BLUE}Health Details:${NC}"
            echo "$health_data" | jq '.' 2>/dev/null || echo "$health_data"
        fi
    else
        echo -e "${RED}✗ Unhealthy${NC}"
    fi
    
    # Check database connection
    echo -n "Database connection... "
    if docker-compose exec -T mongodb mongosh --eval "db.adminCommand('ping')" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Healthy${NC}"
        health_results["database"]="healthy"
    else
        echo -e "${RED}✗ Unhealthy${NC}"
        health_results["database"]="unhealthy"
    fi
    
    # Check Redis connection
    echo -n "Redis connection... "
    if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Healthy${NC}"
        health_results["cache"]="healthy"
    else
        echo -e "${RED}✗ Unhealthy${NC}"
        health_results["cache"]="unhealthy"
    fi
    
    # Check Celery workers
    echo -n "Celery workers... "
    local worker_status=$(docker-compose exec -T celery-worker celery -A core.celery_app inspect active 2>/dev/null)
    if [[ -n "$worker_status" ]]; then
        echo -e "${GREEN}✓ Healthy${NC}"
        health_results["worker"]="healthy"
    else
        echo -e "${RED}✗ Unhealthy${NC}"
        health_results["worker"]="unhealthy"
    fi
    
    # Overall health assessment
    local healthy_count=0
    local total_count=0
    
    for service in frontend backend database cache worker; do
        total_count=$((total_count + 1))
        if [[ "${health_results[$service]}" == "healthy" ]]; then
            healthy_count=$((healthy_count + 1))
        fi
    done
    
    local health_percentage=$((healthy_count * 100 / total_count))
    
    echo -e "\n${BLUE}Overall Health: ${health_percentage}%${NC}"
    
    if [[ $health_percentage -ge 80 ]]; then
        health_results["overall"]="healthy"
        echo -e "${GREEN}System Status: Healthy${NC}"
    elif [[ $health_percentage -ge 50 ]]; then
        health_results["overall"]="degraded"
        echo -e "${YELLOW}System Status: Degraded${NC}"
    else
        health_results["overall"]="unhealthy"
        echo -e "${RED}System Status: Unhealthy${NC}"
    fi
}

# Quick health check
quick_health_check() {
    echo -e "${BLUE}Quick Health Check${NC}"
    echo -e "${BLUE}==================${NC}"
    
    # Check main services
    local all_healthy=true
    
    echo -n "Frontend... "
    if check_service "frontend" "$FRONTEND_URL"; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        all_healthy=false
    fi
    
    echo -n "Backend... "
    if check_service "backend" "$HEALTH_URL"; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        all_healthy=false
    fi
    
    if [[ "$all_healthy" == "true" ]]; then
        health_results["overall"]="healthy"
        echo -e "\n${GREEN}System Status: Healthy${NC}"
    else
        health_results["overall"]="unhealthy"
        echo -e "\n${RED}System Status: Unhealthy${NC}"
    fi
}

# JSON output
json_output() {
    cat << EOF
{
    "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "overall_status": "${health_results[overall]}",
    "services": {
        "frontend": "${health_results[frontend]}",
        "backend": "${health_results[backend]}",
        "database": "${health_results[database]}",
        "cache": "${health_results[cache]}",
        "worker": "${health_results[worker]}"
    },
    "endpoints": {
        "frontend": "$FRONTEND_URL",
        "backend": "$BACKEND_URL",
        "health": "$HEALTH_URL"
    }
}
EOF
}

# Main execution
main() {
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        # Run health check silently for JSON output
        if [[ "$DETAILED" == "true" ]]; then
            detailed_health_check > /dev/null 2>&1
        else
            quick_health_check > /dev/null 2>&1
        fi
        json_output
    else
        if [[ "$DETAILED" == "true" ]]; then
            detailed_health_check
        else
            quick_health_check
        fi
    fi
    
    # Exit with appropriate code
    if [[ "${health_results[overall]}" == "healthy" ]]; then
        exit 0
    else
        exit 1
    fi
}

# Run main function
main "$@"