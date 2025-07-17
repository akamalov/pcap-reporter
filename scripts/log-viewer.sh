#!/bin/bash

# PCAP Reporter Log Viewer Script
# Usage: ./log-viewer.sh [service] [options]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_DIR/logs"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"
COMPOSE_PROD_FILE="$PROJECT_DIR/docker-compose.prod.yml"

# Default values
SERVICE=""
FOLLOW=false
LINES=100
ENV_TYPE="dev"
FILTER=""
SINCE=""
UNTIL=""
LEVEL=""

# Service definitions
SERVICES=(
    "nginx"
    "frontend"
    "backend"
    "celery-worker"
    "mongodb"
    "redis"
)

# Log level colors
declare -A LOG_COLORS
LOG_COLORS["ERROR"]="$RED"
LOG_COLORS["WARN"]="$YELLOW"
LOG_COLORS["WARNING"]="$YELLOW"
LOG_COLORS["INFO"]="$GREEN"
LOG_COLORS["DEBUG"]="$BLUE"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        nginx|frontend|backend|celery-worker|mongodb|redis)
            SERVICE="$1"
            shift
            ;;
        --follow|-f)
            FOLLOW=true
            shift
            ;;
        --lines|-n)
            LINES="$2"
            shift 2
            ;;
        --prod)
            ENV_TYPE="prod"
            shift
            ;;
        --filter)
            FILTER="$2"
            shift 2
            ;;
        --since)
            SINCE="$2"
            shift 2
            ;;
        --until)
            UNTIL="$2"
            shift 2
            ;;
        --level)
            LEVEL="$2"
            shift 2
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Show help
show_help() {
    cat << EOF
${CYAN}PCAP Reporter Log Viewer${NC}

${YELLOW}Usage:${NC}
    ./log-viewer.sh [service] [options]

${YELLOW}Services:${NC}
    ${GREEN}nginx${NC}         - Reverse proxy logs
    ${GREEN}frontend${NC}      - Web interface logs
    ${GREEN}backend${NC}       - API server logs
    ${GREEN}celery-worker${NC} - Task processor logs
    ${GREEN}mongodb${NC}       - Database logs
    ${GREEN}redis${NC}         - Cache and queue logs

${YELLOW}Options:${NC}
    ${GREEN}--follow, -f${NC}        Follow logs in real-time
    ${GREEN}--lines, -n <num>${NC}   Number of lines to show (default: 100)
    ${GREEN}--prod${NC}              Use production environment
    ${GREEN}--filter <pattern>${NC}  Filter logs by pattern (grep)
    ${GREEN}--since <time>${NC}      Show logs since timestamp (e.g., "2024-01-01T10:00:00")
    ${GREEN}--until <time>${NC}      Show logs until timestamp
    ${GREEN}--level <level>${NC}     Filter by log level (ERROR, WARN, INFO, DEBUG)
    ${GREEN}--help, -h${NC}          Show this help message

${YELLOW}Examples:${NC}
    ./log-viewer.sh backend                    # Show backend logs
    ./log-viewer.sh frontend --follow          # Follow frontend logs
    ./log-viewer.sh backend --filter "error"   # Filter backend logs for errors
    ./log-viewer.sh --level ERROR              # Show all error logs
    ./log-viewer.sh nginx --since "1 hour ago" # Show nginx logs from last hour

${YELLOW}All Services Log:${NC}
    ./log-viewer.sh                            # Show logs from all services
EOF
}

# Get Docker Compose command
get_compose_cmd() {
    if [[ "$ENV_TYPE" == "prod" ]]; then
        echo "docker-compose -f $COMPOSE_PROD_FILE"
    else
        echo "docker-compose -f $COMPOSE_FILE"
    fi
}

# Colorize log output
colorize_logs() {
    while IFS= read -r line; do
        local colored_line="$line"
        
        # Color by log level
        for level in "${!LOG_COLORS[@]}"; do
            if echo "$line" | grep -q "\[$level\]"; then
                colored_line="${LOG_COLORS[$level]}$line${NC}"
                break
            fi
        done
        
        # Color timestamps
        colored_line=$(echo "$colored_line" | sed -E "s/([0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}:[0-9]{2}[.0-9]*[Z]?)/\\${CYAN}\\1\\${NC}/g")
        
        # Color service names
        colored_line=$(echo "$colored_line" | sed -E "s/(nginx|frontend|backend|celery-worker|mongodb|redis)_[0-9]+/\\${PURPLE}\\1\\${NC}/g")
        
        echo -e "$colored_line"
    done
}

# Apply filters
apply_filters() {
    local input_stream="$1"
    
    if [[ -n "$FILTER" ]]; then
        input_stream="$input_stream | grep -i '$FILTER'"
    fi
    
    if [[ -n "$LEVEL" ]]; then
        input_stream="$input_stream | grep -i '\\[$LEVEL\\]'"
    fi
    
    echo "$input_stream"
}

# Show logs for a specific service
show_service_logs() {
    local service="$1"
    local compose_cmd=$(get_compose_cmd)
    
    echo -e "${CYAN}Showing logs for service: $service${NC}"
    echo -e "${CYAN}================================${NC}"
    
    # Build docker-compose logs command
    local logs_cmd="$compose_cmd logs"
    
    if [[ "$FOLLOW" == "true" ]]; then
        logs_cmd="$logs_cmd -f"
    fi
    
    logs_cmd="$logs_cmd --tail=$LINES"
    
    if [[ -n "$SINCE" ]]; then
        logs_cmd="$logs_cmd --since='$SINCE'"
    fi
    
    if [[ -n "$UNTIL" ]]; then
        logs_cmd="$logs_cmd --until='$UNTIL'"
    fi
    
    logs_cmd="$logs_cmd $service"
    
    # Apply filters and colorization
    if [[ -n "$FILTER" || -n "$LEVEL" ]]; then
        local filter_cmd=""
        
        if [[ -n "$FILTER" ]]; then
            filter_cmd="grep -i '$FILTER'"
        fi
        
        if [[ -n "$LEVEL" ]]; then
            if [[ -n "$filter_cmd" ]]; then
                filter_cmd="$filter_cmd | grep -i '\\[$LEVEL\\]'"
            else
                filter_cmd="grep -i '\\[$LEVEL\\]'"
            fi
        fi
        
        eval "$logs_cmd | $filter_cmd | colorize_logs"
    else
        eval "$logs_cmd | colorize_logs"
    fi
}

# Show logs for all services
show_all_logs() {
    local compose_cmd=$(get_compose_cmd)
    
    echo -e "${CYAN}Showing logs for all services${NC}"
    echo -e "${CYAN}=============================${NC}"
    
    # Build docker-compose logs command
    local logs_cmd="$compose_cmd logs"
    
    if [[ "$FOLLOW" == "true" ]]; then
        logs_cmd="$logs_cmd -f"
    fi
    
    logs_cmd="$logs_cmd --tail=$LINES"
    
    if [[ -n "$SINCE" ]]; then
        logs_cmd="$logs_cmd --since='$SINCE'"
    fi
    
    if [[ -n "$UNTIL" ]]; then
        logs_cmd="$logs_cmd --until='$UNTIL'"
    fi
    
    # Apply filters and colorization
    if [[ -n "$FILTER" || -n "$LEVEL" ]]; then
        local filter_cmd=""
        
        if [[ -n "$FILTER" ]]; then
            filter_cmd="grep -i '$FILTER'"
        fi
        
        if [[ -n "$LEVEL" ]]; then
            if [[ -n "$filter_cmd" ]]; then
                filter_cmd="$filter_cmd | grep -i '\\[$LEVEL\\]'"
            else
                filter_cmd="grep -i '\\[$LEVEL\\]'"
            fi
        fi
        
        eval "$logs_cmd | $filter_cmd | colorize_logs"
    else
        eval "$logs_cmd | colorize_logs"
    fi
}

# Show log summary
show_log_summary() {
    local compose_cmd=$(get_compose_cmd)
    
    echo -e "${CYAN}Log Summary${NC}"
    echo -e "${CYAN}===========${NC}"
    
    # Get log stats for each service
    for service in "${SERVICES[@]}"; do
        local log_count=$($compose_cmd logs --tail=1000 "$service" 2>/dev/null | wc -l)
        local error_count=$($compose_cmd logs --tail=1000 "$service" 2>/dev/null | grep -i "error" | wc -l)
        local warn_count=$($compose_cmd logs --tail=1000 "$service" 2>/dev/null | grep -i "warn" | wc -l)
        
        echo -e "${BLUE}$service:${NC} $log_count lines, ${RED}$error_count errors${NC}, ${YELLOW}$warn_count warnings${NC}"
    done
}

# Main execution
main() {
    # Check if Docker Compose is available
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}Error: docker-compose not found${NC}"
        exit 1
    fi
    
    # Check if compose file exists
    local compose_file="$COMPOSE_FILE"
    if [[ "$ENV_TYPE" == "prod" ]]; then
        compose_file="$COMPOSE_PROD_FILE"
    fi
    
    if [[ ! -f "$compose_file" ]]; then
        echo -e "${RED}Error: Compose file not found: $compose_file${NC}"
        exit 1
    fi
    
    # Create logs directory if it doesn't exist
    mkdir -p "$LOG_DIR"
    
    # Show logs based on service
    if [[ -n "$SERVICE" ]]; then
        # Validate service name
        local valid_service=false
        for svc in "${SERVICES[@]}"; do
            if [[ "$svc" == "$SERVICE" ]]; then
                valid_service=true
                break
            fi
        done
        
        if [[ "$valid_service" == "false" ]]; then
            echo -e "${RED}Error: Invalid service name: $SERVICE${NC}"
            echo -e "${YELLOW}Available services:${NC}"
            for svc in "${SERVICES[@]}"; do
                echo -e "  ${GREEN}$svc${NC}"
            done
            exit 1
        fi
        
        show_service_logs "$SERVICE"
    else
        show_all_logs
    fi
}

# Handle Ctrl+C gracefully
trap 'echo -e "\n${YELLOW}Log viewer interrupted${NC}"; exit 0' INT

# Run main function
main "$@"