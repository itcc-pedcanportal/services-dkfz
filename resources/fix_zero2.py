#!/usr/bin/env python3
"""
Fix ZERO-ITCC2 data issues:
1. Fix sample ID typos in MAF file (ensure all start with P + 8 chars)
2. Fix malformatted clinical data
3. Fix case lists
4. Optionally filter MAF file
"""

import sys
import os
import re
from collections import defaultdict


def get_samples_from_clinical(filename):
    """Extract sample IDs from clinical sample file"""
    samples = set()
    with open(filename, 'r') as f:
        for line in f:
            if not line.startswith('#') and not line.startswith('SAMPLE_ID'):
                parts = line.strip().split('\t')
                if len(parts) >= 1:
                    samples.add(parts[0])  # SAMPLE_ID is first column
    return samples


def fix_maf_sample_ids(maf_file, clinical_samples, filter_variants=False):
    """Fix sample IDs in MAF file to match clinical data"""
    print(f"\nFixing MAF file: {maf_file}")

    # Backup original
    backup_file = maf_file + '.backup'
    os.rename(maf_file, backup_file)

    # Variant classifications to filter out
    filtered_classifications = {'Silent', 'Intron', '3\'UTR', '3\'Flank', '5\'UTR', '5\'Flank', 'IGR', 'RNA'}

    # Find column indices
    tumor_sample_col = -1
    variant_class_col = -1

    # Track statistics
    fixed_samples = {}
    unfixable_samples = set()
    total_lines = 0
    filtered_lines = 0

    with open(backup_file, 'r') as infile:
        with open(maf_file, 'w') as outfile:
            for line in infile:
                if line.startswith('Hugo_Symbol'):
                    # Header line - find columns
                    outfile.write(line)
                    parts = line.strip().split('\t')
                    try:
                        tumor_sample_col = parts.index('Tumor_Sample_Barcode')
                    except ValueError:
                        print("ERROR: Could not find Tumor_Sample_Barcode column")
                        return
                    try:
                        variant_class_col = parts.index('Variant_Classification')
                    except ValueError:
                        if filter_variants:
                            print("WARNING: Could not find Variant_Classification column")
                elif line.startswith('#') or tumor_sample_col < 0:
                    # Comment or before header
                    outfile.write(line)
                else:
                    # Data line
                    total_lines += 1
                    parts = line.strip().split('\t')

                    if len(parts) > tumor_sample_col:
                        sample_id = parts[tumor_sample_col]

                        # Check if filtering is needed
                        if filter_variants and variant_class_col >= 0 and len(parts) > variant_class_col:
                            if parts[variant_class_col] in filtered_classifications:
                                filtered_lines += 1
                                continue

                        # Fix sample ID if needed
                        fixed_id = sample_id

                        # Check if it already matches the pattern P + 8 chars + _N
                        if not re.match(r'^P[A-Z0-9]{8}_\d+$', sample_id):
                            # Try to fix common typos

                            # Case 1: Double P at the beginning (e.g., PPFE5VY52J_1 -> PFE5VY52J_1)
                            if sample_id.startswith('PP') and len(sample_id) >= 12:
                                test_id = 'P' + sample_id[2:]
                                if test_id in clinical_samples:
                                    fixed_id = test_id
                                    fixed_samples[sample_id] = fixed_id

                            # Case 2: Missing P at the beginning (e.g., FE5VY52J_1 -> PFE5VY52J_1)
                            elif not sample_id.startswith('P'):
                                test_id = 'P' + sample_id
                                if test_id in clinical_samples:
                                    fixed_id = test_id
                                    fixed_samples[sample_id] = fixed_id

                            # Case 3: Extra characters before P
                            elif 'P' in sample_id:
                                idx = sample_id.find('P')
                                test_id = sample_id[idx:]
                                if test_id in clinical_samples:
                                    fixed_id = test_id
                                    fixed_samples[sample_id] = fixed_id

                        # Check if we fixed it or if it's in clinical data
                        if fixed_id not in clinical_samples and sample_id not in clinical_samples:
                            unfixable_samples.add(sample_id)

                        # Update the line with fixed ID
                        if fixed_id != sample_id:
                            parts[tumor_sample_col] = fixed_id
                            line = '\t'.join(parts) + '\n'

                    outfile.write(line)

    print(f"  Total data lines: {total_lines}")
    if filter_variants:
        print(f"  Filtered out {filtered_lines} lines with non-coding variants")
    print(f"  Fixed {len(fixed_samples)} sample ID typos:")
    for old, new in sorted(fixed_samples.items())[:10]:
        print(f"    {old} -> {new}")
    if len(fixed_samples) > 10:
        print(f"    ... and {len(fixed_samples) - 10} more")

    if unfixable_samples:
        print(f"  WARNING: {len(unfixable_samples)} samples could not be matched to clinical data")
        for sample in sorted(unfixable_samples)[:5]:
            print(f"    {sample}")
        if len(unfixable_samples) > 5:
            print(f"    ... and {len(unfixable_samples) - 5} more")

    return unfixable_samples


def fix_seg_sample_ids(seg_file, clinical_samples):
    """Fix sample IDs in SEG file to match clinical data and filter invalid values"""
    print(f"\nFixing SEG file: {seg_file}")

    # Backup original
    backup_file = seg_file + '.backup'
    os.rename(seg_file, backup_file)

    fixed_samples = {}
    unfixable_samples = set()
    total_lines = 0
    skipped_lines = 0

    # Valid chromosome values
    valid_chromosomes = set([str(i) for i in range(1, 23)] + ['X', 'Y', 'M', 'MT'])

    with open(backup_file, 'r') as infile:
        with open(seg_file, 'w') as outfile:
            # Copy header
            header = next(infile)
            outfile.write(header)

            # Process data lines
            for line in infile:
                total_lines += 1
                parts = line.strip().split('\t')

                if len(parts) >= 6:
                    sample_id = parts[0]
                    chrom = parts[1]
                    start = parts[2]
                    end = parts[3]
                    num_probes = parts[4]
                    seg_mean = parts[5]

                    # Check if any field is empty
                    if not all([sample_id, chrom, start, end, num_probes, seg_mean]):
                        skipped_lines += 1
                        continue

                    # Check chromosome value
                    if chrom not in valid_chromosomes:
                        skipped_lines += 1
                        continue

                    # Check if numeric fields are valid
                    try:
                        int(start)
                        int(end)
                        int(num_probes)
                    except ValueError:
                        skipped_lines += 1
                        continue

                    # Check if segment mean is valid (filter out -nan, nan, inf, etc.)
                    if seg_mean.lower() in ['-nan', 'nan', '-inf', 'inf', 'na', 'null']:
                        skipped_lines += 1
                        continue
                    try:
                        # Verify it's a valid float
                        float(seg_mean)
                    except ValueError:
                        skipped_lines += 1
                        continue

                    # Fix sample ID if needed
                    fixed_id = sample_id
                    if not re.match(r'^P[A-Z0-9]{8}_\d+


def fix_clinical_files(sample_file, patient_file):
    """Check and fix clinical files formatting"""
    print("\nChecking clinical files formatting...")

    # First fix the header issue in sample file if it exists
    needs_header_fix = False
    with open(sample_file, 'r') as f:
        for line in f:
            if 'PATIENT_IDSOMATIC_MUTATION_LOAD' in line:
                needs_header_fix = True
                break

    if needs_header_fix:
        print("  Fixing header issue in sample file...")
        backup_file = sample_file + '.backup'
        os.rename(sample_file, backup_file)

        with open(backup_file, 'r') as infile:
            with open(sample_file, 'w') as outfile:
                for line in infile:
                    # Fix the merged column header
                    if 'PATIENT_IDSOMATIC_MUTATION_LOAD' in line:
                        line = line.replace('PATIENT_IDSOMATIC_MUTATION_LOAD', 'PATIENT_ID\tSOMATIC_MUTATION_LOAD')
                    # Fix data lines where patient ID and somatic mutation load are merged
                    # Look for lines ending with patient ID followed directly by numbers
                    parts = line.strip().split('\t')
                    if len(parts) >= 7 and parts[6] and re.match(r'P[A-Z0-9]{8}\d+', parts[6]):
                        # Split the merged field
                        match = re.match(r'(P[A-Z0-9]{8})(\d+)', parts[6])
                        if match:
                            parts[6] = match.group(1)
                            parts.insert(7, match.group(2))
                            line = '\t'.join(parts) + '\n'
                    outfile.write(line)

    # Check and fix patient file too
    print("  Checking patient file formatting...")
    with open(patient_file, 'r') as f:
        patient_lines = f.readlines()

    # Check if patient IDs are in the wrong column
    needs_patient_fix = False
    for line in patient_lines:
        if not line.startswith('#') and not line.startswith('AGE'):
            parts = line.strip().split('\t')
            # Patient ID should be in column 5 (index 4), but might be in column 1 (index 0)
            if len(parts) >= 1 and parts[0] and re.match(r'^P[A-Z0-9]{8}

            headers =[]
            data_lines =[]
            for line in lines:
                if
            line.startswith('#') or line.startswith('SAMPLE_ID'):
            headers.append(line)
            else:
            data_lines.append(line)

            # Find expected column count from header
            expected_cols = 0
            for h in headers:
                if
            h.startswith('SAMPLE_ID'):
            expected_cols = len(h.strip().split('\t'))
            break

    print(f"  Expected {expected_cols} columns in sample file")

    # Check for any malformed lines
    malformed = []
    for i, line in enumerate(data_lines):
        parts = line.strip().split('\t')
        if len(parts) < expected_cols:
            malformed.append(i)

    if malformed:
        print(f"  WARNING: Found {len(malformed)} malformed lines in clinical sample file")
        print(f"  These will need to be fixed or removed")
    else:
        print(f"  Clinical sample file appears properly formatted with {len(data_lines)} samples")


def fix_case_lists(case_lists_dir, clinical_samples):
    """Fix case list files"""
    print("\nFixing case lists...")

    # Fix cases_sequenced.txt
    seq_file = os.path.join(case_lists_dir, 'cases_sequenced.txt')
    if os.path.exists(seq_file):
        # Backup
        backup_file = seq_file + '.backup'
        os.rename(seq_file, backup_file)

        # Read the metadata
        metadata = []
        with open(backup_file, 'r') as f:
            for line in f:
                if not line.startswith('case_list_ids:'):
                    metadata.append(line)

        # Rewrite with correct sample list
        with open(seq_file, 'w') as f:
            for line in metadata:
                f.write(line)
            f.write(f"case_list_ids: {'\t'.join(sorted(clinical_samples))}\n")

        print(f"  Fixed {seq_file} with {len(clinical_samples)} samples")

    # Fix cases_all.txt if it exists
    all_file = os.path.join(case_lists_dir, 'cases_all.txt')
    if os.path.exists(all_file):
        # Backup
        backup_file = all_file + '.backup'
        os.rename(all_file, backup_file)

        # Read the metadata
        metadata = []
        with open(backup_file, 'r') as f:
            for line in f:
                if not line.startswith('case_list_ids:'):
                    metadata.append(line)

        # Rewrite with correct sample list
        with open(all_file, 'w') as f:
            for line in metadata:
                f.write(line)
            f.write(f"case_list_ids: {'\t'.join(sorted(clinical_samples))}\n")

        print(f"  Fixed {all_file} with {len(clinical_samples)} samples")


def update_cancer_type_colors(cancer_type_file):
    """Update cancer type file with proper colors"""
    print("\nUpdating cancer type colors...")

    color_mapping = {
        'all': 'lightblue',
        'aml': 'orange',
        'dsrct': 'mediumpurple',
        'epn': 'steelblue',
        'ews': 'purple',
        'hgg': 'darkblue',
        'hl': 'lightgreen',
        'lgg': 'skyblue',
        'mb': 'darkgreen',
        'mixed': 'gray',
        'nbl': 'red',
        'nhl': 'green',
        'osteo': 'brown',
        'other': 'darkgray',
        'rhabdoid': 'darkred',
        'sts': 'salmon',
        'wt': 'darkorange'
    }

    # Backup and rewrite
    backup_file = cancer_type_file + '.backup'
    os.rename(cancer_type_file, backup_file)

    with open(backup_file, 'r') as infile:
        with open(cancer_type_file, 'w') as outfile:
            for line in infile:
                parts = line.strip().split('\t')
                if len(parts) >= 4:
                    type_id = parts[0]
                    if type_id in color_mapping:
                        parts[2] = color_mapping[type_id]
                    outfile.write('\t'.join(parts) + '\n')

    print("  Updated cancer type colors")


def add_missing_samples_to_clinical(sample_file, patient_file, missing_samples):
    """Add missing samples to clinical files"""
    if not missing_samples:
        return

    print(f"\nAdding {len(missing_samples)} missing samples to clinical files...")

    # Get the header structure from sample file
    with open(sample_file, 'r') as f:
        for line in f:
            if line.startswith('SAMPLE_ID'):
                header_cols = line.strip().split('\t')
                break

    # Add to sample file
    with open(sample_file, 'a') as f:
        for sample_id in sorted(missing_samples):
            # Infer patient ID
            patient_id = sample_id.rsplit('_', 1)[0] if '_' in sample_id else sample_id

            # Create entry based on header structure
            # SAMPLE_ID, MONTHS_SINCE_SAMPLE_EXTRACTION, SAMPLE_CLASS, CANCER_TYPE,
            # CANCER_TYPE_DETAILED, MOLECULAR_DIAG_SUBGROUP, PATIENT_ID, SOMATIC_MUTATION_LOAD, TUMOR_PERCENTAGE
            f.write(f"{sample_id}\t\tOther\tOther\tOther\t\t{patient_id}\t\t\n")

    # Get existing patients
    existing_patients = set()
    with open(patient_file, 'r') as f:
        for line in f:
            if not line.startswith('#') and not line.startswith('AGE'):
                parts = line.strip().split('\t')
                if len(parts) >= 5:
                    existing_patients.add(parts[4])  # PATIENT_ID is 5th column

    # Add missing patients
    new_patients = set()
    for sample_id in missing_samples:
        patient_id = sample_id.rsplit('_', 1)[0] if '_' in sample_id else sample_id
        if patient_id not in existing_patients:
            new_patients.add(patient_id)

    if new_patients:
        with open(patient_file, 'a') as f:
            for patient_id in sorted(new_patients):
                f.write(f"\t\t\t\t{patient_id}\n")
        print(f"  Added {len(new_patients)} new patients")


def main():
    if len(sys.argv) < 2:
        print("Usage: python fix_zero_itcc2.py <study_directory> [--filter-maf]")
        print("Example: python fix_zero_itcc2.py /mnt/cbioportal_data/studies/ZERO-ITCC2")
        print("         python fix_zero_itcc2.py /mnt/cbioportal_data/studies/ZERO-ITCC2 --filter-maf")
        sys.exit(1)

    study_dir = sys.argv[1]
    filter_maf = '--filter-maf' in sys.argv

    # File paths
    clinical_sample_file = os.path.join(study_dir, 'data_clinical_sample.txt')
    clinical_patient_file = os.path.join(study_dir, 'data_clinical_patient.txt')
    maf_file = os.path.join(study_dir, 'data_mutation.maf')
    seg_file = os.path.join(study_dir, 'data_seg.seg')
    case_lists_dir = os.path.join(study_dir, 'case_lists')
    cancer_type_file = os.path.join(study_dir, 'cancer_type.txt')

    print(f"Fixing study directory: {study_dir}")
    if filter_maf:
        print("Will filter MAF file to keep only protein-coding variants")
    print("-" * 50)

    # Get all clinical samples
    clinical_samples = get_samples_from_clinical(clinical_sample_file)
    print(f"Found {len(clinical_samples)} samples in clinical file")

    # Check clinical file formatting
    fix_clinical_files(clinical_sample_file, clinical_patient_file)

    # Fix MAF file
    unfixable_maf = set()
    if os.path.exists(maf_file):
        unfixable_maf = fix_maf_sample_ids(maf_file, clinical_samples, filter_maf)

    # Fix SEG file
    unfixable_seg = set()
    if os.path.exists(seg_file):
        unfixable_seg = fix_seg_sample_ids(seg_file, clinical_samples)

    # Combine all unfixable samples
    all_missing = unfixable_maf | unfixable_seg

    if all_missing:
        print(f"\nFound {len(all_missing)} samples in genomic files that are not in clinical files")
        response = input("Add these missing samples to clinical files? (y/n): ")
        if response.lower() == 'y':
            add_missing_samples_to_clinical(clinical_sample_file, clinical_patient_file, all_missing)
            # Re-read clinical samples after adding
            clinical_samples = get_samples_from_clinical(clinical_sample_file)

    # Fix case lists with updated sample list
    fix_case_lists(case_lists_dir, clinical_samples)


def print_final_summary(study_dir):
    """Print summary of the final data"""
    print("\n" + "=" * 50)
    print("FINAL DATA SUMMARY:")

    # Count samples in clinical file
    clinical_sample_file = os.path.join(study_dir, 'data_clinical_sample.txt')
    clinical_samples = get_samples_from_clinical(clinical_sample_file)
    print(f"  Total clinical samples: {len(clinical_samples)}")

    # Count patients
    clinical_patient_file = os.path.join(study_dir, 'data_clinical_patient.txt')
    patients = set()
    with open(clinical_patient_file, 'r') as f:
        for line in f:
            if not line.startswith('#') and not line.startswith('AGE'):
                parts = line.strip().split('\t')
                if len(parts) >= 5:
                    patients.add(parts[4])
    print(f"  Total patients: {len(patients)}")

    # Count samples with MAF data
    maf_file = os.path.join(study_dir, 'data_mutation.maf')
    maf_samples = set()
    if os.path.exists(maf_file):
        with open(maf_file, 'r') as f:
            for line in f:
                if line.startswith('Hugo_Symbol'):
                    parts = line.strip().split('\t')
                    try:
                        tumor_sample_col = parts.index('Tumor_Sample_Barcode')
                        break
                    except ValueError:
                        tumor_sample_col = -1
            if tumor_sample_col >= 0:
                for line in f:
                    if not line.startswith('#'):
                        parts = line.strip().split('\t')
                        if len(parts) > tumor_sample_col:
                            maf_samples.add(parts[tumor_sample_col])
    print(f"  Samples with MAF data: {len(maf_samples)}")

    # Count samples with SEG data
    seg_file = os.path.join(study_dir, 'data_seg.seg')
    seg_samples = set()
    if os.path.exists(seg_file):
        with open(seg_file, 'r') as f:
            next(f)  # Skip header
            for line in f:
                parts = line.strip().split('\t')
                if parts:
                    seg_samples.add(parts[0])
    print(f"  Samples with SEG data: {len(seg_samples)}")

    # Check for samples without genomic data
    samples_without_genomic = clinical_samples - (maf_samples | seg_samples)
    if samples_without_genomic:
        print(f"  WARNING: {len(samples_without_genomic)} samples have no genomic data")

    print("=" * 50)


def main():
    if len(sys.argv) < 2:
        print("Usage: python fix_zero_itcc2.py <study_directory> [--filter-maf]")
        print("Example: python fix_zero_itcc2.py /mnt/cbioportal_data/studies/ZERO-ITCC2")
        print("         python fix_zero_itcc2.py /mnt/cbioportal_data/studies/ZERO-ITCC2 --filter-maf")
        sys.exit(1)

    study_dir = sys.argv[1]
    filter_maf = '--filter-maf' in sys.argv

    # File paths
    clinical_sample_file = os.path.join(study_dir, 'data_clinical_sample.txt')
    clinical_patient_file = os.path.join(study_dir, 'data_clinical_patient.txt')
    maf_file = os.path.join(study_dir, 'data_mutation.maf')
    seg_file = os.path.join(study_dir, 'data_seg.seg')
    case_lists_dir = os.path.join(study_dir, 'case_lists')
    cancer_type_file = os.path.join(study_dir, 'cancer_type.txt')

    print(f"Fixing study directory: {study_dir}")
    if filter_maf:
        print("Will filter MAF file to keep only protein-coding variants")
    print("-" * 50)

    # Get all clinical samples
    clinical_samples = get_samples_from_clinical(clinical_sample_file)
    print(f"Found {len(clinical_samples)} samples in clinical file")

    # Check clinical file formatting
    fix_clinical_files(clinical_sample_file, clinical_patient_file)

    # Fix MAF file
    unfixable_maf = set()
    if os.path.exists(maf_file):
        unfixable_maf = fix_maf_sample_ids(maf_file, clinical_samples, filter_maf)

    # Fix SEG file
    unfixable_seg = set()
    if os.path.exists(seg_file):
        unfixable_seg = fix_seg_sample_ids(seg_file, clinical_samples)

    # Combine all unfixable samples
    all_missing = unfixable_maf | unfixable_seg

    if all_missing:
        print(f"\nFound {len(all_missing)} samples in genomic files that are not in clinical files")
        response = input("Add these missing samples to clinical files? (y/n): ")
        if response.lower() == 'y':
            add_missing_samples_to_clinical(clinical_sample_file, clinical_patient_file, all_missing)
            # Re-read clinical samples after adding
            clinical_samples = get_samples_from_clinical(clinical_sample_file)

    # Fix case lists with updated sample list
    fix_case_lists(case_lists_dir, clinical_samples)

    # Update cancer type colors
    if os.path.exists(cancer_type_file):
        update_cancer_type_colors(cancer_type_file)

    # Print final summary
    print_final_summary(study_dir)

    print("\nDone! Original files backed up with .backup extension")
    print("\nNext steps:")
    print("1. Re-run the validation script")
    print("2. Try importing again")


if __name__ == "__main__":
    main()
, sample_id):
if sample_id.startswith('PP') and len(sample_id) >= 12:
    test_id = 'P' + sample_id[2:]
if test_id in clinical_samples:
    fixed_id = test_id
fixed_samples[sample_id] = fixed_id
elif not sample_id.startswith('P'):
test_id = 'P' + sample_id
if test_id in clinical_samples:
    fixed_id = test_id
fixed_samples[sample_id] = fixed_id

if fixed_id not in clinical_samples and sample_id not in clinical_samples:
    unfixable_samples.add(sample_id)

# Update the line
if fixed_id != sample_id:
    parts[0] = fixed_id
line = '\t'.join(parts) + '\n'

outfile.write(line)

print(f"  Total SEG lines processed: {total_lines}")
print(f"  Skipped {skipped_lines} lines with invalid values")
if fixed_samples:
    print(f"  Fixed {len(fixed_samples)} sample ID typos")

return unfixable_samples


def fix_clinical_files(sample_file, patient_file):
    """Fix formatting issues in clinical files"""
    print("\nFixing clinical files formatting...")

    # First, read the properly formatted entries to understand the structure
    proper_entries = []
    with open(sample_file, 'r') as f:
        for line in f:
            if not line.startswith('#') and not line.startswith('SAMPLE_ID'):
                parts = line.strip().split('\t')
                if len(parts) >= 8:  # Properly formatted entries have many columns
                    proper_entries.append(line)

    if not proper_entries:
        print("  ERROR: No properly formatted entries found to use as template")
        return

    # Get column count from a proper entry
    expected_cols = len(proper_entries[0].split('\t'))
    print(f"  Expected {expected_cols} columns in sample file")

    # Create backup and rewrite file
    backup_file = sample_file + '.backup2'
    os.rename(sample_file, backup_file)

    with open(backup_file, 'r') as infile:
        with open(sample_file, 'w') as outfile:
            # Copy headers
            for line in infile:
                if line.startswith('#') or line.startswith('SAMPLE_ID'):
                    outfile.write(line)
                else:
                    parts = line.strip().split('\t')
                    if len(parts) >= expected_cols:
                        # Properly formatted line
                        outfile.write(line)
                    elif len(parts) == 4:
                        # This looks like an improperly added line (patient_id, sample_id, cancer_type, cancer_type_detailed)
                        # Need to expand it to full format
                        patient_id = parts[0]
                        sample_id = parts[1]
                        cancer_type = parts[2]
                        cancer_type_detailed = parts[3]

                        # Fix cancer type capitalization
                        if cancer_type.lower() == 'other':
                            cancer_type = 'Other'
                        if cancer_type_detailed.lower() == 'other':
                            cancer_type_detailed = 'Other'

                        # Create a properly formatted line with empty values for missing columns
                        # Based on the header, we need these columns:
                        # SAMPLE_ID, MONTHS_SINCE_SAMPLE_EXTRACTION, SAMPLE_CLASS, CANCER_TYPE,
                        # CANCER_TYPE_DETAILED, MOLECULAR_DIAG_SUBGROUP, PATIENT_ID, SOMATIC_MUTATION_LOAD, TUMOR_PERCENTAGE
                        new_line = f"{sample_id}\t\t{cancer_type}\t{cancer_type}\t{cancer_type_detailed}\t\t{patient_id}\t\t\n"
                        outfile.write(new_line)
                        print(f"  Fixed formatting for sample: {sample_id}")
                    else:
                        print(f"  WARNING: Unexpected line format: {line.strip()}")


def fix_case_lists(case_lists_dir, clinical_samples):
    """Fix case list files"""
    print("\nFixing case lists...")

    # Fix cases_sequenced.txt
    seq_file = os.path.join(case_lists_dir, 'cases_sequenced.txt')
    if os.path.exists(seq_file):
        # Backup
        backup_file = seq_file + '.backup'
        os.rename(seq_file, backup_file)

        # Read the metadata
        metadata = []
        with open(backup_file, 'r') as f:
            for line in f:
                if not line.startswith('case_list_ids:'):
                    metadata.append(line)

        # Rewrite with correct sample list
        with open(seq_file, 'w') as f:
            for line in metadata:
                f.write(line)
            f.write(f"case_list_ids: {'\t'.join(sorted(clinical_samples))}\n")

        print(f"  Fixed {seq_file} with {len(clinical_samples)} samples")

    # Fix cases_all.txt if it exists
    all_file = os.path.join(case_lists_dir, 'cases_all.txt')
    if os.path.exists(all_file):
        # Backup
        backup_file = all_file + '.backup'
        os.rename(all_file, backup_file)

        # Read the metadata
        metadata = []
        with open(backup_file, 'r') as f:
            for line in f:
                if not line.startswith('case_list_ids:'):
                    metadata.append(line)

        # Rewrite with correct sample list
        with open(all_file, 'w') as f:
            for line in metadata:
                f.write(line)
            f.write(f"case_list_ids: {'\t'.join(sorted(clinical_samples))}\n")

        print(f"  Fixed {all_file} with {len(clinical_samples)} samples")


def update_cancer_type_colors(cancer_type_file):
    """Update cancer type file with proper colors"""
    print("\nUpdating cancer type colors...")

    color_mapping = {
        'all': 'lightblue',
        'aml': 'orange',
        'dsrct': 'mediumpurple',
        'epn': 'steelblue',
        'ews': 'purple',
        'hgg': 'darkblue',
        'hl': 'lightgreen',
        'lgg': 'skyblue',
        'mb': 'darkgreen',
        'mixed': 'gray',
        'nbl': 'red',
        'nhl': 'green',
        'osteo': 'brown',
        'other': 'darkgray',
        'rhabdoid': 'darkred',
        'sts': 'salmon',
        'wt': 'darkorange'
    }

    # Backup and rewrite
    backup_file = cancer_type_file + '.backup'
    os.rename(cancer_type_file, backup_file)

    with open(backup_file, 'r') as infile:
        with open(cancer_type_file, 'w') as outfile:
            for line in infile:
                parts = line.strip().split('\t')
                if len(parts) >= 4:
                    type_id = parts[0]
                    if type_id in color_mapping:
                        parts[2] = color_mapping[type_id]
                    outfile.write('\t'.join(parts) + '\n')

    print("  Updated cancer type colors")


def main():
    if len(sys.argv) < 2:
        print("Usage: python fix_zero_itcc2.py <study_directory> [--filter-maf]")
        print("Example: python fix_zero_itcc2.py /mnt/cbioportal_data/studies/ZERO-ITCC2")
        print("         python fix_zero_itcc2.py /mnt/cbioportal_data/studies/ZERO-ITCC2 --filter-maf")
        sys.exit(1)

    study_dir = sys.argv[1]
    filter_maf = '--filter-maf' in sys.argv

    # File paths
    clinical_sample_file = os.path.join(study_dir, 'data_clinical_sample.txt')
    clinical_patient_file = os.path.join(study_dir, 'data_clinical_patient.txt')
    maf_file = os.path.join(study_dir, 'data_mutation.maf')
    seg_file = os.path.join(study_dir, 'data_seg.seg')
    case_lists_dir = os.path.join(study_dir, 'case_lists')
    cancer_type_file = os.path.join(study_dir, 'cancer_type.txt')

    print(f"Fixing study directory: {study_dir}")
    if filter_maf:
        print("Will filter MAF file to keep only protein-coding variants")
    print("-" * 50)

    # Get all clinical samples
    clinical_samples = get_samples_from_clinical(clinical_sample_file)
    print(f"Found {len(clinical_samples)} samples in clinical file")

    # Fix clinical file formatting first
    fix_clinical_files(clinical_sample_file, clinical_patient_file)

    # Re-read clinical samples after fixing
    clinical_samples = get_samples_from_clinical(clinical_sample_file)

    # Fix MAF file
    if os.path.exists(maf_file):
        unfixable_maf = fix_maf_sample_ids(maf_file, clinical_samples, filter_maf)

    # Fix SEG file
    if os.path.exists(seg_file):
        unfixable_seg = fix_seg_sample_ids(seg_file, clinical_samples)

    # Fix case lists
    fix_case_lists(case_lists_dir, clinical_samples)

    # Update cancer type colors
    if os.path.exists(cancer_type_file):
        update_cancer_type_colors(cancer_type_file)

    print("\n" + "-" * 50)
    print("Done! Original files backed up with .backup extension")
    print("\nNext steps:")
    print("1. Re-run the validation script")
    print("2. Try importing again")


if __name__ == "__main__":
    main()
, parts[0]):
if len(parts) < 5 or not parts[4]:
    needs_patient_fix = True
break

if needs_patient_fix:
    print("  Fixing patient ID column placement...")
    backup_file = patient_file + '.backup'
    os.rename(patient_file, backup_file)

    with open(backup_file, 'r') as infile:
        with open(patient_file, 'w') as outfile:
            for line in infile:
                if line.startswith('#') or line.startswith('AGE'):
                    outfile.write(line)
                else:
                    parts = line.strip().split('\t')
                    if len(parts) >= 1 and re.match(r'^P[A-Z0-9]{8}

                    headers =[]
                    data_lines =[]
                    for line in lines:
                        if
                    line.startswith('#') or line.startswith('SAMPLE_ID'):
                    headers.append(line)
                    else:
                    data_lines.append(line)

                    # Find expected column count from header
                    expected_cols = 0
                    for h in headers:
                        if
                    h.startswith('SAMPLE_ID'): \
                        expected_cols = len(h.strip().split('\t'))
        break

print(f"  Expected {expected_cols} columns in sample file")

# Check for any malformed lines
malformed = []
for i, line in enumerate(data_lines):
    parts = line.strip().split('\t')
    if len(parts) < expected_cols:
        malformed.append(i)

if malformed:
    print(f"  WARNING: Found {len(malformed)} malformed lines in clinical sample file")
    print(f"  These will need to be fixed or removed")
else:
    print(f"  Clinical sample file appears properly formatted with {len(data_lines)} samples")


def fix_case_lists(case_lists_dir, clinical_samples):
    """Fix case list files"""
    print("\nFixing case lists...")

    # Fix cases_sequenced.txt
    seq_file = os.path.join(case_lists_dir, 'cases_sequenced.txt')
    if os.path.exists(seq_file):
        # Backup
        backup_file = seq_file + '.backup'
        os.rename(seq_file, backup_file)

        # Read the metadata
        metadata = []
        with open(backup_file, 'r') as f:
            for line in f:
                if not line.startswith('case_list_ids:'):
                    metadata.append(line)

        # Rewrite with correct sample list
        with open(seq_file, 'w') as f:
            for line in metadata:
                f.write(line)
            f.write(f"case_list_ids: {'\t'.join(sorted(clinical_samples))}\n")

        print(f"  Fixed {seq_file} with {len(clinical_samples)} samples")

    # Fix cases_all.txt if it exists
    all_file = os.path.join(case_lists_dir, 'cases_all.txt')
    if os.path.exists(all_file):
        # Backup
        backup_file = all_file + '.backup'
        os.rename(all_file, backup_file)

        # Read the metadata
        metadata = []
        with open(backup_file, 'r') as f:
            for line in f:
                if not line.startswith('case_list_ids:'):
                    metadata.append(line)

        # Rewrite with correct sample list
        with open(all_file, 'w') as f:
            for line in metadata:
                f.write(line)
            f.write(f"case_list_ids: {'\t'.join(sorted(clinical_samples))}\n")

        print(f"  Fixed {all_file} with {len(clinical_samples)} samples")


def update_cancer_type_colors(cancer_type_file):
    """Update cancer type file with proper colors"""
    print("\nUpdating cancer type colors...")

    color_mapping = {
        'all': 'lightblue',
        'aml': 'orange',
        'dsrct': 'mediumpurple',
        'epn': 'steelblue',
        'ews': 'purple',
        'hgg': 'darkblue',
        'hl': 'lightgreen',
        'lgg': 'skyblue',
        'mb': 'darkgreen',
        'mixed': 'gray',
        'nbl': 'red',
        'nhl': 'green',
        'osteo': 'brown',
        'other': 'darkgray',
        'rhabdoid': 'darkred',
        'sts': 'salmon',
        'wt': 'darkorange'
    }

    # Backup and rewrite
    backup_file = cancer_type_file + '.backup'
    os.rename(cancer_type_file, backup_file)

    with open(backup_file, 'r') as infile:
        with open(cancer_type_file, 'w') as outfile:
            for line in infile:
                parts = line.strip().split('\t')
                if len(parts) >= 4:
                    type_id = parts[0]
                    if type_id in color_mapping:
                        parts[2] = color_mapping[type_id]
                    outfile.write('\t'.join(parts) + '\n')

    print("  Updated cancer type colors")


def add_missing_samples_to_clinical(sample_file, patient_file, missing_samples):
    """Add missing samples to clinical files"""
    if not missing_samples:
        return

    print(f"\nAdding {len(missing_samples)} missing samples to clinical files...")

    # Get the header structure from sample file
    with open(sample_file, 'r') as f:
        for line in f:
            if line.startswith('SAMPLE_ID'):
                header_cols = line.strip().split('\t')
                break

    # Add to sample file
    with open(sample_file, 'a') as f:
        for sample_id in sorted(missing_samples):
            # Infer patient ID
            patient_id = sample_id.rsplit('_', 1)[0] if '_' in sample_id else sample_id

            # Create entry based on header structure
            # SAMPLE_ID, MONTHS_SINCE_SAMPLE_EXTRACTION, SAMPLE_CLASS, CANCER_TYPE,
            # CANCER_TYPE_DETAILED, MOLECULAR_DIAG_SUBGROUP, PATIENT_ID, SOMATIC_MUTATION_LOAD, TUMOR_PERCENTAGE
            f.write(f"{sample_id}\t\tOther\tOther\tOther\t\t{patient_id}\t\t\n")

    # Get existing patients
    existing_patients = set()
    with open(patient_file, 'r') as f:
        for line in f:
            if not line.startswith('#') and not line.startswith('AGE'):
                parts = line.strip().split('\t')
                if len(parts) >= 5:
                    existing_patients.add(parts[4])  # PATIENT_ID is 5th column

    # Add missing patients
    new_patients = set()
    for sample_id in missing_samples:
        patient_id = sample_id.rsplit('_', 1)[0] if '_' in sample_id else sample_id
        if patient_id not in existing_patients:
            new_patients.add(patient_id)

    if new_patients:
        with open(patient_file, 'a') as f:
            for patient_id in sorted(new_patients):
                f.write(f"\t\t\t\t{patient_id}\n")
        print(f"  Added {len(new_patients)} new patients")


def main():
    if len(sys.argv) < 2:
        print("Usage: python fix_zero_itcc2.py <study_directory> [--filter-maf]")
        print("Example: python fix_zero_itcc2.py /mnt/cbioportal_data/studies/ZERO-ITCC2")
        print("         python fix_zero_itcc2.py /mnt/cbioportal_data/studies/ZERO-ITCC2 --filter-maf")
        sys.exit(1)

    study_dir = sys.argv[1]
    filter_maf = '--filter-maf' in sys.argv

    # File paths
    clinical_sample_file = os.path.join(study_dir, 'data_clinical_sample.txt')
    clinical_patient_file = os.path.join(study_dir, 'data_clinical_patient.txt')
    maf_file = os.path.join(study_dir, 'data_mutation.maf')
    seg_file = os.path.join(study_dir, 'data_seg.seg')
    case_lists_dir = os.path.join(study_dir, 'case_lists')
    cancer_type_file = os.path.join(study_dir, 'cancer_type.txt')

    print(f"Fixing study directory: {study_dir}")
    if filter_maf:
        print("Will filter MAF file to keep only protein-coding variants")
    print("-" * 50)

    # Get all clinical samples
    clinical_samples = get_samples_from_clinical(clinical_sample_file)
    print(f"Found {len(clinical_samples)} samples in clinical file")

    # Check clinical file formatting
    fix_clinical_files(clinical_sample_file, clinical_patient_file)

    # Fix MAF file
    unfixable_maf = set()
    if os.path.exists(maf_file):
        unfixable_maf = fix_maf_sample_ids(maf_file, clinical_samples, filter_maf)

    # Fix SEG file
    unfixable_seg = set()
    if os.path.exists(seg_file):
        unfixable_seg = fix_seg_sample_ids(seg_file, clinical_samples)

    # Combine all unfixable samples
    all_missing = unfixable_maf | unfixable_seg

    if all_missing:
        print(f"\nFound {len(all_missing)} samples in genomic files that are not in clinical files")
        response = input("Add these missing samples to clinical files? (y/n): ")
        if response.lower() == 'y':
            add_missing_samples_to_clinical(clinical_sample_file, clinical_patient_file, all_missing)
            # Re-read clinical samples after adding
            clinical_samples = get_samples_from_clinical(clinical_sample_file)

    # Fix case lists with updated sample list
    fix_case_lists(case_lists_dir, clinical_samples)


def print_final_summary(study_dir):
    """Print summary of the final data"""
    print("\n" + "=" * 50)
    print("FINAL DATA SUMMARY:")

    # Count samples in clinical file
    clinical_sample_file = os.path.join(study_dir, 'data_clinical_sample.txt')
    clinical_samples = get_samples_from_clinical(clinical_sample_file)
    print(f"  Total clinical samples: {len(clinical_samples)}")

    # Count patients
    clinical_patient_file = os.path.join(study_dir, 'data_clinical_patient.txt')
    patients = set()
    with open(clinical_patient_file, 'r') as f:
        for line in f:
            if not line.startswith('#') and not line.startswith('AGE'):
                parts = line.strip().split('\t')
                if len(parts) >= 5:
                    patients.add(parts[4])
    print(f"  Total patients: {len(patients)}")

    # Count samples with MAF data
    maf_file = os.path.join(study_dir, 'data_mutation.maf')
    maf_samples = set()
    if os.path.exists(maf_file):
        with open(maf_file, 'r') as f:
            for line in f:
                if line.startswith('Hugo_Symbol'):
                    parts = line.strip().split('\t')
                    try:
                        tumor_sample_col = parts.index('Tumor_Sample_Barcode')
                        break
                    except ValueError:
                        tumor_sample_col = -1
            if tumor_sample_col >= 0:
                for line in f:
                    if not line.startswith('#'):
                        parts = line.strip().split('\t')
                        if len(parts) > tumor_sample_col:
                            maf_samples.add(parts[tumor_sample_col])
    print(f"  Samples with MAF data: {len(maf_samples)}")

    # Count samples with SEG data
    seg_file = os.path.join(study_dir, 'data_seg.seg')
    seg_samples = set()
    if os.path.exists(seg_file):
        with open(seg_file, 'r') as f:
            next(f)  # Skip header
            for line in f:
                parts = line.strip().split('\t')
                if parts:
                    seg_samples.add(parts[0])
    print(f"  Samples with SEG data: {len(seg_samples)}")

    # Check for samples without genomic data
    samples_without_genomic = clinical_samples - (maf_samples | seg_samples)
    if samples_without_genomic:
        print(f"  WARNING: {len(samples_without_genomic)} samples have no genomic data")

    print("=" * 50)


def main():
    if len(sys.argv) < 2:
        print("Usage: python fix_zero_itcc2.py <study_directory> [--filter-maf]")
        print("Example: python fix_zero_itcc2.py /mnt/cbioportal_data/studies/ZERO-ITCC2")
        print("         python fix_zero_itcc2.py /mnt/cbioportal_data/studies/ZERO-ITCC2 --filter-maf")
        sys.exit(1)

    study_dir = sys.argv[1]
    filter_maf = '--filter-maf' in sys.argv

    # File paths
    clinical_sample_file = os.path.join(study_dir, 'data_clinical_sample.txt')
    clinical_patient_file = os.path.join(study_dir, 'data_clinical_patient.txt')
    maf_file = os.path.join(study_dir, 'data_mutation.maf')
    seg_file = os.path.join(study_dir, 'data_seg.seg')
    case_lists_dir = os.path.join(study_dir, 'case_lists')
    cancer_type_file = os.path.join(study_dir, 'cancer_type.txt')

    print(f"Fixing study directory: {study_dir}")
    if filter_maf:
        print("Will filter MAF file to keep only protein-coding variants")
    print("-" * 50)

    # Get all clinical samples
    clinical_samples = get_samples_from_clinical(clinical_sample_file)
    print(f"Found {len(clinical_samples)} samples in clinical file")

    # Check clinical file formatting
    fix_clinical_files(clinical_sample_file, clinical_patient_file)

    # Fix MAF file
    unfixable_maf = set()
    if os.path.exists(maf_file):
        unfixable_maf = fix_maf_sample_ids(maf_file, clinical_samples, filter_maf)

    # Fix SEG file
    unfixable_seg = set()
    if os.path.exists(seg_file):
        unfixable_seg = fix_seg_sample_ids(seg_file, clinical_samples)

    # Combine all unfixable samples
    all_missing = unfixable_maf | unfixable_seg

    if all_missing:
        print(f"\nFound {len(all_missing)} samples in genomic files that are not in clinical files")
        response = input("Add these missing samples to clinical files? (y/n): ")
        if response.lower() == 'y':
            add_missing_samples_to_clinical(clinical_sample_file, clinical_patient_file, all_missing)
            # Re-read clinical samples after adding
            clinical_samples = get_samples_from_clinical(clinical_sample_file)

    # Fix case lists with updated sample list
    fix_case_lists(case_lists_dir, clinical_samples)

    # Update cancer type colors
    if os.path.exists(cancer_type_file):
        update_cancer_type_colors(cancer_type_file)

    # Print final summary
    print_final_summary(study_dir)

    print("\nDone! Original files backed up with .backup extension")
    print("\nNext steps:")
    print("1. Re-run the validation script")
    print("2. Try importing again")


if __name__ == "__main__":
    main()
, sample_id):
if sample_id.startswith('PP') and len(sample_id) >= 12:
    test_id = 'P' + sample_id[2:]
if test_id in clinical_samples:
    fixed_id = test_id
fixed_samples[sample_id] = fixed_id
elif not sample_id.startswith('P'):
test_id = 'P' + sample_id
if test_id in clinical_samples:
    fixed_id = test_id
fixed_samples[sample_id] = fixed_id

if fixed_id not in clinical_samples and sample_id not in clinical_samples:
    unfixable_samples.add(sample_id)

# Update the line
if fixed_id != sample_id:
    parts[0] = fixed_id
line = '\t'.join(parts) + '\n'

outfile.write(line)

print(f"  Total SEG lines processed: {total_lines}")
print(f"  Skipped {skipped_lines} lines with invalid values")
if fixed_samples:
    print(f"  Fixed {len(fixed_samples)} sample ID typos")

return unfixable_samples


def fix_clinical_files(sample_file, patient_file):
    """Fix formatting issues in clinical files"""
    print("\nFixing clinical files formatting...")

    # First, read the properly formatted entries to understand the structure
    proper_entries = []
    with open(sample_file, 'r') as f:
        for line in f:
            if not line.startswith('#') and not line.startswith('SAMPLE_ID'):
                parts = line.strip().split('\t')
                if len(parts) >= 8:  # Properly formatted entries have many columns
                    proper_entries.append(line)

    if not proper_entries:
        print("  ERROR: No properly formatted entries found to use as template")
        return

    # Get column count from a proper entry
    expected_cols = len(proper_entries[0].split('\t'))
    print(f"  Expected {expected_cols} columns in sample file")

    # Create backup and rewrite file
    backup_file = sample_file + '.backup2'
    os.rename(sample_file, backup_file)

    with open(backup_file, 'r') as infile:
        with open(sample_file, 'w') as outfile:
            # Copy headers
            for line in infile:
                if line.startswith('#') or line.startswith('SAMPLE_ID'):
                    outfile.write(line)
                else:
                    parts = line.strip().split('\t')
                    if len(parts) >= expected_cols:
                        # Properly formatted line
                        outfile.write(line)
                    elif len(parts) == 4:
                        # This looks like an improperly added line (patient_id, sample_id, cancer_type, cancer_type_detailed)
                        # Need to expand it to full format
                        patient_id = parts[0]
                        sample_id = parts[1]
                        cancer_type = parts[2]
                        cancer_type_detailed = parts[3]

                        # Fix cancer type capitalization
                        if cancer_type.lower() == 'other':
                            cancer_type = 'Other'
                        if cancer_type_detailed.lower() == 'other':
                            cancer_type_detailed = 'Other'

                        # Create a properly formatted line with empty values for missing columns
                        # Based on the header, we need these columns:
                        # SAMPLE_ID, MONTHS_SINCE_SAMPLE_EXTRACTION, SAMPLE_CLASS, CANCER_TYPE,
                        # CANCER_TYPE_DETAILED, MOLECULAR_DIAG_SUBGROUP, PATIENT_ID, SOMATIC_MUTATION_LOAD, TUMOR_PERCENTAGE
                        new_line = f"{sample_id}\t\t{cancer_type}\t{cancer_type}\t{cancer_type_detailed}\t\t{patient_id}\t\t\n"
                        outfile.write(new_line)
                        print(f"  Fixed formatting for sample: {sample_id}")
                    else:
                        print(f"  WARNING: Unexpected line format: {line.strip()}")


def fix_case_lists(case_lists_dir, clinical_samples):
    """Fix case list files"""
    print("\nFixing case lists...")

    # Fix cases_sequenced.txt
    seq_file = os.path.join(case_lists_dir, 'cases_sequenced.txt')
    if os.path.exists(seq_file):
        # Backup
        backup_file = seq_file + '.backup'
        os.rename(seq_file, backup_file)

        # Read the metadata
        metadata = []
        with open(backup_file, 'r') as f:
            for line in f:
                if not line.startswith('case_list_ids:'):
                    metadata.append(line)

        # Rewrite with correct sample list
        with open(seq_file, 'w') as f:
            for line in metadata:
                f.write(line)
            f.write(f"case_list_ids: {'\t'.join(sorted(clinical_samples))}\n")

        print(f"  Fixed {seq_file} with {len(clinical_samples)} samples")

    # Fix cases_all.txt if it exists
    all_file = os.path.join(case_lists_dir, 'cases_all.txt')
    if os.path.exists(all_file):
        # Backup
        backup_file = all_file + '.backup'
        os.rename(all_file, backup_file)

        # Read the metadata
        metadata = []
        with open(backup_file, 'r') as f:
            for line in f:
                if not line.startswith('case_list_ids:'):
                    metadata.append(line)

        # Rewrite with correct sample list
        with open(all_file, 'w') as f:
            for line in metadata:
                f.write(line)
            f.write(f"case_list_ids: {'\t'.join(sorted(clinical_samples))}\n")

        print(f"  Fixed {all_file} with {len(clinical_samples)} samples")


def update_cancer_type_colors(cancer_type_file):
    """Update cancer type file with proper colors"""
    print("\nUpdating cancer type colors...")

    color_mapping = {
        'all': 'lightblue',
        'aml': 'orange',
        'dsrct': 'mediumpurple',
        'epn': 'steelblue',
        'ews': 'purple',
        'hgg': 'darkblue',
        'hl': 'lightgreen',
        'lgg': 'skyblue',
        'mb': 'darkgreen',
        'mixed': 'gray',
        'nbl': 'red',
        'nhl': 'green',
        'osteo': 'brown',
        'other': 'darkgray',
        'rhabdoid': 'darkred',
        'sts': 'salmon',
        'wt': 'darkorange'
    }

    # Backup and rewrite
    backup_file = cancer_type_file + '.backup'
    os.rename(cancer_type_file, backup_file)

    with open(backup_file, 'r') as infile:
        with open(cancer_type_file, 'w') as outfile:
            for line in infile:
                parts = line.strip().split('\t')
                if len(parts) >= 4:
                    type_id = parts[0]
                    if type_id in color_mapping:
                        parts[2] = color_mapping[type_id]
                    outfile.write('\t'.join(parts) + '\n')

    print("  Updated cancer type colors")


def main():
    if len(sys.argv) < 2:
        print("Usage: python fix_zero_itcc2.py <study_directory> [--filter-maf]")
        print("Example: python fix_zero_itcc2.py /mnt/cbioportal_data/studies/ZERO-ITCC2")
        print("         python fix_zero_itcc2.py /mnt/cbioportal_data/studies/ZERO-ITCC2 --filter-maf")
        sys.exit(1)

    study_dir = sys.argv[1]
    filter_maf = '--filter-maf' in sys.argv

    # File paths
    clinical_sample_file = os.path.join(study_dir, 'data_clinical_sample.txt')
    clinical_patient_file = os.path.join(study_dir, 'data_clinical_patient.txt')
    maf_file = os.path.join(study_dir, 'data_mutation.maf')
    seg_file = os.path.join(study_dir, 'data_seg.seg')
    case_lists_dir = os.path.join(study_dir, 'case_lists')
    cancer_type_file = os.path.join(study_dir, 'cancer_type.txt')

    print(f"Fixing study directory: {study_dir}")
    if filter_maf:
        print("Will filter MAF file to keep only protein-coding variants")
    print("-" * 50)

    # Get all clinical samples
    clinical_samples = get_samples_from_clinical(clinical_sample_file)
    print(f"Found {len(clinical_samples)} samples in clinical file")

    # Fix clinical file formatting first
    fix_clinical_files(clinical_sample_file, clinical_patient_file)

    # Re-read clinical samples after fixing
    clinical_samples = get_samples_from_clinical(clinical_sample_file)

    # Fix MAF file
    if os.path.exists(maf_file):
        unfixable_maf = fix_maf_sample_ids(maf_file, clinical_samples, filter_maf)

    # Fix SEG file
    if os.path.exists(seg_file):
        unfixable_seg = fix_seg_sample_ids(seg_file, clinical_samples)

    # Fix case lists
    fix_case_lists(case_lists_dir, clinical_samples)

    # Update cancer type colors
    if os.path.exists(cancer_type_file):
        update_cancer_type_colors(cancer_type_file)

    print("\n" + "-" * 50)
    print("Done! Original files backed up with .backup extension")
    print("\nNext steps:")
    print("1. Re-run the validation script")
    print("2. Try importing again")


if __name__ == "__main__":
    main()
, parts[0]):
# Patient ID is in wrong column, move it
patient_id = parts[0]
# Create properly formatted line with patient ID in column 5
# AGE, SEX, OS_MONTHS, OS_STATUS, PATIENT_ID
if len(parts) >= 4:
    new_line = f"{parts[1]}\t{parts[2]}\t{parts[3]}\t{parts[4] if len(parts) > 4 else ''}\t{patient_id}\n"
else:
    new_line = f"\t\t\t\t{patient_id}\n"
outfile.write(new_line)
else:
outfile.write(line)

headers = []
data_lines = []
for line in lines:
    if
line.startswith('#') or line.startswith('SAMPLE_ID'):
headers.append(line)
else:
data_lines.append(line)

# Find expected column count from header
expected_cols = 0
for h in headers:
    if
h.startswith('SAMPLE_ID'): \
    expected_cols = len(h.strip().split('\t'))
break

print(f"  Expected {expected_cols} columns in sample file")

# Check for any malformed lines
malformed = []
for i, line in enumerate(data_lines):
    parts = line.strip().split('\t')
    if len(parts) < expected_cols:
        malformed.append(i)

if malformed:
    print(f"  WARNING: Found {len(malformed)} malformed lines in clinical sample file")
    print(f"  These will need to be fixed or removed")
else:
    print(f"  Clinical sample file appears properly formatted with {len(data_lines)} samples")


def fix_case_lists(case_lists_dir, clinical_samples):
    """Fix case list files"""
    print("\nFixing case lists...")

    # Fix cases_sequenced.txt
    seq_file = os.path.join(case_lists_dir, 'cases_sequenced.txt')
    if os.path.exists(seq_file):
        # Backup
        backup_file = seq_file + '.backup'
        os.rename(seq_file, backup_file)

        # Read the metadata
        metadata = []
        with open(backup_file, 'r') as f:
            for line in f:
                if not line.startswith('case_list_ids:'):
                    metadata.append(line)

        # Rewrite with correct sample list
        with open(seq_file, 'w') as f:
            for line in metadata:
                f.write(line)
            f.write(f"case_list_ids: {'\t'.join(sorted(clinical_samples))}\n")

        print(f"  Fixed {seq_file} with {len(clinical_samples)} samples")

    # Fix cases_all.txt if it exists
    all_file = os.path.join(case_lists_dir, 'cases_all.txt')
    if os.path.exists(all_file):
        # Backup
        backup_file = all_file + '.backup'
        os.rename(all_file, backup_file)

        # Read the metadata
        metadata = []
        with open(backup_file, 'r') as f:
            for line in f:
                if not line.startswith('case_list_ids:'):
                    metadata.append(line)

        # Rewrite with correct sample list
        with open(all_file, 'w') as f:
            for line in metadata:
                f.write(line)
            f.write(f"case_list_ids: {'\t'.join(sorted(clinical_samples))}\n")

        print(f"  Fixed {all_file} with {len(clinical_samples)} samples")


def update_cancer_type_colors(cancer_type_file):
    """Update cancer type file with proper colors"""
    print("\nUpdating cancer type colors...")

    color_mapping = {
        'all': 'lightblue',
        'aml': 'orange',
        'dsrct': 'mediumpurple',
        'epn': 'steelblue',
        'ews': 'purple',
        'hgg': 'darkblue',
        'hl': 'lightgreen',
        'lgg': 'skyblue',
        'mb': 'darkgreen',
        'mixed': 'gray',
        'nbl': 'red',
        'nhl': 'green',
        'osteo': 'brown',
        'other': 'darkgray',
        'rhabdoid': 'darkred',
        'sts': 'salmon',
        'wt': 'darkorange'
    }

    # Backup and rewrite
    backup_file = cancer_type_file + '.backup'
    os.rename(cancer_type_file, backup_file)

    with open(backup_file, 'r') as infile:
        with open(cancer_type_file, 'w') as outfile:
            for line in infile:
                parts = line.strip().split('\t')
                if len(parts) >= 4:
                    type_id = parts[0]
                    if type_id in color_mapping:
                        parts[2] = color_mapping[type_id]
                    outfile.write('\t'.join(parts) + '\n')

    print("  Updated cancer type colors")


def add_missing_samples_to_clinical(sample_file, patient_file, missing_samples):
    """Add missing samples to clinical files"""
    if not missing_samples:
        return

    print(f"\nAdding {len(missing_samples)} missing samples to clinical files...")

    # Get the header structure from sample file
    with open(sample_file, 'r') as f:
        for line in f:
            if line.startswith('SAMPLE_ID'):
                header_cols = line.strip().split('\t')
                break

    # Add to sample file
    with open(sample_file, 'a') as f:
        for sample_id in sorted(missing_samples):
            # Infer patient ID
            patient_id = sample_id.rsplit('_', 1)[0] if '_' in sample_id else sample_id

            # Create entry based on header structure
            # SAMPLE_ID, MONTHS_SINCE_SAMPLE_EXTRACTION, SAMPLE_CLASS, CANCER_TYPE,
            # CANCER_TYPE_DETAILED, MOLECULAR_DIAG_SUBGROUP, PATIENT_ID, SOMATIC_MUTATION_LOAD, TUMOR_PERCENTAGE
            f.write(f"{sample_id}\t\tOther\tOther\tOther\t\t{patient_id}\t\t\n")

    # Get existing patients
    existing_patients = set()
    with open(patient_file, 'r') as f:
        for line in f:
            if not line.startswith('#') and not line.startswith('AGE'):
                parts = line.strip().split('\t')
                if len(parts) >= 5:
                    existing_patients.add(parts[4])  # PATIENT_ID is 5th column

    # Add missing patients
    new_patients = set()
    for sample_id in missing_samples:
        patient_id = sample_id.rsplit('_', 1)[0] if '_' in sample_id else sample_id
        if patient_id not in existing_patients:
            new_patients.add(patient_id)

    if new_patients:
        with open(patient_file, 'a') as f:
            for patient_id in sorted(new_patients):
                f.write(f"\t\t\t\t{patient_id}\n")
        print(f"  Added {len(new_patients)} new patients")


def main():
    if len(sys.argv) < 2:
        print("Usage: python fix_zero_itcc2.py <study_directory> [--filter-maf]")
        print("Example: python fix_zero_itcc2.py /mnt/cbioportal_data/studies/ZERO-ITCC2")
        print("         python fix_zero_itcc2.py /mnt/cbioportal_data/studies/ZERO-ITCC2 --filter-maf")
        sys.exit(1)

    study_dir = sys.argv[1]
    filter_maf = '--filter-maf' in sys.argv

    # File paths
    clinical_sample_file = os.path.join(study_dir, 'data_clinical_sample.txt')
    clinical_patient_file = os.path.join(study_dir, 'data_clinical_patient.txt')
    maf_file = os.path.join(study_dir, 'data_mutation.maf')
    seg_file = os.path.join(study_dir, 'data_seg.seg')
    case_lists_dir = os.path.join(study_dir, 'case_lists')
    cancer_type_file = os.path.join(study_dir, 'cancer_type.txt')

    print(f"Fixing study directory: {study_dir}")
    if filter_maf:
        print("Will filter MAF file to keep only protein-coding variants")
    print("-" * 50)

    # Get all clinical samples
    clinical_samples = get_samples_from_clinical(clinical_sample_file)
    print(f"Found {len(clinical_samples)} samples in clinical file")

    # Check clinical file formatting
    fix_clinical_files(clinical_sample_file, clinical_patient_file)

    # Fix MAF file
    unfixable_maf = set()
    if os.path.exists(maf_file):
        unfixable_maf = fix_maf_sample_ids(maf_file, clinical_samples, filter_maf)

    # Fix SEG file
    unfixable_seg = set()
    if os.path.exists(seg_file):
        unfixable_seg = fix_seg_sample_ids(seg_file, clinical_samples)

    # Combine all unfixable samples
    all_missing = unfixable_maf | unfixable_seg

    if all_missing:
        print(f"\nFound {len(all_missing)} samples in genomic files that are not in clinical files")
        response = input("Add these missing samples to clinical files? (y/n): ")
        if response.lower() == 'y':
            add_missing_samples_to_clinical(clinical_sample_file, clinical_patient_file, all_missing)
            # Re-read clinical samples after adding
            clinical_samples = get_samples_from_clinical(clinical_sample_file)

    # Fix case lists with updated sample list
    fix_case_lists(case_lists_dir, clinical_samples)


def print_final_summary(study_dir):
    """Print summary of the final data"""
    print("\n" + "=" * 50)
    print("FINAL DATA SUMMARY:")

    # Count samples in clinical file
    clinical_sample_file = os.path.join(study_dir, 'data_clinical_sample.txt')
    clinical_samples = get_samples_from_clinical(clinical_sample_file)
    print(f"  Total clinical samples: {len(clinical_samples)}")

    # Count patients
    clinical_patient_file = os.path.join(study_dir, 'data_clinical_patient.txt')
    patients = set()
    with open(clinical_patient_file, 'r') as f:
        for line in f:
            if not line.startswith('#') and not line.startswith('AGE'):
                parts = line.strip().split('\t')
                if len(parts) >= 5:
                    patients.add(parts[4])
    print(f"  Total patients: {len(patients)}")

    # Count samples with MAF data
    maf_file = os.path.join(study_dir, 'data_mutation.maf')
    maf_samples = set()
    if os.path.exists(maf_file):
        with open(maf_file, 'r') as f:
            for line in f:
                if line.startswith('Hugo_Symbol'):
                    parts = line.strip().split('\t')
                    try:
                        tumor_sample_col = parts.index('Tumor_Sample_Barcode')
                        break
                    except ValueError:
                        tumor_sample_col = -1
            if tumor_sample_col >= 0:
                for line in f:
                    if not line.startswith('#'):
                        parts = line.strip().split('\t')
                        if len(parts) > tumor_sample_col:
                            maf_samples.add(parts[tumor_sample_col])
    print(f"  Samples with MAF data: {len(maf_samples)}")

    # Count samples with SEG data
    seg_file = os.path.join(study_dir, 'data_seg.seg')
    seg_samples = set()
    if os.path.exists(seg_file):
        with open(seg_file, 'r') as f:
            next(f)  # Skip header
            for line in f:
                parts = line.strip().split('\t')
                if parts:
                    seg_samples.add(parts[0])
    print(f"  Samples with SEG data: {len(seg_samples)}")

    # Check for samples without genomic data
    samples_without_genomic = clinical_samples - (maf_samples | seg_samples)
    if samples_without_genomic:
        print(f"  WARNING: {len(samples_without_genomic)} samples have no genomic data")

    print("=" * 50)


def main():
    if len(sys.argv) < 2:
        print("Usage: python fix_zero_itcc2.py <study_directory> [--filter-maf]")
        print("Example: python fix_zero_itcc2.py /mnt/cbioportal_data/studies/ZERO-ITCC2")
        print("         python fix_zero_itcc2.py /mnt/cbioportal_data/studies/ZERO-ITCC2 --filter-maf")
        sys.exit(1)

    study_dir = sys.argv[1]
    filter_maf = '--filter-maf' in sys.argv

    # File paths
    clinical_sample_file = os.path.join(study_dir, 'data_clinical_sample.txt')
    clinical_patient_file = os.path.join(study_dir, 'data_clinical_patient.txt')
    maf_file = os.path.join(study_dir, 'data_mutation.maf')
    seg_file = os.path.join(study_dir, 'data_seg.seg')
    case_lists_dir = os.path.join(study_dir, 'case_lists')
    cancer_type_file = os.path.join(study_dir, 'cancer_type.txt')

    print(f"Fixing study directory: {study_dir}")
    if filter_maf:
        print("Will filter MAF file to keep only protein-coding variants")
    print("-" * 50)

    # Get all clinical samples
    clinical_samples = get_samples_from_clinical(clinical_sample_file)
    print(f"Found {len(clinical_samples)} samples in clinical file")

    # Check clinical file formatting
    fix_clinical_files(clinical_sample_file, clinical_patient_file)

    # Fix MAF file
    unfixable_maf = set()
    if os.path.exists(maf_file):
        unfixable_maf = fix_maf_sample_ids(maf_file, clinical_samples, filter_maf)

    # Fix SEG file
    unfixable_seg = set()
    if os.path.exists(seg_file):
        unfixable_seg = fix_seg_sample_ids(seg_file, clinical_samples)

    # Combine all unfixable samples
    all_missing = unfixable_maf | unfixable_seg

    if all_missing:
        print(f"\nFound {len(all_missing)} samples in genomic files that are not in clinical files")
        response = input("Add these missing samples to clinical files? (y/n): ")
        if response.lower() == 'y':
            add_missing_samples_to_clinical(clinical_sample_file, clinical_patient_file, all_missing)
            # Re-read clinical samples after adding
            clinical_samples = get_samples_from_clinical(clinical_sample_file)

    # Fix case lists with updated sample list
    fix_case_lists(case_lists_dir, clinical_samples)

    # Update cancer type colors
    if os.path.exists(cancer_type_file):
        update_cancer_type_colors(cancer_type_file)

    # Print final summary
    print_final_summary(study_dir)

    print("\nDone! Original files backed up with .backup extension")
    print("\nNext steps:")
    print("1. Re-run the validation script")
    print("2. Try importing again")


if __name__ == "__main__":
    main()
, sample_id):
if sample_id.startswith('PP') and len(sample_id) >= 12:
    test_id = 'P' + sample_id[2:]
if test_id in clinical_samples:
    fixed_id = test_id
fixed_samples[sample_id] = fixed_id
elif not sample_id.startswith('P'):
test_id = 'P' + sample_id
if test_id in clinical_samples:
    fixed_id = test_id
fixed_samples[sample_id] = fixed_id

if fixed_id not in clinical_samples and sample_id not in clinical_samples:
    unfixable_samples.add(sample_id)

# Update the line
if fixed_id != sample_id:
    parts[0] = fixed_id
line = '\t'.join(parts) + '\n'

outfile.write(line)

print(f"  Total SEG lines processed: {total_lines}")
print(f"  Skipped {skipped_lines} lines with invalid values")
if fixed_samples:
    print(f"  Fixed {len(fixed_samples)} sample ID typos")

return unfixable_samples


def fix_clinical_files(sample_file, patient_file):
    """Fix formatting issues in clinical files"""
    print("\nFixing clinical files formatting...")

    # First, read the properly formatted entries to understand the structure
    proper_entries = []
    with open(sample_file, 'r') as f:
        for line in f:
            if not line.startswith('#') and not line.startswith('SAMPLE_ID'):
                parts = line.strip().split('\t')
                if len(parts) >= 8:  # Properly formatted entries have many columns
                    proper_entries.append(line)

    if not proper_entries:
        print("  ERROR: No properly formatted entries found to use as template")
        return

    # Get column count from a proper entry
    expected_cols = len(proper_entries[0].split('\t'))
    print(f"  Expected {expected_cols} columns in sample file")

    # Create backup and rewrite file
    backup_file = sample_file + '.backup2'
    os.rename(sample_file, backup_file)

    with open(backup_file, 'r') as infile:
        with open(sample_file, 'w') as outfile:
            # Copy headers
            for line in infile:
                if line.startswith('#') or line.startswith('SAMPLE_ID'):
                    outfile.write(line)
                else:
                    parts = line.strip().split('\t')
                    if len(parts) >= expected_cols:
                        # Properly formatted line
                        outfile.write(line)
                    elif len(parts) == 4:
                        # This looks like an improperly added line (patient_id, sample_id, cancer_type, cancer_type_detailed)
                        # Need to expand it to full format
                        patient_id = parts[0]
                        sample_id = parts[1]
                        cancer_type = parts[2]
                        cancer_type_detailed = parts[3]

                        # Fix cancer type capitalization
                        if cancer_type.lower() == 'other':
                            cancer_type = 'Other'
                        if cancer_type_detailed.lower() == 'other':
                            cancer_type_detailed = 'Other'

                        # Create a properly formatted line with empty values for missing columns
                        # Based on the header, we need these columns:
                        # SAMPLE_ID, MONTHS_SINCE_SAMPLE_EXTRACTION, SAMPLE_CLASS, CANCER_TYPE,
                        # CANCER_TYPE_DETAILED, MOLECULAR_DIAG_SUBGROUP, PATIENT_ID, SOMATIC_MUTATION_LOAD, TUMOR_PERCENTAGE
                        new_line = f"{sample_id}\t\t{cancer_type}\t{cancer_type}\t{cancer_type_detailed}\t\t{patient_id}\t\t\n"
                        outfile.write(new_line)
                        print(f"  Fixed formatting for sample: {sample_id}")
                    else:
                        print(f"  WARNING: Unexpected line format: {line.strip()}")


def fix_case_lists(case_lists_dir, clinical_samples):
    """Fix case list files"""
    print("\nFixing case lists...")

    # Fix cases_sequenced.txt
    seq_file = os.path.join(case_lists_dir, 'cases_sequenced.txt')
    if os.path.exists(seq_file):
        # Backup
        backup_file = seq_file + '.backup'
        os.rename(seq_file, backup_file)

        # Read the metadata
        metadata = []
        with open(backup_file, 'r') as f:
            for line in f:
                if not line.startswith('case_list_ids:'):
                    metadata.append(line)

        # Rewrite with correct sample list
        with open(seq_file, 'w') as f:
            for line in metadata:
                f.write(line)
            f.write(f"case_list_ids: {'\t'.join(sorted(clinical_samples))}\n")

        print(f"  Fixed {seq_file} with {len(clinical_samples)} samples")

    # Fix cases_all.txt if it exists
    all_file = os.path.join(case_lists_dir, 'cases_all.txt')
    if os.path.exists(all_file):
        # Backup
        backup_file = all_file + '.backup'
        os.rename(all_file, backup_file)

        # Read the metadata
        metadata = []
        with open(backup_file, 'r') as f:
            for line in f:
                if not line.startswith('case_list_ids:'):
                    metadata.append(line)

        # Rewrite with correct sample list
        with open(all_file, 'w') as f:
            for line in metadata:
                f.write(line)
            f.write(f"case_list_ids: {'\t'.join(sorted(clinical_samples))}\n")

        print(f"  Fixed {all_file} with {len(clinical_samples)} samples")


def update_cancer_type_colors(cancer_type_file):
    """Update cancer type file with proper colors"""
    print("\nUpdating cancer type colors...")

    color_mapping = {
        'all': 'lightblue',
        'aml': 'orange',
        'dsrct': 'mediumpurple',
        'epn': 'steelblue',
        'ews': 'purple',
        'hgg': 'darkblue',
        'hl': 'lightgreen',
        'lgg': 'skyblue',
        'mb': 'darkgreen',
        'mixed': 'gray',
        'nbl': 'red',
        'nhl': 'green',
        'osteo': 'brown',
        'other': 'darkgray',
        'rhabdoid': 'darkred',
        'sts': 'salmon',
        'wt': 'darkorange'
    }

    # Backup and rewrite
    backup_file = cancer_type_file + '.backup'
    os.rename(cancer_type_file, backup_file)

    with open(backup_file, 'r') as infile:
        with open(cancer_type_file, 'w') as outfile:
            for line in infile:
                parts = line.strip().split('\t')
                if len(parts) >= 4:
                    type_id = parts[0]
                    if type_id in color_mapping:
                        parts[2] = color_mapping[type_id]
                    outfile.write('\t'.join(parts) + '\n')

    print("  Updated cancer type colors")


def main():
    if len(sys.argv) < 2:
        print("Usage: python fix_zero_itcc2.py <study_directory> [--filter-maf]")
        print("Example: python fix_zero_itcc2.py /mnt/cbioportal_data/studies/ZERO-ITCC2")
        print("         python fix_zero_itcc2.py /mnt/cbioportal_data/studies/ZERO-ITCC2 --filter-maf")
        sys.exit(1)

    study_dir = sys.argv[1]
    filter_maf = '--filter-maf' in sys.argv

    # File paths
    clinical_sample_file = os.path.join(study_dir, 'data_clinical_sample.txt')
    clinical_patient_file = os.path.join(study_dir, 'data_clinical_patient.txt')
    maf_file = os.path.join(study_dir, 'data_mutation.maf')
    seg_file = os.path.join(study_dir, 'data_seg.seg')
    case_lists_dir = os.path.join(study_dir, 'case_lists')
    cancer_type_file = os.path.join(study_dir, 'cancer_type.txt')

    print(f"Fixing study directory: {study_dir}")
    if filter_maf:
        print("Will filter MAF file to keep only protein-coding variants")
    print("-" * 50)

    # Get all clinical samples
    clinical_samples = get_samples_from_clinical(clinical_sample_file)
    print(f"Found {len(clinical_samples)} samples in clinical file")

    # Fix clinical file formatting first
    fix_clinical_files(clinical_sample_file, clinical_patient_file)

    # Re-read clinical samples after fixing
    clinical_samples = get_samples_from_clinical(clinical_sample_file)

    # Fix MAF file
    if os.path.exists(maf_file):
        unfixable_maf = fix_maf_sample_ids(maf_file, clinical_samples, filter_maf)

    # Fix SEG file
    if os.path.exists(seg_file):
        unfixable_seg = fix_seg_sample_ids(seg_file, clinical_samples)

    # Fix case lists
    fix_case_lists(case_lists_dir, clinical_samples)

    # Update cancer type colors
    if os.path.exists(cancer_type_file):
        update_cancer_type_colors(cancer_type_file)

    print("\n" + "-" * 50)
    print("Done! Original files backed up with .backup extension")
    print("\nNext steps:")
    print("1. Re-run the validation script")
    print("2. Try importing again")


if __name__ == "__main__":
    main()