import logging
import shutil
from pathlib import Path
from app import app
import config
from models import JobState, write_state

logger = logging.getLogger(__name__)


@app.task(name="tasks.etl.copy_to_staging")
def copy_to_staging(source_dir: str, study_id: str) -> dict:
    source = Path(source_dir)
    staging = config.STUDIES_STAGING_DIR / study_id
    logger.info(f"[{study_id}] Copying {source} → {staging}")
    try:
        if staging.exists():
            logger.warning(f"[{study_id}] Existing staging dir removed and replaced")
            shutil.rmtree(staging)
        shutil.copytree(source, staging, ignore=shutil.ignore_patterns(".*"))
    except Exception as exc:
        _fail(source, study_id, f"ETL copy failed: {exc}")
        raise
    logger.info(f"[{study_id}] Copy complete")
    return {"source_dir": source_dir, "study_id": study_id, "staging_dir": str(staging)}


def _fail(source: Path, study_id: str, reason: str) -> None:
    logger.error(f"[{study_id}] {reason}")
    write_state(source, JobState.FAILED, study_id=study_id, error=reason)
