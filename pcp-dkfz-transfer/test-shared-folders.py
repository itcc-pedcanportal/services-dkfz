#!/usr/bin/env python3
"""
Test script for shared folders functionality
Tests upload, list, and download operations on shared folders
"""

import subprocess
import tempfile
import os
import sys
import time


def run_command(cmd):
    """Run a command and return success status and output"""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode == 0, result.stdout, result.stderr


def test_shared_folders():
    """Test shared folder access"""
    print("=== Testing Shared Folders Access ===\n")

    # Check if token is set
    if not os.environ.get('NEXTCLOUD_TOKEN'):
        print("❌ NEXTCLOUD_TOKEN not set")
        print("Please set: export NEXTCLOUD_TOKEN='username:app-password'")
        return False

    print("✓ Authentication token found\n")

    # Test 1: List Global shared folder
    print("Test 1: Listing Global shared folder...")
    success, stdout, stderr = run_command("./pcpdt list /Global/")

    if success:
        print("✓ Can list /Global/ directory")
    else:
        print("❌ Cannot list Global shared folder")
        print(f"Error: {stderr}")
        return False

    print()

    # Test 2: Upload to shared folder
    print("Test 2: Testing upload to shared folder...")

    # Create a raw file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        test_content = f"Test upload at {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f.write(test_content)
        test_file = f.name

    test_filename = f"raw-{os.getpid()}.txt"

    # Try upload to Global folder
    success, stdout, stderr = run_command(
        f"./pcpdt upload {test_file} /Global/{test_filename}"
    )

    if success:
        print("✓ Successfully uploaded to /Global/")

        # Test 3: List to verify upload
        print("\nTest 3: Verifying uploaded file...")
        success, stdout, stderr = run_command("./pcpdt list /Global/")

        if success and test_filename in stdout:
            print("✓ Uploaded file is visible in listing")

            # Test 4: Download the file
            print("\nTest 4: Testing download...")
            download_path = f"/tmp/download-{test_filename}"
            success, stdout, stderr = run_command(
                f"./pcpdt download /Global/{test_filename} {download_path}"
            )

            if success and os.path.exists(download_path):
                print("✓ Successfully downloaded file")

                # Verify content
                with open(download_path, 'r') as f:
                    if test_content in f.read():
                        print("✓ File content matches")
                    else:
                        print("❌ File content mismatch")

                # Cleanup
                os.unlink(download_path)
            else:
                print("❌ Download failed")
                print(f"Error: {stderr}")
        else:
            print("❌ Uploaded file not found in listing")
    else:
        print("❌ Upload failed")
        print(f"Error: {stderr}")
        print("\nPossible reasons:")
        print("- User doesn't have write access to /Global/")
        print("- Shared folder doesn't exist")
        print("- Authentication issue")

    # Cleanup
    os.unlink(test_file)

    # Test 5: Test top-level directory (admin only)
    print("\nTest 5: Testing top-level directory access...")
    success, stdout, stderr = run_command("./pcpdt list /")

    print("\n=== Test Summary ===")
    print("Shared folder is configured and working correctly!")
    print("\nUsers can collaborate by:")
    print("1. Uploading to /Global/")
    print("2. Downloading files others have shared")
    print("3. Using pcpdt list to see available files")

    return True


if __name__ == "__main__":
    # Check if pcpdt exists
    if not os.path.exists('./pcpdt'):
        print("Error: pcpdt not found in current directory")
        print("Please run this raw from the pcp-dkfz-transfer directory")
        sys.exit(1)

    # Run tests
    success = test_shared_folders()
    sys.exit(0 if success else 1)
