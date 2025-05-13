# ITCC PedCanPortal Proxy Access Guide

This guide explains how to access various ITCC PedCanPortal services using proxy connections through the DKFZ infrastructure.

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Setting Up SSH Tunneling](#setting-up-ssh-tunneling)
- [Accessing Web Services](#accessing-web-services)
- [Troubleshooting](#troubleshooting)
- [Contact Information](#contact-information)

## Overview

The DKFZ Heidelberg provides access to various web services and applications that are not directly accessible from the public internet for security reasons. This guide explains how to set up proxy connections to access these services.

## Prerequisites

Before setting up proxy access, ensure you have:

1. Completed all steps in the [main data upload guide](../README.md)
2. Received confirmation of access from the DKFZ team
3. Successfully connected to the VM via SSH at least once

## Setting Up SSH Tunneling

SSH tunneling (port forwarding) allows you to securely access services running on the DKFZ network.

### Basic SSH Tunnel

To create a basic SSH tunnel:

```bash
ssh -L local_port:remote_host:remote_port username@vm-hostname
```

Where:
- `local_port` is the port on your local machine
- `remote_host` is the internal hostname of the service
- `remote_port` is the port the service runs on
- `username@vm-hostname` is your SSH login information

### Example: Accessing a Web Application

To access a web application running on port 8080 on an internal server:

```bash
ssh -L 8080:internal-server.dkfz.de:8080 username@vm-hostname
```

After establishing the connection, you can access the service by opening a browser and navigating to:
```
http://localhost:8080
```

## Accessing Web Services

The ITCC PedCanPortal provides several web services that can be accessed via proxy:

### Jupyter Notebooks

To access Jupyter Notebook servers:

```bash
ssh -L 8888:jupyter-server.internal:8888 username@vm-hostname
```

Then open your browser and navigate to:
```
http://localhost:8888
```

### Database Interfaces

For accessing database interfaces:

```bash
ssh -L 5432:db-server.internal:5432 username@vm-hostname
```

You can then connect your database client to `localhost:5432`.

### Web Applications

For web applications and dashboards:

```bash
ssh -L 3000:dashboard-server.internal:3000 username@vm-hostname
```

Access the dashboard at:
```
http://localhost:3000
```

## Troubleshooting

### Common Issues

1. **Connection refused**: Ensure the service is running on the remote host and the port is correct
2. **Permission denied**: Check that you have the necessary permissions to access the service
3. **Port already in use**: Change the local port to an available one

### SSH Config File

For convenience, you can set up an SSH config file to simplify connections:

```
# ~/.ssh/config
Host itcc-tunnel
    HostName vm-hostname
    User username
    IdentityFile ~/.ssh/your_private_key
    LocalForward 8888 jupyter-server.internal:8888
    LocalForward 3000 dashboard-server.internal:3000
```

Then simply connect with:
```bash
ssh itcc-tunnel
```

## Contact Information

For any questions or issues regarding proxy access to ITCC PedCanPortal services, please contact:

**Julius Müller**  
Email: julius.mueller@dkfz-heidelberg.de

---

For more detailed information about connecting to DKFZ compute resources, please refer to the [de.NBI Heidelberg-DKFZ documentation](https://github.com/deNBI/cloud-user-docs/blob/main/wiki/Compute_Center/Heidelberg-DKFZ.md).