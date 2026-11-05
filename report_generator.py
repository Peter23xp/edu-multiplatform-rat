#!/usr/bin/env python3
"""
Professional pentest report generator for Educational RAT
Generates PDF reports documenting the engagement
"""

import os
import time
import platform
import socket

try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False


class PentestReport:
    def __init__(self):
        self.entries = []
        self.target_info = {}
        self.start_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.tester_info = {
            "hostname": socket.gethostname(),
            "platform": f"{platform.system()} {platform.release()}",
        }
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            self.tester_info["ip"] = s.getsockname()[0]
            s.close()
        except:
            self.tester_info["ip"] = "127.0.0.1"

    def set_target(self, ip, hostname="Unknown", os_info="Unknown", info_dict=None):
        self.target_info = {
            "ip": ip,
            "hostname": hostname,
            "os": os_info,
        }
        if info_dict:
            self.target_info.update(info_dict)

    def add_entry(self, category, title, description, severity="Info", evidence=""):
        self.entries.append({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "category": category,
            "title": title,
            "description": description,
            "severity": severity,
            "evidence": evidence,
        })

    def add_command_result(self, command, output):
        self.add_entry(
            "Command Execution",
            f"Executed: {command}",
            f"Remote command execution successful",
            severity="High",
            evidence=output[:500]
        )

    def add_screenshot(self, filename):
        self.add_entry(
            "Screen Capture",
            "Screenshot captured",
            "Successfully captured target screen",
            severity="High",
            evidence=f"Saved as: {filename}"
        )

    def add_file_access(self, action, filepath):
        self.add_entry(
            "File Access",
            f"File {action}: {filepath}",
            f"Successfully {action}ed file on target",
            severity="Medium",
            evidence=filepath
        )

    def add_persistence(self, method, success):
        self.add_entry(
            "Persistence",
            f"Persistence method: {method}",
            f"Persistence {'installed' if success else 'failed'}",
            severity="Critical" if success else "Info",
            evidence=f"Method: {method}, Status: {'Active' if success else 'Failed'}"
        )

    def add_network_finding(self, finding):
        self.add_entry(
            "Network Recon",
            "Network scan results",
            finding,
            severity="Medium",
        )

    def generate_text_report(self):
        """Generate a plain text report"""
        lines = []
        lines.append("=" * 70)
        lines.append("         PENETRATION TEST REPORT - EDUCATIONAL")
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"Report generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Engagement start: {self.start_time}")
        lines.append("")
        lines.append("-" * 70)
        lines.append("TESTER INFORMATION")
        lines.append("-" * 70)
        for k, v in self.tester_info.items():
            lines.append(f"  {k:15s}: {v}")
        lines.append("")
        lines.append("-" * 70)
        lines.append("TARGET INFORMATION")
        lines.append("-" * 70)
        for k, v in self.target_info.items():
            lines.append(f"  {k:15s}: {v}")
        lines.append("")
        lines.append("-" * 70)
        lines.append("FINDINGS SUMMARY")
        lines.append("-" * 70)

        severity_count = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Info": 0}
        for entry in self.entries:
            sev = entry["severity"]
            if sev in severity_count:
                severity_count[sev] += 1

        for sev, count in severity_count.items():
            if count > 0:
                lines.append(f"  [{sev:10s}] : {count} finding(s)")

        lines.append("")
        lines.append("-" * 70)
        lines.append("DETAILED FINDINGS")
        lines.append("-" * 70)

        for i, entry in enumerate(self.entries, 1):
            lines.append(f"\n  Finding #{i}")
            lines.append(f"  {'~' * 40}")
            lines.append(f"  Time     : {entry['timestamp']}")
            lines.append(f"  Category : {entry['category']}")
            lines.append(f"  Title    : {entry['title']}")
            lines.append(f"  Severity : {entry['severity']}")
            lines.append(f"  Details  : {entry['description']}")
            if entry['evidence']:
                lines.append(f"  Evidence : {entry['evidence'][:200]}")

        lines.append("")
        lines.append("=" * 70)
        lines.append("RECOMMENDATIONS")
        lines.append("=" * 70)
        lines.append("")
        lines.append("  1. Implement network segmentation to limit lateral movement")
        lines.append("  2. Deploy endpoint detection and response (EDR) solutions")
        lines.append("  3. Enable application whitelisting")
        lines.append("  4. Monitor outbound connections for C2 traffic")
        lines.append("  5. Implement principle of least privilege")
        lines.append("  6. Regular security awareness training")
        lines.append("  7. Keep systems patched and up to date")
        lines.append("")
        lines.append("=" * 70)
        lines.append("  DISCLAIMER: This report was generated for educational purposes")
        lines.append("  as part of an authorized security assessment exercise.")
        lines.append("=" * 70)

        return "\n".join(lines)

    def generate_pdf_report(self, output_path="pentest_report.pdf"):
        """Generate a professional PDF report"""
        if not FPDF_AVAILABLE:
            text_path = output_path.replace(".pdf", ".txt")
            with open(text_path, "w", encoding="utf-8") as f:
                f.write(self.generate_text_report())
            return text_path

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Title page
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 24)
        pdf.ln(40)
        pdf.cell(0, 15, "PENETRATION TEST REPORT", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 14)
        pdf.ln(10)
        pdf.cell(0, 10, "Educational Security Assessment", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(20)
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 8, f"Date: {time.strftime('%Y-%m-%d')}", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, f"Tester: {self.tester_info.get('hostname', 'N/A')}", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, f"Target: {self.target_info.get('ip', 'N/A')}", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(30)
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(0, 8, "CONFIDENTIAL - For authorized personnel only", align="C", new_x="LMARGIN", new_y="NEXT")

        # Executive Summary
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "Executive Summary", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)
        pdf.set_font("Helvetica", "", 11)

        severity_count = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Info": 0}
        for entry in self.entries:
            sev = entry["severity"]
            if sev in severity_count:
                severity_count[sev] += 1

        total = len(self.entries)
        pdf.multi_cell(0, 7,
                       f"This penetration test identified {total} findings across the target system. "
                       f"The assessment demonstrated successful remote access and control capabilities.",
                       new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Findings by Severity:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 11)
        for sev, count in severity_count.items():
            if count > 0:
                pdf.cell(0, 7, f"  {sev}: {count}", new_x="LMARGIN", new_y="NEXT")

        # Target Info
        pdf.ln(10)
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "Target Information", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 11)
        for k, v in self.target_info.items():
            pdf.cell(0, 7, f"  {k}: {v}", new_x="LMARGIN", new_y="NEXT")

        # Detailed Findings
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "Detailed Findings", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

        for i, entry in enumerate(self.entries, 1):
            if pdf.get_y() > 250:
                pdf.add_page()

            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(0, 7, f"Finding #{i}: {entry['title'][:60]}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 6, f"  Severity: {entry['severity']} | Category: {entry['category']}", new_x="LMARGIN", new_y="NEXT")
            pdf.cell(0, 6, f"  Time: {entry['timestamp']}", new_x="LMARGIN", new_y="NEXT")
            pdf.multi_cell(0, 6, f"  Description: {entry['description'][:150]}",
                           new_x="LMARGIN", new_y="NEXT")
            if entry['evidence']:
                pdf.set_font("Helvetica", "I", 9)
                evidence_text = entry['evidence'][:100].replace('\r', '').replace('\n', ' ')
                pdf.multi_cell(0, 5, f"  Evidence: {evidence_text}",
                               new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "", 10)
            pdf.ln(3)

        # Recommendations
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "Recommendations", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)
        pdf.set_font("Helvetica", "", 11)
        recommendations = [
            "1. Deploy EDR/XDR solution with behavioral analysis",
            "2. Implement network segmentation and zero-trust architecture",
            "3. Enable application whitelisting (AppLocker/SRP)",
            "4. Monitor outbound connections for C2 patterns",
            "5. Implement least privilege access controls",
            "6. Regular security awareness training for staff",
            "7. Patch management - keep all systems updated",
            "8. Enable Windows Defender Credential Guard",
            "9. Implement DNS filtering and monitoring",
            "10. Regular penetration testing and red team exercises",
        ]
        for rec in recommendations:
            pdf.cell(0, 8, f"  {rec}", new_x="LMARGIN", new_y="NEXT")

        # Disclaimer
        pdf.ln(15)
        pdf.set_font("Helvetica", "I", 9)
        pdf.multi_cell(0, 5,
                       "DISCLAIMER: This report was generated as part of an authorized educational "
                       "security assessment. The techniques demonstrated are for learning purposes only. "
                       "Unauthorized use of these techniques is illegal and unethical.",
                       new_x="LMARGIN", new_y="NEXT")

        pdf.output(output_path)
        return output_path

    def save_report(self, output_dir=".", filename=None):
        """Save report in both text and PDF formats"""
        if filename is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"pentest_report_{timestamp}"

        os.makedirs(output_dir, exist_ok=True)

        txt_path = os.path.join(output_dir, f"{filename}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(self.generate_text_report())

        pdf_path = os.path.join(output_dir, f"{filename}.pdf")
        actual_pdf = self.generate_pdf_report(pdf_path)

        return txt_path, actual_pdf
