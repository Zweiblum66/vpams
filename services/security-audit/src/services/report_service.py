"""Report Service - Generate security audit reports"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import structlog

logger = structlog.get_logger()


class ReportService:
    """Service for generating security audit reports"""
    
    def __init__(self):
        self.report_templates = {
            "executive": "executive_summary.html",
            "technical": "technical_report.html",
            "compliance": "compliance_report.html"
        }
    
    async def generate_report(
        self,
        audit_id: str,
        findings: List[Dict[str, Any]],
        compliance_results: List[Dict[str, Any]],
        format: str = "json"
    ) -> str:
        """Generate security audit report"""
        
        logger.info(f"Generating {format} report for audit {audit_id}")
        
        report_data = {
            "audit_id": audit_id,
            "generated_at": datetime.utcnow().isoformat(),
            "findings": findings,
            "compliance_results": compliance_results,
            "summary": self._generate_summary(findings, compliance_results)
        }
        
        if format == "json":
            return json.dumps(report_data, indent=2)
        elif format == "html":
            return self._generate_html_report(report_data)
        elif format == "pdf":
            return await self._generate_pdf_report(report_data)
        else:
            raise ValueError(f"Unsupported report format: {format}")
    
    def _generate_summary(
        self,
        findings: List[Dict[str, Any]],
        compliance_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate report summary"""
        
        severity_counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0
        }
        
        for finding in findings:
            severity = finding.get("severity", "info").lower()
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        compliance_scores = {}
        for result in compliance_results:
            standard = result.get("standard")
            score = result.get("score", 0)
            compliance_scores[standard] = score
        
        return {
            "total_findings": len(findings),
            "severity_distribution": severity_counts,
            "compliance_scores": compliance_scores,
            "risk_level": self._calculate_risk_level(severity_counts)
        }
    
    def _calculate_risk_level(self, severity_counts: Dict[str, int]) -> str:
        """Calculate overall risk level"""
        
        if severity_counts["critical"] > 0:
            return "CRITICAL"
        elif severity_counts["high"] > 5:
            return "HIGH"
        elif severity_counts["medium"] > 10:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _generate_html_report(self, data: Dict[str, Any]) -> str:
        """Generate HTML report"""
        
        # Simple HTML template
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Security Audit Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; }}
                .summary {{ margin: 20px 0; }}
                .findings {{ margin: 20px 0; }}
                .critical {{ color: #d9534f; }}
                .high {{ color: #f0ad4e; }}
                .medium {{ color: #5bc0de; }}
                .low {{ color: #5cb85c; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Security Audit Report</h1>
                <p>Audit ID: {data['audit_id']}</p>
                <p>Generated: {data['generated_at']}</p>
            </div>
            
            <div class="summary">
                <h2>Executive Summary</h2>
                <p>Total Findings: {data['summary']['total_findings']}</p>
                <p>Risk Level: <span class="{data['summary']['risk_level'].lower()}">{data['summary']['risk_level']}</span></p>
            </div>
            
            <div class="findings">
                <h2>Security Findings</h2>
                <ul>
                """
        
        for finding in data['findings']:
            severity_class = finding.get('severity', 'info').lower()
            html += f"""
                    <li class="{severity_class}">
                        <strong>{finding.get('title', 'Unknown')}</strong> - 
                        {finding.get('description', 'No description')}
                    </li>
                """
        
        html += """
                </ul>
            </div>
        </body>
        </html>
        """
        
        return html
    
    async def _generate_pdf_report(self, data: Dict[str, Any]) -> str:
        """Generate PDF report (placeholder)"""
        
        # In a real implementation, would use a PDF library
        logger.info("PDF generation not implemented, returning JSON")
        return json.dumps(data, indent=2)