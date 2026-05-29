#!/bin/bash
#
# PostgreSQL Database Restore Script for NuviaButik
# This script restores database from a compressed backup file
#
# Usage: ./restore_database.sh <backup_file.sql.gz>
# Example: ./restore_database.sh /var/backups/nuviabutik/database/nuviabutik_20251024_020000.sql.gz

set -e

# Configuration
DB_NAME="nuviabutik_db"
DB_USER="nuviabutik_user"

# Check if backup file is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo "Example: $0 /var/backups/nuviabutik/database/nuviabutik_20251024_020000.sql.gz"
    exit 1
fi

BACKUP_FILE="$1"

# Check if file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Log file
LOG_FILE="/var/log/nuviabutik_restore.log"

# Function to log messages
log_message() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_message "Starting database restore from: $BACKUP_FILE"

# Warning
echo "WARNING: This will replace the current database!"
echo "Press Ctrl+C within 5 seconds to cancel..."
sleep 5

log_message "Dropping existing database..."
sudo -u postgres psql -c "DROP DATABASE IF EXISTS ${DB_NAME};"

log_message "Creating new database..."
sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"

log_message "Restoring database from backup..."
if gunzip -c "$BACKUP_FILE" | sudo -u postgres psql "$DB_NAME"; then
    log_message "Database restore completed successfully!"
else
    log_message "ERROR: Database restore failed!"
    exit 1
fi

log_message "Restore process completed."


