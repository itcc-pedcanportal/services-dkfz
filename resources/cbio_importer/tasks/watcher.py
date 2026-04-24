import logging
from pathlib import Path
from app import app
import config
from models import JobState, write_state, read_state
from pipeline import build_pipeline

logger = logging.getLogger(__name__)


def _parse_study_id(meta_study_path: Path) -> str | None:
    try:
        for line in meta_study_path.read_text().splitlines():
            key, _, value = line.partition(":")
            if key.strip() == "cancer_study_identifier":
                return value.strip()
    except OSError as exc:
        logger.error(f"Could not read {meta_study_path}: {exc}")
    return None


@app.task(name="tasks.watcher.scan")
def scan() -> int:
    dispatched = 0
    for entry in sorted(config.NC_WATCH_DIR.iterdir()):
        if not entry.is_dir() or not (entry / config.SENTINEL).exists():
            continue
        current_state = read_state(entry)
        if current_state in (JobState.PROCESSING, JobState.IMPORTED, JobState.FAILED):
            continue
        meta_file = entry / "meta_study.txt"
        if not meta_file.exists():
            logger.error(f"[{entry.name}] No meta_study.txt — marking failed")
            write_state(entry, JobState.FAILED, error="Missing meta_study.txt")
            continue
        study_id = _parse_study_id(meta_file)
        if not study_id:
            logger.error(f"[{entry.name}] Cannot parse cancer_study_identifier — marking failed")
            write_state(entry, JobState.FAILED, error="Unparseable cancer_study_identifier")
            continue
        write_state(entry, JobState.PROCESSING, study_id=study_id)
        logger.info(f"Dispatching pipeline for study '{study_id}' from {entry}")
        build_pipeline(str(entry), study_id).delay()
        dispatched += 1
    logger.info(f"Watcher scan complete — {dispatched} pipeline(s) dispatched")
    return dispatched
