# PCP-DKFZ Transfer Tool - Quick Reference

## Setup
```bash
# One-time authentication setup
export NEXTCLOUD_TOKEN="username:app-password"
```

## Shared Folders
- `/_shared/pedcanportal_all/` - All users (read/write)
- `/_shared/cbioportal_uploaders/` - Restricted access (read/write)

## Commands

### Info
```bash
pcpdt info                          # Show shared folders info
```

### Upload
```bash
pcpdt upload file.pdf /Documents/   # To personal space
pcpdt upload file.csv /_shared/pedcanportal_all/   # To shared folder
pcpdt upload ./folder /Projects/    # Upload entire folder
```

### Download
```bash
pcpdt download /Documents/file.pdf ./
pcpdt download /_shared/pedcanportal_all/data.csv ./
```

### List
```bash
pcpdt list /                        # List root directory
pcpdt list /_shared/pedcanportal_all/   # List shared folder
```

### Share (Internal Only)
```bash
pcpdt share /file.pdf username      # Share with user
pcpdt share /file.pdf @groupname    # Share with group
pcpdt share /folder @team -p write  # Share with write access
```

## Important Notes
- ❌ **No public links** for regular users (admin only)
- ✅ Use shared folders for collaboration
- ✅ Internal sharing with users/groups allowed
- 🔐 Always use app passwords

## Examples

### Team Collaboration
```bash
# Upload to shared space
pcpdt upload results.xlsx /_shared/pedcanportal_all/june-2024/

# Others download
pcpdt download /_shared/pedcanportal_all/june-2024/results.xlsx
```

### Restricted Upload
```bash
# Only for cbioportal_uploaders role
pcpdt upload patient-data.zip /_shared/cbioportal_uploaders/
```

## Troubleshooting
- **Auth failed**: Check app password
- **Access denied**: Check folder permissions/role
- **No public links**: Use internal sharing instead