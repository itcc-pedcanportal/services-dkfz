# PCP-DKFZ Transfer Tool (pcpdt)

A simple, cross-platform command-line tool for uploading, downloading, and sharing files via the PedCanPortal Nextcloud instance.

**Current Version:** 1.3.1

## Features

- 📤 **Upload** files and folders to your personal space or shared folders
- 📥 **Download** files from Nextcloud with resume support
- 📁 **Access shared folders** for collaboration
- 👥 **Internal sharing** with specific users (no public links or group sharing)
- 📊 **Progress tracking** - visual progress bar with speed and ETA
- 🔄 **Parallel uploads** - upload multiple files simultaneously
- 🔁 **Retry mechanism** - automatically handles connection resets
- 🔒 **Secure** - uses HTTPS and app passwords
- 📦 **Zero dependencies** - uses only Python standard library
- 🖥️ **Cross-platform** - works on Windows, macOS, and Linux

## Shared Folders

This Nextcloud instance provides a shared folder for collaboration:

- **`/Global/`** - Available to all authenticated users (read/write)

**IMPORTANT:** 
- Everything inside `/Global/` is shared among all users (read/write)
- Everything outside `/Global/` is shared only with the admin
- There is a top-level directory that is only visible to the admin

**Note:** Public share links are switched off and group sharing is not implemented. All sharing is done internally with specific users only.

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

### Command-Line Options

```bash
# Show help
pcpdt --help

# Enable verbose mode (debug output)
pcpdt -v <command>

# Quiet mode (suppress progress information)
pcpdt -q <command>
```

### Show Information
```bash
# Show shared folders and upload methods
pcpdt info
```

### Upload Files

Upload to your personal space:
```bash
pcpdt upload report.pdf /Documents/
pcpdt upload data.csv /Projects/Analysis/
```

Upload to shared folder:
```bash
# Upload to Global shared folder (all users)
pcpdt upload results.csv /Global/
```

Upload entire folder:
```bash
pcpdt upload ./results /Projects/Experiment1/
```

Advanced upload options:
```bash
# Upload with chunked method (more reliable for unstable connections)
pcpdt upload --chunk large_file.zip /Global/

# Upload with parallel chunks (faster chunked uploads)
pcpdt upload --chunk --parallel-chunks 4 large_file.zip /Global/

# Upload directory with parallel file uploads (faster for many small files)
pcpdt upload -p 8 ./my_folder /Global/
```

### Download Files

Download from your personal space:
```bash
pcpdt download /Documents/report.pdf ./
pcpdt download /Projects/data.csv ~/Downloads/
```

Download from shared folder:
```bash
pcpdt download /Global/shared-data.csv ./
```

Downloads include:
- Progress bar showing download status
- Automatic resume of interrupted downloads
- Proper handling of large files

### List Files

List files in a directory:
```bash
pcpdt list /Documents/
pcpdt list /Global/
```

### Share with Other Users (Internal Only)

Share with specific user:
```bash
pcpdt share /Documents/report.pdf colleague_username
```

Available permissions: `read`, `write`, `all`

**Note:** Group sharing is not implemented in this Nextcloud instance.

## Examples

### Example 0: Progress Bar and Performance

```bash
# Upload with progress bar (automatic)
pcpdt upload large_file.zip /Global/
# Output:
# large_file.zip | ██████████░░░░░░░░ | 50.5% | 5.2 MB/s | ETA: 0:01:30

# Download with progress bar (automatic)
pcpdt download /Global/large_file.zip ./
# Output:
# [========================          ] 67,108,864/134,217,728 bytes

# Parallel uploads for better performance
pcpdt upload -p 4 ./dataset /Global/
# Output:
# Using 4 parallel uploads for 20 files...
```

### Example 1: Collaborate via Shared Folder

```bash
# Upload data for all team members
pcpdt upload analysis-results.xlsx /Global/2024-06-Results/

# Team members can download
pcpdt download /Global/2024-06-Results/analysis-results.xlsx ./
```

### Example 2: Personal Space Upload

```bash
# Upload to your personal space
pcpdt upload patient-data.tar.gz /Documents/cohort-A/

# List files in your personal folder
pcpdt list /Documents/
```

### Example 3: Automated Script

```bash
#!/bin/bash
# Daily upload to shared folder

DATE=$(date +%Y%m%d)
REPORT="daily-report-$DATE.pdf"

# Generate report
generate_report.sh > "$REPORT"

# Upload to Global shared folder
NEXTCLOUD_TOKEN="user:app-password" pcpdt upload "$REPORT" /Global/reports/

# Clean up
rm "$REPORT"
```

## Important Notes

1. **No Public Links**: Public share links are switched off in this Nextcloud instance.

2. **Internal Sharing Only**: Use the `share` command to share with specific Nextcloud users (not groups).

3. **Shared Folder Access**: 
   - Everything inside `/Global/` is shared among all users (read/write)
   - Everything outside `/Global/` is shared only with the admin
   - There is a top-level directory that is only visible to the admin

4. **App Passwords**: Always use app passwords, never your main login password.

## Troubleshooting

### "Authentication failed"
- Ensure you're using an app password, not your regular password
- Check username is correct
- Verify token format: `username:app-password`

### "Permission denied" accessing shared folder
- `/Global/` - Should work for all authenticated users
- Top-level directory - Only visible to the admin

### Cannot create public share links
- This is intentional - public share links are switched off
- Use internal sharing: `pcpdt share file.txt username`

### Connection issues during upload
- If uploads fail with "Connection reset by peer" errors:
  - Use chunked mode: `pcpdt upload --chunk large_file.zip /Global/`
  - For faster chunked uploads: `pcpdt upload --chunk --parallel-chunks 4 large_file.zip /Global/`
- The tool includes an automatic retry mechanism (up to 20 retries with exponential backoff)
- Use verbose mode to see detailed error information: `pcpdt -v upload file.txt /Global/`

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
