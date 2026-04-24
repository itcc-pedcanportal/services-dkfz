import logging
import subprocess
from pathlib import Path
from app import app
import config
from models import JobState, write_state

logger = logging.getLogger(__name__)


@app.task(name="tasks.validator.validate_study")
def validate_study(ctx: dict) -> dict:
    study_id = ctx["study_id"]
    source = Path(ctx["source_dir"])
    cmd = [
        str(config.CBIO_VENV_PYTHON),
        str(config.CBIO_SCRIPTS_DIR / "validateData.py"),
        "-s", ctx["staging_dir"],
        "-n",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired as exc:
        _fail(source, study_id, "validateData.py timed out after 600s")
        raise RuntimeError(f"[{study_id}] Validation timed out") from exc
    if result.stdout:
        logger.info(f"[{study_id}] validate stdout:\n{result.stdout[-4000:]}")
    if result.stderr:
        logger.debug(f"[{study_id}] validate stderr:\n{result.stderr[-2000:]}")
    if result.returncode != 0:
        reason = f"validateData.py exited {result.returncode}"
        _fail(source, study_id, reason)
        raise RuntimeError(f"[{study_id}] {reason}")
    logger.info(f"[{study_id}] Validation passed")
    return ctx


def _fail(source: Path, study_id: str, reason: str) -> None:
    logger.error(f"[{study_id}] {reason}")
    write_state(source, JobState.FAILED, study_id=study_id, error=reason)
