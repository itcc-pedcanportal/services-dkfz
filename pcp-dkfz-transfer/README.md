# PCP-DKFZ Transfer Tool (pcpdt)

A simple, cross-platform command-line tool for uploading, downloading, and sharing files via the DKFZ Nextcloud instance.

## Features

- **Upload** files and folders to the DKFZ de.NBI cloud Nextcloud instance
- **Download** files from Nextcloud or public shares
- **Create shares** with optional passwords and expiry dates
- **Cross-platform** - works on Windows, macOS, and Linux
- **Secure** - uses HTTPS and supports password-protected shares

## Requirements

- Python 3.6 or higher (pre-installed on most modern systems)
- No additional packages required!

## Installation

### Quick Install

1. Clone the repository:
```bash
git clone https://github.com/your-org/pcp-dkfz-transfer.git
cd pcp-dkfz-transfer
```

2. Make the script executable (Linux/macOS):
```bash
chmod +x pcpdt
```

3. Optionally, add to your PATH:
```bash
# Linux/macOS
echo 'export PATH="$PATH:'$(pwd)'"' >> ~/.bashrc
source ~/.bashrc

# Or copy to a directory already in PATH
sudo cp pcpdt /usr/local/bin/
```

### Windows Installation

1. Clone or download the repository
2. Add the folder to your PATH environment variable, or
3. Run using `python pcpdt` from the folder

## Authentication

You can authenticate in two ways:

### Method 1: Environment Variable (Recommended)
```bash
export NEXTCLOUD_TOKEN="your-username:your-app-password"
```

### Method 2: Interactive Prompt
Simply run any command without setting the token, and you'll be prompted for credentials.

**Important**: Use app passwords, not your main password!
Get an app password from: https://cbioportal-upload.pedcanportal.de/settings/user/security

## Usage

### Upload Files

Upload a single file:
```bash
pcpdt upload report.pdf /Documents/
pcpdt upload data.csv /Projects/Analysis/
```

Upload an entire folder:
```bash
pcpdt upload ./results /Projects/Experiment1/
pcpdt upload ~/Desktop/data /Backup/
```

### Download Files

Download your own files:
```bash
pcpdt download /Documents/report.pdf ./
pcpdt download /Projects/data.csv ~/Downloads/
```

Download from a public share:
```bash
# Simple download (no password)
pcpdt download https://cbioportal-upload.pedcanportal.de/s/Hy7Kg9sX3 ./

# Password-protected share
pcpdt download https://cbioportal-upload.pedcanportal.de/s/Hy7Kg9sX3 ./ -p secretpass
```

### Create Shares

Create a simple share:
```bash
pcpdt share /Documents/report.pdf
```

Create a password-protected share with 7-day expiry:
```bash
pcpdt share /Projects/sensitive-data.zip -p mypassword -e 7
```

## Examples

### Example 1: Share Research Data with Collaborator

```bash
# Upload your data
pcpdt upload ~/research/results.tar.gz /Shared/

# Create a secure, time-limited share
pcpdt share /Shared/results.tar.gz -p "SecurePass123" -e 14

# Output:
# ✅ Share created successfully!
# 
# 📎 Share URL: https://cbioportal-upload.pedcanportal.de/s/Hy7Kg9sX3
# 🔒 Password: SecurePass123
# 📅 Expires: 14 days
# 
# Send the URL and password to your collaborator (separately for security)
```

### Example 2: Automated Backup Script

```bash
#!/bin/bash
# backup.sh - Daily backup to Nextcloud

DATE=$(date +%Y%m%d)
tar -czf backup-$DATE.tar.gz /important/data/

# Upload with token authentication
NEXTCLOUD_TOKEN="user:app-password" pcpdt upload backup-$DATE.tar.gz /Backups/

# Clean up
rm backup-$DATE.tar.gz
```

### Example 3: Download from Share on Remote Server

On a remote HPC cluster without GUI:
```bash
# Option 1: Using wget (if pcpdt not available)
wget "https://cbioportal-upload.pedcanportal.de/s/Hy7Kg9sX3/download" -O data.zip

# Option 2: Using pcpdt
./pcpdt download https://cbioportal-upload.pedcanportal.de/s/Hy7Kg9sX3 data.zip

# Option 3: Password-protected share
./pcpdt download https://cbioportal-upload.pedcanportal.de/s/Hy7Kg9sX3 -p password
```

## Advanced Usage

### Quiet Mode

For scripts and automation, use quiet mode:
```bash
pcpdt -q upload file.txt /Folder/
```

### Specify Token on Command Line

For one-off commands:
```bash
pcpdt -t "username:password" upload file.txt /
```

### Check Version

```bash
pcpdt --version
```

## Troubleshooting

### "Authentication failed"
- Make sure you're using an app password, not your regular password
- Check that your username is correct
- Verify the token format is `username:app-password`

### "SSL: CERTIFICATE_VERIFY_FAILED"
This can happen on some systems. Solutions:
1. Update your system's certificate store
2. On macOS: `brew install ca-certificates`
3. On older systems, you may need to update Python

### "Permission denied" on Linux/macOS
Make the script executable:
```bash
chmod +x pcpdt
```

### Download Issues with Shares
- Check if the share has expired
- Verify the password is correct
- Ensure the share URL is complete

## Security Best Practices

1. **Use App Passwords**: Never use your main Keycloak password
2. **Protect Share Passwords**: Send URLs and passwords via different channels
3. **Set Expiry Dates**: Use the shortest practical expiry time
4. **Clean Up**: Delete shares after they're no longer needed

## Platform-Specific Notes

### Windows
- Run using `python pcpdt` if not in PATH
- Use PowerShell or Command Prompt
- Paths use backslashes: `pcpdt upload C:\data\file.txt /`

### macOS
- May need to install certificates: `brew install ca-certificates`
- Use Terminal.app or iTerm2

### Linux
- Works out of the box on most distributions
- May need `python3` instead of `python` on older systems

## Contributing

Issues and pull requests welcome at: https://github.com/your-org/pcp-dkfz-transfer

## License

MIT License - See LICENSE file for details

## Support

For issues with:
- The tool itself: Create an issue on GitHub
- Nextcloud access: Contact ITCC support
- Account problems: Contact your administrator