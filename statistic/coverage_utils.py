import xml.etree.ElementTree as ET
import os
import sys
import shutil
import subprocess
from typing import Dict, Set, Tuple
from pathlib import Path

def generate_coverage_report(cwd, coverage_file_path, coverage_file_target_path, report_file_path, gradle_task_name, gradle_args: list, jdk_version):
    """
    Generate a JaCoCo coverage report for the given Java project.
    
    Args:
        cwd: Current working directory
        coverage_file_path: Path to the JaCoCo coverage file
        coverage_file_target_path: Path to the target coverage file
        report_file_path: Path to the output coverage report file
        gradle_args: List of arguments to pass to the Gradle task
        jdk_version: Java version to use for coverage analysis
        
    Returns:
        report_file_path: Path to the output coverage report file
    """

    # Initialize original_cwd to avoid unbound variable error
    original_cwd = os.getcwd()
    
    try:
        os.chdir(cwd)
        subprocess.run(['dot_clean', '-m', cwd], check=True)
        subprocess.run(['jenv', 'global', jdk_version], check=True)
        print("--- GRADLE LOGS ---")
        subprocess.run(['./gradlew', 'clean', 'assembleDebug', '--no-daemon'] + gradle_args, check=True, stdout=sys.stdout, stderr=sys.stdout)
        print("--- END GRADLE LOGS ---")
        os.makedirs(Path(coverage_file_target_path).parent.absolute(), exist_ok=True)
        shutil.copy2(coverage_file_path, coverage_file_target_path)
        if os.path.exists(report_file_path):
            os.remove(report_file_path)
        print("--- GRADLE LOGS ---")
        subprocess.run(['./gradlew', gradle_task_name, '--no-daemon'] + gradle_args, check=True, stdout=sys.stdout, stderr=sys.stdout)
        print("--- END GRADLE LOGS ---")
        os.chdir(original_cwd)
        return report_file_path
        
    except Exception as e:
        os.chdir(original_cwd)
        print(f"[ERROR] Failed to generate coverage report: {e}")


def _parse_jacoco_report(xml_file_path: str) -> Tuple[Dict[str, Set[int]], int]:
    """
    Parse a JaCoCo XML report and extract covered lines for each source file.
    
    Args:
        xml_file_path: Path to the JaCoCo XML report file
        
    Returns:
        Tuple of (covered_lines_dict, total_lines)
        - covered_lines_dict: Dictionary mapping source file names to sets of covered line numbers
        - total_lines: Total number of lines in the report
    """
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"[ERROR] Failed to parse XML file {xml_file_path}: {e}")
        raise e
    except FileNotFoundError as e:
        print(f"[ERROR] Failed to parse XML file {xml_file_path}: File not found")
        raise e
    except Exception as e:
        print(f"[ERROR] An error occurred while parsing XML file {xml_file_path}: {e}")
        raise e

    covered_lines = {}
    total_lines = 0
    
    for sourcefile in root.findall('.//sourcefile'):
        filename = sourcefile.get('name')
        if filename:
            covered_lines[filename] = set()            
            for line in sourcefile.findall('line'):
                line_number = line.get('nr')
                covered_instructions = line.get('ci', '0')
                
                # Count all lines
                if line_number:
                    total_lines += 1
                    
                # A line is covered if it has covered instructions (ci > 0)
                if line_number and int(covered_instructions) > 0:
                    covered_lines[filename].add(int(line_number))
    
    return covered_lines, total_lines


def calculate_coverage_ratio(report1_path: str, report2_path: str) -> Tuple[float, float]:
    """
    Calculate coverage ratios between two reports.
    
    Args:
        report1_path: Path to the first JaCoCo report
        report2_path: Path to the second JaCoCo report
        
    Returns:
        Tuple of (common_coverage_ratio, new_coverage_ratio)
        - common_coverage_ratio: ratio of commonly covered lines to lines covered in report2
        - new_coverage_ratio: ratio of newly covered lines in report2 to total lines covered in report2
    """
    try:
        print(f"Parsing first report: {report1_path}")
        coverage1_data, _ = _parse_jacoco_report(report1_path)
        
        print(f"Parsing second report: {report2_path}")
        coverage2_data, _ = _parse_jacoco_report(report2_path)
    except Exception as e:
        print(f"[ERROR] Failed to calculate coverage ratios: {e}")
        return 0.0, 0.0
    
    total_covered_lines_report1 = sum(len(lines) for lines in coverage1_data.values())
    total_covered_lines_report2 = sum(len(lines) for lines in coverage2_data.values())
    
    print(f"Report 1 total covered lines: {total_covered_lines_report1}")
    print(f"Report 2 total covered lines: {total_covered_lines_report2}")
    
    common_covered_lines = 0
    newly_covered_lines = 0
    
    common_files = set(coverage1_data.keys()) & set(coverage2_data.keys())
    
    print(f"Common source files: {sorted(common_files)}")
    
    for filename in common_files:
        lines1 = coverage1_data[filename]
        lines2 = coverage2_data[filename]
        common_lines_in_file = lines1 & lines2
        new_lines_in_file = lines2 - lines1
        
        common_covered_lines += len(common_lines_in_file)
        newly_covered_lines += len(new_lines_in_file)
        
        print(f"  {filename}:")
        print(f"    Report 1 covered lines: {len(lines1)}")
        print(f"    Report 2 covered lines: {len(lines2)}")
        print(f"    Common covered lines: {len(common_lines_in_file)}")
        print(f"    Newly covered lines: {len(new_lines_in_file)}")
    
    report2_only_files = set(coverage2_data.keys()) - set(coverage1_data.keys())
    if report2_only_files:
        print(f"Files only in report 2: {sorted(report2_only_files)}")
        for filename in report2_only_files:
            file_covered_lines = len(coverage2_data[filename])
            newly_covered_lines += file_covered_lines
            print(f"  {filename}: {file_covered_lines} covered lines (all newly covered)")
    
    print(f"\nTotal common covered lines: {common_covered_lines}")
    print(f"Total newly covered lines: {newly_covered_lines}")
    print(f"Total covered lines in report 2: {total_covered_lines_report2}")

    if total_covered_lines_report2 == 0:
        print("Warning: Report 2 has no covered lines!")
        return 0.0, 0.0
    
    common_ratio = common_covered_lines / total_covered_lines_report2
    new_ratio = newly_covered_lines / total_covered_lines_report2
    
    # verification: common + new should equal total
    verification_total = common_covered_lines + newly_covered_lines
    if verification_total != total_covered_lines_report2:
        print(f"Warning: Verification failed. Common + New = {verification_total}, Total = {total_covered_lines_report2}")
    
    return common_ratio, new_ratio

def calculate_coverage_lines(report_path: str) -> Tuple[int, int]:
    """
    Calculate the number of covered and total lines in a JaCoCo report.
    
    Args:
        report_path: Path to the JaCoCo report
        
    Returns:
        Tuple of (covered_lines, total_lines)
    """

    try:
        covered_lines_dict, total_lines = _parse_jacoco_report(report_path)
    except Exception as e:
        print(f"[ERROR] Failed to calculate coverage lines: {e}")
        return 0, 0
    
    covered_lines = sum(len(lines) for lines in covered_lines_dict.values())
    
    return covered_lines, total_lines
