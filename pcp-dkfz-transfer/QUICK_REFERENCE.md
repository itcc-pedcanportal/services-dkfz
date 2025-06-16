# PCP-DKFZ Transfer Tool - Quick Reference

## Setup
```bash
# One-time authentication setup
export NEXTCLOUD_TOKEN="username:app-password"
```

## Shared Folders
- `/Global/` - All users (read/write)
- Top-level directory - Admin only

**IMPORTANT:**
- Everything inside `/Global/` is shared among all users
- Everything outside `/Global/` is shared only with the admin

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
pcpdt share /file.pdf username -p write  # Share with write access
```

**Note:** Group sharing is not implemented.

## Important Notes
- ❌ **No public links** - public sharing is switched off
- ❌ **No group sharing** - group sharing is not implemented
- ✅ Use `/Global/` folder for collaboration
- ✅ Internal sharing with specific users only
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
- **Access denied**: Remember that only `/Global/` is shared with all users
- **Sharing issues**: Only sharing with specific users is supported
