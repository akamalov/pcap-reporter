#!/bin/bash

# Test script for PCAP Reporter management scripts
# Usage: ./test-scripts.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Testing PCAP Reporter Management Scripts${NC}"
echo -e "${BLUE}=======================================${NC}"

# Test 1: Script permissions
echo -e "\n${YELLOW}Test 1: Checking script permissions...${NC}"
for script in pcap-reporter.sh health-check.sh log-viewer.sh; do
    if [[ -x "$SCRIPT_DIR/$script" ]]; then
        echo -e "${GREEN}✓${NC} $script is executable"
    else
        echo -e "${RED}✗${NC} $script is not executable"
        chmod +x "$SCRIPT_DIR/$script"
        echo -e "${YELLOW}  Fixed permissions for $script${NC}"
    fi
done

# Test 2: Help commands
echo -e "\n${YELLOW}Test 2: Testing help commands...${NC}"
for script in pcap-reporter.sh health-check.sh log-viewer.sh; do
    echo -e "\n${BLUE}Testing $script --help:${NC}"
    if "$SCRIPT_DIR/$script" --help >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $script help command works"
    else
        echo -e "${RED}✗${NC} $script help command failed"
    fi
done

# Test 3: Dependencies check
echo -e "\n${YELLOW}Test 3: Checking dependencies...${NC}"

# Check Docker
if command -v docker >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Docker is installed"
    if docker info >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Docker daemon is running"
    else
        echo -e "${YELLOW}⚠${NC} Docker daemon is not running"
    fi
else
    echo -e "${RED}✗${NC} Docker is not installed"
fi

# Check Docker Compose
if command -v docker-compose >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Docker Compose is installed"
else
    echo -e "${RED}✗${NC} Docker Compose is not installed"
fi

# Test 4: Configuration files
echo -e "\n${YELLOW}Test 4: Checking configuration files...${NC}"
if [[ -f "$PROJECT_DIR/docker-compose.yml" ]]; then
    echo -e "${GREEN}✓${NC} docker-compose.yml exists"
else
    echo -e "${RED}✗${NC} docker-compose.yml not found"
fi

if [[ -f "$PROJECT_DIR/docker-compose.prod.yml" ]]; then
    echo -e "${GREEN}✓${NC} docker-compose.prod.yml exists"
else
    echo -e "${YELLOW}⚠${NC} docker-compose.prod.yml not found (optional)"
fi

# Test 5: Color support
echo -e "\n${YELLOW}Test 5: Testing color support...${NC}"
if [[ -t 1 ]] && command -v tput >/dev/null 2>&1 && tput colors >/dev/null 2>&1; then
    local colors=$(tput colors)
    echo -e "${GREEN}✓${NC} Terminal supports $colors colors"
else
    echo -e "${YELLOW}⚠${NC} Terminal has limited color support"
fi

# Test 6: Script syntax
echo -e "\n${YELLOW}Test 6: Checking script syntax...${NC}"
for script in pcap-reporter.sh health-check.sh log-viewer.sh; do
    if bash -n "$SCRIPT_DIR/$script"; then
        echo -e "${GREEN}✓${NC} $script syntax is valid"
    else
        echo -e "${RED}✗${NC} $script has syntax errors"
    fi
done

# Test 7: Directory structure
echo -e "\n${YELLOW}Test 7: Checking directory structure...${NC}"
required_dirs=("logs" "uploads" "scripts" "backend" "frontend")
for dir in "${required_dirs[@]}"; do
    if [[ -d "$PROJECT_DIR/$dir" ]]; then
        echo -e "${GREEN}✓${NC} $dir directory exists"
    else
        echo -e "${YELLOW}⚠${NC} $dir directory not found"
        if [[ "$dir" == "logs" || "$dir" == "uploads" ]]; then
            mkdir -p "$PROJECT_DIR/$dir"
            echo -e "${BLUE}  Created $dir directory${NC}"
        fi
    fi
done

# Test 8: Script functionality (dry run)
echo -e "\n${YELLOW}Test 8: Testing script functionality (dry run)...${NC}"

# Test status without services running
echo -e "\n${BLUE}Testing status command:${NC}"
if "$SCRIPT_DIR/pcap-reporter.sh" status >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Status command works"
else
    echo -e "${YELLOW}⚠${NC} Status command returned non-zero (expected if services not running)"
fi

# Test health check
echo -e "\n${BLUE}Testing health check:${NC}"
if "$SCRIPT_DIR/health-check.sh" >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Health check works"
else
    echo -e "${YELLOW}⚠${NC} Health check returned non-zero (expected if services not running)"
fi

# Test log viewer
echo -e "\n${BLUE}Testing log viewer:${NC}"
if "$SCRIPT_DIR/log-viewer.sh" --help >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Log viewer help works"
else
    echo -e "${RED}✗${NC} Log viewer help failed"
fi

# Summary
echo -e "\n${BLUE}Test Summary${NC}"
echo -e "${BLUE}============${NC}"
echo -e "${GREEN}✓${NC} All basic tests completed"
echo -e "${YELLOW}Note:${NC} Some warnings are expected if Docker services are not running"
echo -e "${BLUE}To fully test, run:${NC} ./scripts/pcap-reporter.sh start && ./scripts/pcap-reporter.sh status"

echo -e "\n${GREEN}Script testing completed!${NC}"