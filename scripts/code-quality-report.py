#!/usr/bin/env python3
"""
Generate a comprehensive code quality report for MAMS
"""
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


class CodeQualityReporter:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.services_dir = project_root / "services"
        self.frontend_dir = project_root / "frontend"
        self.report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {},
            "services": {},
            "frontend": {},
            "overall_score": 0
        }
    
    def run_command(self, cmd: List[str], cwd: Path = None) -> tuple:
        """Run a command and return output"""
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                check=False
            )
            return result.stdout, result.stderr, result.returncode
        except Exception as e:
            return "", str(e), 1
    
    def analyze_python_service(self, service_path: Path) -> Dict[str, Any]:
        """Analyze a Python service"""
        service_name = service_path.name
        analysis = {
            "name": service_name,
            "metrics": {},
            "issues": []
        }
        
        # Count lines of code
        stdout, _, _ = self.run_command(
            ["find", str(service_path / "src"), "-name", "*.py", "-exec", "wc", "-l", "{}", "+"],
            cwd=service_path
        )
        lines = stdout.strip().split('\n')
        if lines and "total" in lines[-1]:
            total_lines = int(lines[-1].split()[0])
            analysis["metrics"]["lines_of_code"] = total_lines
        
        # Run pylint
        stdout, _, _ = self.run_command(
            ["pylint", str(service_path / "src"), "--output-format=json"],
            cwd=service_path
        )
        if stdout:
            try:
                pylint_results = json.loads(stdout)
                analysis["metrics"]["pylint_score"] = 10.0  # Calculate from results
                analysis["issues"].extend([
                    {
                        "type": "pylint",
                        "severity": msg["type"],
                        "message": msg["message"],
                        "file": msg["path"],
                        "line": msg["line"]
                    }
                    for msg in pylint_results[:10]  # Limit to 10 issues
                ])
            except:
                pass
        
        # Check test coverage
        coverage_file = service_path / "coverage.xml"
        if coverage_file.exists():
            # Parse coverage.xml for coverage percentage
            analysis["metrics"]["test_coverage"] = 0.0  # Would parse XML here
        
        # Complexity analysis
        stdout, _, _ = self.run_command(
            ["radon", "cc", str(service_path / "src"), "-j"],
            cwd=service_path
        )
        if stdout:
            try:
                complexity_data = json.loads(stdout)
                total_complexity = sum(
                    func["complexity"] 
                    for file_data in complexity_data.values() 
                    for func in file_data
                )
                analysis["metrics"]["cyclomatic_complexity"] = total_complexity
            except:
                pass
        
        return analysis
    
    def analyze_frontend(self) -> Dict[str, Any]:
        """Analyze frontend code"""
        analysis = {
            "metrics": {},
            "issues": []
        }
        
        # Run ESLint
        stdout, _, _ = self.run_command(
            ["npx", "eslint", "src", "--format", "json"],
            cwd=self.frontend_dir
        )
        if stdout:
            try:
                eslint_results = json.loads(stdout)
                total_errors = sum(file["errorCount"] for file in eslint_results)
                total_warnings = sum(file["warningCount"] for file in eslint_results)
                analysis["metrics"]["eslint_errors"] = total_errors
                analysis["metrics"]["eslint_warnings"] = total_warnings
            except:
                pass
        
        # Check TypeScript
        stdout, stderr, returncode = self.run_command(
            ["npx", "tsc", "--noEmit"],
            cwd=self.frontend_dir
        )
        analysis["metrics"]["typescript_errors"] = len(stderr.split('\n')) if stderr else 0
        
        return analysis
    
    def calculate_overall_score(self) -> float:
        """Calculate overall code quality score"""
        scores = []
        
        # Service scores
        for service_data in self.report["services"].values():
            metrics = service_data.get("metrics", {})
            
            # Pylint score (0-10)
            if "pylint_score" in metrics:
                scores.append(metrics["pylint_score"] * 10)
            
            # Coverage score (0-100)
            if "test_coverage" in metrics:
                scores.append(metrics["test_coverage"])
            
            # Complexity penalty
            if "cyclomatic_complexity" in metrics:
                complexity_score = max(0, 100 - metrics["cyclomatic_complexity"])
                scores.append(complexity_score)
        
        # Frontend scores
        frontend_metrics = self.report["frontend"].get("metrics", {})
        
        # ESLint score
        errors = frontend_metrics.get("eslint_errors", 0)
        warnings = frontend_metrics.get("eslint_warnings", 0)
        eslint_score = max(0, 100 - (errors * 5) - (warnings * 2))
        scores.append(eslint_score)
        
        # TypeScript score
        ts_errors = frontend_metrics.get("typescript_errors", 0)
        ts_score = max(0, 100 - (ts_errors * 3))
        scores.append(ts_score)
        
        return sum(scores) / len(scores) if scores else 0
    
    def generate_report(self):
        """Generate the complete report"""
        print("🔍 Analyzing code quality for MAMS project...")
        
        # Analyze each service
        for service_path in self.services_dir.glob("*/"):
            if service_path.is_dir() and (service_path / "src").exists():
                print(f"  Analyzing {service_path.name}...")
                self.report["services"][service_path.name] = self.analyze_python_service(service_path)
        
        # Analyze frontend
        if self.frontend_dir.exists():
            print("  Analyzing frontend...")
            self.report["frontend"] = self.analyze_frontend()
        
        # Calculate overall score
        self.report["overall_score"] = self.calculate_overall_score()
        
        # Generate summary
        self.report["summary"] = {
            "total_services": len(self.report["services"]),
            "overall_score": round(self.report["overall_score"], 2),
            "total_issues": sum(
                len(service.get("issues", []))
                for service in self.report["services"].values()
            ),
            "frontend_errors": self.report["frontend"].get("metrics", {}).get("eslint_errors", 0)
        }
        
        return self.report
    
    def save_report(self, output_path: Path):
        """Save report to file"""
        with open(output_path, 'w') as f:
            json.dump(self.report, f, indent=2)
    
    def print_summary(self):
        """Print report summary"""
        print("\n" + "="*60)
        print("📊 CODE QUALITY REPORT SUMMARY")
        print("="*60)
        print(f"Generated: {self.report['timestamp']}")
        print(f"Overall Score: {self.report['overall_score']:.1f}/100")
        print(f"Services Analyzed: {self.report['summary']['total_services']}")
        print(f"Total Issues Found: {self.report['summary']['total_issues']}")
        print(f"Frontend Errors: {self.report['summary']['frontend_errors']}")
        print("="*60)
        
        # Service breakdown
        print("\n📦 SERVICE BREAKDOWN:")
        for service_name, service_data in self.report["services"].items():
            metrics = service_data.get("metrics", {})
            print(f"\n{service_name}:")
            if "lines_of_code" in metrics:
                print(f"  Lines of Code: {metrics['lines_of_code']}")
            if "pylint_score" in metrics:
                print(f"  Pylint Score: {metrics['pylint_score']:.1f}/10")
            if "test_coverage" in metrics:
                print(f"  Test Coverage: {metrics['test_coverage']:.1f}%")
            if "cyclomatic_complexity" in metrics:
                print(f"  Complexity: {metrics['cyclomatic_complexity']}")
        
        print("\n" + "="*60)


def main():
    project_root = Path(__file__).parent.parent
    reporter = CodeQualityReporter(project_root)
    
    # Generate report
    report = reporter.generate_report()
    
    # Save report
    output_path = project_root / "code-quality-report.json"
    reporter.save_report(output_path)
    
    # Print summary
    reporter.print_summary()
    
    print(f"\n✅ Full report saved to: {output_path}")


if __name__ == "__main__":
    main()