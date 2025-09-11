#!/bin/bash

# NuviaButik.com Deployment Script
# Run this script on your Ubuntu server as root or with sudo

set -e

echo "🚀 Starting NuviaButik.com deployment..."

# Variables
PROJECT_NAME="nuviabutik"
PROJECT_DIR="/var/www/$PROJECT_NAME"
DOMAIN="nuviabutik.com"
SERVER_IP="31.57.33.34"
DB_NAME="nuviabutik_db"
DB_USER="nuviabutik_user"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   print_error "This script must be run as root (use sudo)"
   exit 1
fi

print_status "Updating system packages..."
apt update && apt upgrade -y

print_status "Installing required packages..."
apt install -y python3 python3-pip python3-venv python3-dev \
    postgresql postgresql-contrib nginx certbot python3-certbot-nginx \
    git curl wget unzip software-properties-common \
    build-essential libpq-dev

print_status "Creating project user and directories..."
# Create www-data directories if they don't exist
mkdir -p /var/www
mkdir -p /var/log/django
mkdir -p /var/log/gunicorn
mkdir -p /var/run/gunicorn

# Set proper permissions
chown -R www-data:www-data /var/www
chown -R www-data:www-data /var/log/django
chown -R www-data:www-data /var/log/gunicorn
chown -R www-data:www-data /var/run/gunicorn

print_status "Setting up PostgreSQL database..."
sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME};" 2>/dev/null || print_warning "Database already exists"
sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD 'change_this_password';" 2>/dev/null || print_warning "User already exists"
sudo -u postgres psql -c "ALTER ROLE ${DB_USER} SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "ALTER ROLE ${DB_USER} SET default_transaction_isolation TO 'read committed';"
sudo -u postgres psql -c "ALTER ROLE ${DB_USER} SET timezone TO 'UTC';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"

print_status "Configuring PostgreSQL for better performance..."
# Basic PostgreSQL optimization
PG_VERSION=$(sudo -u postgres psql -t -c "SELECT version();" | grep -oP '(?<=PostgreSQL )\d+\.\d+')
PG_CONF="/etc/postgresql/${PG_VERSION}/main/postgresql.conf"

if [ -f "$PG_CONF" ]; then
    cp "$PG_CONF" "${PG_CONF}.backup"
    
    # Update configuration for better performance
    sed -i "s/#shared_buffers = 128MB/shared_buffers = 256MB/" "$PG_CONF"
    sed -i "s/#effective_cache_size = 4GB/effective_cache_size = 1GB/" "$PG_CONF"
    sed -i "s/#maintenance_work_mem = 64MB/maintenance_work_mem = 128MB/" "$PG_CONF"
    sed -i "s/#random_page_cost = 4.0/random_page_cost = 1.1/" "$PG_CONF"
    
    systemctl restart postgresql
fi

print_status "Project directory will be: $PROJECT_DIR"
print_warning "Please upload your Django project to $PROJECT_DIR"
print_warning "Make sure to include: .env file with production settings"

echo
print_status "Next steps to complete manually:"
echo "1. Upload your Django project to $PROJECT_DIR"
echo "2. Create virtual environment: python3 -m venv $PROJECT_DIR/venv"
echo "3. Install requirements: $PROJECT_DIR/venv/bin/pip install -r $PROJECT_DIR/requirements.txt"
echo "4. Copy .env.production to $PROJECT_DIR/.env and update database password"
echo "5. Run migrations: $PROJECT_DIR/venv/bin/python $PROJECT_DIR/manage.py migrate --settings=production_settings"
echo "6. Collect static files: $PROJECT_DIR/venv/bin/python $PROJECT_DIR/manage.py collectstatic --noinput --settings=production_settings"
echo "7. Create superuser: $PROJECT_DIR/venv/bin/python $PROJECT_DIR/manage.py createsuperuser --settings=production_settings"

print_status "Configuring Nginx..."
# Remove default nginx site
rm -f /etc/nginx/sites-enabled/default

# Copy nginx configuration (this will be done manually)
print_warning "Copy nginx_nuviabutik.conf to /etc/nginx/sites-available/$DOMAIN"
print_warning "Then run: ln -s /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/"

print_status "Configuring systemd service..."
print_warning "Copy nuviabutik.service to /etc/systemd/system/"
print_warning "Then run: systemctl daemon-reload && systemctl enable nuviabutik"

print_status "Setting up SSL certificate (Let's Encrypt)..."
print_warning "After completing all steps, run:"
echo "certbot --nginx -d $DOMAIN -d www.$DOMAIN"

print_status "Firewall configuration..."
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

print_status "Basic server setup completed!"
print_warning "Remember to:"
echo "1. Change the database password in PostgreSQL"
echo "2. Update the .env file with secure values"
echo "3. Upload your Django project files"
echo "4. Complete the manual steps listed above"
echo "5. Test the application before going live"

print_status "Database password change command:"
echo "sudo -u postgres psql -c \"ALTER USER ${DB_USER} PASSWORD 'your_secure_password_here';\""
