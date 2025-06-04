# ZipLeague Migration Deployment Checklist

## Pre-Migration (Development)
- [ ] All code changes committed and tested locally
- [ ] Migration scripts tested in development environment
- [ ] Database backup strategy confirmed
- [ ] Rollback plan documented and tested
- [ ] Downtime window scheduled and communicated

## Migration Execution
- [ ] Server access confirmed (SSH/terminal)
- [ ] All migration scripts uploaded to server
- [ ] Scripts made executable (`chmod +x *.sh`)
- [ ] Current application state verified working
- [ ] Database credentials ready
- [ ] Run `migrate_to_zipleague_complete.sh`
- [ ] Monitor script output for errors
- [ ] Complete without interruption

## Post-Migration Verification
- [ ] Run `verify_migration.sh`
- [ ] Review verification report
- [ ] Test admin interface login
- [ ] Test main application functionality
- [ ] Verify data integrity (player/match counts)
- [ ] Check all templates render correctly
- [ ] Test user registration flow
- [ ] Test match recording
- [ ] Verify leaderboard display

## Configuration Updates
- [ ] Update web server configuration (Apache/Nginx)
- [ ] Update systemd service files
- [ ] Update SSL certificate paths if needed
- [ ] Update monitoring configurations
- [ ] Update backup scripts
- [ ] Test automated backups work

## External Dependencies
- [ ] Update DNS records if domain changed
- [ ] Update any external API configurations
- [ ] Update monitoring service configurations
- [ ] Update CI/CD pipeline configurations
- [ ] Notify any external integrations

## Testing Phase (First 24-48 Hours)
- [ ] Monitor application logs for errors
- [ ] Check database performance
- [ ] Verify all user workflows
- [ ] Test edge cases and error conditions
- [ ] Monitor server resource usage
- [ ] Collect user feedback

## Cleanup (After 1-2 Weeks)
- [ ] Application running stable
- [ ] No critical issues reported
- [ ] Remove old backup directories
- [ ] Update documentation
- [ ] Archive migration scripts
- [ ] Update team knowledge base

## Emergency Procedures
- [ ] Rollback script tested and ready
- [ ] Emergency contact list updated
- [ ] Escalation procedure documented
- [ ] Database restore procedure tested

## Success Criteria
- [ ] Application loads without errors
- [ ] All user workflows functional
- [ ] Data integrity maintained
- [ ] Performance acceptable
- [ ] No critical bugs reported
- [ ] Admin interface working
- [ ] Search functionality working
- [ ] User registration working
- [ ] Match recording working

## Command Quick Reference

### Check Application Status
```bash
cd /var/www/ZipLeague
source venv/bin/activate
python manage.py check
```

### Verify Database
```bash
python manage.py shell -c "
from core.models import Player, Match
print(f'Players: {Player.objects.count()}')
print(f'Matches: {Match.objects.count()}')
"
```

### Check Services
```bash
systemctl status apache2
systemctl status nginx
systemctl status zipleague  # if using systemd service
```

### View Logs
```bash
tail -f /var/log/apache2/error.log
tail -f /var/log/nginx/error.log
journalctl -u zipleague -f
```

### Emergency Rollback
```bash
sudo ./rollback_migration.sh
```

## Risk Assessment

### High Risk Items
- Database schema changes
- File system restructuring
- Service configuration updates

### Mitigation
- Comprehensive backups before migration
- Tested rollback procedure
- Verification scripts
- Minimal change deployment approach

### Recovery Time
- Rollback: 5-10 minutes
- Full restore from backup: 15-30 minutes

## Contact Information
- Server Administrator: [Your Contact]
- Database Administrator: [Your Contact]
- Development Team: [Your Contact]
- Emergency Contact: [Your Contact]

---

**Note**: Keep this checklist handy during migration and mark off each item as completed. Do not skip verification steps.
