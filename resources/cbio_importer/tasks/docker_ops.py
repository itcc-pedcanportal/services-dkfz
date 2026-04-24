import logging
import subprocess
from pathlib import Path
import redis
from app import app
import config
from models import JobState, write_state

logger = logging.getLogger(__name__)


@app.task(name="tasks.docker_ops.restart_portal")
def restart_portal(ctx: dict) -> dict:
    study_id = ctx["study_id"]
    source = Path(ctx["source_dir"])
    r = redis.Redis.from_url(config.BROKER_URL)
    acquired = r.set(config.RESTART_LOCK_KEY, study_id, nx=True, ex=config.RESTART_LOCK_TTL)
    if not acquired:
        owner = (r.get(config.RESTART_LOCK_KEY) or b"").decode()
        logger.info(f"[{study_id}] Restart skipped — lock held by '{owner}', portal will reload on next restart")
    else:
        logger.info(f"[{study_id}] Acquired restart lock, restarting cBioPortal")
        try:
            result = subprocess.run(
                ["docker", "compose", "restart", "cbioportal"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(config.CBIO_COMPOSE_DIR),
            )
        except subprocess.TimeoutExpired as exc:
            _fail(source, study_id, "docker compose restart timed out after 120s")
            raise RuntimeError(f"[{study_id}] Restart timed out") from exc
        if result.returncode != 0:
            reason = f"docker compose restart failed: {result.stderr[:500]}"
            _fail(source, study_id, reason)
            raise RuntimeError(f"[{study_id}] {reason}")
        logger.info(f"[{study_id}] cBioPortal restarted successfully")
    write_state(source, JobState.IMPORTED, study_id=study_id)
    logger.info(f"[{study_id}] Pipeline complete")
    return {**ctx, "status": "DONE"}


def _fail(source: Path, study_id: str, reason: str) -> None:
    logger.error(f"[{study_id}] {reason}")
    write_state(source, JobState.FAILED, study_id=study_id, error=reason)
