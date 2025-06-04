#!/bin/bash

# Complete Migration Script: SpikeballRanking to ZipLeague
# This script handles database table renaming, Django migration history updates,
# and safe deployment without data loss.

set -e  # Exit on any error

# Configuration
BACKUP_DIR="/var/backups/zipleague"
OLD_PROJECT_DIR="/var/www/SpikeballRanking"
NEW_PROJECT_DIR="/var/www/ZipLeague"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
VENV_PATH="/var/www/ZipLeague/venv"

# Database configuration (will be read from .env)
DB_NAME=""
DB_USER=""
DB_PASSWORD=""
DB_HOST="localhost"
DB_PORT="5432"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if running as root or with sudo
    if [[ $EUID -eq 0 ]]; then
        warn "Running as root. Make sure you understand the implications."
    fi
    
    # Check if PostgreSQL is available
    if ! command -v psql &> /dev/null; then
        error "PostgreSQL client (psql) is not installed"
    fi
    
    # Check if old project directory exists
    if [[ ! -d "$OLD_PROJECT_DIR" ]]; then
        error "Old project directory $OLD_PROJECT_DIR does not exist"
    fi
    
    # Create backup directory
    mkdir -p "$BACKUP_DIR"
    
    log "Prerequisites check passed"
}

read_env_config() {
    log "Reading environment configuration..."
    
    if [[ -f "$OLD_PROJECT_DIR/.env" ]]; then
        source "$OLD_PROJECT_DIR/.env"
        DB_NAME=${DATABASE_NAME:-"spikeball_ranking"}
        DB_USER=${DATABASE_USER:-"spikeball_user"}
        DB_PASSWORD=${DATABASE_PASSWORD:-""}
        DB_HOST=${DATABASE_HOST:-"localhost"}
        DB_PORT=${DATABASE_PORT:-"5432"}
    else
        warn ".env file not found. Using default values."
        DB_NAME="spikeball_ranking"
        DB_USER="spikeball_user"
        read -s -p "Enter database password: " DB_PASSWORD
        echo
    fi
    
    log "Database: $DB_NAME, User: $DB_USER, Host: $DB_HOST:$DB_PORT"
}

backup_database() {
    log "Creating database backup..."
    
    local backup_file="$BACKUP_DIR/spikeball_ranking_backup_$TIMESTAMP.sql"
    
    export PGPASSWORD="$DB_PASSWORD"
    pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" > "$backup_file"
    
    if [[ $? -eq 0 ]]; then
        log "Database backup created: $backup_file"
        # Compress the backup
        gzip "$backup_file"
        log "Backup compressed: $backup_file.gz"
    else
        error "Failed to create database backup"
    fi
}

stop_services() {
    log "Stopping services..."
    
    # Stop Apache/Nginx
    if systemctl is-active --quiet apache2; then
        systemctl stop apache2
        log "Apache2 stopped"
    fi
    
    if systemctl is-active --quiet nginx; then
        systemctl stop nginx
        log "Nginx stopped"
    fi
    
    # Stop any running Django processes
    pkill -f "manage.py runserver" || true
    pkill -f "gunicorn.*spikeball" || true
    
    log "Services stopped"
}

rename_project_directory() {
    log "Renaming project directory..."
    
    if [[ -d "$NEW_PROJECT_DIR" ]]; then
        warn "New project directory already exists. Creating backup..."
        mv "$NEW_PROJECT_DIR" "$NEW_PROJECT_DIR.backup.$TIMESTAMP"
    fi
    
    cp -r "$OLD_PROJECT_DIR" "$NEW_PROJECT_DIR"
    log "Project directory copied to $NEW_PROJECT_DIR"
}

update_database_schema() {
    log "Updating database schema..."
    
    export PGPASSWORD="$DB_PASSWORD"
    
    # Create SQL script for table renaming
    local sql_script="$BACKUP_DIR/rename_tables_$TIMESTAMP.sql"
    
    cat > "$sql_script" << 'EOF'
-- Rename tables from rankings_* to core_*
ALTER TABLE rankings_player RENAME TO core_player;
ALTER TABLE rankings_match RENAME TO core_match;
ALTER TABLE rankings_registrationtoken RENAME TO core_registrationtoken;

-- Update Django migration history
UPDATE django_migrations SET app = 'core' WHERE app = 'rankings';

-- Update Django content types
UPDATE django_content_type SET app_label = 'core' WHERE app_label = 'rankings';

-- Update any foreign key references in django_admin_log if they exist
UPDATE django_admin_log SET content_type_id = (
    SELECT id FROM django_content_type WHERE app_label = 'core' AND model = 'player'
) WHERE content_type_id = (
    SELECT id FROM django_content_type WHERE app_label = 'rankings' AND model = 'player'
) AND EXISTS (
    SELECT 1 FROM django_content_type WHERE app_label = 'rankings' AND model = 'player'
);

UPDATE django_admin_log SET content_type_id = (
    SELECT id FROM django_content_type WHERE app_label = 'core' AND model = 'match'
) WHERE content_type_id = (
    SELECT id FROM django_content_type WHERE app_label = 'rankings' AND model = 'match'
) AND EXISTS (
    SELECT 1 FROM django_content_type WHERE app_label = 'rankings' AND model = 'match'
);

UPDATE django_admin_log SET content_type_id = (
    SELECT id FROM django_content_type WHERE app_label = 'core' AND model = 'registrationtoken'
) WHERE content_type_id = (
    SELECT id FROM django_content_type WHERE app_label = 'rankings' AND model = 'registrationtoken'
) AND EXISTS (
    SELECT 1 FROM django_content_type WHERE app_label = 'rankings' AND model = 'registrationtoken'
);

-- Update permissions
UPDATE auth_permission SET content_type_id = (
    SELECT id FROM django_content_type WHERE app_label = 'core' AND model = 'player'
) WHERE content_type_id = (
    SELECT id FROM django_content_type WHERE app_label = 'rankings' AND model = 'player'
) AND EXISTS (
    SELECT 1 FROM django_content_type WHERE app_label = 'rankings' AND model = 'player'
);

UPDATE auth_permission SET content_type_id = (
    SELECT id FROM django_content_type WHERE app_label = 'core' AND model = 'match'
) WHERE content_type_id = (
    SELECT id FROM django_content_type WHERE app_label = 'rankings' AND model = 'match'
) AND EXISTS (
    SELECT 1 FROM django_content_type WHERE app_label = 'rankings' AND model = 'match'
);

UPDATE auth_permission SET content_type_id = (
    SELECT id FROM django_content_type WHERE app_label = 'core' AND model = 'registrationtoken'
) WHERE content_type_id = (
    SELECT id FROM django_content_type WHERE app_label = 'rankings' AND model = 'registrationtoken'
) AND EXISTS (
    SELECT 1 FROM django_content_type WHERE app_label = 'rankings' AND model = 'registrationtoken'
);
EOF
    
    # Execute the SQL script
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$sql_script"
    
    if [[ $? -eq 0 ]]; then
        log "Database schema updated successfully"
    else
        error "Failed to update database schema"
    fi
}

update_database_user_and_name() {
    log "Creating new database user and database..."
    
    export PGPASSWORD="$DB_PASSWORD"
    
    # Create new database user
    psql -h "$DB_HOST" -p "$DB_PORT" -U postgres -c "CREATE USER zip_league_user WITH PASSWORD '$DB_PASSWORD';" || warn "User may already exist"
    
    # Create new database
    psql -h "$DB_HOST" -p "$DB_PORT" -U postgres -c "CREATE DATABASE zip_league OWNER zip_league_user;" || warn "Database may already exist"
    
    # Dump from old database and restore to new
    local temp_dump="$BACKUP_DIR/temp_migration_$TIMESTAMP.sql"
    pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" > "$temp_dump"
    
    # Restore to new database
    export PGPASSWORD="$DB_PASSWORD"
    psql -h "$DB_HOST" -p "$DB_PORT" -U zip_league_user -d zip_league < "$temp_dump"
    
    if [[ $? -eq 0 ]]; then
        log "Data migrated to new database: zip_league"
        rm "$temp_dump"
    else
        error "Failed to migrate to new database"
    fi
}

setup_virtual_environment() {
    log "Setting up virtual environment..."
    
    cd "$NEW_PROJECT_DIR"
    
    # Create virtual environment if it doesn't exist
    if [[ ! -d "$VENV_PATH" ]]; then
        python3 -m venv "$VENV_PATH"
    fi
    
    # Activate virtual environment
    source "$VENV_PATH/bin/activate"
    
    # Install requirements
    if [[ -f "requirements.txt" ]]; then
        pip install -r requirements.txt
        log "Requirements installed"
    else
        warn "requirements.txt not found"
    fi
}

run_django_migrations() {
    log "Running Django migrations..."
    
    cd "$NEW_PROJECT_DIR"
    source "$VENV_PATH/bin/activate"
    
    # Set environment for new database
    export DATABASE_NAME="zip_league"
    export DATABASE_USER="zip_league_user"
    export DATABASE_PASSWORD="$DB_PASSWORD"
    
    # Run migrations to ensure everything is in sync
    python manage.py migrate --fake-initial
    
    # Collect static files
    python manage.py collectstatic --noinput
    
    log "Django migrations completed"
}

update_configuration_files() {
    log "Updating configuration files..."
    
    cd "$NEW_PROJECT_DIR"
    
    # Update .env file
    if [[ -f ".env" ]]; then
        sed -i 's/DATABASE_NAME=spikeball_ranking/DATABASE_NAME=zip_league/g' .env
        sed -i 's/DATABASE_USER=spikeball_user/DATABASE_USER=zip_league_user/g' .env
        log ".env file updated"
    fi
    
    # Update any remaining configuration files
    find . -name "*.py" -type f -exec sed -i 's/spikeball_ranking/zip_league/g' {} +
    find . -name "*.conf" -type f -exec sed -i 's/spikeball_ranking/zip_league/g' {} +
    find . -name "*.yml" -type f -exec sed -i 's/spikeball_ranking/zip_league/g' {} +
    
    log "Configuration files updated"
}

test_application() {
    log "Testing application..."
    
    cd "$NEW_PROJECT_DIR"
    source "$VENV_PATH/bin/activate"
    
    # Run Django check
    python manage.py check
    
    if [[ $? -eq 0 ]]; then
        log "Django check passed"
    else
        error "Django check failed"
    fi
    
    # Test database connection
    python manage.py shell -c "from django.db import connection; connection.cursor()"
    
    if [[ $? -eq 0 ]]; then
        log "Database connection test passed"
    else
        error "Database connection test failed"
    fi
}

start_services() {
    log "Starting services..."
    
    # Update systemd service files if they exist
    if [[ -f "/etc/systemd/system/spikeball.service" ]]; then
        sed -i "s|$OLD_PROJECT_DIR|$NEW_PROJECT_DIR|g" /etc/systemd/system/spikeball.service
        sed -i 's/spikeball_ranking/zip_league/g' /etc/systemd/system/spikeball.service
        systemctl daemon-reload
        systemctl restart spikeball
        log "Systemd service updated and restarted"
    fi
    
    # Start web server
    if systemctl is-enabled --quiet apache2; then
        systemctl start apache2
        log "Apache2 started"
    fi
    
    if systemctl is-enabled --quiet nginx; then
        systemctl start nginx
        log "Nginx started"
    fi
    
    log "Services started"
}

cleanup() {
    log "Performing cleanup..."
    
    # Keep the old directory as backup for now
    if [[ -d "$OLD_PROJECT_DIR" ]]; then
        mv "$OLD_PROJECT_DIR" "$OLD_PROJECT_DIR.backup.$TIMESTAMP"
        log "Old project directory backed up to $OLD_PROJECT_DIR.backup.$TIMESTAMP"
    fi
    
    log "Cleanup completed"
}

main() {
    log "Starting complete migration from SpikeballRanking to ZipLeague"
    
    check_prerequisites
    read_env_config
    backup_database
    stop_services
    rename_project_directory
    update_database_schema
    update_database_user_and_name
    setup_virtual_environment
    run_django_migrations
    update_configuration_files
    test_application
    start_services
    cleanup
    
    log "Migration completed successfully!"
    log "Backup files are stored in: $BACKUP_DIR"
    log "Old project directory backed up to: $OLD_PROJECT_DIR.backup.$TIMESTAMP"
    log ""
    log "Next steps:"
    log "1. Test the application thoroughly"
    log "2. Update your DNS/domain settings if needed"
    log "3. Update any external integrations"
    log "4. Remove backup files after confirming everything works"
}

# Handle script interruption
trap 'error "Migration interrupted. Check logs and restore from backup if needed."' INT TERM

# Run main function
main "$@"
