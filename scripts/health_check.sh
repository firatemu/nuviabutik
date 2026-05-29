#!/bin/bash
#
# NuviaButik System Health Check Script
# This script monitors system resources, services, and application health
#
# Usage: ./health_check.sh
# Cron: */5 * * * * /var/www/nuviabutik/scripts/health_check.sh

set -e

# Configuration
LOG_FILE="/var/log/nuviabutik_health.log"
ALERT_FILE="/var/log/nuviabutik_alerts.log"
APP_URL="http://127.0.0.1:8000"
DOMAIN="https://nuviabutik.com"

# Thresholds
CPU_THRESHOLD=80
MEMORY_THRESHOLD=85
DISK_THRESHOLD=90

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to log messages
log_message() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log_alert() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ALERT: $1" >> "$ALERT_FILE"
}

print_status() {
    local status=$1
    local message=$2
    if [ "$status" = "OK" ]; then
        echo -e "${GREEN}✅ $message${NC}"
    elif [ "$status" = "WARNING" ]; then
        echo -e "${YELLOW}⚠️  $message${NC}"
    else
        echo -e "${RED}❌ $message${NC}"
    fi
}

echo "==================================="
echo "NuviaButik Health Check"
echo "Timestamp: $(date +'%Y-%m-%d %H:%M:%S')"
echo "==================================="
echo ""

# 1. Check CPU Usage
echo "1. CPU Status:"
echo "-----------------------------------"
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1 | cut -d'.' -f1)
LOAD_AVG=$(uptime | awk -F'load average:' '{print $2}' | cut -d',' -f1 | xargs)

if [ "$CPU_USAGE" -lt "$CPU_THRESHOLD" ]; then
    print_status "OK" "CPU Usage: ${CPU_USAGE}% (Load: ${LOAD_AVG})"
else
    print_status "WARNING" "CPU Usage: ${CPU_USAGE}% (Load: ${LOAD_AVG}) - HIGH!"
    log_alert "High CPU usage: ${CPU_USAGE}%"
fi
echo ""

# 2. Check Memory Usage
echo "2. Memory Status:"
echo "-----------------------------------"
MEMORY_USAGE=$(free | grep Mem | awk '{printf("%.0f", $3/$2 * 100.0)}')
MEMORY_AVAILABLE=$(free -h | grep Mem | awk '{print $7}')

if [ "$MEMORY_USAGE" -lt "$MEMORY_THRESHOLD" ]; then
    print_status "OK" "Memory Usage: ${MEMORY_USAGE}% (Available: ${MEMORY_AVAILABLE})"
else
    print_status "WARNING" "Memory Usage: ${MEMORY_USAGE}% (Available: ${MEMORY_AVAILABLE}) - HIGH!"
    log_alert "High memory usage: ${MEMORY_USAGE}%"
fi
echo ""

# 3. Check Disk Usage
echo "3. Disk Status:"
echo "-----------------------------------"
DISK_USAGE=$(df -h / | tail -1 | awk '{print $5}' | cut -d'%' -f1)
DISK_AVAILABLE=$(df -h / | tail -1 | awk '{print $4}')

if [ "$DISK_USAGE" -lt "$DISK_THRESHOLD" ]; then
    print_status "OK" "Disk Usage: ${DISK_USAGE}% (Available: ${DISK_AVAILABLE})"
else
    print_status "ERROR" "Disk Usage: ${DISK_USAGE}% (Available: ${DISK_AVAILABLE}) - CRITICAL!"
    log_alert "Critical disk usage: ${DISK_USAGE}%"
fi
echo ""

# 4. Check Services
echo "4. Service Status:"
echo "-----------------------------------"

# Check Nginx
if systemctl is-active --quiet nginx; then
    print_status "OK" "Nginx is running"
else
    print_status "ERROR" "Nginx is NOT running!"
    log_alert "Nginx service is down"
fi

# Check Gunicorn (nuviabutik)
if systemctl is-active --quiet nuviabutik.service 2>/dev/null || pgrep -f "gunicorn.*stoktakip" > /dev/null; then
    WORKER_COUNT=$(pgrep -f "gunicorn.*stoktakip" | wc -l)
    print_status "OK" "Gunicorn is running ($WORKER_COUNT workers)"
else
    print_status "ERROR" "Gunicorn is NOT running!"
    log_alert "Gunicorn service is down"
fi

# Check PostgreSQL
if systemctl is-active --quiet postgresql 2>/dev/null || pgrep -f postgres > /dev/null; then
    print_status "OK" "PostgreSQL is running"
else
    print_status "ERROR" "PostgreSQL is NOT running!"
    log_alert "PostgreSQL service is down"
fi

# Check Redis
if systemctl is-active --quiet redis-server 2>/dev/null || pgrep -f redis-server > /dev/null; then
    print_status "OK" "Redis is running"
else
    print_status "WARNING" "Redis is NOT running"
    log_alert "Redis service is down"
fi
echo ""

# 5. Check Application Response
echo "5. Application Health:"
echo "-----------------------------------"

# Check local app
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$APP_URL" 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "301" ]; then
    print_status "OK" "Local app responding (HTTP $HTTP_CODE)"
else
    print_status "ERROR" "Local app not responding (HTTP $HTTP_CODE)"
    log_alert "Application not responding on localhost"
fi

# Check public domain
DOMAIN_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$DOMAIN" 2>/dev/null || echo "000")
if [ "$DOMAIN_CODE" = "200" ] || [ "$DOMAIN_CODE" = "302" ] || [ "$DOMAIN_CODE" = "301" ]; then
    print_status "OK" "Public domain responding (HTTP $DOMAIN_CODE)"
else
    print_status "WARNING" "Public domain check failed (HTTP $DOMAIN_CODE)"
fi
echo ""

# 6. Check Database Connections
echo "6. Database Status:"
echo "-----------------------------------"
DB_CONNECTIONS=$(sudo -u postgres psql -t -c "SELECT count(*) FROM pg_stat_activity WHERE datname='nuviabutik_db';" 2>/dev/null | xargs || echo "0")
DB_SIZE=$(sudo -u postgres psql -d nuviabutik_db -t -c "SELECT pg_size_pretty(pg_database_size('nuviabutik_db'));" 2>/dev/null | xargs || echo "Unknown")

if [ "$DB_CONNECTIONS" -gt 0 ]; then
    print_status "OK" "Database connections: $DB_CONNECTIONS (Size: $DB_SIZE)"
else
    print_status "WARNING" "No active database connections"
fi
echo ""

# 7. Check Process Health
echo "7. Process Health:"
echo "-----------------------------------"

# Check if any processes are in zombie state
ZOMBIE_COUNT=$(ps aux | awk '{print $8}' | grep -c Z 2>/dev/null || echo "0")
ZOMBIE_COUNT=$(echo "$ZOMBIE_COUNT" | tr -d '\n' | xargs)
if [ "$ZOMBIE_COUNT" -eq 0 ] 2>/dev/null; then
    print_status "OK" "No zombie processes"
else
    print_status "WARNING" "$ZOMBIE_COUNT zombie processes found"
    log_alert "Zombie processes detected: $ZOMBIE_COUNT"
fi

# Check system uptime
UPTIME_DAYS=$(uptime | awk '{print $3}' | cut -d',' -f1)
print_status "OK" "System uptime: $UPTIME_DAYS days"
echo ""

# 8. Check Recent Errors in Logs
echo "8. Recent Errors:"
echo "-----------------------------------"
ERROR_COUNT=$(tail -100 /var/log/gunicorn/nuviabutik_error.log 2>/dev/null | grep -ci error 2>/dev/null || echo "0")
ERROR_COUNT=$(echo "$ERROR_COUNT" | tr -d '\n' | xargs)
if [ "$ERROR_COUNT" -eq 0 ] 2>/dev/null; then
    print_status "OK" "No recent errors in logs"
elif [ "$ERROR_COUNT" -lt 5 ] 2>/dev/null; then
    print_status "WARNING" "$ERROR_COUNT errors in last 100 log lines"
else
    print_status "ERROR" "$ERROR_COUNT errors in last 100 log lines - Check logs!"
    log_alert "High error count in logs: $ERROR_COUNT"
fi
echo ""

echo "==================================="
echo "Health Check Completed!"
echo "==================================="
echo ""

log_message "Health check completed - CPU: ${CPU_USAGE}%, Memory: ${MEMORY_USAGE}%, Disk: ${DISK_USAGE}%"

