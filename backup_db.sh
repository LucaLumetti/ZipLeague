#!/bin/bash

# Set variables
BACKUP_DIR="/home/llumetti/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DB_BACKUP_FILE="$BACKUP_DIR/zip_league_db_$TIMESTAMP.sql"
MEDIA_BACKUP_FILE="$BACKUP_DIR/zip_league_media_$TIMESTAMP.tar.gz"

# Ensure backup directory exists
mkdir -p $BACKUP_DIR

# Go to the project directory
cd /home/llumetti/ZipLeague

# Get database credentials from .env file
DB_NAME=$(grep DB_NAME .env | cut -d '=' -f2 | tr -d "'" | tr -d '"')
DB_USER=$(grep DB_USER .env | cut -d '=' -f2 | tr -d "'" | tr -d '"')
DB_PASSWORD=$(grep DB_PASSWORD .env | cut -d '=' -f2 | tr -d "'" | tr -d '"')
DB_HOST=$(grep DB_HOST .env | cut -d '=' -f2 | tr -d "'" | tr -d '"')

echo "Starting database backup..."
# Create database backup
docker compose exec -T db pg_dump -U $DB_USER -d $DB_NAME > $DB_BACKUP_FILE
if [ $? -eq 0 ]; then
    echo "Database backup successful."
else
    echo "Database backup failed!"
    exit 1
fi

# Compress the database backup
gzip $DB_BACKUP_FILE
echo "Database backup compressed: ${DB_BACKUP_FILE}.gz"

# Back up media files
echo "Starting media files backup..."
tar -czf $MEDIA_BACKUP_FILE -C /home/llumetti/ZipLeague media
if [ $? -eq 0 ]; then
    echo "Media files backup successful: $MEDIA_BACKUP_FILE"
else
    echo "Media files backup failed!"
fi

# Keep only the last 5 backups (increased retention period)
find $BACKUP_DIR -name "zipleague_db_*.sql.gz" -type f -mtime +5 -delete
find $BACKUP_DIR -name "zipleague_media_*.tar.gz" -type f -mtime +5 -delete

echo "Backup completed at $(date)"
echo "Database: ${DB_BACKUP_FILE}.gz"
echo "Media: $MEDIA_BACKUP_FILE"
