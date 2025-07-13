#!/bin/bash

# Fix Docker permissions script
# This script ensures that Docker containers run with the same user ID as the host user
# to prevent permission issues with mounted volumes

set -e

echo "🔧 PCAP Reporter - Docker Permission Fix"
echo "========================================"

# Get current user and group IDs
CURRENT_USER_ID=$(id -u)
CURRENT_GROUP_ID=$(id -g)

echo "Current user ID: $CURRENT_USER_ID"
echo "Current group ID: $CURRENT_GROUP_ID"

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env << EOF
# Docker user permissions
USER_ID=$CURRENT_USER_ID
GROUP_ID=$CURRENT_GROUP_ID

# MongoDB configuration
MONGO_PASSWORD=secure_password_change_in_production

# Application secrets
SECRET_KEY=your-very-secure-secret-key-change-in-production-256-bits
JWT_SECRET=your-jwt-secret-key-change-in-production

# Environment
ENVIRONMENT=development
DEBUG=true
EOF
    echo "✅ Created .env file with user permissions"
else
    echo "📝 Updating existing .env file..."
    
    # Update or add USER_ID and GROUP_ID
    if grep -q "^USER_ID=" .env; then
        sed -i "s/^USER_ID=.*/USER_ID=$CURRENT_USER_ID/" .env
    else
        echo "USER_ID=$CURRENT_USER_ID" >> .env
    fi
    
    if grep -q "^GROUP_ID=" .env; then
        sed -i "s/^GROUP_ID=.*/GROUP_ID=$CURRENT_GROUP_ID/" .env
    else
        echo "GROUP_ID=$CURRENT_GROUP_ID" >> .env
    fi
    
    echo "✅ Updated .env file with current user permissions"
fi

# Create necessary directories with correct permissions
echo "📁 Creating required directories..."

directories=(
    "uploads"
    "logs"
    "nginx/ssl"
    "nginx/conf.d"
    "mongodb/init"
)

for dir in "${directories[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo "  Created: $dir"
    fi
done

# Set correct permissions on directories
echo "🔐 Setting directory permissions..."
chmod 755 uploads logs
chown $CURRENT_USER_ID:$CURRENT_GROUP_ID uploads logs 2>/dev/null || echo "  Note: Could not change ownership (running as non-root user)"

echo ""
echo "✅ Docker permission fix completed!"
echo ""
echo "Next steps:"
echo "1. Run: docker-compose build --no-cache"
echo "2. Run: docker-compose up -d"
echo ""
echo "The containers will now run with your user ID ($CURRENT_USER_ID) to prevent permission issues."