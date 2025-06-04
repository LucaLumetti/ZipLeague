#!/bin/bash

# Rollback Script: ZipLeague to SpikeballRanking
# Use this script if the migration fails and you need to rollback

set -e

# Configuration
BACKUP_DIR="/var/backups/zipleague"
OLD_PROJECT_DIR="/var/www/SpikeballRanking"
NEW_PROJECT_DIR="/var/www/ZipLeague"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

list_backups() {
    log "Available backups:"
    ls -la "$BACKUP_DIR"/*.sql.gz 2>/dev/null || echo "No SQL backups found"
    ls -la "$OLD_PROJECT_DIR".backup.* 2>/dev/null || echo "No project backups found"
}

rollback_database() {
    log "Rolling back database..."
    
    # Find the most recent backup
    local latest_backup=$(ls -t "$BACKUP_DIR"/spikeball_ranking_backup_*.sql.gz 2>/dev/null | head -1)
    
    if [[ -z "$latest_backup" ]]; then
        error "No database backup found"
    fi
    
    log "Using backup: $latest_backup"
    
    # Read database credentials
    read -p "Database user: " DB_USER
    read -s -p "Database password: " DB_PASSWORD
    echo
    read -p "Database host [localhost]: " DB_HOST
    DB_HOST=${DB_HOST:-localhost}
    
    export PGPASSWORD="$DB_PASSWORD"
    
    # Drop the new database and recreate the old one
    psql -h "$DB_HOST" -U postgres -c "DROP DATABASE IF EXISTS zip_league;"
    psql -h "$DB_HOST" -U postgres -c "CREATE DATABASE spikeball_ranking OWNER $DB_USER;"
    
    # Restore from backup
    gunzip -c "$latest_backup" | psql -h "$DB_HOST" -U "$DB_USER" -d spikeball_ranking
    
    log "Database rolled back successfully"
}

rollback_project() {
    log "Rolling back project directory..."
    
    # Find the most recent project backup
    local latest_backup=$(ls -td "$OLD_PROJECT_DIR".backup.* 2>/dev/null | head -1)
    
    if [[ -z "$latest_backup" ]]; then
        error "No project backup found"
    fi
    
    log "Using project backup: $latest_backup"
    
    # Stop services
    systemctl stop apache2 2>/dev/null || true
    systemctl stop nginx 2>/dev/null || true
    
    # Remove new directory and restore old one
    rm -rf "$NEW_PROJECT_DIR"
    mv "$latest_backup" "$OLD_PROJECT_DIR"
    
    # Restore systemd service if it exists
    if [[ -f "/etc/systemd/system/spikeball.service" ]]; then
        sed -i "s|$NEW_PROJECT_DIR|$OLD_PROJECT_DIR|g" /etc/systemd/system/spikeball.service
        sed -i 's/zip_league/spikeball_ranking/g' /etc/systemd/system/spikeball.service
        systemctl daemon-reload
    fi
    
    # Start services
    systemctl start apache2 2>/dev/null || true
    systemctl start nginx 2>/dev/null || true
    
    log "Project rolled back successfully"
}

main() {
    log "Starting rollback from ZipLeague to SpikeballRanking"
    
    list_backups
    
    read -p "Do you want to proceed with the rollback? (y/N): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        log "Rollback cancelled"
        exit 0
    fi
    
    rollback_database
    rollback_project
    
    log "Rollback completed successfully!"
    log "Your original SpikeballRanking application should now be restored"
}

main "$@"
