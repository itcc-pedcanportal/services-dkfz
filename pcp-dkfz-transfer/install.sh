#!/bin/bash
# Quick installer for PCP-DKFZ Transfer Tool

echo "Installing PCP-DKFZ Transfer Tool..."

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    echo "Please install Python 3 from https://python.org"
    exit 1
fi

# Download the tool
echo "Downloading pcpdt..."
curl -s -o pcpdt https://raw.githubusercontent.com/your-org/pcp-dkfz-transfer/main/pcpdt || {
    wget -q -O pcpdt https://raw.githubusercontent.com/your-org/pcp-dkfz-transfer/main/pcpdt
}

# Make executable
chmod +x pcpdt

# Test it works
if ./pcpdt --version > /dev/null 2>&1; then
    echo "✓ Installation successful!"
    echo ""
    echo "To use pcpdt from anywhere, either:"
    echo "1. Add $(pwd) to your PATH"
    echo "2. Copy to /usr/local/bin: sudo cp pcpdt /usr/local/bin/"
    echo ""
    echo "Quick start:"
    echo "  ./pcpdt upload myfile.txt /Documents/"
    echo "  ./pcpdt download /Documents/myfile.txt ./"
    echo "  ./pcpdt share /Documents/myfile.txt -p password -e 7"
    echo ""
    echo "Set your credentials:"
    echo "  export NEXTCLOUD_TOKEN='username:app-password'"
else
    echo "✗ Installation failed. Please check Python installation."
    exit 1
fi