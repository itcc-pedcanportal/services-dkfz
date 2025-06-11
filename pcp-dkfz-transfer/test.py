#!/usr/bin/env python3
"""
Test script for PCP-DKFZ Transfer Tool
Verifies the installation and connection
"""

import sys
import os
import tempfile
import subprocess


def run_test(command):
    """Run a test command and return success status"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def main():
    print("PCP-DKFZ Transfer Tool - Installation Test")
    print("=" * 50)

    # Test 1: Check if pcpdt is accessible
    print("\n1. Checking pcpdt installation...", end=" ")
    success, stdout, stderr = run_test("./pcpdt --version")
    if success:
        print("✓")
        print(f"   Version: {stdout.strip()}")
    else:
        print("✗")
        print("   Error: pcpdt not found or not executable")
        print("   Try: chmod +x pcpdt")
        return False

    # Test 2: Check Python version
    print("\n2. Checking Python version...", end=" ")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 6:
        print("✓")
        print(f"   Python {version.major}.{version.minor}.{version.micro}")
    else:
        print("✗")
        print(f"   Python 3.6+ required, found {version.major}.{version.minor}")
        return False

    # Test 3: Check if token is set
    print("\n3. Checking authentication...", end=" ")
    token = os.environ.get('NEXTCLOUD_TOKEN')
    if token:
        print("✓")
        print("   Token found in environment")
    else:
        print("!")
        print("   No token set. You'll be prompted for credentials.")
        print("   Set: export NEXTCLOUD_TOKEN='username:app-password'")

    # Test 4: Test connection (if token is set)
    if token:
        print("\n4. Testing server connection...", end=" ")
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test")
            testfile = f.name

        success, stdout, stderr = run_test(f"./pcpdt -q upload {testfile} /test-pcpdt.txt")
        os.unlink(testfile)

        if success:
            print("✓")
            print("   Successfully connected to Nextcloud")
            # Try to clean up
            run_test("./pcpdt -q download /test-pcpdt.txt /dev/null")
        else:
            print("✗")
            print("   Could not connect. Check your credentials.")
            if "401" in stderr:
                print("   Authentication failed - check username/password")
            elif "SSL" in stderr:
                print("   SSL certificate issue - check system certificates")

    # Test 5: Check for common issues
    print("\n5. Checking for common issues...", end=" ")
    issues = []

    # Check SSL
    try:
        import ssl
        ssl.create_default_context()
    except:
        issues.append("SSL certificates may need updating")

    # Check if behind proxy
    if os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY'):
        issues.append("Proxy detected - may need configuration")

    if issues:
        print("!")
        for issue in issues:
            print(f"   - {issue}")
    else:
        print("✓")
        print("   No issues detected")

    print("\n" + "=" * 50)
    print("Test complete!")

    if not token:
        print("\nNext steps:")
        print("1. Get app password: https://cbioportal-upload.pedcanportal.de/settings/user/security")
        print("2. Set token: export NEXTCLOUD_TOKEN='username:app-password'")
        print("3. Try: ./pcpdt upload test.txt /")
    else:
        print("\nReady to use! Try:")
        print("  ./pcpdt upload myfile.txt /Documents/")
        print("  ./pcpdt share /Documents/myfile.txt -p password")

    return True


if __name__ == "__main__":
    main()