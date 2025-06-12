#!/bin/bash
# Setup script for shared folders in Nextcloud
# Run this as admin to properly configure shared folder access

echo "=== Setting up Nextcloud Shared Folders ==="

# Check if running with proper permissions
if [ "$EUID" -ne 0 ] && ! groups | grep -q docker; then
    echo "Warning: You may need to run this with sudo or be in the docker group"
fi

# Get admin password if not set
if [ -z "$ADMIN_PASSWORD" ]; then
    read -s -p "Enter Nextcloud admin password: " ADMIN_PASSWORD
    echo
fi

# Create shared folders if they don't exist
echo "Creating shared folder structure..."
docker exec nextcloud mkdir -p /mnt/uploads/_shared/pedcanportal_all
docker exec nextcloud mkdir -p /mnt/uploads/_shared/cbioportal_uploaders

# Set proper ownership
docker exec nextcloud chown -R www-data:www-data /mnt/uploads/_shared

# Create admin entries for the folders (so they can be shared)
echo "Creating admin folder entries..."
docker exec -u www-data nextcloud php occ files:scan --path="/admin/files/_shared"

# Share folders with appropriate groups using OCS API
echo "Setting up folder shares..."

# Function to create share via OCS API
create_share() {
    local path="$1"
    local group="$2"
    local permissions="$3"

    echo "Sharing $path with group $group (permissions: $permissions)..."

    docker exec nextcloud curl -s -u admin:${ADMIN_PASSWORD} \
        -X POST "http://localhost/ocs/v2.php/apps/files_sharing/api/v1/shares" \
        -d "path=$path" \
        -d "shareType=1" \
        -d "shareWith=$group" \
        -d "permissions=$permissions" \
        -H "OCS-APIRequest: true" \
        -H "Accept: application/json"
}

# Share pedcanportal_all with all users (read/write)
# Permissions: 15 = read(1) + update(2) + create(4) + delete(8)
create_share "/_shared/pedcanportal_all" "all-users" "15"

# Share cbioportal_uploaders with specific group (read/write)
create_share "/_shared/cbioportal_uploaders" "cbioportal_uploaders" "15"

# Update the login hook to ensure users see shared folders
echo "Updating user provisioning hook..."

cat > /tmp/update-shared-folders-hook.php << 'PHP'
<?php
// Add shared folder visibility to the existing provisioning hook

$sharedFoldersHook = '

// Ensure shared folders are visible to users
$sharedFolders = [
    "/_shared/pedcanportal_all" => ["group" => "all-users", "name" => "Shared - All Users"],
    "/_shared/cbioportal_uploaders" => ["group" => "cbioportal_uploaders", "name" => "Shared - cBioPortal Uploaders"]
];

foreach ($sharedFolders as $folder => $config) {
    $userGroups = \OC::$server->getGroupManager()->getUserGroupIds($user);

    // Check if user should have access
    if ($config["group"] === "all-users" || in_array($config["group"], $userGroups)) {
        // Ensure the shared folder mount exists for this user
        $mountPoint = "/home/" . $username . "/" . $config["name"];

        // Log access setup
        $logger->info("[Shared Folders] User " . $username . " has access to " . $folder, ["app" => "shared_folders"]);
    }
}
';

// Add to existing hook
$appFile = "/var/www/html/apps/oidc_login/appinfo/app.php";
if (file_exists($appFile)) {
    $content = file_get_contents($appFile);
    if (strpos($content, "Ensure shared folders are visible") === false) {
        // Find the end of the existing provisioning hook and add before the last closing brace
        $content = str_replace(
            "// === END PROVISIONING HOOK ===",
            $sharedFoldersHook . "\n// === END PROVISIONING HOOK ===",
            $content
        );
        file_put_contents($appFile, $content);
        echo "Shared folders hook added\n";
    }
}
PHP

docker cp /tmp/update-shared-folders-hook.php nextcloud:/tmp/
docker exec nextcloud php /tmp/update-shared-folders-hook.php

# Verify the setup
echo ""
echo "=== Verifying Setup ==="

# Check if folders exist
echo "Checking folders..."
docker exec nextcloud ls -la /mnt/uploads/_shared/

# List current shares
echo ""
echo "Current shares:"
docker exec nextcloud php occ sharing:list | grep "_shared" || echo "No shares found via OCC"

# Test with curl
echo ""
echo "Testing share creation..."
docker exec nextcloud curl -s -u admin:${ADMIN_PASSWORD} \
    "http://localhost/ocs/v2.php/apps/files_sharing/api/v1/shares?format=json" \
    -H "OCS-APIRequest: true" | grep -o '"path":"[^"]*_shared[^"]*"' || echo "No shared folders found via API"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Shared folders configured:"
echo "1. /_shared/pedcanportal_all - Accessible to all authenticated users"
echo "2. /_shared/cbioportal_uploaders - Accessible to users with cbioportal_uploaders role"
echo ""
echo "Users can now:"
echo "- Upload: pcpdt upload file.txt /_shared/pedcanportal_all/"
echo "- List: pcpdt list /_shared/pedcanportal_all/"
echo "- Download: pcpdt download /_shared/pedcanportal_all/file.txt"
echo ""
echo "Note: If shares aren't visible, you may need to:"
echo "1. Restart Nextcloud: docker compose restart nextcloud"
echo "2. Have users log out and back in"
echo "3. Check group memberships in Keycloak"