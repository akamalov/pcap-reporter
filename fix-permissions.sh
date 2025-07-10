#!/bin/bash

# Fix permissions for Docker containers
# This script ensures that the uploads and logs directories have proper permissions

echo "Setting up directories and permissions for Docker containers..."

# Get current user and group IDs
USER_ID=$(id -u)
GROUP_ID=$(id -g)

echo "Current user ID: $USER_ID"
echo "Current group ID: $GROUP_ID"

# Create directories if they don't exist
mkdir -p uploads logs

# Set proper permissions (readable/writable by owner and group)
chmod 755 uploads logs

# Make sure the current user owns these directories
chown -R $USER_ID:$GROUP_ID uploads logs

echo "Permissions fixed:"
echo "uploads directory: $(ls -ld uploads)"
echo "logs directory: $(ls -ld logs)"

# Set environment variables for docker-compose
export USER_ID=$USER_ID
export GROUP_ID=$GROUP_ID

echo ""
echo "Environment variables set:"
echo "USER_ID=$USER_ID"
echo "GROUP_ID=$GROUP_ID"

# Check if docker-compose.yml exists
if [ -f "docker-compose.yml" ]; then
    echo ""
    echo "To apply these changes, restart your Docker containers:"
    echo "export USER_ID=$USER_ID GROUP_ID=$GROUP_ID"
    echo "docker-compose down && docker-compose up -d"
else
    echo "docker-compose.yml not found in current directory"
fi