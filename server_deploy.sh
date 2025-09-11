#!/bin/bash

# NuviaButik Deployment Script
# Bu script sunucuda manuel deployment için de kullanılabilir

set -e

PROJECT_DIR="/var/www/nuviabutik"
BACKUP_DIR="/var/backups/nuviabutik"
LOG_FILE="/var/log/deployment.log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

log "🚀 Starting NuviaButik deployment..."

# Create backup directory if not exists
mkdir -p $BACKUP_DIR

# Navigate to project directory
cd $PROJECT_DIR

# Create backup
BACKUP_NAME="nuviabutik_backup_$(date +%Y%m%d_%H%M%S)"
log "📦 Creating backup: $BACKUP_NAME"
cp -r . $BACKUP_DIR/$BACKUP_NAME

# Clean up old backups (keep only last 5)
log "🧹 Cleaning old backups..."
cd $BACKUP_DIR && ls -t | tail -n +6 | xargs -d '\n' rm -rf --

# Return to project directory
cd $PROJECT_DIR

# Check if git repository exists
if [ ! -d ".git" ]; then
    log "❌ Git repository not found!"
    exit 1
fi

# Pull latest changes
log "📥 Pulling latest changes from GitHub..."
git fetch origin
git reset --hard origin/main

# Activate virtual environment
log "🐍 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
log "📋 Installing/updating dependencies..."
pip install -r requirements.txt

# Django management commands
log "🗃️ Running database migrations..."
python manage.py migrate --noinput

log "📁 Collecting static files..."
python manage.py collectstatic --noinput

# Set proper permissions
log "🔐 Setting permissions..."
chown -R www-data:www-data /var/www/nuviabutik/media
chown -R www-data:www-data /var/www/nuviabutik/staticfiles
chmod -R 755 /var/www/nuviabutik/media
chmod -R 755 /var/www/nuviabutik/staticfiles

# Restart services
log "🔄 Restarting services..."
systemctl restart nuviabutik
systemctl restart nginx

# Wait for services to start
sleep 5

# Check service status
log "✅ Checking service status..."
if systemctl is-active --quiet nuviabutik; then
    log "✅ Gunicorn service is running"
else
    log "❌ Gunicorn service failed to start"
    systemctl status nuviabutik
    exit 1
fi

if systemctl is-active --quiet nginx; then
    log "✅ Nginx service is running"
else
    log "❌ Nginx service failed to start"
    systemctl status nginx
    exit 1
fi

# Health check
log "🏥 Performing health check..."
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost)
if [ $response -eq 200 ] || [ $response -eq 302 ]; then
    log "✅ Health check passed! Site is accessible."
else
    log "❌ Health check failed! HTTP status: $response"
    exit 1
fi

log "🎉 Deployment completed successfully!"
log "📊 Deployment summary:"
log "   - Backup created: $BACKUP_NAME"
log "   - Services restarted: nuviabutik, nginx"
log "   - Health check: PASSED"
log "   - Site URL: http://nuviabutik.com"
