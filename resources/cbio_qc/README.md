# itcc_qc

Lightweight QC framework for cBioPortal study uploads. Runs `validateData.py`,
reports issues in a structured table, suggests fixes, and optionally applies them.

No extra dependencies — uses the existing `cbioportal-core` venv Python.

> **Safety rule:** Fixes are never applied inside `/mnt/nc_uploads/`. That tree is
> read-only by policy. `--stage` copies the study to `/mnt/cbioportal_data/studies/<name>/`
> first. Validation (read-only) can be run against the raw upload at any time.

---

## Typical workflow

### 1. Validate the raw upload (read-only)

```bash
cd resources/cbio_qc
python itcc_qc.py /mnt/nc_uploads/__groupfolders/1/<study_dir>
```

Example output:

```
[QC] Validating /mnt/nc_uploads/__groupfolders/1/maxima_dataset_20260416 ...

Issue type                Level      Count    File(s)
--------------------------------------------------------------------------------
dfs_missing               WARNING    1        data_clinical_patient.txt
hgvsp_missing             WARNING    1        data_mutation.maf
other                     WARNING    21       ...
swissprot_format          WARNING    2        data_mutation.maf
swissprot_missing         WARNING    1        data_mutation.maf
variant_filtered          INFO       1        data_mutation.maf

Status: PASS_WITH_WARNINGS  |  Importable: True

Suggested fixers for detected issues:
  --fix fix_swissprot        Strip .NNN version suffixes from SWISSPROT column in MAF files
```

### 2a. Stage + fix in one step

```bash
python itcc_qc.py /mnt/nc_uploads/__groupfolders/1/<study_dir> --stage --fix-all
```

This copies the study to `/mnt/cbioportal_data/studies/<study_dir>/`, validates it,
then applies all suggested fixers. Dotfiles (e.g. `.ready`) are excluded from the copy.

### 2b. Stage first, fix separately

```bash
# Copy to staging and validate
python itcc_qc.py /mnt/nc_uploads/__groupfolders/1/<study_dir> --stage

# Apply a specific fixer to the staged copy
python itcc_qc.py /mnt/cbioportal_data/studies/<study_id> --fix fix_swissprot

# Re-validate to confirm the fix resolved the warnings
python itcc_qc.py /mnt/cbioportal_data/studies/<study_id>
```

### 3. Import

Once QC passes (exit code 0 or 3), hand the staged study off to the import pipeline.

---

## All options

| Flag | Description |
|------|-------------|
| `--stage` | Copy to `/mnt/cbioportal_data/studies/<name>/` before validating/fixing. Fails if the target already exists. |
| `--fix <NAME>` | Run a named fixer (repeatable). |
| `--fix-all` | Run all fixers that match detected issue types. |
| `--list-fixers` | Print available fixers and exit. |
| `--raw` | Also print the full raw validator output. |

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Importable (clean pass or warnings only) |
| 1 | Errors — not importable, or a fixer failed |

---

## Fixers

| Name | Triggered by | What it does |
|------|-------------|--------------|
| `fix_swissprot` | `swissprot_format` warnings | Strips `.NNN` version suffixes from the SWISSPROT column in MAF files (e.g. `Q99504.176` → `Q99504`). For comma-separated multi-accession values, keeps the first accession only. Writes `.bak` backups before modifying. |

---

## Adding a new fixer

1. Write `fix_<name>(study_dir: Path) -> FixResult` in `fixers.py`. Call
   `_assert_not_uploads(study_dir)` as the first line.
2. Add an entry to `REGISTRY`: `"fix_<name>": ("<description>", fix_<name>)`.
3. Optionally map an issue type to it in `ISSUE_TYPE_TO_FIXER` so it appears
   automatically under "Suggested fixers".
