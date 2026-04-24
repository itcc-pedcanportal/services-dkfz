"""Fixers for common cBioPortal QC issues.

Each fixer is a callable(study_dir: Path) -> FixResult.
Register new fixers in REGISTRY at the bottom of this file.

IMPORTANT: Fixers must NEVER write to /mnt/nc_uploads/. That path is the raw
delivery zone and must stay read-only. All fixes must target the staging area
under /mnt/cbioportal_data/studies/.
"""
from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

_UPLOADS_ROOT = Path("/mnt/nc_uploads")
_STAGING_ROOT = Path("/mnt/cbioportal_data/studies")


def _assert_not_uploads(study_dir: Path) -> None:
    """Raise if study_dir is inside the uploads tree — fixers must never write there."""
    try:
        study_dir.resolve().relative_to(_UPLOADS_ROOT.resolve())
        raise PermissionError(
            f"Refusing to modify files under {_UPLOADS_ROOT}.\n"
            f"Copy the study to {_STAGING_ROOT}/<study_id>/ first, "
            f"then re-run the fixer against the staging copy."
        )
    except ValueError:
        pass  # not under uploads root — safe to proceed

_VERSION_RE = re.compile(r"\.\d+$")


@dataclass
class FixResult:
    fixer: str
    files_modified: list[str] = field(default_factory=list)
    rows_changed: int = 0
    skipped: bool = False
    skip_reason: str = ""
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error


# ---------------------------------------------------------------------------
# SwissProt version-suffix fixer
# ---------------------------------------------------------------------------

def _strip_swissprot_version(value: str) -> str:
    """Strip .NNN version from a single accession or take first of comma-separated."""
    if not value or value in ("NA", ""):
        return value
    if "," in value:
        # multi-value: take the first accession and strip its version
        value = value.split(",")[0].strip()
    return _VERSION_RE.sub("", value)


def fix_swissprot(study_dir: Path) -> FixResult:
    """Strip version suffixes from SWISSPROT column in MAF files."""
    _assert_not_uploads(study_dir)
    result = FixResult(fixer="fix_swissprot")
    maf_files = list(study_dir.glob("*.maf")) + list(study_dir.glob("data_mutation*"))
    maf_files = [f for f in maf_files if f.is_file()]

    if not maf_files:
        result.skipped = True
        result.skip_reason = "No MAF / mutation files found in study directory"
        return result

    for maf_path in maf_files:
        lines = maf_path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)

        # find SWISSPROT column index from the header
        header_idx = next(
            (i for i, ln in enumerate(lines) if not ln.startswith("#")), None
        )
        if header_idx is None:
            continue
        header = lines[header_idx].rstrip("\n").split("\t")
        try:
            sp_col = header.index("SWISSPROT")
        except ValueError:
            continue  # column absent — nothing to fix

        changed = 0
        new_lines = list(lines)
        for i in range(header_idx + 1, len(lines)):
            row = lines[i].rstrip("\n").split("\t")
            if sp_col >= len(row):
                continue
            original = row[sp_col]
            fixed = _strip_swissprot_version(original)
            if fixed != original:
                row[sp_col] = fixed
                new_lines[i] = "\t".join(row) + "\n"
                changed += 1

        if changed:
            backup = maf_path.with_suffix(maf_path.suffix + ".bak")
            shutil.copy2(maf_path, backup)
            maf_path.write_text("".join(new_lines), encoding="utf-8")
            result.files_modified.append(maf_path.name)
            result.rows_changed += changed

    if not result.files_modified:
        result.skipped = True
        result.skip_reason = "SWISSPROT column present but no versioned accessions found"
    return result


# ---------------------------------------------------------------------------
# Registry — add new fixers here
# ---------------------------------------------------------------------------

REGISTRY: dict[str, tuple[str, callable]] = {
    "fix_swissprot": (
        "Strip .NNN version suffixes from SWISSPROT column in MAF files",
        fix_swissprot,
    ),
}

ISSUE_TYPE_TO_FIXER: dict[str, str] = {
    "swissprot_format": "fix_swissprot",
}
