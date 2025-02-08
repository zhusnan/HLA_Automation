import os
import subprocess
from pathlib import Path
import tempfile
import re
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime
import gzip
import shutil

# Enhanced logging configuration
log_filename = f"hla_verifier_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class HLAVerifier:
    def __init__(self):
        self.hla_sites = ['A', 'B', 'C', 'DRB1', 'DQB1', 'DPB1', 'DPA1', 'DQA1', 'DRB3', 'DRB4', 'DRB5']
        self.verification_sites = ['A', 'B', 'C', 'DRB1', 'DQB1', 'DPB1']
        self.ref_path = "/home/huben/bowtie2_test/HLA_seq"
        self.single_allele_ref_path = "/home/huben/bowtie2_test/Single_allele_ref"
        os.makedirs(self.single_allele_ref_path, exist_ok=True)
        logger.info(f"Initialized HLAVerifier with reference path: {self.ref_path}")
        logger.debug(f"HLA sites: {self.hla_sites}")
        logger.debug(f"Verification sites: {self.verification_sites}")

    def get_input_folders(self) -> Tuple[str, str]:
        fastq_folder = input("Enter the path to folder A (fastq files): ").strip()
        result_folder = input("Enter the path to folder B (HLA-HD results): ").strip()
        logger.info(f"Input folders - FASTQ: {fastq_folder}, Results: {result_folder}")

        if not os.path.exists(fastq_folder):
            logger.error(f"FASTQ folder does not exist: {fastq_folder}")
            raise FileNotFoundError(f"FASTQ folder not found: {fastq_folder}")
        if not os.path.exists(result_folder):
            logger.error(f"Result folder does not exist: {result_folder}")
            raise FileNotFoundError(f"Result folder not found: {result_folder}")

        return fastq_folder, result_folder

    def parse_hla_result(self, result_file: str) -> Dict[str, List[str]]:
        logger.info(f"Parsing HLA result file: {result_file}")
        hla_results = {}
        try:
            with open(result_file, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if parts[0] in self.hla_sites:
                        alleles = [allele for allele in parts[1:] if allele != '-' and 'Not typed' not in allele]
                        hla_results[parts[0]] = alleles
                        logger.debug(f"Parsed {parts[0]}: {alleles}")

            logger.info(f"Successfully parsed {len(hla_results)} HLA sites")
            return hla_results
        except Exception as e:
            logger.error(f"Error parsing HLA result file: {e}")
            raise

    def try_search_patterns(self, hla_type: str, site: str, line: str) -> Optional[Tuple[str, str]]:
        """
        Try to match HLA type against a reference line using simplified pattern matching.

        Args:
            hla_type: The HLA type to search for (e.g., "02:09")
            site: The HLA site (e.g., "A")
            line: A single line from the reference file

        Returns:
            Tuple of (allele_name, sequence) if found, None otherwise
        """
        if not isinstance(hla_type, str) or not isinstance(site, str) or not isinstance(line, str):
            logger.error(f"Invalid input types: hla_type={type(hla_type)}, site={type(site)}, line={type(line)}")
            return None

        if not line.strip():
            return None

        fields = line.strip().split()
        if len(fields) < 4:  # Need at least HLA:ID, allele, length, and sequence
            return None

        ref_allele = fields[1]  # The allele from reference (e.g., "A*02:09:01:01")
        sequence = fields[3]  # The DNA sequence

        # Clean up the input HLA type
        cleaned_hla_type = str(hla_type)
        if cleaned_hla_type.startswith('HLA-'):
            cleaned_hla_type = cleaned_hla_type[4:]
        if cleaned_hla_type.startswith(f'{site}*'):
            cleaned_hla_type = cleaned_hla_type[len(site) + 1:]

        # Clean up reference allele
        if not ref_allele.startswith(f"{site}*"):
            return None
        cleaned_ref_allele = ref_allele[len(site) + 1:]

        # Get the base parts for pattern matching
        base_parts = cleaned_hla_type.split(':')

        if len(base_parts) >= 2:
            # Match just the first two fields against the start of the reference
            base_pattern = f"^{':'.join(base_parts[:2])}"

            try:
                if re.search(base_pattern, cleaned_ref_allele):
                    logger.info(f"Found match for {hla_type}: {ref_allele}")
                    return (ref_allele, sequence)
            except Exception as e:
                logger.error(f"Error in pattern matching: {e}")
                return None

        return None

    def get_reference_sequence(self, hla_type: str, site: str) -> str:
        """
        Get the reference sequence for a given HLA type.

        Args:
            hla_type: The HLA type (e.g., "HLA-A*02:09:01")
            site: The HLA site (e.g., "A")

        Returns:
            FASTA format string with the reference sequence, or empty string if not found
        """
        logger.debug(f"Getting reference sequence for {site} {hla_type}")
        ref_file = os.path.join(self.ref_path, f"{site}_DNA_3560.txt")

        if not os.path.exists(ref_file):
            logger.error(f"Reference file not found: {ref_file}")
            return ""

        try:
            with open(ref_file, 'r') as f:
                for line in f:
                    try:
                        result = self.try_search_patterns(hla_type, site, line)
                        if result:
                            allele_name, sequence = result
                            logger.debug(f"Reference sequence found for {hla_type}: {allele_name}")
                            return f">{allele_name}\n{sequence}"
                    except Exception as e:
                        logger.error(f"Error processing line for {hla_type}: {e}")
                        continue

                logger.warning(f"No reference sequence found for {site} {hla_type}")
                return ""

        except Exception as e:
            logger.error(f"Error reading reference file {ref_file}: {e}")
            return ""

    def get_cached_reference_path(self, allele_name: str) -> Optional[str]:
        """Check if a reference file exists in the cache."""
        cached_path = os.path.join(self.single_allele_ref_path, f"{allele_name}.fa")
        return cached_path if os.path.exists(cached_path) else None

    def cache_reference(self, sequence: str, allele_name: str) -> str:
        """Save reference sequence to cache and return the path."""
        cached_path = os.path.join(self.single_allele_ref_path, f"{allele_name}.fa")
        with open(cached_path, 'w') as f:
            f.write(sequence)
        return cached_path

    def create_temp_reference(self, sequence: str, allele_name: str) -> str:
        """Create or retrieve reference file, checking cache first."""
        cached_path = self.get_cached_reference_path(allele_name)
        if cached_path:
            logger.debug(f"Using cached reference for {allele_name}")
            return cached_path

        logger.debug(f"Creating new reference file for {allele_name}")
        return self.cache_reference(sequence, allele_name)

    def find_fastq_files(self, sample_dir: str) -> Tuple[Optional[str], Optional[str]]:
        """Find the best matching pair of FASTQ files."""

        def find_pairs(pattern: str) -> List[Tuple[str, str]]:
            r1_files = list(Path(sample_dir).glob(pattern.format('1')))
            r2_files = list(Path(sample_dir).glob(pattern.format('2')))
            return [(str(r1), str(r2)) for r1 in r1_files
                    for r2 in r2_files if r1.stem[:-2] == r2.stem[:-2]]

        # Search priorities
        pairs = []
        # 1. Look for combined uncompressed files first
        pairs.extend(find_pairs("*combined_R{}.fastq"))
        # 2. Look for combined compressed files
        pairs.extend(find_pairs("*combined_R{}.fastq.gz"))
        # 3. Look for subset files last
        pairs.extend(find_pairs("*subset_R{}.fastq"))

        if not pairs:
            logger.warning(f"No FASTQ pairs found in {sample_dir}")
            return None, None

        r1_file, r2_file = pairs[0]  # Take the first pair based on priority
        logger.info(f"Selected FASTQ pair: {r1_file}, {r2_file}")
        return r1_file, r2_file

    def align_and_count(self, r1_file: str, r2_file: str, ref_file: str) -> int:
        logger.info(f"Starting alignment with files - R1: {r1_file}, R2: {r2_file}, Ref: {ref_file}")

        # Create bowtie2 index if not exists
        index_base = ref_file.rsplit('.', 1)[0]

        try:
            if not all(os.path.exists(f"{index_base}.{ext}")
                       for ext in ['1.bt2', '2.bt2', '3.bt2', '4.bt2', 'rev.1.bt2', 'rev.2.bt2']):
                logger.debug("Building bowtie2 index")
                build_result = subprocess.run(
                    ['bowtie2-build', '--quiet', ref_file, index_base],
                    capture_output=True,
                    text=True
                )
                if build_result.returncode != 0:
                    logger.error(f"Bowtie2-build failed: {build_result.stderr}")
                    raise subprocess.CalledProcessError(build_result.returncode, 'bowtie2-build')
        except Exception as e:
            logger.error(f"Error building bowtie2 index: {e}")
            raise

        # Align with strict parameters
        align_cmd = [
            'bowtie2',
            '--end-to-end',  # Force end-to-end alignment
            '--very-sensitive',  # Increase sensitivity
            '--no-mixed',  # No unpaired alignments
            '--no-discordant',  # No discordant alignments
            '--no-unal',  # Suppress unaligned reads
            '--score-min', 'L,0,0',  # Require perfect matches
            '-p', '32',  # Use 8 threads
            '-x', index_base,
            '-1', r1_file,
            '-2', r2_file,
            '--reorder'  # Output in same order as input
        ]

        logger.debug(f"Running alignment command: {' '.join(align_cmd)}")

        try:
            result = subprocess.run(
                align_cmd,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                logger.error(f"Bowtie2 alignment failed: {result.stderr}")
                raise subprocess.CalledProcessError(result.returncode, 'bowtie2')

            # Count perfect matches
            perfect_match_count = sum(1 for line in result.stdout.split('\n')
                                      if line and not line.startswith('@')
                                      and 'NM:i:0' in line)

            logger.info(f"Found {perfect_match_count} perfect matches")
            return perfect_match_count

        except Exception as e:
            logger.error(f"Error during alignment: {e}")
            raise

    def format_verification_results(self, results: List[str]) -> List[str]:
        """Format verification results into a readable summary."""
        formatted_results = []
        for result in results:
            parts = result.split()
            if len(parts) == 6:  # site allele1 allele2 count1 count2 result
                formatted_line = f"{parts[0]}: {parts[1]} {parts[2]} - Matches: {parts[3]}/{parts[4]} - {parts[5]}"
                formatted_results.append(formatted_line)
        return formatted_results

    def verify_sample(self, sample_dir: str, result_dir: str) -> List[str]:
        logger.info(f"Starting verification for sample directory: {sample_dir}")

        try:
            # Find result file
            result_files = list(Path(result_dir).glob("*_final.result.txt"))
            if not result_files:
                logger.error(f"No result file found in {result_dir}")
                raise FileNotFoundError(f"No result file found in {result_dir}")

            result_file = result_files[0]
            logger.info(f"Found result file: {result_file}")

            hla_results = self.parse_hla_result(str(result_file))

            # Find fastq files
            r1_file, r2_file = self.find_fastq_files(sample_dir)
            if not r1_file or not r2_file:
                raise FileNotFoundError("Required FASTQ files not found")

            verification_results = []

            for site in self.hla_sites:
                logger.debug(f"Processing site: {site}")
                if site not in hla_results:
                    logger.warning(f"Site {site} not found in HLA results")
                    verification_results.append(f"{site} Not_typed")
                    continue

                alleles = hla_results[site]
                if len(alleles) == 1:
                    logger.debug(f"Single allele found for {site}: {alleles[0]}")
                    verification_results.append(f"{site} {alleles[0]}")
                    continue

                if site in self.verification_sites and len(alleles) == 2:
                    logger.info(f"Verifying site {site} with alleles: {alleles}")

                    # Get reference sequences
                    ref1 = self.get_reference_sequence(alleles[0], site)
                    ref2 = self.get_reference_sequence(alleles[1], site)

                    if not ref1 or not ref2:
                        logger.warning(f"Reference sequence not found for site {site}")
                        verification_results.append(
                            f"{site} {alleles[0]} {alleles[1]} Reference_not_found Reference_not_found FAIL")
                        continue

                    # Get allele names from the reference sequences
                    allele1_name = ref1.split('\n')[0][1:]  # Remove '>' from FASTA header
                    allele2_name = ref2.split('\n')[0][1:]

                    try:
                        # Create or get cached reference files
                        ref_file1 = self.create_temp_reference(ref1, allele1_name)
                        ref_file2 = self.create_temp_reference(ref2, allele2_name)

                        # Align and count
                        count1 = self.align_and_count(r1_file, r2_file, ref_file1)
                        count2 = self.align_and_count(r1_file, r2_file, ref_file2)

                        # Check ratio
                        if count1 == 0 or count2 == 0:
                            logger.warning(f"Zero count found for site {site}: count1={count1}, count2={count2}")
                            result = "FAIL"
                        else:
                            ratio = count1 / count2
                            result = "PASS" if 0.5 <= ratio <= 2 else "FAIL"
                            logger.info(f"Site {site} - Ratio: {ratio:.2f}, Result: {result}")

                        verification_results.append(f"{site} {alleles[0]} {alleles[1]} {count1} {count2} {result}")

                    except Exception as e:
                        logger.error(f"Error during verification of {site}: {e}")
                        verification_results.append(f"{site} {alleles[0]} {alleles[1]} Error Error FAIL")
                        continue
                else:
                    logger.debug(f"Site {site} not verified: {len(alleles)} alleles found")
                    verification_results.append(f"{site} {' '.join(alleles)}")

            return verification_results

        except Exception as e:
            logger.error(f"Error during sample verification: {e}")
            raise

    def process_all_samples(self, fastq_folder: str, result_folder: str):
        logger.info("Starting processing of all samples")
        logger.info(f"FASTQ folder: {fastq_folder}")
        logger.info(f"Result folder: {result_folder}")

        # Create summary file in the fastq folder
        summary_file = os.path.join(fastq_folder, "verification_summary.txt")
        all_results = []

        try:
            sample_dirs = [d for d in Path(fastq_folder).iterdir() if d.is_dir()]
            logger.info(f"Found {len(sample_dirs)} sample directories")

            for sample_dir in sample_dirs:
                sample_name = sample_dir.name
                result_dir = Path(result_folder) / sample_name / "result"

                if not result_dir.exists():
                    logger.warning(f"No result directory found for sample {sample_name}")
                    continue

                logger.info(f"Processing sample {sample_name}")
                try:
                    results = self.verify_sample(str(sample_dir), str(result_dir))

                    # Format results for summary
                    formatted_results = self.format_verification_results(results)
                    if formatted_results:
                        all_results.append(f"\nSample: {sample_name}")
                        all_results.extend(formatted_results)

                except Exception as e:
                    logger.error(f"Error processing sample {sample_name}: {e}")
                    all_results.append(f"\nSample: {sample_name}")
                    all_results.append(f"Error processing sample: {str(e)}")
                    continue

            # Write collective summary
            logger.info(f"Writing collective summary to {summary_file}")
            with open(summary_file, 'w') as f:
                f.write("HLA Verification Summary\n")
                f.write("=" * 50 + "\n")
                f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 50 + "\n\n")
                for line in all_results:
                    f.write(line + "\n")

        except Exception as e:
            logger.error(f"Error processing samples: {e}")
            raise


def main():
    logger.info("Starting HLA verification process")
    try:
        verifier = HLAVerifier()
        fastq_folder, result_folder = verifier.get_input_folders()
        verifier.process_all_samples(fastq_folder, result_folder)
        logger.info("HLA verification completed successfully")
    except Exception as e:
        logger.error(f"Fatal error in main process: {e}")
        raise


if __name__ == "__main__":
    main()