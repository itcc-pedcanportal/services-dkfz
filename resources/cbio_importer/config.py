from pathlib import Path

NC_WATCH_DIR = Path("/mnt/nc_uploads/__groupfolders/1")
STUDIES_STAGING_DIR = Path("/mnt/cbioportal_data/studies")
STATE_DIR = Path("/mnt/cbioportal_data/cbio-importer-state")

CBIO_VENV_PYTHON = Path("/mnt/cbioportal_data/cbioportal-core/scripts/importer/.venv/bin/python3")
CBIO_SCRIPTS_DIR = Path("/mnt/cbioportal_data/cbioportal-core/scripts/importer")
CBIO_COMPOSE_DIR = Path("/home/ubuntu/cbioportal-docker-compose")
CBIO_CONTAINER_STUDIES_PREFIX = "/studies"

SENTINEL = ".ready"

DB_HOST = "127.0.0.1"
DB_PORT = 3306
DB_USER = "cbio_user"
DB_PASSWORD = "somepassword"
DB_NAME = "cbioportal"

BROKER_URL = "redis://localhost:6379/0"
RESULT_BACKEND = "redis://localhost:6379/1"

RESTART_LOCK_KEY = "cbio:restart_lock"
RESTART_LOCK_TTL = 300
