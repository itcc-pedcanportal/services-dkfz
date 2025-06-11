#!/usr/bin/env bash

# Bash script to upload a file to Zipline with progress bar and optional expiry
# Usage: ./upload_to_zipline.sh <API_TOKEN> <FILE_PATH> [--delete-after <1d|7d|30d>]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

show_help() {
  echo "Usage: $0 <API_TOKEN> <FILE_PATH> [--delete-after <1d|7d|30d>]"
  exit 1
}

if [ $# -lt 2 ]; then
  show_help
fi

TOKEN="$1"
FILE="$2"
DELETE_AFTER=""
ZIPLINE_URL="https://cbioportal-upload.pedcanportal.de/api/upload"

# Check for --delete-after argument
shift 2
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --delete-after)
      DELETE_AFTER="$2"
      shift 2
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      show_help
      ;;
  esac
done

# Validate file
if [ ! -f "$FILE" ]; then
  echo -e "${RED}Error: File not found: $FILE${NC}"
  exit 1
fi

echo -e "${GREEN}Uploading file: $FILE${NC}"

# Build curl command
CURL_CMD=(
  curl -X POST "$ZIPLINE_URL"
  -H "Authorization: Bearer $TOKEN"
  --progress-bar
  -F "file=@$FILE"
)

# If delete-after is set, add header
if [ -n "$DELETE_AFTER" ]; then
  CURL_CMD+=( -H "x-zipline-deletes-at: $DELETE_AFTER" )
fi

# Execute upload
RESPONSE=$("${CURL_CMD[@]}")

# Check if upload succeeded
if echo "$RESPONSE" | grep -q '"success":true'; then
  echo -e "\n${GREEN}Upload successful!${NC}"
  echo "Response: $RESPONSE"
else
  echo -e "\n${RED}Upload failed!${NC}"
  echo "Response: $RESPONSE"
  exit 1
fi
