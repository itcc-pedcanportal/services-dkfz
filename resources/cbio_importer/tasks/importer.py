import logging
import subprocess
from pathlib import Path
from app import app
import config
from models import JobState, write_state

logger = logging.getLogger(__name__)


_IMPORT_STEPS = ["import-study", "import-study-data", "import-case-list"]


@app.task(name="tasks.importer.import_study")
def import_study(ctx: dict) -> dict:
    study_id = ctx["study_id"]
    source = Path(ctx["source_dir"])
    container_path = f"{config.CBIO_CONTAINER_STUDIES_PREFIX}/{study_id}"
    for step in _IMPORT_STEPS:
        # subcommand must come before -s; placing -s first causes argparse to
        # reset study_directory to None when the subparser is invoked
        cmd = [
            "docker", "compose", "exec", "-T", "cbioportal",
            "cbioportalImporter.py", step, "-s", container_path,
        ]
        logger.info(f"[{study_id}] Running {step}")
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800,
                cwd=str(config.CBIO_COMPOSE_DIR),
            )
        except subprocess.TimeoutExpired as exc:
            _fail(source, study_id, f"{step} timed out after 1800s")
            raise RuntimeError(f"[{study_id}] {step} timed out") from exc
        if result.stdout:
            logger.info(f"[{study_id}] {step} stdout:\n{result.stdout[-4000:]}")
        if result.stderr:
            logger.debug(f"[{study_id}] {step} stderr:\n{result.stderr[-2000:]}")
        if result.returncode != 0:
            reason = f"{step} exited {result.returncode}"
            _fail(source, study_id, reason)
            raise RuntimeError(f"[{study_id}] {reason}")
        logger.info(f"[{study_id}] {step} OK")
    return ctx


def _fail(source: Path, study_id: str, reason: str) -> None:
    logger.error(f"[{study_id}] {reason}")
    write_state(source, JobState.FAILED, study_id=study_id, error=reason)
