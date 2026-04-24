#!/usr/bin/env python3
"""
cBioPortal Study Merger Script
Merges multiple cBioPortal studies into a single cohort

Key features:
- Validates patient IDs to be 9 characters starting with 'P'
- Automatically fixes 8-character patient IDs by adding 'P' prefix
- Validates and fixes sample IDs (patient_id + underscore + serial)
- Strict validation: fails on NA values or malformed IDs with detailed error messages
- Handles special INFORM format sample IDs
- Preserves all data columns across studies
"""

import argparse
import os
import sys
import pandas as pd
import re
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
import logging
import warnings

# Suppress pandas warnings for cleaner output
warnings.filterwarnings('ignore', category=pd.errors.PerformanceWarning)

# Configure logging - will be updated in main()
logger = logging.getLogger(__name__)


@dataclass
class StudyConfig:
    """Configuration for a merged study"""
    cancer_study_identifier: str
    type_of_cancer: str
    name: str
    description: str
    groups: str = "PUBLIC"
    reference_genome: str = "hg38"
    add_global_case_list: str = "true"


class PatientSampleValidator:
    """Validates and fixes patient and sample IDs"""

    @staticmethod
    def validate_patient_id(patient_id: str, file_path: str = "", line_num: int = -1, full_line: str = "") -> str:
        """Ensure patient ID is 9 characters starting with P"""
        # Check for empty/NA values
        if pd.isna(patient_id) or patient_id == '' or str(patient_id).strip() == '' or str(patient_id).upper() == 'NA':
            error_msg = f"\nEmpty or NA patient ID found!\n"
            error_msg += f"File: {file_path}\n"
            if line_num >= 0:
                error_msg += f"Line number: {line_num}\n"
            if full_line:
                error_msg += f"Full line: {full_line}\n"
            error_msg += f"Patient ID value: '{patient_id}'"
            raise ValueError(error_msg)

        patient_id = str(patient_id).strip()

        if len(patient_id) == 9 and patient_id.startswith('P'):
            return patient_id
        elif len(patient_id) == 8:
            logger.debug(f"Adding 'P' prefix to 8-char patient ID: {patient_id}")
            return 'P' + patient_id
        else:
            error_msg = f"\nInvalid patient ID!\n"
            error_msg += f"File: {file_path}\n"
            if line_num >= 0:
                error_msg += f"Line number: {line_num}\n"
            if full_line:
                error_msg += f"Full line: {full_line}\n"
            error_msg += f"Patient ID: '{patient_id}' (length: {len(patient_id)})\n"
            error_msg += f"Expected: 9 characters starting with 'P' or 8 characters (will add 'P')"
            raise ValueError(error_msg)

    @staticmethod
    def validate_sample_id(sample_id: str, file_path: str = "", line_num: int = -1, full_line: str = "") -> str:
        """Fix sample ID format"""
        # Check for empty/NA values
        if pd.isna(sample_id) or sample_id == '' or str(sample_id).strip() == '' or str(sample_id).upper() == 'NA':
            error_msg = f"\nEmpty or NA sample ID found!\n"
            error_msg += f"File: {file_path}\n"
            if line_num >= 0:
                error_msg += f"Line number: {line_num}\n"
            if full_line:
                error_msg += f"Full line: {full_line}\n"
            error_msg += f"Sample ID value: '{sample_id}'"
            raise ValueError(error_msg)

        sample_id = str(sample_id).strip()

        # Handle special case IDs that don't follow patient ID format
        # (e.g., I128_094_tumor011-01 from older pipelines)
        if (sample_id.startswith('I') and '_' in sample_id and
                len(sample_id.split('_')[0]) > 1 and sample_id.split('_')[0][1:].isdigit()):
            logger.warning(f"Special format sample ID detected: {sample_id} - keeping as-is")
            return sample_id

        # Handle INFORM format (e.g., PH2KRL2JM_T_1 -> PH2KRL2JM_1)
        if '_T_' in sample_id:
            parts = sample_id.split('_T_')
            if len(parts) == 2:
                logger.debug(f"Fixing INFORM format: {sample_id} -> {parts[0]}_{parts[1]}")
                sample_id = f"{parts[0]}_{parts[1]}"

        # Split by underscore
        parts = sample_id.split('_')

        if len(parts) == 1:
            # No underscore, append _1
            patient_part = PatientSampleValidator.validate_patient_id(
                parts[0], file_path, line_num, full_line
            )
            return f"{patient_part}_1"
        else:
            # Has underscore, validate patient part
            patient_part = PatientSampleValidator.validate_patient_id(
                parts[0], file_path, line_num, full_line
            )
            serial_parts = '_'.join(parts[1:])
            return f"{patient_part}_{serial_parts}"


class DataMerger:
    """Base class for merging different data types"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def merge_files(self, file_paths: List[Path]) -> pd.DataFrame:
        """Merge multiple files with common headers"""
        if not file_paths:
            return pd.DataFrame()

        # Read all files
        dfs = []
        for fp in file_paths:
            if fp.exists():
                df = self._read_file(fp)
                if not df.empty:
                    dfs.append(df)

        if not dfs:
            return pd.DataFrame()

        # Find all unique columns
        all_columns = []
        seen = set()
        for df in dfs:
            for col in df.columns:
                if col not in seen:
                    all_columns.append(col)
                    seen.add(col)

        # Reindex all dataframes to have same columns
        aligned_dfs = []
        for df in dfs:
            aligned_df = df.reindex(columns=all_columns, fill_value='NA')
            aligned_dfs.append(aligned_df)

        # Concatenate
        return pd.concat(aligned_dfs, ignore_index=True)

    def _read_file(self, file_path: Path) -> pd.DataFrame:
        """Read file with proper handling of comments and headers"""
        return pd.read_csv(file_path, sep='\t', comment='#', dtype=str)


class ClinicalDataMerger(DataMerger):
    """Merger for clinical data files"""

    def merge_clinical_files(self, study_dirs: List[Path], filename: str) -> pd.DataFrame:
        """Merge clinical files from multiple studies"""
        file_paths = [d / filename for d in study_dirs]

        # Read files with tracking of source
        dfs_with_source = []
        for fp in file_paths:
            if fp.exists():
                # Count comment lines
                comment_lines = 0
                with open(fp, 'r') as f:
                    for line in f:
                        if line.startswith('#'):
                            comment_lines += 1
                        else:
                            break

                df = self._read_file(fp)
                if not df.empty:
                    # Add source file info
                    df['_source_file'] = str(fp)
                    # Account for comment lines and header
                    df['_line_num'] = range(comment_lines + 2, len(df) + comment_lines + 2)
                    dfs_with_source.append(df)

        if not dfs_with_source:
            return pd.DataFrame()

        # Merge all dataframes
        df = pd.concat(dfs_with_source, ignore_index=True)

        logger.debug(f"Merging {filename} with {len(df)} rows from {len(dfs_with_source)} files")

        # Validate IDs based on file type
        if 'data_clinical_patient' in filename:
            if 'PATIENT_ID' in df.columns:
                logger.debug(f"Validating patient IDs in {filename}")
                for idx, row in df.iterrows():
                    try:
                        df.at[idx, 'PATIENT_ID'] = PatientSampleValidator.validate_patient_id(
                            row['PATIENT_ID'],
                            file_path=row['_source_file'],
                            line_num=row['_line_num'],
                            full_line=row.to_string()
                        )
                    except ValueError as e:
                        raise ValueError(f"Error in clinical patient file:\n{str(e)}")

        elif 'data_clinical_sample' in filename:
            if 'PATIENT_ID' in df.columns:
                logger.debug(f"Validating patient IDs in {filename}")
                for idx, row in df.iterrows():
                    try:
                        df.at[idx, 'PATIENT_ID'] = PatientSampleValidator.validate_patient_id(
                            row['PATIENT_ID'],
                            file_path=row['_source_file'],
                            line_num=row['_line_num'],
                            full_line=row.to_string()
                        )
                    except ValueError as e:
                        raise ValueError(f"Error in clinical sample file:\n{str(e)}")

            if 'SAMPLE_ID' in df.columns:
                logger.debug(f"Validating sample IDs in {filename}")
                for idx, row in df.iterrows():
                    try:
                        df.at[idx, 'SAMPLE_ID'] = PatientSampleValidator.validate_sample_id(
                            row['SAMPLE_ID'],
                            file_path=row['_source_file'],
                            line_num=row['_line_num'],
                            full_line=row.to_string()
                        )
                    except ValueError as e:
                        raise ValueError(f"Error in clinical sample file:\n{str(e)}")

        # Remove tracking columns
        df = df.drop(columns=['_source_file', '_line_num'], errors='ignore')

        # Reindex to ensure all columns are present
        all_columns = []
        seen = set()
        for col in df.columns:
            if col not in seen:
                all_columns.append(col)
                seen.add(col)

        return df

    def write_clinical_file(self, df: pd.DataFrame, filename: str, meta_lines: List[str]):
        """Write clinical file with proper headers"""
        output_path = self.output_dir / filename

        with open(output_path, 'w') as f:
            # Write meta lines
            for line in meta_lines:
                f.write(line)

            # Write data
            df.to_csv(f, sep='\t', index=False, na_rep='NA')


class MAFMerger(DataMerger):
    """Merger for MAF files"""

    def merge_maf_files(self, study_dirs: List[Path]) -> pd.DataFrame:
        """Merge MAF files from multiple studies"""
        file_paths = [d / 'data_mutation.maf' for d in study_dirs]

        # MAF files have special header
        dfs = []
        for fp in file_paths:
            if fp.exists():
                logger.debug(f"Reading MAF file: {fp}")
                # Skip the version line
                df = pd.read_csv(fp, sep='\t', comment='#', skiprows=1, dtype=str, low_memory=False)
                if not df.empty:
                    logger.debug(f"MAF file {fp} has {len(df)} rows")
                    # Add source tracking
                    df['_source_file'] = str(fp)
                    df['_line_num'] = range(3, len(df) + 3)  # Start from line 3 (after version and header)

                    # Validate sample IDs
                    if 'Tumor_Sample_Barcode' in df.columns:
                        for idx, row in df.iterrows():
                            try:
                                df.at[idx, 'Tumor_Sample_Barcode'] = PatientSampleValidator.validate_sample_id(
                                    row['Tumor_Sample_Barcode'],
                                    file_path=str(fp),
                                    line_num=row['_line_num'],
                                    full_line=f"Hugo_Symbol={row.get('Hugo_Symbol', 'NA')}, "
                                              f"Chromosome={row.get('Chromosome', 'NA')}, "
                                              f"Start_Position={row.get('Start_Position', 'NA')}, "
                                              f"Tumor_Sample_Barcode={row['Tumor_Sample_Barcode']}"
                                )
                            except ValueError as e:
                                raise ValueError(f"Error in MAF file:\n{str(e)}")

                    # Remove tracking columns
                    df = df.drop(columns=['_source_file', '_line_num'], errors='ignore')
                    dfs.append(df)

        if not dfs:
            return pd.DataFrame()

        # Merge with all columns
        all_columns = []
        seen = set()
        for df in dfs:
            for col in df.columns:
                if col not in seen:
                    all_columns.append(col)
                    seen.add(col)

        aligned_dfs = []
        for df in dfs:
            aligned_df = df.reindex(columns=all_columns, fill_value='')
            aligned_dfs.append(aligned_df)

        result = pd.concat(aligned_dfs, ignore_index=True)
        logger.debug(f"Merged MAF has {len(result)} total rows")
        return result

    def write_maf_file(self, df: pd.DataFrame):
        """Write MAF file with version header"""
        output_path = self.output_dir / 'data_mutation.maf'

        with open(output_path, 'w') as f:
            f.write('#version 2.4\n')
            df.to_csv(f, sep='\t', index=False, na_rep='')


class SEGMerger(DataMerger):
    """Merger for SEG files"""

    def merge_seg_files(self, study_dirs: List[Path]) -> pd.DataFrame:
        """Merge SEG files from multiple studies"""
        file_paths = [d / 'data_seg.seg' for d in study_dirs]

        logger.debug(f"Merging SEG files from {len(file_paths)} studies")

        # Read files with source tracking
        dfs = []
        for fp in file_paths:
            if fp.exists():
                # Count comment lines
                comment_lines = 0
                with open(fp, 'r') as f:
                    for line in f:
                        if line.startswith('#'):
                            comment_lines += 1
                        else:
                            break

                df = self._read_file(fp)
                if not df.empty:
                    # Add source tracking
                    df['_source_file'] = str(fp)
                    # Account for comment lines and header
                    df['_line_num'] = range(comment_lines + 2, len(df) + comment_lines + 2)
                    dfs.append(df)

        if not dfs:
            return pd.DataFrame()

        # Merge
        df = pd.concat(dfs, ignore_index=True)

        if 'ID' in df.columns:
            logger.debug(f"SEG data has {len(df)} rows")
            logger.debug(f"First few IDs: {df['ID'].head(10).tolist()}")

            # Validate IDs
            for idx, row in df.iterrows():
                try:
                    df.at[idx, 'ID'] = PatientSampleValidator.validate_sample_id(
                        row['ID'],
                        file_path=row['_source_file'],
                        line_num=row['_line_num'],
                        full_line=f"ID={row['ID']}, chrom={row.get('chrom', 'NA')}, "
                                  f"start={row.get('loc.start', 'NA')}, end={row.get('loc.end', 'NA')}"
                    )
                except ValueError as e:
                    raise ValueError(f"Error in SEG file:\n{str(e)}")
        else:
            logger.warning("No 'ID' column found in SEG file")

        # Remove tracking columns
        df = df.drop(columns=['_source_file', '_line_num'], errors='ignore')

        # Ensure all columns are aligned
        all_columns = []
        seen = set()
        for col in df.columns:
            if col not in seen:
                all_columns.append(col)
                seen.add(col)

        return df


class CancerTypeMerger:
    """Merger for cancer types"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def merge_cancer_types(self, study_dirs: List[Path]) -> pd.DataFrame:
        """Merge cancer type definitions"""
        cancer_types = {}

        for study_dir in study_dirs:
            cancer_file = study_dir / 'cancer_type.txt'
            if cancer_file.exists():
                df = pd.read_csv(cancer_file, sep='\t', header=None,
                                 names=['type_id', 'name', 'color', 'parent'])
                for _, row in df.iterrows():
                    cancer_types[row['type_id']] = row.to_dict()

        if not cancer_types:
            return pd.DataFrame()

        # Convert back to dataframe
        df = pd.DataFrame.from_dict(cancer_types, orient='index')
        return df.reset_index(drop=True)


class MetaFileMerger:
    """Handles merging and creation of meta files"""

    def __init__(self, output_dir: Path, study_config: StudyConfig):
        self.output_dir = output_dir
        self.study_config = study_config

    def create_meta_files(self):
        """Create all meta files for the merged study"""
        # meta_study.txt
        self._write_meta_study()

        # meta_cancer_type.txt
        self._write_meta_cancer_type()

        # meta_clinical_patient.txt
        self._write_meta_clinical_patient()

        # meta_clinical_sample.txt
        self._write_meta_clinical_sample()

        # meta_mutation.txt
        self._write_meta_mutation()

        # meta_seg.txt
        self._write_meta_seg()

    def _write_meta_study(self):
        """Write meta_study.txt"""
        content = f"""cancer_study_identifier: {self.study_config.cancer_study_identifier}
type_of_cancer: {self.study_config.type_of_cancer}
name: {self.study_config.name}
description: {self.study_config.description}
groups: {self.study_config.groups}
reference_genome: {self.study_config.reference_genome}
add_global_case_list: {self.study_config.add_global_case_list}
"""
        (self.output_dir / 'meta_study.txt').write_text(content)

    def _write_meta_cancer_type(self):
        """Write meta_cancer_type.txt"""
        content = """genetic_alteration_type: CANCER_TYPE
datatype: CANCER_TYPE
data_filename: cancer_type.txt
"""
        (self.output_dir / 'meta_cancer_type.txt').write_text(content)

    def _write_meta_clinical_patient(self):
        """Write meta_clinical_patient.txt"""
        content = f"""cancer_study_identifier: {self.study_config.cancer_study_identifier}
genetic_alteration_type: CLINICAL
datatype: PATIENT_ATTRIBUTES
data_filename: data_clinical_patient.txt
"""
        (self.output_dir / 'meta_clinical_patient.txt').write_text(content)

    def _write_meta_clinical_sample(self):
        """Write meta_clinical_sample.txt"""
        content = f"""cancer_study_identifier: {self.study_config.cancer_study_identifier}
genetic_alteration_type: CLINICAL
datatype: SAMPLE_ATTRIBUTES
data_filename: data_clinical_sample.txt
"""
        (self.output_dir / 'meta_clinical_sample.txt').write_text(content)

    def _write_meta_mutation(self):
        """Write meta_mutation.txt"""
        content = f"""cancer_study_identifier: {self.study_config.cancer_study_identifier}
genetic_alteration_type: MUTATION_EXTENDED
datatype: MAF
data_filename: data_mutation.maf
stable_id: mutations
profile_name: Mutations
profile_description: WGS mutations
show_profile_in_analysis_tab: true
swissprot_identifier: name
"""
        (self.output_dir / 'meta_mutation.txt').write_text(content)

    def _write_meta_seg(self):
        """Write meta_seg.txt"""
        content = f"""cancer_study_identifier: {self.study_config.cancer_study_identifier}
genetic_alteration_type: COPY_NUMBER_ALTERATION
datatype: SEG
data_filename: data_seg.seg
description: CNA seg
reference_genome_id: hg38
"""
        (self.output_dir / 'meta_seg.txt').write_text(content)


class CaseListMerger:
    """Handles case list creation"""

    def __init__(self, output_dir: Path, study_config: StudyConfig):
        self.output_dir = output_dir
        self.study_config = study_config
        self.case_dir = output_dir / 'case_lists'
        self.case_dir.mkdir(exist_ok=True)

    def create_cases_sequenced(self, sample_ids: List[str]):
        """Create cases_sequenced.txt"""
        if not sample_ids:
            logger.warning("No sample IDs found for case list")
            return

        content = f"""cancer_study_identifier: {self.study_config.cancer_study_identifier}
stable_id: {self.study_config.cancer_study_identifier}_sequenced
case_list_name: All sequenced tumors
case_list_description: All tumors that were sequenced
case_list_ids: {'\t'.join(sorted(set(sample_ids)))}
"""
        (self.case_dir / 'cases_sequenced.txt').write_text(content)


class StudyMerger:
    """Main class to orchestrate the merging process"""

    def __init__(self, input_dirs: List[str], output_dir: str, study_config: StudyConfig):
        self.input_dirs = [Path(d) for d in input_dirs]
        self.output_dir = Path(output_dir)
        self.study_config = study_config

        # Validate input directories
        for d in self.input_dirs:
            if not d.exists():
                raise ValueError(f"Input directory does not exist: {d}")

    def merge(self, append: bool = False):
        """Perform the merge operation"""
        logger.info(f"Merging {len(self.input_dirs)} studies into {self.output_dir}")

        if self.output_dir.exists() and not append:
            raise ValueError(
                f"Output directory already exists: {self.output_dir}. Use append mode to add to existing study.")

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize mergers
        clinical_merger = ClinicalDataMerger(self.output_dir)
        maf_merger = MAFMerger(self.output_dir)
        seg_merger = SEGMerger(self.output_dir)
        cancer_merger = CancerTypeMerger(self.output_dir)
        meta_merger = MetaFileMerger(self.output_dir, self.study_config)
        case_merger = CaseListMerger(self.output_dir, self.study_config)

        # Create meta files
        logger.info("Creating meta files...")
        meta_merger.create_meta_files()

        # Merge cancer types
        logger.info("Merging cancer types...")
        cancer_df = cancer_merger.merge_cancer_types(self.input_dirs)
        if not cancer_df.empty:
            cancer_df.to_csv(self.output_dir / 'cancer_type.txt', sep='\t',
                             index=False, header=False)
        else:
            # Create a default cancer type file if none found
            logger.warning("No cancer type files found, creating default")
            default_cancer = f"{self.study_config.type_of_cancer}\t{self.study_config.type_of_cancer}\tgray\ttissue\n"
            (self.output_dir / 'cancer_type.txt').write_text(default_cancer)

        # Merge clinical data
        logger.info("Merging clinical patient data...")
        patient_df = clinical_merger.merge_clinical_files(self.input_dirs, 'data_clinical_patient.txt')
        if not patient_df.empty:
            # Get header lines from first file
            header_lines = self._get_clinical_header_lines(self.input_dirs[0] / 'data_clinical_patient.txt')
            clinical_merger.write_clinical_file(patient_df, 'data_clinical_patient.txt', header_lines)

        logger.info("Merging clinical sample data...")
        sample_df = clinical_merger.merge_clinical_files(self.input_dirs, 'data_clinical_sample.txt')
        sample_ids = []
        if not sample_df.empty:
            header_lines = self._get_clinical_header_lines(self.input_dirs[0] / 'data_clinical_sample.txt')
            clinical_merger.write_clinical_file(sample_df, 'data_clinical_sample.txt', header_lines)
            if 'SAMPLE_ID' in sample_df.columns:
                # Filter out NA values
                sample_ids = [sid for sid in sample_df['SAMPLE_ID'].tolist() if sid and sid != 'NA']
                logger.info(f"Found {len(sample_ids)} valid sample IDs")

        # Merge MAF files
        logger.info("Merging mutation data...")
        maf_df = maf_merger.merge_maf_files(self.input_dirs)
        if not maf_df.empty:
            maf_merger.write_maf_file(maf_df)

        # Merge SEG files
        logger.info("Merging CNA data...")
        seg_df = seg_merger.merge_seg_files(self.input_dirs)
        if not seg_df.empty:
            seg_df.to_csv(self.output_dir / 'data_seg.seg', sep='\t', index=False)

        # Create case lists
        logger.info("Creating case lists...")
        if sample_ids:
            case_merger.create_cases_sequenced(sample_ids)

        logger.info("Merge completed successfully!")

    def _get_clinical_header_lines(self, file_path: Path) -> List[str]:
        """Extract header comment lines from clinical file"""
        header_lines = []
        if file_path.exists():
            with open(file_path, 'r') as f:
                for line in f:
                    if line.startswith('#'):
                        header_lines.append(line)
                    else:
                        break
        return header_lines


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Merge multiple cBioPortal studies into a single cohort',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('-i', '--input', required=True,
                        help='Comma-separated list of input study directories')
    parser.add_argument('-o', '--output', required=True,
                        help='Output directory for merged study')
    parser.add_argument('--append', action='store_true',
                        help='Append to existing study if output directory exists')
    parser.add_argument('--study-id', default='merged_study',
                        help='Cancer study identifier (default: merged_study)')
    parser.add_argument('--cancer-type', default='mixed',
                        help='Type of cancer (default: mixed)')
    parser.add_argument('--name', default='Merged Study',
                        help='Study name (default: Merged Study)')
    parser.add_argument('--description', default='Merged cBioPortal study',
                        help='Study description')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')

    args = parser.parse_args()

    # Configure logging based on debug flag
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(levelname)s: %(message)s' if not args.debug else '%(levelname)s [%(name)s]: %(message)s'
    )

    # Parse input directories
    input_dirs = [d.strip() for d in args.input.split(',')]

    # Create study configuration
    study_config = StudyConfig(
        cancer_study_identifier=args.study_id,
        type_of_cancer=args.cancer_type,
        name=args.name,
        description=args.description
    )

    # Create merger and run
    try:
        merger = StudyMerger(input_dirs, args.output, study_config)
        merger.merge(append=args.append)
    except Exception as e:
        logger.error(f"Error during merge: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()