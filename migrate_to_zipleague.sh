#!/bin/bash
# migrate_to_zipleague.sh
# Safely backup existing database and deploy code renamed to ZipLeague

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 ZipLeague Migration Script${NC}"
echo "This script will:"
echo "1. Backup your current database"
echo "2. Rename database tables from 'rankings_*' to 'core_*'"
echo "3. Update Django migration history"
echo "4. Pull latest ZipLeague code"
echo "5. Rebuild and restart containers"
echo "6. Apply any new migrations"

# Prompt for backup directory
read -p "Enter directory where backup should be saved: " BACKUP_DIR
mkdir -p "${BACKUP_DIR}"

# Timestamp for file naming
timestamp=$(date +"%Y%m%d_%H%M%S")

# Load DB credentials from .env
if [ ! -f .env ]; then
    echo -e "${RED}❌ .env file not found!${NC}"
    exit 1
fi

export $(grep -E '^(DB_NAME|DB_USER|DB_PASSWORD|DB_HOST|DB_PORT)=' .env | xargs)

# Backup filename
backup_file="${BACKUP_DIR}/${DB_NAME}_backup_${timestamp}.sql"

echo -e "\n${YELLOW}[1/7] Backing up database '${DB_NAME}' to '${backup_file}'...${NC}"
# Dump the database from the 'db' container
docker-compose exec -T db pg_dump -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" "$DB_NAME" > "$backup_file"

echo "Compressing backup..."
gzip -f "$backup_file"

echo -e "${GREEN}✅ Backup completed: ${backup_file}.gz${NC}"

# Confirm before proceeding
echo -e "\n${YELLOW}⚠️  This will modify your database and deploy new code.${NC}"
echo -n "Proceed to pull new code and apply ZipLeague rename? [y/N]: "
read answer
if [[ ! "$answer" =~ ^[Yy]$ ]]; then
  echo "Aborting migration."
  exit 1
fi

echo -e "\n${YELLOW}[2/7] Checking existing database structure...${NC}"
# Check if rankings tables exist
table_exists=$(docker-compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'rankings_player');")

if [[ "$table_exists" =~ "t" ]]; then
    echo -e "${YELLOW}[3/7] Renaming database tables from 'rankings_*' to 'core_*'...${NC}"
    
    # Rename tables
    docker-compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" <<EOF
-- Rename main tables
ALTER TABLE IF EXISTS rankings_player RENAME TO core_player;
ALTER TABLE IF EXISTS rankings_match RENAME TO core_match;
ALTER TABLE IF EXISTS rankings_registrationtoken RENAME TO core_registrationtoken;

-- Rename sequences
ALTER SEQUENCE IF EXISTS rankings_player_id_seq RENAME TO core_player_id_seq;
ALTER SEQUENCE IF EXISTS rankings_match_id_seq RENAME TO core_match_id_seq;
ALTER SEQUENCE IF EXISTS rankings_registrationtoken_id_seq RENAME TO core_registrationtoken_id_seq;

-- Update django_content_type table
UPDATE django_content_type SET app_label = 'core' WHERE app_label = 'rankings';

-- Update django_migrations table
UPDATE django_migrations SET app = 'core' WHERE app = 'rankings';

EOF
    
    echo -e "${GREEN}✅ Database tables renamed successfully${NC}"
else
    echo -e "${GREEN}✅ No 'rankings_*' tables found, skipping table rename${NC}"
fi

echo -e "\n${YELLOW}[4/7] Pulling latest code from Git...${NC}"
git stash push -m "Pre-migration stash $(date)"
git pull origin main

echo -e "\n${YELLOW}[5/7] Rebuilding Docker images and starting containers...${NC}"
docker-compose down
docker-compose up -d --build

# Wait for containers to be ready
echo "Waiting for containers to be ready..."
sleep 15

echo -e "\n${YELLOW}[6/7] Applying Django migrations...${NC}"
# Mark core migrations as already applied (since we renamed the tables)
docker-compose exec web python manage.py migrate core --fake
# Apply any other pending migrations
docker-compose exec web python manage.py migrate --noinput

echo -e "\n${YELLOW}[7/7] Collecting static files...${NC}"
docker-compose exec web python manage.py collectstatic --noinput

# Verify everything is working
echo -e "\n${YELLOW}Verifying migration...${NC}"
docker-compose exec web python manage.py check --deploy

echo -e "\n${GREEN}✅ Migration to ZipLeague naming complete!${NC}"
echo -e "${GREEN}✅ Application restarted successfully!${NC}"
echo -e "\n${YELLOW}Next steps:${NC}"
echo "1. Test your application at http://localhost:8000 (or your domain)"
echo "2. Verify all data is intact"
echo "3. If everything looks good, you can delete the backup: ${backup_file}.gz"
echo "4. Consider updating your .env file with new database names if needed"
