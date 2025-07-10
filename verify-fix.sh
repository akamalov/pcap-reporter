#!/bin/bash

echo "=== Docker Permission Fix Verification ==="
echo ""

# Check if directories exist
echo "1. Checking directory structure:"
for dir in uploads logs; do
    if [ -d "$dir" ]; then
        echo "   ✓ $dir directory exists"
        ls -ld "$dir"
    else
        echo "   ✗ $dir directory missing"
    fi
done
echo ""

# Check environment variables
echo "2. Checking environment variables:"
USER_ID=${USER_ID:-$(id -u)}
GROUP_ID=${GROUP_ID:-$(id -g)}
echo "   USER_ID: $USER_ID"
echo "   GROUP_ID: $GROUP_ID"
echo "   Current user: $(id -u):$(id -g)"

if [ "$USER_ID" = "$(id -u)" ] && [ "$GROUP_ID" = "$(id -g)" ]; then
    echo "   ✓ Environment variables match current user"
else
    echo "   ⚠ Environment variables don't match current user"
    echo "   Run: export USER_ID=$(id -u) GROUP_ID=$(id -g)"
fi
echo ""

# Check Dockerfile modifications
echo "3. Checking Dockerfile modifications:"
if grep -q "ARG USER_ID" backend/Dockerfile; then
    echo "   ✓ Dockerfile has USER_ID argument"
else
    echo "   ✗ Dockerfile missing USER_ID argument"
fi

if grep -q "ARG GROUP_ID" backend/Dockerfile; then
    echo "   ✓ Dockerfile has GROUP_ID argument"
else
    echo "   ✗ Dockerfile missing GROUP_ID argument"
fi
echo ""

# Check docker-compose.yml modifications
echo "4. Checking docker-compose.yml modifications:"
if grep -q "USER_ID:" docker-compose.yml; then
    echo "   ✓ docker-compose.yml has USER_ID build arg"
else
    echo "   ✗ docker-compose.yml missing USER_ID build arg"
fi

if grep -q "GROUP_ID:" docker-compose.yml; then
    echo "   ✓ docker-compose.yml has GROUP_ID build arg"
else
    echo "   ✗ docker-compose.yml missing GROUP_ID build arg"
fi
echo ""

# Test file creation
echo "5. Testing file creation permissions:"
TEST_FILE="uploads/test-$(date +%s).txt"
if touch "$TEST_FILE" 2>/dev/null; then
    echo "   ✓ Can create files in uploads directory"
    rm -f "$TEST_FILE"
else
    echo "   ✗ Cannot create files in uploads directory"
fi

TEST_LOG="logs/test-$(date +%s).log"
if touch "$TEST_LOG" 2>/dev/null; then
    echo "   ✓ Can create files in logs directory"
    rm -f "$TEST_LOG"
else
    echo "   ✗ Cannot create files in logs directory"
fi
echo ""

echo "=== Next Steps ==="
echo "If all checks pass, rebuild your containers:"
echo "  export USER_ID=$(id -u) GROUP_ID=$(id -g)"
echo "  docker-compose down"
echo "  docker-compose up -d"
echo ""
echo "If any checks fail, run:"
echo "  ./fix-permissions.sh"