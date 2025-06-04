# ZipLeague Migration Guide

This guide covers the complete migration process from SpikeballRanking to ZipLeague, including database changes, code refactoring, and safe deployment.

## Overview

The migration transforms a spikeball-specific ranking system into a generic sport-agnostic league management system called "ZipLeague".

### Key Changes
- **App name**: `rankings` → `core`
- **Project name**: `spikeball_ranking` → `zip_league`
- **Database**: `spikeball_ranking` → `zip_league`
- **Database user**: `spikeball_user` → `zip_league_user`
- **Templates**: All `rankings/*` → `core/*`
- **Branding**: "SpikeBall Rankings" → "ZipLeague"

## Migration Scripts

### 1. `migrate_to_zipleague_complete.sh`
**Main migration script** - Handles the complete migration process including:
- Database backup
- Service management
- Directory renaming
- Database schema updates
- Django migration history updates
- Configuration file updates
- Testing and validation

### 2. `rollback_migration.sh`
**Rollback script** - Use this if the migration fails:
- Restores database from backup
- Restores project directory
- Reverts service configurations

### 3. `verify_migration.sh`
**Verification script** - Tests the migration results:
- Checks project structure
- Validates Django configuration
- Tests database connectivity
- Verifies models and admin interface
- Generates a detailed report

## Pre-Migration Preparation

### 1. Requirements
- Ubuntu/Debian Linux server
- PostgreSQL database
- Python 3.8+
- Django application
- Root or sudo access

### 2. Pre-flight Checklist
```bash
# 1. Verify current setup
cd /var/www/SpikeballRanking
python manage.py check
python manage.py migrate --check

# 2. Create additional backup
cp -r /var/www/SpikeballRanking /var/backups/manual_backup_$(date +%Y%m%d)

# 3. Test database connection
python manage.py shell -c "from django.db import connection; connection.cursor()"

# 4. Note current statistics
python manage.py shell -c "
from rankings.models import Player, Match
print(f'Players: {Player.objects.count()}')
print(f'Matches: {Match.objects.count()}')
"
```

## Migration Process

### Step 1: Run the Migration
```bash
# Make script executable
chmod +x migrate_to_zipleague_complete.sh

# Run migration (will prompt for database password)
sudo ./migrate_to_zipleague_complete.sh
```

### Step 2: Verify Migration
```bash
# Make verification script executable
chmod +x verify_migration.sh

# Run verification
sudo ./verify_migration.sh
```

### Step 3: Manual Testing
After successful migration, manually test:

1. **Admin Interface**: Visit `/admin/` and verify:
   - Can log in
   - Models appear correctly
   - Can create/edit records

2. **Main Application**: Test core functionality:
   - Home page loads
   - Leaderboard displays
   - Match recording works
   - User registration works

3. **Database Integrity**: Verify data:
   ```bash
   cd /var/www/ZipLeague
   source venv/bin/activate
   python manage.py shell -c "
   from core.models import Player, Match
   print(f'Players: {Player.objects.count()}')
   print(f'Matches: {Match.objects.count()}')
   "
   ```

## Rollback Procedure

If issues occur during or after migration:

```bash
# Make rollback script executable
chmod +x rollback_migration.sh

# Run rollback
sudo ./rollback_migration.sh
```

## Post-Migration Tasks

### 1. Update External Configurations
- **DNS/Domain**: Update to point to new directory
- **SSL Certificates**: Update paths if needed
- **Monitoring**: Update service names
- **Backups**: Update backup scripts for new paths

### 2. Update Web Server Configuration
If using Apache or Nginx, update virtual host configurations:

```apache
# Apache example
DocumentRoot /var/www/ZipLeague
WSGIScriptAlias / /var/www/ZipLeague/zip_league/wsgi.py
```

```nginx
# Nginx example
root /var/www/ZipLeague;
uwsgi_param SCRIPT_NAME /var/www/ZipLeague/zip_league/wsgi.py;
```

### 3. Update Systemd Services
```bash
# Update service file
sudo nano /etc/systemd/system/zipleague.service

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart zipleague
```

### 4. Clean Up (After Confirming Everything Works)
```bash
# Remove old backups (after 1-2 weeks of stable operation)
sudo rm -rf /var/www/SpikeballRanking.backup.*
sudo rm -rf /var/backups/zipleague/spikeball_ranking_backup_*.sql.gz

# Keep at least one backup for safety
```

## Troubleshooting

### Common Issues

**1. Migration Script Fails**
- Check database connectivity
- Verify sufficient disk space
- Ensure all services are stopped
- Check file permissions

**2. Django Check Fails**
- Verify all imports are updated
- Check migration dependencies
- Ensure virtual environment is activated

**3. Database Connection Issues**
- Verify new database exists
- Check user permissions
- Confirm password is correct

**4. Template Errors**
- Check template inheritance paths
- Verify all `{% extends %}` tags are updated
- Ensure static files are collected

### Log Locations
- Migration logs: Console output (redirect with `2>&1 | tee migration.log`)
- Django logs: Check `zip_league/settings.py` LOGGING configuration
- Database logs: `/var/log/postgresql/`
- Web server logs: `/var/log/apache2/` or `/var/log/nginx/`

## Files Modified During Migration

### Project Structure
```
OLD: /var/www/SpikeballRanking/
├── rankings/                    → core/
├── spikeball_ranking/          → zip_league/
└── rankings/templates/rankings/ → core/templates/core/

NEW: /var/www/ZipLeague/
├── core/
├── zip_league/
└── core/templates/core/
```

### Configuration Files
- `zip_league/settings.py` - Updated INSTALLED_APPS
- `zip_league/urls.py` - Updated URL includes
- `zip_league/wsgi.py` - Updated module references
- `zip_league/asgi.py` - Updated module references
- `manage.py` - Updated settings module
- `.env` - Updated database configurations
- `docker-compose.yml` - Updated service references
- `Dockerfile` - Updated application paths

### Database Changes
- Tables: `rankings_*` → `core_*`
- Migration history: Updated app references
- Content types: Updated app labels
- Permissions: Updated content type references

## Security Considerations

- Database credentials are preserved
- File permissions are maintained
- Service configurations are updated securely
- Backups are created before any changes
- Rollback capability is provided

## Performance Impact

- Migration downtime: 5-15 minutes (depending on data size)
- No data loss occurs
- Application performance remains unchanged
- Database size unchanged (only table renames)

## Support

For issues during migration:
1. Check the verification report
2. Review migration logs
3. Use rollback script if needed
4. Restore from backup as last resort

Remember: The migration creates comprehensive backups, so you can always restore to the original state if needed.
