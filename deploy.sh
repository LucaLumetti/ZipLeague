#!/bin/bash

# Deploy script for ZipLeague application
# This script performs: compose down, git pull, rebuild, up, makemigrations, migrate

set -e  # Exit on any error

echo "🚀 Starting ZipLeague deployment..."

# Function to check if command was successful
check_command() {
    if [ $? -ne 0 ]; then
        echo "❌ Failed during: $1"
        exit 1
    fi
    echo "✅ $1 completed successfully"
}

# Step 1: Docker Compose Down
echo "📦 Stopping containers..."
sudo docker compose down
check_command "Docker compose down"

# Step 2: Git Pull
echo "🔄 Pulling latest changes from git..."
git pull
check_command "Git pull"

# Step 3: Rebuild containers
echo "🔨 Building containers..."
sudo docker compose build --no-cache
check_command "Docker compose build"

# Step 4: Start containers
echo "🚀 Starting containers..."
sudo docker compose up -d
check_command "Docker compose up"

# Wait a moment for containers to be ready
echo "⏳ Waiting for containers to be ready..."
sleep 10

# Step 5: Make migrations
echo "📝 Creating migrations..."
sudo docker compose exec web python manage.py makemigrations
check_command "Django makemigrations"

# Step 6: Apply migrations
echo "🗄️ Applying migrations..."
sudo docker compose exec web python manage.py migrate
check_command "Django migrate"

# Optional: Collect static files (uncomment if needed)
echo "📁 Collecting static files..."
sudo docker compose exec web python manage.py collectstatic --noinput
check_command "Django collectstatic"

# Reload Nginx
echo "🔄 Reloading Nginx..."
sudo systemctl reload nginx
check_command "Nginx reload"

echo "🎉 Deployment completed successfully!"
echo "🌐 Application should be available at your configured URL"
