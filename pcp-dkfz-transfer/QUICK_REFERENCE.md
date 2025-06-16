# PCP-DKFZ Transfer Tool - Quick Reference

## Setup
```bash
# One-time authentication setup
export NEXTCLOUD_TOKEN="username:app-password"
```

## Shared Folders
- `/Global/` - All users (read/write)
- Top-level directory - Admin only

## Commands

### Info
```bash
pcpdt info                          # Show shared folders info
```

### Upload
```bash
pcpdt upload file.pdf /Documents/   # To personal space
pcpdt upload file.csv /Global/   # To shared folder
pcpdt upload ./folder /Projects/    # Upload entire folder
```

### Download
```bash
pcpdt download /Documents/file.pdf ./
pcpdt download /Global/data.csv ./
```

### List
```bash
pcpdt list /                        # List root directory
pcpdt list /Global/   # List shared folder
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
pcpdt upload results.xlsx /Global/june-2024/

# Others download
pcpdt download /Global/june-2024/results.xlsx
```

### Personal Space Upload
```bash
# Upload to your personal space
pcpdt upload patient-data.zip /Documents/sensitive-data/
```

## Troubleshooting
- **Auth failed**: Check app password
- **Access denied**: Check folder permissions/role
- **No public links**: Use internal sharing instead
