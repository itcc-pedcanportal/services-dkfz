# PCP-DKFZ Transfer Tool - Quick Reference

## Setup (One Time)
```bash
# Set credentials
export NEXTCLOUD_TOKEN="username:app-password"

# Get app password from:
# https://cbioportal-upload.pedcanportal.eu/settings/user/security
```

## Basic Commands

### Upload
```bash
# Upload file
pcpdt upload myfile.pdf /Documents/

# Upload folder
pcpdt upload ./data /Projects/
```

### Download
```bash
# Download your file
pcpdt download /Documents/report.pdf ./

# Download from share
pcpdt download https://nextcloud/s/ABC123 ./

# Download password-protected share
pcpdt download https://nextcloud/s/ABC123 ./ -p password
```

### Share
```bash
# Create simple share
pcpdt share /Documents/file.pdf

# With password & 7-day expiry
pcpdt share /Projects/data.zip -p pass123 -e 7
```

## Common Workflows

### Share with External User
```bash
# 1. Upload and share
pcpdt upload results.tar.gz /Shared/
pcpdt share /Shared/results.tar.gz -p secret -e 14

# 2. Send them:
# URL: https://nextcloud/s/ABC123
# Pass: secret
# They download: wget "https://nextcloud/s/ABC123/download"
```

### Automated Backup
```bash
#!/bin/bash
DATE=$(date +%Y%m%d)
tar -czf backup-$DATE.tar.gz /data/
NEXTCLOUD_TOKEN="user:pass" pcpdt upload backup-$DATE.tar.gz /Backups/
rm backup-$DATE.tar.gz
```

## Options
- `-q` : Quiet mode (no progress)
- `-t` : Specify token on command line
- `-p` : Password (for shares)
- `-e` : Expiry days (for shares)

## Troubleshooting
- **Auth failed**: Use app password, not regular password
- **SSL error**: Update system certificates
- **Not found**: Check file paths start with /