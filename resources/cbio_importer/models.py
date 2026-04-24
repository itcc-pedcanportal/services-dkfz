from enum import Enum
from pathlib import Path
import json
from datetime import datetime
import config


class JobState(str, Enum):
    PROCESSING = "processing"
    IMPORTED = "imported"
    FAILED = "failed"


def state_file(upload_dir: Path) -> Path:
    config.STATE_DIR.mkdir(parents=True, exist_ok=True)
    return config.STATE_DIR / f"{upload_dir.name}.json"


def write_state(upload_dir: Path, state: JobState, study_id: str = "", error: str = "") -> None:
    state_file(upload_dir).write_text(json.dumps({
        "state": state.value,
        "upload_dir": str(upload_dir),
        "study_id": study_id,
        "updated_at": datetime.now().isoformat(),
        "error": error,
    }, indent=2))


def read_state(upload_dir: Path) -> JobState | None:
    sf = state_file(upload_dir)
    if not sf.exists():
        return None
    return JobState(json.loads(sf.read_text())["state"])
