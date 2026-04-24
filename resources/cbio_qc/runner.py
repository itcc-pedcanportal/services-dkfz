"""Run cBioPortal validateData.py and parse output into structured issues."""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

VENV_PYTHON = Path(
    "/mnt/cbioportal_data/cbioportal-core/scripts/importer/.venv/bin/python3"
)
VALIDATE_SCRIPT = Path(
    "/mnt/cbioportal_data/cbioportal-core/scripts/importer/validateData.py"
)

Level = Literal["INFO", "WARNING", "ERROR", "CRITICAL"]

# exit code → human label
_EXIT_LABELS: dict[int, str] = {
    0: "PASS",
    3: "PASS_WITH_WARNINGS",
    1: "ERRORS",
    2: "CRITICAL",
}

_LINE_RE = re.compile(
    r"^(?P<level>INFO|WARNING|ERROR|CRITICAL):\s+"
    r"(?P<file>[^:]+?):\s+"
    r"(?:lines? [\d,\s()more]+:\s+)?"
    r"(?P<message>.+)$"
)


@dataclass
class ValidationIssue:
    level: Level
    file: str
    message: str
    count: int = 1

    @property
    def issue_type(self) -> str:
        msg = self.message.lower()
        if "swissprot" in msg and "missing value" in msg:
            return "swissprot_missing"
        if "swissprot" in msg and ("not a" in msg or "format" in msg):
            return "swissprot_format"
        if "swissprot" in msg:
            return "swissprot_missing"
        if "hgvsp" in msg:
            return "hgvsp_missing"
        if "dfs" in msg or "disease free" in msg:
            return "dfs_missing"
        if "filter" in msg and "variant" in msg:
            return "variant_filtered"
        return "other"


@dataclass
class ValidationReport:
    study_dir: Path
    exit_code: int
    raw_output: str
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def status_label(self) -> str:
        return _EXIT_LABELS.get(self.exit_code, f"UNKNOWN({self.exit_code})")

    @property
    def is_importable(self) -> bool:
        return self.exit_code in (0, 3)

    def issues_by_type(self) -> dict[str, list[ValidationIssue]]:
        result: dict[str, list[ValidationIssue]] = {}
        for issue in self.issues:
            result.setdefault(issue.issue_type, []).append(issue)
        return result

    def summary_table(self) -> str:
        by_type = self.issues_by_type()
        if not by_type:
            return "No issues found."
        lines = [
            f"{'Issue type':<25} {'Level':<10} {'Count':<8} {'File(s)'}",
            "-" * 80,
        ]
        for itype, group in sorted(by_type.items()):
            level = max(g.level for g in group)
            total = sum(g.count for g in group)
            files = ", ".join(sorted({g.file for g in group}))
            lines.append(f"{itype:<25} {level:<10} {total:<8} {files}")
        lines.append("")
        lines.append(f"Status: {self.status_label}  |  Importable: {self.is_importable}")
        return "\n".join(lines)


def _parse_output(raw: str) -> list[ValidationIssue]:
    """Collapse duplicate messages and return deduplicated ValidationIssue list."""
    seen: dict[tuple[str, str, str], ValidationIssue] = {}
    for line in raw.splitlines():
        m = _LINE_RE.match(line.strip())
        if not m:
            continue
        level = m.group("level")
        file_ = m.group("file").strip()
        message = m.group("message").strip()
        key = (level, file_, message)
        if key in seen:
            seen[key].count += 1
        else:
            seen[key] = ValidationIssue(level=level, file=file_, message=message)
    return list(seen.values())


def run_validation(study_dir: Path) -> ValidationReport:
    """Run validateData.py on *study_dir* and return a ValidationReport."""
    cmd = [str(VENV_PYTHON), str(VALIDATE_SCRIPT), "-s", str(study_dir), "-n"]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=600,
    )
    raw = result.stdout + result.stderr
    issues = _parse_output(raw)
    return ValidationReport(
        study_dir=study_dir,
        exit_code=result.returncode,
        raw_output=raw,
        issues=issues,
    )
