#!/bin/bash
#
# NuviaButik System Information Script
# Quick overview of system status
#
# Usage: ./system_info.sh

echo "======================================="
echo "      NUVIABUTIK SYSTEM INFO"
echo "======================================="
echo ""

# System Information
echo "📊 SYSTEM INFORMATION"
echo "---------------------------------------"
echo "Hostname: $(hostname)"
echo "OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
echo "Kernel: $(uname -r)"
echo "CPU: $(grep "model name" /proc/cpuinfo | head -1 | cut -d':' -f2 | xargs)"
echo "CPU Cores: $(nproc)"
echo "Uptime: $(uptime -p)"
echo ""

# Resource Usage
echo "💾 RESOURCE USAGE"
echo "---------------------------------------"
echo "CPU Load: $(uptime | awk -F'load average:' '{print $2}')"
echo "RAM: $(free -h | grep Mem | awk '{print "Used: "$3" / Total: "$2" ("$3/$2*100"%)"}')"
echo "Disk: $(df -h / | tail -1 | awk '{print "Used: "$3" / Total: "$2" ("$5" used)"}')"
echo "Swap: $(free -h | grep Swap | awk '{print "Used: "$3" / Total: "$2}')"
echo ""

# Network
echo "🌐 NETWORK"
echo "---------------------------------------"
echo "Public IP: $(curl -s ifconfig.me 2>/dev/null || echo "Unable to fetch")"
echo "Local IP: $(hostname -I | awk '{print $1}')"
echo "Active Connections: $(ss -tan | grep ESTAB | wc -l)"
echo ""

# Services
echo "🔧 SERVICES STATUS"
echo "---------------------------------------"
systemctl is-active nginx >/dev/null 2>&1 && echo "✅ Nginx: Running" || echo "❌ Nginx: Stopped"
pgrep -f "gunicorn.*stoktakip" >/dev/null && echo "✅ Gunicorn: Running ($(pgrep -f 'gunicorn.*stoktakip' | wc -l) workers)" || echo "❌ Gunicorn: Stopped"
systemctl is-active postgresql >/dev/null 2>&1 && echo "✅ PostgreSQL: Running" || echo "❌ PostgreSQL: Stopped"
systemctl is-active redis-server >/dev/null 2>&1 && echo "✅ Redis: Running" || echo "❌ Redis: Stopped"
echo ""

# Database Info
echo "🗄️  DATABASE"
echo "---------------------------------------"
DB_SIZE=$(sudo -u postgres psql -d nuviabutik_db -t -c "SELECT pg_size_pretty(pg_database_size('nuviabutik_db'));" 2>/dev/null | xargs || echo "Unknown")
DB_CONN=$(sudo -u postgres psql -t -c "SELECT count(*) FROM pg_stat_activity WHERE datname='nuviabutik_db';" 2>/dev/null | xargs || echo "0")
echo "Database Size: $DB_SIZE"
echo "Active Connections: $DB_CONN"
echo ""

# Application Info
echo "🚀 APPLICATION"
echo "---------------------------------------"
echo "Project Path: /var/www/nuviabutik"
echo "Project Size: $(du -sh /var/www/nuviabutik 2>/dev/null | cut -f1)"
echo "Python Version: $(python3 --version 2>/dev/null || echo "Unknown")"
echo "Django Version: $(cd /var/www/nuviabutik && ./venv/bin/python -c "import django; print(django.get_version())" 2>/dev/null || echo "Unknown")"
echo ""

# Recent Activity
echo "📋 RECENT ACTIVITY"
echo "---------------------------------------"
echo "Last 5 Nginx Access:"
tail -5 /var/log/nginx/access.log 2>/dev/null | awk '{print $4" "$5" "$7" "$9}' | tr -d '[]' || echo "No logs available"
echo ""

# SSL Certificate
echo "🔒 SSL CERTIFICATE"
echo "---------------------------------------"
if [ -f "/etc/letsencrypt/live/nuviabutik.com/cert.pem" ]; then
    EXPIRY=$(openssl x509 -in /etc/letsencrypt/live/nuviabutik.com/cert.pem -noout -enddate | cut -d= -f2)
    DAYS_LEFT=$(( ($(date -d "$EXPIRY" +%s) - $(date +%s)) / 86400 ))
    echo "Certificate: Valid"
    echo "Expires: $EXPIRY"
    echo "Days Left: $DAYS_LEFT days"
else
    echo "Certificate: Not found"
fi
echo ""

# Backups
echo "💾 BACKUP STATUS"
echo "---------------------------------------"
BACKUP_COUNT=$(find /var/backups/nuviabutik/database -name "*.sql.gz" 2>/dev/null | wc -l || echo "0")
LAST_BACKUP=$(ls -t /var/backups/nuviabutik/database/*.sql.gz 2>/dev/null | head -1 | xargs -r stat -c %y | cut -d'.' -f1 || echo "No backups found")
echo "Total Backups: $BACKUP_COUNT"
echo "Last Backup: $LAST_BACKUP"
echo ""

echo "======================================="
echo "         End of System Info"
echo "======================================="


