# PCP-DKFZ Transfer Tool (pcpdt)

A simple, cross-platform command-line tool for uploading, downloading, and sharing files via the PedCanPortal Nextcloud instance.

## Features

- 📤 **Upload** files and folders to your personal space or shared folders
- 📥 **Download** files from Nextcloud
- 📁 **Access shared folders** for collaboration
- 👥 **Internal sharing** with users and groups (no public links)
- 🔒 **Secure** - uses HTTPS and app passwords
- 📦 **Zero dependencies** - uses only Python standard library
- 🖥️ **Cross-platform** - works on Windows, macOS, and Linux

## Shared Folders

This Nextcloud instance provides shared folders for collaboration:

- **`/_shared/pedcanportal_all/`** - Available to all authenticated users (read/write)
- **`/_shared/cbioportal_uploaders/`** - Only for users with `cbioportal_uploaders` role (read/write)

**Note:** Public share links are restricted to admin users only. All sharing is done internally.

## Requirements

- Python 3.6 or higher (pre-installed on most modern systems)
- Nextcloud account with app password

## Installation

1. Clone the repository:
```bash
git clone https://github.com/itcc-pedcanportal/services-dkfz.git
cd services-dkfz/pcp-dkfz-transfer
```

2. The script is already executable. If not:
```bash
chmod +x pcpdt
```

3. Optionally, add to your PATH:
```bash
# Linux/macOS
sudo cp pcpdt /usr/local/bin/

# Or add current directory to PATH
echo 'export PATH="$PATH:'$(pwd)'"' >> ~/.bashrc
source ~/.bashrc
```

## Authentication

### Get App Password

1. Log in to Nextcloud: https://cbioportal-upload.pedcanportal.eu
2. Go to Settings → Security
3. Create a new app password
4. Use this password with your username

### Set Authentication

**Method 1: Environment Variable (Recommended)**
```bash
export NEXTCLOUD_TOKEN="your-username:your-app-password"
```

**Method 2: Interactive Prompt**
Just run any command without setting the token.

## Usage

### Show Shared Folders Information
```bash
pcpdt info
```

### Upload Files

Upload to your personal space:
```bash
pcpdt upload report.pdf /Documents/
pcpdt upload data.csv /Projects/Analysis/
```

Upload to shared folders:
```bash
# Upload to shared folder (all users)
pcpdt upload results.csv /_shared/pedcanportal_all/

# Upload to restricted folder (cbioportal_uploaders only)
pcpdt upload sensitive-data.tar.gz /_shared/cbioportal_uploaders/
```

Upload entire folder:
```bash
pcpdt upload ./results /Projects/Experiment1/
```

### Download Files

Download from your personal space:
```bash
pcpdt download /Documents/report.pdf ./
pcpdt download /Projects/data.csv ~/Downloads/
```

Download from shared folders:
```bash
pcpdt download /_shared/pedcanportal_all/shared-data.csv ./
```

### List Files

List files in a directory:
```bash
pcpdt list /Documents/
pcpdt list /_shared/pedcanportal_all/
```

### Share with Other Users (Internal Only)

Share with specific user:
```bash
pcpdt share /Documents/report.pdf colleague_username
```

Share with group (use @ prefix):
```bash
pcpdt share /Projects/results.csv @researchers -p write
```

Available permissions: `read`, `write`, `all`

## Examples

### Example 1: Collaborate via Shared Folder

```bash
# Upload data for all team members
pcpdt upload analysis-results.xlsx /_shared/pedcanportal_all/2024-06-Results/

# Team members can download
pcpdt download /_shared/pedcanportal_all/2024-06-Results/analysis-results.xlsx ./
```

### Example 2: Restricted Data Upload

```bash
# Only users with cbioportal_uploaders role can access
pcpdt upload patient-data.tar.gz /_shared/cbioportal_uploaders/cohort-A/

# List files in restricted folder (only if you have access)
pcpdt list /_shared/cbioportal_uploaders/
```

### Example 3: Automated Script

```bash
#!/bin/bash
# Daily upload to shared folder

DATE=$(date +%Y%m%d)
REPORT="daily-report-$DATE.pdf"

# Generate report
generate_report.sh > "$REPORT"

# Upload to shared folder
NEXTCLOUD_TOKEN="user:app-password" pcpdt upload "$REPORT" /_shared/pedcanportal_all/reports/

# Clean up
rm "$REPORT"
```

## Important Notes

1. **No Public Links**: Public share links are disabled for regular users. Only admins can create public links.

2. **Internal Sharing Only**: Use the `share` command to share with other Nextcloud users or groups.

3. **Shared Folder Access**: 
   - Everyone can read/write to `/_shared/pedcanportal_all/`
   - Only users with `cbioportal_uploaders` role can access `/_shared/cbioportal_uploaders/`

4. **App Passwords**: Always use app passwords, never your main login password.

## Troubleshooting

### "Authentication failed"
- Ensure you're using an app password, not your regular password
- Check username is correct
- Verify token format: `username:app-password`

### "Permission denied" accessing shared folders
- `/_shared/pedcanportal_all/` - Should work for all authenticated users
- `/_shared/cbioportal_uploaders/` - Check if you have the `cbioportal_uploaders` role

### Cannot create public share links
- This is intentional - only admins can create public links
- Use internal sharing: `pcpdt share file.txt @groupname`

## Platform Notes

### Windows
```cmd
python pcpdt upload C:\data\file.txt /Documents/
```

### macOS/Linux
```bash
./pcpdt upload ~/data/file.txt /Documents/
```

## Support

- Tool issues: Create issue on [GitHub](https://github.com/itcc-pedcanportal/services-dkfz)
- Access problems: Contact your Nextcloud administrator
- Server: https://cbioportal-upload.pedcanportal.eu