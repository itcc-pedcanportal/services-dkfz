#!/usr/bin/env python3
"""itcc_qc — QC and optional auto-fix for cBioPortal study uploads.

Usage:
  python itcc_qc.py <study_dir>                     # validate only
  python itcc_qc.py <study_dir> --stage             # copy to staging, then validate
  python itcc_qc.py <study_dir> --stage --fix-all   # copy, validate, fix
  python itcc_qc.py <staging_dir> --fix fix_swissprot
  python itcc_qc.py --list-fixers
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from fixers import ISSUE_TYPE_TO_FIXER, REGISTRY, _UPLOADS_ROOT, _STAGING_ROOT
from runner import run_validation


def _list_fixers() -> None:
    print("Available fixers:")
    for name, (description, _) in REGISTRY.items():
        print(f"  {name:<25} {description}")


def _run_fixer(name: str, study_dir: Path) -> bool:
    if name not in REGISTRY:
        print(f"[ERROR] Unknown fixer: {name!r}. Run --list-fixers to see options.")
        return False
    _, fn = REGISTRY[name]
    print(f"[FIX] Running {name} ...")
    result = fn(study_dir)
    if result.skipped:
        print(f"  Skipped: {result.skip_reason}")
    elif result.error:
        print(f"  Error: {result.error}")
        return False
    else:
        print(f"  Modified {result.rows_changed} row(s) in: {', '.join(result.files_modified) or 'none'}")
        if result.files_modified:
            print("  Backups written as <file>.bak")
    return result.ok


def _stage(study_dir: Path) -> Path:
    """Copy study_dir to the staging root and return the staging path."""
    dest = _STAGING_ROOT / study_dir.name
    if dest.exists():
        print(f"[ERROR] Staging path already exists: {dest}", file=sys.stderr)
        print( "  Remove it first or run fixes directly against the existing staging copy.", file=sys.stderr)
        sys.exit(1)
    print(f"[STAGE] Copying {study_dir.name} → {dest} ...")
    shutil.copytree(
        study_dir,
        dest,
        ignore=shutil.ignore_patterns(".*"),  # exclude dotfiles (.ready, .DS_Store, …)
    )
    print(f"[STAGE] Done.")
    return dest


def _is_under_uploads(path: Path) -> bool:
    try:
        path.resolve().relative_to(_UPLOADS_ROOT.resolve())
        return True
    except ValueError:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="itcc_qc",
        description="Validate and optionally fix a cBioPortal study directory.",
    )
    parser.add_argument("study_dir", nargs="?", type=Path, help="Path to study directory")
    parser.add_argument(
        "--stage",
        action="store_true",
        help=f"Copy study to {_STAGING_ROOT}/<name>/ before validating and fixing",
    )
    parser.add_argument(
        "--fix",
        metavar="NAME",
        action="append",
        dest="fixers",
        default=[],
        help="Run a specific fixer (may be repeated)",
    )
    parser.add_argument(
        "--fix-all",
        action="store_true",
        help="Run all fixers that match detected issue types",
    )
    parser.add_argument(
        "--list-fixers",
        action="store_true",
        help="List available fixers and exit",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Also print raw validator output",
    )
    args = parser.parse_args()

    if args.list_fixers:
        _list_fixers()
        sys.exit(0)

    if not args.study_dir:
        parser.error("study_dir is required unless --list-fixers is used")

    study_dir = args.study_dir.resolve()
    if not study_dir.is_dir():
        print(f"[ERROR] Not a directory: {study_dir}", file=sys.stderr)
        sys.exit(1)

    # --stage: copy uploads → staging, then work from the staging copy
    if args.stage:
        study_dir = _stage(study_dir)
        print()

    print(f"[QC] Validating {study_dir} ...")
    report = run_validation(study_dir)
    print()
    print(report.summary_table())

    # Suggest applicable fixers for detected issue types
    applicable: list[str] = []
    for itype in report.issues_by_type():
        fixer_name = ISSUE_TYPE_TO_FIXER.get(itype)
        if fixer_name and fixer_name not in applicable:
            applicable.append(fixer_name)

    if applicable:
        print()
        print("Suggested fixers for detected issues:")
        for name in applicable:
            desc = REGISTRY[name][0]
            print(f"  --fix {name:<20} {desc}")

    if args.raw:
        print()
        print("--- raw validator output ---")
        print(report.raw_output)

    # Resolve the full fixer list
    fixers_to_run: list[str] = list(args.fixers)
    if args.fix_all:
        for name in applicable:
            if name not in fixers_to_run:
                fixers_to_run.append(name)

    if fixers_to_run:
        if _is_under_uploads(study_dir):
            staging_hint = _STAGING_ROOT / study_dir.name
            print(
                f"\n[ERROR] Fixes cannot be applied inside {_UPLOADS_ROOT}.\n"
                f"  Use --stage to copy to staging first:\n"
                f"\n"
                f"    python itcc_qc.py {args.study_dir} --stage"
                + (f" --fix-all" if args.fix_all else
                   "".join(f" --fix {n}" for n in fixers_to_run))
                + "\n",
                file=sys.stderr,
            )
            sys.exit(1)

        print()
        all_ok = True
        for name in fixers_to_run:
            ok = _run_fixer(name, study_dir)
            all_ok = all_ok and ok
        if all_ok:
            print()
            print("[QC] Fixes applied. Re-run without --fix flags to confirm validation passes.")

    sys.exit(0 if report.is_importable else 1)


if __name__ == "__main__":
    main()
