# ITCC PedCanPortal Data Upload Guide

This repository contains documentation for bioinformaticians on how to upload data to the ITCC PedCanPortal hosted at DKFZ Heidelberg.

## Table of Contents
- [Overview](#overview)
- [Step 1: Create a Life Science Account](#step-1-create-a-life-science-account)
- [Step 2: Register for de.NBI Cloud Portal](#step-2-register-for-denbi-cloud-portal)
- [Step 3: Apply for Access to ITCCprod Services](#step-3-apply-for-access-to-itccprod-services)
- [Step 4: SSH Connection and Data Upload](#step-4-ssh-connection-and-data-upload)
- [Contact Information](#contact-information)
- [Additional Documentation](#additional-documentation)

## Overview

The ITCC PedCanPortal (https://www.pedcanportal.eu/) allows institutes around the world to share sensitive genetic data of bioinformatics pipelines within the consortium and present the data in non-public web interfaces. This guide will help you connect to our OpenStack hosted VMs at DKFZ Heidelberg for data upload.

## Step 1: Create a Life Science Account

Before you can access our services, you need to create a Life Science ID:

1. Visit the [Life Science Login registration page](https://lifescience-ri.eu/ls-login/version-2023/user/how-to-get-ls-id.html)
2. Follow these steps to create your account:
   - Click on "Register" on the Life Science Login page
   - Fill in your personal information
   - Verify your email address
   - Complete your profile information
   - Your Life Science ID will be created

This account will serve as your identity for accessing various Life Science research infrastructure services.

## Step 2: Register for de.NBI Cloud Portal

After obtaining your Life Science ID, you need to register for the de.NBI Cloud Portal:

1. Visit the [de.NBI Cloud Portal registration page](https://cloud.denbi.de/register)
2. Log in using your Life Science ID credentials
3. Complete the registration form with your information
4. Accept the terms and conditions
5. Submit your registration

The de.NBI Cloud Portal provides access to bioinformatics computing resources across Germany.

## Step 3: Apply for Access to ITCCprod Services

Once registered with the de.NBI Cloud Portal, you can apply for access to our specific services:

1. Visit the [ITCCcloud_prod application page](https://signup.aai.lifescience-ri.eu/fed/registrar/?vo=denbi&group=ITCCcloud_prod)
2. Log in with your Life Science ID
3. Complete the application form, providing details about your research and data upload needs
4. Submit your application

After submission, please wait for approval. The DKFZ team will review your application and:
- Add your public SSH key to the relevant VM
- Send confirmation from julius.mueller@dkfz-heidelberg.de when access is granted

## Step 4: SSH Connection and Data Upload

After receiving confirmation of access:

1. Connect to the VM using SSH:
   ```
   ssh username@vm-hostname
   ```

2. Upload your data to the appropriate subdirectory in `/mnt/nfs-share/upload`
   - You can use tools like `scp`, `rsync`, or `sftp` for data transfer
   - Example using scp:
     ```
     scp -r /path/to/your/data username@vm-hostname:/mnt/nfs-share/upload/your-subdirectory
     ```

For more detailed information about connecting to DKFZ compute resources, please refer to the [de.NBI Heidelberg-DKFZ documentation](https://github.com/deNBI/cloud-user-docs/blob/main/wiki/Compute_Center/Heidelberg-DKFZ.md).

## Contact Information

For any questions or issues regarding data upload or access to the ITCC PedCanPortal services, please contact:

**Julius Müller**  
Email: julius.mueller@dkfz-heidelberg.de

---

## Additional Documentation

- [Proxy Access Guide](docs/proxy-access-guide.md) - Instructions for accessing ITCC PedCanPortal services using proxy connections
