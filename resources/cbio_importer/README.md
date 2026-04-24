# cbio_importer

Automated pipeline that watches the Nextcloud upload folder for new cBioPortal studies and imports them into the local portal.

## How it works

1. **Celery Beat** wakes up every 5 minutes and runs `tasks.watcher.scan`.
2. The scanner looks for subdirectories in `/mnt/nc_uploads/__groupfolders/1/` that contain a `.ready` sentinel file.
3. The `cancer_study_identifier` is parsed from `meta_study.txt` inside that directory.
4. A Celery chain runs: `copy_to_staging → validate → db_check → import → restart`.
5. State is persisted to `/mnt/cbioportal_data/cbio-importer-state/<dir_name>.json`.

## Prerequisites

- Python 3.13 (managed by `uv`)
- Redis (via the included `docker-compose.yml`)
- The cbioportal-core venv must exist at `/mnt/cbioportal_data/cbioportal-core/scripts/importer/.venv/`
- The cBioPortal Docker Compose stack must be running in `/home/ubuntu/cbioportal-docker-compose/`
- The user running the worker must have permission to run `docker compose`

## Setup

```bash
cd resources/cbio_importer

# Install uv if not already installed
curl -Lsf https://astral.sh/uv/install.sh | sh

# Create venv and install dependencies
uv sync

# Start Redis
docker compose up -d
```

## Running

Open three terminals (or use a process manager):

```bash
# Terminal 1 — Celery worker
cd resources/cbio_importer
uv run celery -A app worker --loglevel=info

# Terminal 2 — Celery Beat scheduler (5-minute poll)
cd resources/cbio_importer
uv run celery -A app beat --loglevel=info

# Terminal 3 — Optional flower monitor
uv run celery -A app flower
```

## Triggering an import

Place the study directory in `/mnt/nc_uploads/__groupfolders/1/` and create the sentinel file:

```
/mnt/nc_uploads/__groupfolders/1/
└── my_study_dir/
    ├── .ready          ← sentinel; pipeline ignores this dir without it
    ├── meta_study.txt  ← must contain: cancer_study_identifier: <study_id>
    ├── meta_clinical_patient.txt
    ├── data_clinical_patient.txt
    └── ...
```

The next scan (within 5 minutes) will pick it up automatically.

## State files

Each upload directory gets a JSON state file in `/mnt/cbioportal_data/cbio-importer-state/`:

| State | Meaning |
|-------|---------|
| `processing` | Pipeline dispatched, in progress |
| `imported` | Successfully imported |
| `failed` | Pipeline failed; error message in JSON |

**To retry a failed study:** delete the state file and re-drop the `.ready` sentinel.

```bash
rm /mnt/cbioportal_data/cbio-importer-state/<dir_name>.json
touch /mnt/nc_uploads/__groupfolders/1/<dir_name>/.ready
```

## After import

Studies are imported but not automatically made public. Use the existing aliases to set visibility:

```bash
cbio-list                    # find the study's numeric ID
cbio-make-visible <ID>       # make it public
# or
cbio-set-group <ID> ADMIN    # restrict to ADMIN group
```

## Pipeline stages

| Stage | Script | Notes |
|-------|--------|-------|
| `copy_to_staging` | `shutil.copytree` | Copies to `/mnt/cbioportal_data/studies/<study_id>/`; dotfiles excluded |
| `validate_study` | `validateData.py -s <path> -n` | Runs on host using cbioportal-core venv |
| `check_study_not_imported` | MySQL query | Aborts if `cancer_study_identifier` already in DB |
| `import_study` | `docker compose exec -T cbioportal cbioportalImporter.py` | Single `-s <path>` call; `process_study_directory` handles all meta/data/case-list files |
| `restart_portal` | `docker compose restart cbioportal` | Redis NX lock prevents concurrent restarts |
