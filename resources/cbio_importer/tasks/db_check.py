import logging
from pathlib import Path
import pymysql
from app import app
import config
from models import JobState, write_state

logger = logging.getLogger(__name__)


@app.task(name="tasks.db_check.check_study_not_imported")
def check_study_not_imported(ctx: dict) -> dict:
    study_id = ctx["study_id"]
    source = Path(ctx["source_dir"])
    try:
        with pymysql.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            connect_timeout=10,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM cancer_study WHERE CANCER_STUDY_IDENTIFIER = %s",
                    (study_id,),
                )
                (count,) = cur.fetchone()
    except pymysql.Error as exc:
        _fail(source, study_id, f"DB connection error: {exc}")
        raise RuntimeError(f"[{study_id}] DB error") from exc
    if count:
        reason = f"study '{study_id}' already exists in DB — skipping"
        _fail(source, study_id, reason)
        raise RuntimeError(f"[{study_id}] {reason}")
    logger.info(f"[{study_id}] Not in DB — proceeding with import")
    return ctx


def _fail(source: Path, study_id: str, reason: str) -> None:
    logger.error(f"[{study_id}] {reason}")
    write_state(source, JobState.FAILED, study_id=study_id, error=reason)
