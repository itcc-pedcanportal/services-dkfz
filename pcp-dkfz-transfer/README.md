# PCP-DKFZ Transfer Tool (pcpdt)

A simple command-line tool for transferring files to the PedCanPortal Nextcloud instance. This tool allows collaborators to easily copy data to DKFZ for integration into the initiatives portal.

**Purpose:** This tool is designed for ITCC collaborators to transfer data to DKFZ. It's a straightforward utility that mimics the behavior of standard file copy commands like `cp -r` while handling the authentication and transfer to the Nextcloud server.

**Current Version:** 1.0.0

## Features

- Upload files and folders to the Nextcloud instance (similar to cp -r)
- Download files from Nextcloud
- Access the Global shared folder for collaboration
- Basic file operations: upload, download, list files
- Works on Windows, macOS, and Linux

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
- App password from our Nextcloud instance (see Authentication section below)

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
4. Use this password with your username as environment variable or interactive prompt

### Set Authentication

**Method 1: Environment Variable (Recommended)**

For Linux/macOS (Bash/Zsh):
```bash
export NEXTCLOUD_TOKEN="your-username:your-app-password"
```

For Windows Command Prompt:
```cmd
set NEXTCLOUD_TOKEN=your-username:your-app-password
```

For Windows PowerShell:
```powershell
$env:NEXTCLOUD_TOKEN = "your-username:your-app-password"
```

To make the environment variable persistent:
- **Linux**: Add the export command to your `~/.bashrc` or `~/.zshrc`
- **macOS**: Add the export command to your `~/.bash_profile` or `~/.zshrc`
- **Windows**: Set through System Properties > Advanced > Environment Variables

**Method 2: Interactive Prompt**
Just run any command without setting the token. The tool will prompt you for credentials.

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
pcpdt upload report.pdf /
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

For directory uploads (similar to cp -r):
```bash
# Upload a directory and all its contents
pcpdt upload ./my_folder /Global/
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


### List Files

List files in a directory:
```bash
pcpdt list
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


### Basic Usage Example

```bash
# Upload data to the shared folder
pcpdt upload analysis-results.xlsx /Global/

# Download files from the shared folder
pcpdt download /Global/analysis-results.xlsx ./

# List files in the shared folder
pcpdt list /Global/
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
- If uploads fail, try using verbose mode for more information: `pcpdt -v upload file.txt /Global/`
- For large files or unstable connections, use the chunked mode: `pcpdt upload --chunk large_file.zip /Global/`

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

- Tool issues: Create issue on [GitHub](https://github.com/itcc-pedcanportal/services-dkfz/issues)
- Access problems: Contact [julius.mueller@dkfz-heidelberg.de](mailto:julius.mueller@dkfz-heidelberg.de)
- Server: https://cbioportal-upload.pedcanportal.eu
