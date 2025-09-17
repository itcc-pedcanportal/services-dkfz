#!/usr/bin/env python3
"""
Transform ZERO-ITCC study data into cBioPortal-compatible format
"""

import os
import sys
import glob
from typing import List, Set, Tuple, Optional

def read_file_skip_comments(filepath: str) -> List[str]:
    """Read file and return lines that don't start with #"""
    lines = []
    with open(filepath, 'r') as f:
        for line in f:
            if not line.startswith('#'):
                lines.append(line.rstrip('\n'))  # Only remove newline, not tabs
    return lines


def get_header_from_comments(filepath: str) -> Optional[str]:
    """Extract the actual header from comment lines"""
    with open(filepath, 'r') as f:
        lines = f.readlines()
        # Look for the last comment line before data starts
        for i, line in enumerate(lines):
            if not line.startswith('#') and i > 0:
                # The previous line should be the header
                return lines[i - 1].strip('#').strip()
    return None


def collect_all_sample_ids(input_dir: str) -> Set[str]:
    """Collect all unique sample IDs from MAF and SEG files"""
    sample_ids = set()

    # Collect from MAF files
    maf_files = glob.glob(os.path.join(input_dir, 'maf/*.maf'))
    for maf_file in maf_files:
        with open(maf_file, 'r') as f:
            header_found = False
            tumor_sample_col = -1
            for line in f:
                if line.startswith('#'):
                    continue
                if line.startswith('Hugo_Symbol'):
                    # Header line
                    parts = line.strip().split('\t')
                    try:
                        tumor_sample_col = parts.index('Tumor_Sample_Barcode')
                        header_found = True
                    except ValueError:
                        print(f"Warning: Could not find Tumor_Sample_Barcode column in {maf_file}")
                    continue
                if header_found and tumor_sample_col >= 0:
                    parts = line.strip().split('\t')
                    if len(parts) > tumor_sample_col:
                        sample_ids.add(parts[tumor_sample_col])

    # Collect from SEG files
    seg_files = glob.glob(os.path.join(input_dir, 'seg/*.seg'))
    for seg_file in seg_files:
        with open(seg_file, 'r') as f:
            # Skip header
            next(f)
            for line in f:
                parts = line.strip().split('\t')
                if parts:
                    sample_ids.add(parts[0])

    return sample_ids


def transform_clinical_data(input_dir: str, output_dir: str) -> Tuple[int, int]:
    """Transform clinical data files"""
    print("Transforming clinical data...")

    # Keep track of seen patients to avoid duplicates
    seen_patients = set()
    patient_data = {}

    # Process patient data
    patient_file = os.path.join(input_dir, 'zero_cbioportal_patient.txt')
    if os.path.exists(patient_file):
        with open(patient_file, 'r') as f:
            all_lines = f.readlines()

        # Find the header line (AGE, SEX, OS_MONTHS, OS_STATUS, PATIENT_ID)
        header_idx = -1
        for i, line in enumerate(all_lines):
            if 'AGE\tSEX\tOS_MONTHS\tOS_STATUS\tPATIENT_ID' in line:
                header_idx = i
                break

        if header_idx < 0:
            print("  ERROR: Could not find header line in patient file!")
            return 0, 0

        # Write patient clinical data
        with open(os.path.join(output_dir, 'data_clinical_patient.txt'), 'w') as f:
            # Write the required headers
            f.write("#Patient Identifier\tAge at Diagnosis\tSex\tOverall Survival Status\tOverall Survival (Months)\n")
            f.write("#Patient Identifier\tAge at Diagnosis\tSex\tOverall Survival Status\tOverall Survival (Months)\n")
            f.write("#STRING\tNUMBER\tSTRING\tSTRING\tNUMBER\n")
            f.write("#1\t1\t1\t1\t1\n")
            f.write("PATIENT_ID\tAGE\tSEX\tOS_STATUS\tOS_MONTHS\n")

            # Process data lines after header
            for line in all_lines[header_idx + 1:]:
                line = line.rstrip('\n')
                if line:
                    parts = line.split('\t')
                    # Original format: AGE, SEX, OS_MONTHS, OS_STATUS, PATIENT_ID
                    if len(parts) >= 5:
                        age = parts[0]
                        sex = parts[1]
                        os_months = parts[2]
                        os_status = parts[3]
                        patient_id = parts[4]

                        # Skip duplicate patients
                        if patient_id in seen_patients:
                            continue
                        seen_patients.add(patient_id)

                        # Store patient data for later verification
                        patient_data[patient_id] = {
                            'age': age,
                            'sex': sex,
                            'os_status': os_status,
                            'os_months': os_months
                        }

                        # Fix OS_STATUS format (remove space after colon)
                        os_status = os_status.replace(": ", ":")
                        f.write(f"{patient_id}\t{age}\t{sex}\t{os_status}\t{os_months}\n")

        print(f"  Successfully parsed {len(seen_patients)} unique patients")

    # Process sample data
    sample_file = os.path.join(input_dir, 'zero_cbioportal_sample.txt')

    # First collect all sample IDs from all sources
    print(f"  Collecting sample IDs from genomic data files...")
    all_sample_ids = collect_all_sample_ids(input_dir)
    print(f"  Found {len(all_sample_ids)} unique sample IDs in genomic files")

    # Read existing sample data
    sample_data = {}
    if os.path.exists(sample_file):
        with open(sample_file, 'r') as f:
            # Read all lines
            all_lines = f.readlines()

        # Find the header line (should be the last line starting with TUMOR_TYPE_ID)
        header_idx = -1
        for i, line in enumerate(all_lines):
            if line.startswith('TUMOR_TYPE_ID'):
                header_idx = i
                break

        if header_idx >= 0:
            # Parse data lines after header
            for line in all_lines[header_idx + 1:]:
                if line.strip():
                    parts = line.rstrip('\n').split('\t')
                    if len(parts) >= 9:
                        sample_id = parts[1].strip()
                        patient_id = parts[4].strip()
                        cancer_type = parts[5].strip() if len(parts) > 5 and parts[5].strip() else "Other"
                        cancer_type_detailed = parts[8].strip() if len(parts) > 8 and parts[8].strip() else cancer_type

                        if sample_id:  # Only add if sample_id is not empty
                            # Validate cancer type - cannot be empty
                            if not cancer_type or cancer_type == "Other":
                                print(
                                    f"    WARNING: Sample {sample_id} has invalid cancer type: '{parts[5] if len(parts) > 5 else 'MISSING'}'")

                            sample_data[sample_id] = {
                                'patient_id': patient_id,
                                'cancer_type': cancer_type,
                                'cancer_type_detailed': cancer_type_detailed
                            }

        print(f"  Successfully parsed {len(sample_data)} samples from clinical file")

    # Check which genomic samples have clinical data
    matched_samples = 0
    missing_clinical = []
    for sample_id in all_sample_ids:
        if sample_id in sample_data:
            matched_samples += 1
        else:
            missing_clinical.append(sample_id)

    if missing_clinical:
        print(f"  ERROR: {len(missing_clinical)} samples from genomic files have no clinical data!")
        print(f"    This is not allowed. All samples must have clinical data.")
        print(f"    Missing samples: {missing_clinical[:10]}...")
        sys.exit(1)

    # Check which clinical samples have genomic data
    clinical_only = []
    for sample_id in sample_data:
        if sample_id not in all_sample_ids:
            clinical_only.append(sample_id)

    if clinical_only:
        print(f"  WARNING: {len(clinical_only)} samples from clinical file have no genomic data!")
        print(f"    Examples: {clinical_only[:5]}")

    # Only write samples that have both clinical and genomic data
    final_samples = {}
    for sample_id in sample_data:
        if sample_id in all_sample_ids:
            final_samples[sample_id] = sample_data[sample_id]

    # Write sample clinical data
    with open(os.path.join(output_dir, 'data_clinical_sample.txt'), 'w') as f:
        # Write the required headers
        f.write("#Patient Identifier\tSample Identifier\tCancer Type\tCancer Type Detailed\n")
        f.write("#Patient Identifier\tSample Identifier\tCancer Type\tCancer Type Detailed\n")
        f.write("#STRING\tSTRING\tSTRING\tSTRING\n")
        f.write("#1\t1\t1\t1\n")
        f.write("PATIENT_ID\tSAMPLE_ID\tCANCER_TYPE\tCANCER_TYPE_DETAILED\n")

        # Write data
        for sample_id, data in sorted(final_samples.items()):
            f.write(f"{data['patient_id']}\t{sample_id}\t{data['cancer_type']}\t{data['cancer_type_detailed']}\n")

    # Make sure we have patient entries for all patients with samples
    patients_with_samples = set(data['patient_id'] for data in final_samples.values())
    missing_patients = patients_with_samples - seen_patients

    if missing_patients:
        print(f"  Adding {len(missing_patients)} patients who have samples but no patient data")
        with open(os.path.join(output_dir, 'data_clinical_patient.txt'), 'a') as f:
            for patient_id in sorted(missing_patients):
                # Add minimal patient data
                f.write(f"{patient_id}\t\t\t\t\n")

    return len(final_samples), len(seen_patients) + len(missing_patients)


def combine_maf_files(input_dir: str, output_dir: str) -> int:
    """Combine all MAF files into one"""
    print("Combining MAF files...")

    maf_files = glob.glob(os.path.join(input_dir, 'maf/*.maf'))

    if not maf_files:
        print("Warning: No MAF files found")
        return 0

    # Variant classifications to filter out
    filtered_classifications = {'Silent', 'Intron', '3\'UTR', '3\'Flank', '5\'UTR', '5\'Flank', 'IGR', 'RNA'}

    total_lines = 0
    filtered_lines = 0
    samples_with_maf = set()

    with open(os.path.join(output_dir, 'data_mutation.maf'), 'w') as outfile:
        # Write header from first file
        first_file = True
        variant_class_col = -1
        tumor_sample_col = -1

        for maf_file in sorted(maf_files):
            with open(maf_file, 'r') as infile:
                for line in infile:
                    if line.startswith('#'):
                        # Write comments only from first file
                        if first_file:
                            outfile.write(line)
                    elif line.startswith('Hugo_Symbol'):
                        # Header line
                        if first_file:
                            outfile.write(line)
                            # Find columns
                            parts = line.strip().split('\t')
                            try:
                                variant_class_col = parts.index('Variant_Classification')
                            except ValueError:
                                print(f"Warning: Could not find Variant_Classification column")
                            try:
                                tumor_sample_col = parts.index('Tumor_Sample_Barcode')
                            except ValueError:
                                print(f"Warning: Could not find Tumor_Sample_Barcode column")
                    else:
                        # Data line - check variant classification
                        if variant_class_col >= 0 and tumor_sample_col >= 0:
                            parts = line.strip().split('\t')
                            if len(parts) > max(variant_class_col, tumor_sample_col):
                                total_lines += 1
                                samples_with_maf.add(parts[tumor_sample_col])
                                if parts[variant_class_col] not in filtered_classifications:
                                    outfile.write(line)
                                else:
                                    filtered_lines += 1
                        else:
                            # If we couldn't find the column, write all lines
                            outfile.write(line)
                            total_lines += 1
                first_file = False

    print(f"  Total MAF files: {len(maf_files)}")
    print(f"  Total mutation lines processed: {total_lines}")
    print(f"  Filtered out {filtered_lines} lines with non-coding variant classifications")
    print(f"  Kept {total_lines - filtered_lines} lines")
    print(f"  Samples with MAF data: {len(samples_with_maf)}")

    return len(samples_with_maf)


def combine_seg_files(input_dir: str, output_dir: str) -> int:
    """Combine all SEG files into one"""
    print("Combining SEG files...")

    seg_files = glob.glob(os.path.join(input_dir, 'seg/*.seg'))

    if not seg_files:
        print("Warning: No SEG files found")
        return 0

    skipped_lines = 0
    total_lines = 0
    samples_with_seg = set()

    # Valid chromosome values
    valid_chromosomes = set([str(i) for i in range(1, 23)] + ['X', 'Y', 'M', 'MT'])

    with open(os.path.join(output_dir, 'data_seg.seg'), 'w') as outfile:
        # Write header with cBioPortal-expected column names
        outfile.write("ID\tchrom\tloc.start\tloc.end\tnum.mark\tseg.mean\n")

        # Process each file
        for seg_file in sorted(seg_files):
            with open(seg_file, 'r') as infile:
                # Skip header line
                next(infile)
                # Write data lines
                for line in infile:
                    total_lines += 1
                    parts = line.strip().split('\t')
                    if len(parts) >= 6:
                        # Validate all required fields
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

                        # Check if segment mean is valid
                        if seg_mean.lower() in ['-nan', 'nan', '-inf', 'inf', 'na', 'null']:
                            skipped_lines += 1
                            continue
                        try:
                            # Verify it's a valid float
                            float(seg_mean)
                            samples_with_seg.add(sample_id)
                            outfile.write(line)
                        except ValueError:
                            skipped_lines += 1
                            continue

    print(f"  Total SEG files: {len(seg_files)}")
    print(f"  Total SEG lines processed: {total_lines}")
    print(f"  Skipped {skipped_lines} lines with invalid values (chromosome or segment mean)")
    print(f"  Samples with SEG data: {len(samples_with_seg)}")

    return len(samples_with_seg)


def create_meta_files(output_dir: str, study_id: str = "ZERO_ITCC") -> None:
    """Create all required meta files"""
    print("Creating meta files...")

    # meta_study.txt
    with open(os.path.join(output_dir, 'meta_study.txt'), 'w') as f:
        f.write(f"type_of_cancer: mixed\n")
        f.write(f"cancer_study_identifier: {study_id}\n")
        f.write(f"name: ZERO ITCC Study\n")
        f.write(f"description: ZERO ITCC genomic data\n")
        f.write(f"reference_genome: hg38\n")

    # meta_clinical_patient.txt
    with open(os.path.join(output_dir, 'meta_clinical_patient.txt'), 'w') as f:
        f.write("cancer_study_identifier: {}\n".format(study_id))
        f.write("genetic_alteration_type: CLINICAL\n")
        f.write("datatype: PATIENT_ATTRIBUTES\n")
        f.write("data_filename: data_clinical_patient.txt\n")

    # meta_clinical_sample.txt
    with open(os.path.join(output_dir, 'meta_clinical_sample.txt'), 'w') as f:
        f.write("cancer_study_identifier: {}\n".format(study_id))
        f.write("genetic_alteration_type: CLINICAL\n")
        f.write("datatype: SAMPLE_ATTRIBUTES\n")
        f.write("data_filename: data_clinical_sample.txt\n")

    # meta_mutation.txt
    if os.path.exists(os.path.join(output_dir, 'data_mutation.maf')):
        with open(os.path.join(output_dir, 'meta_mutation.txt'), 'w') as f:
            f.write("cancer_study_identifier: {}\n".format(study_id))
            f.write("genetic_alteration_type: MUTATION_EXTENDED\n")
            f.write("datatype: MAF\n")
            f.write("stable_id: mutations\n")
            f.write("show_profile_in_analysis_tab: true\n")
            f.write("profile_name: Mutations\n")
            f.write("profile_description: Mutation data\n")
            f.write("data_filename: data_mutation.maf\n")
            f.write("swissprot_identifier: name\n")

    # meta_seg.txt
    if os.path.exists(os.path.join(output_dir, 'data_seg.seg')):
        with open(os.path.join(output_dir, 'meta_seg.txt'), 'w') as f:
            f.write("cancer_study_identifier: {}\n".format(study_id))
            f.write("genetic_alteration_type: COPY_NUMBER_ALTERATION\n")
            f.write("datatype: SEG\n")
            f.write("reference_genome_id: hg38\n")
            f.write("description: Segmented copy number data\n")
            f.write("data_filename: data_seg.seg\n")

    # meta_cancer_type.txt
    with open(os.path.join(output_dir, 'meta_cancer_type.txt'), 'w') as f:
        f.write("genetic_alteration_type: CANCER_TYPE\n")
        f.write("datatype: CANCER_TYPE\n")
        f.write("data_filename: cancer_type.txt\n")


def create_cancer_type_file(output_dir: str, clinical_sample_file: Optional[str] = None) -> None:
    """Create cancer_type.txt file with all cancer types found in the data"""
    print("Creating cancer type file...")

    # Include base types
    cancer_types = set()
    cancer_types.add(('mixed', 'Mixed Cancer Types', 'gray', 'tissue'))

    # Collect all unique cancer types from clinical sample file
    if clinical_sample_file and os.path.exists(clinical_sample_file):
        with open(clinical_sample_file, 'r') as f:
            for line in f:
                if not line.startswith('#') and not line.startswith('PATIENT_ID'):
                    parts = line.strip().split('\t')
                    if len(parts) >= 3:
                        cancer_type = parts[2].strip()
                        if cancer_type:
                            # Use the cancer type as-is (no mapping)
                            cancer_types.add((cancer_type.lower(), cancer_type, 'gray', 'tissue'))

    with open(os.path.join(output_dir, 'cancer_type.txt'), 'w') as f:
        for type_id, name, color, parent in sorted(cancer_types):
            f.write(f"{type_id}\t{name}\t{color}\t{parent}\n")

    print(f"  Created cancer type file with {len(cancer_types)} cancer types")


def create_case_lists(input_dir: str, output_dir: str, study_id: str = "ZERO_ITCC") -> None:
    """Create case lists directory and files"""
    print("Creating case lists...")

    case_lists_dir = os.path.join(output_dir, 'case_lists')
    os.makedirs(case_lists_dir, exist_ok=True)

    # Get all samples from the generated clinical sample file
    sample_file = os.path.join(output_dir, 'data_clinical_sample.txt')
    samples = []

    if os.path.exists(sample_file):
        with open(sample_file, 'r') as f:
            for line in f:
                if not line.startswith('#') and not line.startswith('PATIENT_ID'):
                    parts = line.strip().split('\t')
                    if len(parts) >= 2:
                        samples.append(parts[1])  # SAMPLE_ID is second column

    # Create cases_sequenced.txt
    with open(os.path.join(case_lists_dir, 'cases_sequenced.txt'), 'w') as f:
        f.write("cancer_study_identifier: {}\n".format(study_id))
        f.write("stable_id: {}_sequenced\n".format(study_id))
        f.write("case_list_name: Sequenced Tumors\n")
        f.write("case_list_description: All sequenced samples\n")
        f.write("case_list_ids: {}\n".format('\t'.join(samples)))

    # Create cases_all.txt
    with open(os.path.join(case_lists_dir, 'cases_all.txt'), 'w') as f:
        f.write("cancer_study_identifier: {}\n".format(study_id))
        f.write("stable_id: {}_all\n".format(study_id))
        f.write("case_list_name: All Tumors\n")
        f.write("case_list_description: All samples\n")
        f.write("case_list_ids: {}\n".format('\t'.join(samples)))


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python transform_cbioportal.py <input_directory> [output_directory]")
        print("Example: python transform_cbioportal.py /mnt/cbioportal_data/studies/ZERO-ITCC ./output")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "."

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    print(f"Input directory: {input_dir}")
    print(f"Output directory: {output_dir}")
    print("-" * 50)

    # Transform clinical data (this must be done first to collect all samples)
    num_samples, num_patients = transform_clinical_data(input_dir, output_dir)

    # Combine MAF files
    samples_with_maf = combine_maf_files(input_dir, output_dir)

    # Combine SEG files
    samples_with_seg = combine_seg_files(input_dir, output_dir)

    # Create cancer type file (pass the generated clinical sample file)
    create_cancer_type_file(output_dir, os.path.join(output_dir, 'data_clinical_sample.txt'))

    # Create meta files (after data files are created)
    create_meta_files(output_dir)

    # Create case lists (must be done after clinical data is created)
    create_case_lists(input_dir, output_dir)

    print("-" * 50)
    print("Transformation complete!")
    print("\nSummary:")
    print(f"  Total patients: {num_patients}")
    print(f"  Total samples: {num_samples}")
    print(f"  Samples with MAF data: {samples_with_maf}")
    print(f"  Samples with SEG data: {samples_with_seg}")

    print("\nGenerated files:")
    for file in sorted(os.listdir(output_dir)):
        if os.path.isfile(os.path.join(output_dir, file)):
            print(f"  - {file}")

    case_lists_dir = os.path.join(output_dir, 'case_lists')
    if os.path.exists(case_lists_dir):
        print("\n  case_lists/")
        for file in sorted(os.listdir(case_lists_dir)):
            print(f"    - {file}")


if __name__ == "__main__":
    main()