#!/usr/bin/env python3
"""
MAMS Test Coverage Report Generator

This script runs tests for all services and generates a consolidated coverage report.
It helps track progress toward the 90% coverage goal for Milestone 2.8.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import xml.etree.ElementTree as ET
from datetime import datetime
import argparse

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def get_service_directories() -> List[Path]:
    """Get all service directories that contain tests."""
    services_dir = Path(__file__).parent.parent / "services"
    service_dirs = []
    
    for service_path in services_dir.iterdir():
        if service_path.is_dir() and (service_path / "tests").exists():
            service_dirs.append(service_path)
    
    return sorted(service_dirs)

def run_service_tests(service_path: Path, generate_html: bool = False) -> Tuple[bool, float, str]:
    """
    Run tests for a single service and return coverage percentage.
    
    Returns:
        Tuple of (success, coverage_percentage, error_message)
    """
    service_name = service_path.name
    coverage_xml = service_path / "coverage.xml"
    coverage_html = service_path / "htmlcov"
    
    # Build pytest command
    cmd = [
        "python3", "-m", "pytest",
        "tests/",
        "--cov=src",
        "--cov-report=xml",
        "--cov-report=term",
        "-v"
    ]
    
    if generate_html:
        cmd.append("--cov-report=html")
    
    try:
        # Run tests
        result = subprocess.run(
            cmd,
            cwd=service_path,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            return False, 0.0, result.stderr
        
        # Parse coverage XML
        if coverage_xml.exists():
            tree = ET.parse(coverage_xml)
            root = tree.getroot()
            coverage_percent = float(root.attrib.get('line-rate', '0')) * 100
            return True, coverage_percent, ""
        else:
            # Try to extract from terminal output
            for line in result.stdout.split('\n'):
                if 'TOTAL' in line and '%' in line:
                    parts = line.split()
                    for part in parts:
                        if part.endswith('%'):
                            coverage_percent = float(part.rstrip('%'))
                            return True, coverage_percent, ""
            
            return True, 0.0, "Could not parse coverage"
            
    except Exception as e:
        return False, 0.0, str(e)

def generate_summary_report(results: Dict[str, Dict]) -> str:
    """Generate a summary report of all test coverage."""
    report = []
    
    # Header
    report.append(f"{Colors.HEADER}{'='*80}{Colors.ENDC}")
    report.append(f"{Colors.HEADER}MAMS Test Coverage Report{Colors.ENDC}")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")
    
    # Calculate totals
    total_services = len(results)
    passing_services = sum(1 for r in results.values() if r['success'])
    total_coverage = sum(r['coverage'] for r in results.values() if r['success'])
    avg_coverage = total_coverage / passing_services if passing_services > 0 else 0
    
    # Summary
    report.append(f"{Colors.BOLD}Summary:{Colors.ENDC}")
    report.append(f"  Total Services: {total_services}")
    report.append(f"  Passing Services: {passing_services}")
    report.append(f"  Failed Services: {total_services - passing_services}")
    report.append(f"  Average Coverage: {avg_coverage:.1f}%")
    report.append(f"  Target Coverage: 90%")
    
    if avg_coverage >= 90:
        report.append(f"  Status: {Colors.OKGREEN}✓ TARGET MET{Colors.ENDC}")
    else:
        report.append(f"  Status: {Colors.WARNING}⚠ {90 - avg_coverage:.1f}% below target{Colors.ENDC}")
    
    report.append(f"\n{Colors.BOLD}Service Details:{Colors.ENDC}")
    report.append(f"{'Service':<30} {'Status':<10} {'Coverage':<10} {'Notes':<30}")
    report.append("-" * 80)
    
    # Sort services by coverage
    sorted_results = sorted(results.items(), key=lambda x: x[1]['coverage'], reverse=True)
    
    for service_name, result in sorted_results:
        status = f"{Colors.OKGREEN}PASS{Colors.ENDC}" if result['success'] else f"{Colors.FAIL}FAIL{Colors.ENDC}"
        
        coverage = result['coverage']
        if coverage >= 90:
            coverage_str = f"{Colors.OKGREEN}{coverage:>6.1f}%{Colors.ENDC}"
        elif coverage >= 80:
            coverage_str = f"{Colors.WARNING}{coverage:>6.1f}%{Colors.ENDC}"
        else:
            coverage_str = f"{Colors.FAIL}{coverage:>6.1f}%{Colors.ENDC}"
        
        notes = result.get('error', '')[:30]
        report.append(f"{service_name:<30} {status:<10} {coverage_str:<10} {notes:<30}")
    
    # Services needing attention
    report.append(f"\n{Colors.BOLD}Services Below 90% Coverage:{Colors.ENDC}")
    below_target = [(name, r) for name, r in sorted_results if r['success'] and r['coverage'] < 90]
    
    if below_target:
        for service_name, result in below_target:
            gap = 90 - result['coverage']
            report.append(f"  • {service_name}: {result['coverage']:.1f}% (needs +{gap:.1f}%)")
    else:
        report.append(f"  {Colors.OKGREEN}All services meet target!{Colors.ENDC}")
    
    # Failed services
    failed = [(name, r) for name, r in results.items() if not r['success']]
    if failed:
        report.append(f"\n{Colors.BOLD}Failed Services:{Colors.ENDC}")
        for service_name, result in failed:
            report.append(f"  • {service_name}: {result.get('error', 'Unknown error')}")
    
    report.append(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
    
    return '\n'.join(report)

def save_json_report(results: Dict[str, Dict], output_path: Path):
    """Save results as JSON for CI/CD integration."""
    report_data = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total_services': len(results),
            'passing_services': sum(1 for r in results.values() if r['success']),
            'average_coverage': sum(r['coverage'] for r in results.values() if r['success']) / max(1, sum(1 for r in results.values() if r['success'])),
            'target_coverage': 90,
            'target_met': sum(r['coverage'] for r in results.values() if r['success']) / max(1, sum(1 for r in results.values() if r['success'])) >= 90
        },
        'services': results
    }
    
    with open(output_path, 'w') as f:
        json.dump(report_data, f, indent=2)

def main():
    parser = argparse.ArgumentParser(description='Generate test coverage report for all MAMS services')
    parser.add_argument('--html', action='store_true', help='Generate HTML coverage reports')
    parser.add_argument('--json', type=str, help='Save JSON report to specified file')
    parser.add_argument('--service', type=str, help='Run tests for specific service only')
    parser.add_argument('--parallel', action='store_true', help='Run service tests in parallel')
    args = parser.parse_args()
    
    print(f"{Colors.HEADER}Starting MAMS Test Coverage Analysis...{Colors.ENDC}\n")
    
    # Get services to test
    if args.service:
        service_path = Path(__file__).parent.parent / "services" / args.service
        if not service_path.exists():
            print(f"{Colors.FAIL}Service '{args.service}' not found!{Colors.ENDC}")
            sys.exit(1)
        service_dirs = [service_path]
    else:
        service_dirs = get_service_directories()
    
    results = {}
    
    # Run tests for each service
    for i, service_path in enumerate(service_dirs, 1):
        service_name = service_path.name
        print(f"{Colors.OKCYAN}[{i}/{len(service_dirs)}] Testing {service_name}...{Colors.ENDC}")
        
        success, coverage, error = run_service_tests(service_path, args.html)
        
        results[service_name] = {
            'success': success,
            'coverage': coverage,
            'error': error
        }
        
        if success:
            if coverage >= 90:
                print(f"  {Colors.OKGREEN}✓ {coverage:.1f}% coverage{Colors.ENDC}")
            else:
                print(f"  {Colors.WARNING}⚠ {coverage:.1f}% coverage{Colors.ENDC}")
        else:
            print(f"  {Colors.FAIL}✗ Test failed{Colors.ENDC}")
    
    # Generate and display summary
    print("\n" + generate_summary_report(results))
    
    # Save JSON report if requested
    if args.json:
        json_path = Path(args.json)
        save_json_report(results, json_path)
        print(f"\nJSON report saved to: {json_path}")
    
    # Exit with appropriate code
    all_passing = all(r['success'] and r['coverage'] >= 90 for r in results.values())
    sys.exit(0 if all_passing else 1)

if __name__ == "__main__":
    main()