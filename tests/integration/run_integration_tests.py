#!/usr/bin/env python3
"""
Integration Test Runner

Runs all integration tests with proper setup and reporting.
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path
import json
import time


class IntegrationTestRunner:
    """Manages integration test execution."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.compose_file = self.project_root / "docker-compose.yml"
        self.test_dir = Path(__file__).parent
    
    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met."""
        print("Checking prerequisites...")
        
        # Check Docker
        try:
            subprocess.run(["docker", "--version"], check=True, capture_output=True)
            print("✓ Docker is installed")
        except:
            print("✗ Docker is not installed or not in PATH")
            return False
        
        # Check Docker Compose
        try:
            subprocess.run(["docker-compose", "--version"], check=True, capture_output=True)
            print("✓ Docker Compose is installed")
        except:
            print("✗ Docker Compose is not installed or not in PATH")
            return False
        
        # Check if services are defined
        if not self.compose_file.exists():
            print(f"✗ Docker Compose file not found: {self.compose_file}")
            return False
        
        print("✓ All prerequisites met")
        return True
    
    def start_services(self, services: list = None) -> bool:
        """Start required Docker services."""
        print("\nStarting services...")
        
        cmd = ["docker-compose", "-f", str(self.compose_file), "up", "-d"]
        if services:
            cmd.extend(services)
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print("✓ Services started successfully")
            
            # Wait for services to be ready
            print("Waiting for services to be ready...")
            time.sleep(10)  # Basic wait, actual health checks are in conftest.py
            
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to start services: {e.stderr}")
            return False
    
    def stop_services(self) -> None:
        """Stop Docker services."""
        print("\nStopping services...")
        
        try:
            subprocess.run(
                ["docker-compose", "-f", str(self.compose_file), "down"],
                check=True,
                capture_output=True
            )
            print("✓ Services stopped")
        except:
            print("⚠ Failed to stop some services")
    
    def run_tests(self, args: argparse.Namespace) -> int:
        """Run integration tests with pytest."""
        print("\nRunning integration tests...")
        
        pytest_args = [
            "python", "-m", "pytest",
            str(self.test_dir),
            "-v",
            "-m", "integration",
            "--tb=short"
        ]
        
        # Add coverage if requested
        if args.coverage:
            pytest_args.extend([
                "--cov=services",
                "--cov-report=term",
                "--cov-report=html:htmlcov_integration"
            ])
        
        # Add specific test file if provided
        if args.test:
            pytest_args.append(str(self.test_dir / args.test))
        
        # Add markers
        if args.slow:
            pytest_args.extend(["-m", "integration and slow"])
        
        # Add parallel execution
        if args.parallel:
            pytest_args.extend(["-n", str(args.parallel)])
        
        # Add verbose output
        if args.verbose:
            pytest_args.append("-s")
        
        # Add JUnit XML output for CI
        if args.junit:
            pytest_args.extend(["--junit-xml=integration_test_results.xml"])
        
        # Run tests
        try:
            result = subprocess.run(pytest_args, cwd=self.project_root)
            return result.returncode
        except KeyboardInterrupt:
            print("\n⚠ Tests interrupted by user")
            return 1
    
    def generate_report(self) -> None:
        """Generate test report summary."""
        print("\nGenerating test report...")
        
        # Look for JUnit XML results
        junit_file = self.project_root / "integration_test_results.xml"
        if junit_file.exists():
            # Parse and summarize results
            import xml.etree.ElementTree as ET
            tree = ET.parse(junit_file)
            root = tree.getroot()
            
            testsuite = root.find(".//testsuite")
            if testsuite is not None:
                tests = int(testsuite.get("tests", 0))
                failures = int(testsuite.get("failures", 0))
                errors = int(testsuite.get("errors", 0))
                skipped = int(testsuite.get("skipped", 0))
                time_taken = float(testsuite.get("time", 0))
                
                print(f"\nTest Summary:")
                print(f"  Total Tests: {tests}")
                print(f"  Passed: {tests - failures - errors - skipped}")
                print(f"  Failed: {failures}")
                print(f"  Errors: {errors}")
                print(f"  Skipped: {skipped}")
                print(f"  Time: {time_taken:.2f}s")
                
                # Save summary as JSON
                summary = {
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "total_tests": tests,
                    "passed": tests - failures - errors - skipped,
                    "failed": failures,
                    "errors": errors,
                    "skipped": skipped,
                    "duration": time_taken
                }
                
                with open("integration_test_summary.json", "w") as f:
                    json.dump(summary, f, indent=2)
                
                print("\n✓ Test summary saved to integration_test_summary.json")


def main():
    parser = argparse.ArgumentParser(description="Run MAMS integration tests")
    
    parser.add_argument(
        "--no-services",
        action="store_true",
        help="Don't start Docker services (assume they're already running)"
    )
    
    parser.add_argument(
        "--keep-services",
        action="store_true",
        help="Don't stop services after tests"
    )
    
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    
    parser.add_argument(
        "--test",
        type=str,
        help="Run specific test file"
    )
    
    parser.add_argument(
        "--slow",
        action="store_true",
        help="Include slow tests"
    )
    
    parser.add_argument(
        "--parallel",
        type=int,
        metavar="N",
        help="Run tests in parallel with N workers"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--junit",
        action="store_true",
        help="Generate JUnit XML report"
    )
    
    parser.add_argument(
        "--services",
        nargs="+",
        help="Specific services to start"
    )
    
    args = parser.parse_args()
    
    runner = IntegrationTestRunner()
    
    # Check prerequisites
    if not runner.check_prerequisites():
        sys.exit(1)
    
    # Start services if needed
    if not args.no_services:
        if not runner.start_services(args.services):
            sys.exit(1)
    
    try:
        # Run tests
        exit_code = runner.run_tests(args)
        
        # Generate report
        if args.junit:
            runner.generate_report()
        
        return exit_code
        
    finally:
        # Stop services if needed
        if not args.no_services and not args.keep_services:
            runner.stop_services()


if __name__ == "__main__":
    sys.exit(main())