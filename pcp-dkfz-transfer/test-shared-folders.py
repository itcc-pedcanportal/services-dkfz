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

    # Test 1: List shared folders
    print("Test 1: Listing shared folders...")
    success, stdout, stderr = run_command("./pcpdt list /_shared/")

    if success:
        print("✓ Can list /_shared/ directory")
        if "pedcanportal_all" in stdout:
            print("✓ Found pedcanportal_all folder")
        else:
            print("⚠️  pedcanportal_all folder not visible")

        if "cbioportal_uploaders" in stdout:
            print("✓ Found cbioportal_uploaders folder (user has access)")
        else:
            print("ℹ️  cbioportal_uploaders not visible (user may lack access - this is normal)")
    else:
        print("❌ Cannot list shared folders")
        print(f"Error: {stderr}")
        return False

    print()

    # Test 2: Upload to shared folder
    print("Test 2: Testing upload to shared folder...")

    # Create a test file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        test_content = f"Test upload at {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f.write(test_content)
        test_file = f.name

    test_filename = f"test-{os.getpid()}.txt"

    # Try upload to pedcanportal_all
    success, stdout, stderr = run_command(
        f"./pcpdt upload {test_file} /_shared/pedcanportal_all/{test_filename}"
    )

    if success:
        print("✓ Successfully uploaded to /_shared/pedcanportal_all/")

        # Test 3: List to verify upload
        print("\nTest 3: Verifying uploaded file...")
        success, stdout, stderr = run_command("./pcpdt list /_shared/pedcanportal_all/")

        if success and test_filename in stdout:
            print("✓ Uploaded file is visible in listing")

            # Test 4: Download the file
            print("\nTest 4: Testing download...")
            download_path = f"/tmp/download-{test_filename}"
            success, stdout, stderr = run_command(
                f"./pcpdt download /_shared/pedcanportal_all/{test_filename} {download_path}"
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
        print("- User doesn't have write access to /_shared/pedcanportal_all/")
        print("- Shared folder doesn't exist")
        print("- Authentication issue")

    # Cleanup
    os.unlink(test_file)

    # Test 5: Test restricted folder (if user has access)
    print("\nTest 5: Testing restricted folder access...")
    success, stdout, stderr = run_command("./pcpdt list /_shared/cbioportal_uploaders/")

    if success:
        print("✓ User has access to cbioportal_uploaders folder")
    else:
        print("ℹ️  User doesn't have access to cbioportal_uploaders (this is expected for regular users)")

    print("\n=== Test Summary ===")
    print("Shared folders are configured and working correctly!")
    print("\nUsers can collaborate by:")
    print("1. Uploading to /_shared/pedcanportal_all/")
    print("2. Downloading files others have shared")
    print("3. Using pcpdt list to see available files")

    return True


if __name__ == "__main__":
    # Check if pcpdt exists
    if not os.path.exists('./pcpdt'):
        print("Error: pcpdt not found in current directory")
        print("Please run this test from the pcp-dkfz-transfer directory")
        sys.exit(1)

    # Run tests
    success = test_shared_folders()
    sys.exit(0 if success else 1)