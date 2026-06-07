"""
IntentGuard - Report Generator

Generate human-readable verification reports
"""

import json
from typing import Optional

from .constraint import VerificationReport, VerificationResult


class ReportGenerator:
    """Report generator"""
    
    def __init__(self, report: VerificationReport):
        self.report = report
    
    def to_text(self) -> str:
        """Generate text format report"""
        lines = []
        lines.append("=" * 60)
        lines.append("IntentGuard Verification Report")
        lines.append("=" * 60)
        lines.append("")
        
        # Summary
        summary = self.report.summary
        lines.append(f"[SCORE] {summary['score']}%")
        lines.append(f"   Passed: {summary['passed']} | Failed: {summary['failed']} | Uncertain: {summary['uncertain']}")
        lines.append("")
        
        # Details
        lines.append("-" * 60)
        lines.append("Details")
        lines.append("-" * 60)
        
        for i, result in enumerate(self.report.results, 1):
            status_icon = self._get_status_icon(result.status)
            priority_badge = self._get_priority_badge(result.constraint.priority.value)
            
            lines.append(f"\n{status_icon} [{result.constraint.type.value}] {priority_badge} {result.constraint.source_line}")
            
            if result.status == "passed":
                lines.append(f"   [OK] Satisfied: line {result.line_number}")
                if result.matched_code:
                    code_preview = result.matched_code.strip()[:60]
                    lines.append(f"   Code: {code_preview}")
                    
            elif result.status == "failed":
                lines.append(f"   [FAIL] Not satisfied")
                if result.reason:
                    lines.append(f"   Reason: {result.reason}")
                if result.suggestion:
                    lines.append(f"   Suggestion: {result.suggestion}")
                if result.line_number:
                    lines.append(f"   Location: line {result.line_number}")
                    
            elif result.status == "uncertain":
                lines.append(f"   [WARN] Cannot determine")
                if result.reason:
                    lines.append(f"   Note: {result.reason}")
        
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def to_json(self, indent: int = 2) -> str:
        """Generate JSON format report"""
        return json.dumps(self.report.to_dict(), ensure_ascii=False, indent=indent)
    
    def to_markdown(self) -> str:
        """Generate Markdown format report"""
        lines = []
        lines.append("# IntentGuard Verification Report")
        lines.append("")
        
        # Summary table
        summary = self.report.summary
        lines.append("## Summary")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Score | {summary['score']}% |")
        lines.append(f"| Total Constraints | {summary['total']} |")
        lines.append(f"| Passed | {summary['passed']} |")
        lines.append(f"| Failed | {summary['failed']} |")
        lines.append(f"| Uncertain | {summary['uncertain']} |")
        lines.append("")
        
        # Details
        lines.append("## Details")
        lines.append("")
        
        for result in self.report.results:
            status_icon = self._get_status_icon(result.status)
            
            lines.append(f"### {status_icon} {result.constraint.source_line}")
            lines.append("")
            lines.append(f"- **Type**: {result.constraint.type.value}")
            lines.append(f"- **Priority**: {result.constraint.priority.value}")
            lines.append(f"- **Status**: {result.status}")
            
            if result.line_number:
                lines.append(f"- **Line**: {result.line_number}")
            if result.matched_code:
                lines.append(f"- **Matched Code**: `{result.matched_code.strip()}`")
            if result.reason:
                lines.append(f"- **Reason**: {result.reason}")
            if result.suggestion:
                lines.append(f"- **Suggestion**: {result.suggestion}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _get_status_icon(self, status: str) -> str:
        """Get status icon (ASCII for CLI)"""
        icons = {
            "passed": "[+]",
            "failed": "[X]",
            "uncertain": "[?]",
            "skipped": "[-]"
        }
        return icons.get(status, "[?]")
    
    def _get_priority_badge(self, priority: str) -> str:
        """Get priority badge (ASCII for CLI)"""
        badges = {
            "critical": "[CRITICAL]",
            "high": "[HIGH]",
            "medium": "[MEDIUM]",
            "low": "[LOW]"
        }
        return badges.get(priority, "")


def format_report(report: VerificationReport, fmt: str = "text") -> str:
    """
    Format report
    
    Args:
        report: Verification report
        fmt: Output format (text/json/markdown)
        
    Returns:
        Formatted report string
    """
    generator = ReportGenerator(report)
    
    if fmt == "json":
        return generator.to_json()
    elif fmt == "markdown":
        return generator.to_markdown()
    else:
        return generator.to_text()


# Test
if __name__ == "__main__":
    from engine import verify_code
    
    test_code = '''
import logger

def send_sms(phone, message):
    logger.info(f"Sending SMS")
    sms_service.send(phone, message)

def create_order(user_id):
    if user_id <= 0:
        raise ValueError("Invalid user")
    order = db.save({"user_id": user_id})
    send_sms(user.phone, "Order created")
    return order
'''
    
    test_requirements = '''
用户下单后必须发送短信通知
重要：每次API调用必须记录日志
禁止直接操作数据库
'''
    
    report = verify_code(test_code, test_requirements)
    
    print("=== Text Report ===")
    print(format_report(report, "text"))
    
    print("\n=== Markdown Report ===")
    print(format_report(report, "markdown"))