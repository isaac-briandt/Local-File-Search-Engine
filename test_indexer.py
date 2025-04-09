#!/usr/bin/env python3
import os
import json
import shutil
import time
from datetime import datetime, timedelta
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from index_manager import FileIndexManager

# ANSI color codes


class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


class IndexTester:
    def __init__(self):
        self.test_dir = "test_data"
        self.report_dir = "test_reports"
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'total': 0
        }
        self.test_logs = []
        self.setup_test_environment()

    def log_test(self, command, output, success, expected_success=True):
        """Log test results for PDF report"""
        self.test_logs.append({
            'command': command,
            'output': output,
            'success': success,
            'expected_success': expected_success,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'duration': '0.0s'  # Could be enhanced to track actual duration
        })

    def generate_json_report(self):
        """Generate a JSON report of test results"""
        report_dir = self.report_dir
        if not os.path.exists(report_dir):
            os.makedirs(report_dir)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(report_dir, f"test_report_{timestamp}.json")
        
        # Prepare report data
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_tests': self.test_results['total'],
                'passed_tests': self.test_results['passed'],
                'failed_tests': self.test_results['failed'],
                'success_rate': round((self.test_results['passed'] / self.test_results['total'] * 100), 2)
            },
            'passed_tests': [
                {
                    'command': test['command'],
                    'timestamp': test['timestamp'],
                    'duration': test['duration']
                }
                for test in self.test_logs
                if test['success'] == test['expected_success']
            ],
            'failed_tests': [
                {
                    'command': test['command'],
                    'timestamp': test['timestamp'],
                    'duration': test['duration'],
                    'error': test['output'].strip()
                }
                for test in self.test_logs
                if test['success'] != test['expected_success']
            ],
            'test_cases': []
        }

        # Add detailed test results
        for test in self.test_logs:
            clean_output = test['output'].replace('\033[91m', '').replace('\033[92m', '') \
                                      .replace('\033[93m', '').replace('\033[94m', '') \
                                      .replace('\033[1m', '').replace('\033[0m', '')
            
            test_case = {
                'command': test['command'],
                'timestamp': test['timestamp'],
                'duration': test['duration'],
                'success': test['success'],
                'expected_success': test['expected_success'],
                'output': clean_output.strip(),
                'status': 'PASSED' if test['success'] == test['expected_success'] else 'FAILED'
            }
            report_data['test_cases'].append(test_case)

        # Write JSON report
        try:
            with open(filename, 'w') as f:
                json.dump(report_data, f, indent=2)
            print(f"\n{Colors.GREEN}JSON report generated: {filename}{Colors.END}")
            return filename
        except Exception as e:
            print(f"\n{Colors.RED}Error generating JSON report: {e}{Colors.END}")
            return None

    def generate_pdf_report(self):
        """Generate PDF report of test results"""
        report_dir = self.report_dir
        if not os.path.exists(report_dir):
            os.makedirs(report_dir)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(report_dir, f"test_report_{timestamp}.pdf")
        
        doc = SimpleDocTemplate(filename, pagesize=letter,
                              rightMargin=36, leftMargin=36,
                              topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()
        
        # Create custom styles
        styles.add(ParagraphStyle(
            name='CommandStyle',
            parent=styles['Normal'],
            fontName='Courier',
            fontSize=10,
            spaceAfter=5
        ))

        styles.add(ParagraphStyle(
            name='PassedTest',
            parent=styles['Normal'],
            textColor=colors.green,
            fontSize=10,
            spaceAfter=3
        ))

        styles.add(ParagraphStyle(
            name='FailedTest',
            parent=styles['Normal'],
            textColor=colors.red,
            fontSize=10,
            spaceAfter=3
        ))

        styles.add(ParagraphStyle(
            name='TableHeader',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=12,
            textColor=colors.white,
            alignment=1  # Center alignment
        ))

        styles.add(ParagraphStyle(
            name='TableCell',
            parent=styles['Normal'],
            fontSize=10,
            spaceBefore=6,
            spaceAfter=6,
            leading=14  # Line spacing
        ))
        
        content = []
        
        # Add title and timestamp
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=24,
            spaceAfter=30,
            alignment=1
        )
        content.append(Paragraph("File Index Manager Test Report", title_style))
        content.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                               ParagraphStyle('DateTime', parent=styles['Normal'], 
                                            alignment=1, spaceAfter=20)))
        
        # Add summary table with larger size
        summary_table = Table([
            [Paragraph("Test Summary", styles['TableHeader']), ""],
            ["Total Tests", str(self.test_results['total'])],
            ["Passed", str(self.test_results['passed'])],
            ["Failed", str(self.test_results['failed'])],
            ["Success Rate", f"{(self.test_results['passed'] / self.test_results['total'] * 100):.1f}%"]
        ], colWidths=[4*inch, 2*inch])
        
        summary_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2F5597')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            # Data rows
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#E9EDF4')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            # Grid
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        content.append(summary_table)
        content.append(Spacer(1, 30))

        # Add test execution overview table
        content.append(Paragraph("Test Execution Overview", 
                               ParagraphStyle('SectionTitle', parent=styles['Heading1'],
                                            fontSize=16, spaceAfter=15)))

        # Create detailed test results table
        test_table_data = [
            [
                Paragraph("Test #", styles['TableHeader']),
                Paragraph("Command", styles['TableHeader']),
                Paragraph("Status", styles['TableHeader']),
                Paragraph("Duration", styles['TableHeader'])
            ]
        ]

        for i, test in enumerate(self.test_logs, 1):
            status = "✓ PASSED" if test['success'] == test['expected_success'] else "✗ FAILED"
            status_color = colors.green if test['success'] == test['expected_success'] else colors.red
            
            row = [
                Paragraph(str(i), styles['TableCell']),
                Paragraph(test['command'], styles['TableCell']),
                Paragraph(status, ParagraphStyle(
                    f'Status_{i}',
                    parent=styles['TableCell'],
                    textColor=status_color,
                    fontName='Helvetica-Bold'
                )),
                Paragraph(test['duration'], styles['TableCell'])
            ]
            test_table_data.append(row)

        # Create the test results table with adjusted column widths
        test_table = Table(test_table_data, colWidths=[
            0.5*inch,    # Test number
            4.0*inch,    # Command
            1.0*inch,    # Status
            0.8*inch     # Duration
        ])

        test_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2F5597')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            # Data rows
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#E9EDF4')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),  # Left-align command column
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            # Grid
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#E9EDF4'), colors.white]),
            # Padding
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ]))

        content.append(test_table)
        content.append(Spacer(1, 30))

        # Add detailed test results
        content.append(Paragraph("Detailed Test Results", 
                               ParagraphStyle('SectionTitle', parent=styles['Heading1'],
                                            fontSize=16, spaceAfter=15)))
        
        # Add detailed test results with improved formatting
        for i, test in enumerate(self.test_logs, 1):
            # Test header with custom style
            header_style = ParagraphStyle(
                'TestHeader',
                parent=styles['Heading2'],
                fontSize=14,
                textColor=colors.HexColor('#2F5597'),
                spaceBefore=15,
                spaceAfter=5
            )
            content.append(Paragraph(f"Test #{i}: {test['command']}", header_style))
            
            # Status with enhanced visibility
            status = "✓ PASSED" if test['success'] == test['expected_success'] else "✗ FAILED"
            color = colors.green if test['success'] == test['expected_success'] else colors.red
            status_style = ParagraphStyle(
                f"Status_{i}",
                parent=styles['Normal'],
                textColor=color,
                fontName='Helvetica-Bold',
                fontSize=12,
                leftIndent=20
            )
            content.append(Paragraph(f"Status: {status}", status_style))
            
            # Metadata with improved formatting
            meta_style = ParagraphStyle(
                'TestMeta',
                parent=styles['Normal'],
                fontSize=10,
                leftIndent=20,
                spaceAfter=3
            )
            content.append(Paragraph(f"Timestamp: {test['timestamp']}", meta_style))
            content.append(Paragraph(f"Duration: {test['duration']}", meta_style))
            
            # Output with improved readability
            if test['output']:
                output_style = ParagraphStyle(
                    f"Output_{i}",
                    parent=styles['Normal'],
                    fontName='Courier',
                    fontSize=9,
                    leftIndent=20,
                    rightIndent=20,
                    spaceBefore=5,
                    spaceAfter=10,
                    leading=14
                )
                clean_output = test['output'].replace('\033[91m', '').replace('\033[92m', '') \
                                          .replace('\033[93m', '').replace('\033[94m', '') \
                                          .replace('\033[1m', '').replace('\033[0m', '')
                content.append(Paragraph(f"Output:<br/>{clean_output}", output_style))
            
            content.append(Spacer(1, 10))
        
        doc.build(content)
        print(f"\n{Colors.GREEN}PDF report generated: {filename}{Colors.END}")
        return filename
        
    def setup_test_environment(self):
        """Create test directory and sample files"""
        print(f"\n{Colors.BOLD}=== Setting up test environment ==={Colors.END}")
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)

        # Create test files with different sizes and dates
        files = {
            'small.txt': 'Small text file content',
            'medium.txt': 'M' * 1000,  # 1KB file
            'large.txt': 'L' * 10000,  # 10KB file
            'document.pdf': 'PDF' * 100,
            'image.jpg': 'JPG' * 500,
            'script.py': 'print("Hello, World!")',
            'test_data.txt': 'Test data content',
            'sample_script.py': 'print("Sample")'
        }

        # Create files with different timestamps
        for filename, content in files.items():
            file_path = os.path.join(self.test_dir, filename)
            with open(file_path, 'w') as f:
                f.write(content)

            # Set different modification times for testing date-based sorting
            if 'small' in filename:
                mtime = time.time() - 86400  # 1 day ago
            elif 'medium' in filename:
                mtime = time.time() - 43200  # 12 hours ago
            elif 'large' in filename:
                mtime = time.time()  # current time
            else:
                continue

            os.utime(file_path, (mtime, mtime))

        print(f"{Colors.GREEN}Created test files in {
              self.test_dir}{Colors.END}")

    def run_command(self, command, expected_success=True):
        """Run a CLI command and print its output"""
        print(f"\n{Colors.BOLD}> {command}{Colors.END}")

        # Record start time
        start_time = time.time()

        output_file = "command_output.tmp"
        result = os.system(f"python3 cli.py {command} > {output_file} 2>&1")

        # Calculate duration
        duration = time.time() - start_time

        with open(output_file, 'r') as f:
            output = f.read()
        os.remove(output_file)

        print(output)

        success = (result == 0)
        test_passed = success if expected_success else not success

        self.test_results['total'] += 1
        if test_passed:
            self.test_results['passed'] += 1
            if not expected_success:
                print(f"{Colors.GREEN}TEST PASSED: Command failed as expected{
                      Colors.END}")
        else:
            self.test_results['failed'] += 1
            if expected_success:
                print(f"{Colors.RED}TEST FAILED: Command failed but expected to succeed{
                      Colors.END}")
            else:
                print(f"{Colors.RED}TEST FAILED: Command succeeded but expected to fail{
                      Colors.END}")

        # Log test with duration
        test_log = {
            'command': command,
            'output': output,
            'success': success,
            'expected_success': expected_success,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'duration': f"{duration:.3f}s"
        }
        self.test_logs.append(test_log)

    def print_test_section(self, section_name):
        """Print a formatted test section header"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}=== {
              section_name} ==={Colors.END}")

    def print_test_summary(self):
        """Print test results summary"""
        print(f"\n{Colors.BOLD}=== Test Summary ==={Colors.END}")
        print(f"Total Tests: {self.test_results['total']}")

        if self.test_results['passed'] > 0:
            print(f"{Colors.GREEN}Passed: {
                  self.test_results['passed']}{Colors.END}")
        if self.test_results['failed'] > 0:
            print(f"{Colors.RED}Failed: {
                  self.test_results['failed']}{Colors.END}")

        success_rate = (
            self.test_results['passed'] / self.test_results['total']) * 100
        color = Colors.GREEN if success_rate == 100 else Colors.YELLOW if success_rate >= 80 else Colors.RED
        print(f"Success Rate: {color}{success_rate:.1f}%{Colors.END}")


    def run_tests(self):
        """Run all test cases"""
        self.print_test_section("Starting Tests")

        # Create FileIndexManager instance
        index = FileIndexManager()

        # Test 1: Add files
        self.print_test_section("1. Testing file addition")
        for file in os.listdir(self.test_dir):
            self.run_command(f"add {os.path.join(self.test_dir, file)}")

        # Test 2: Show statistics
        self.print_test_section("2. Testing statistics")
        self.run_command("stats")

        # Test 3: Search by file type with sorting
        self.print_test_section("3. Testing file type search with sorting")
        self.run_command("search-type txt --sort-by size --sort-order desc")
        self.run_command("search-type py --sort-by name --sort-order asc")
        self.run_command("search-type pdf --sort-by date --sort-order desc")

        # Test 4: Search by size with sorting
        self.print_test_section("4. Testing size-based search with sorting")
        self.run_command("search-size 0 --max-size 100 --sort-by date")
        self.run_command("search-size 1000 --max-size 5000 --sort-by size")
        self.run_command("search-size 5000 --sort-by name")

        # Test 5: Search by date with sorting
        self.print_test_section("5. Testing date-based search with sorting")
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        self.run_command(f"search-date --start {yesterday} --sort-by size")
        self.run_command(
            f"search-date --end {today} --sort-by date --sort-order asc")
        self.run_command(
            f"search-date --start {yesterday} --end {today} --sort-by name")
        self.run_command("search-date --start invalid-date",
                         expected_success=False)
        self.run_command("search-date", expected_success=False)

        # Test 6: Error cases
        self.print_test_section("6. Testing error cases")
        self.run_command("add nonexistent_file.txt", expected_success=False)
        self.run_command("remove nonexistent_file.txt", expected_success=False)
        self.run_command("search-type txt --sort-by invalid",
                         expected_success=False)

       # Generate reports
        self.print_test_summary()
        
        # Save all reports to the test_reports directory
        if not os.path.exists(self.report_dir):
            os.makedirs(self.report_dir)

        # Generate JSON test report
        json_report = self.generate_json_report()
        
        # Generate PDF test report
        pdf_report = self.generate_pdf_report()
        
        # Save a copy of the index file
        index_report = index.save_index_to_report(self.report_dir)
        
        # Print report locations
        print(f"\nTest reports generated:")
        print(f"- JSON Test Report: {json_report}")
        print(f"- PDF Test Report:  {pdf_report}")
        print(f"- Index File:       {index_report}")

    def cleanup(self):
        """Clean up test environment"""
        print(f"\n{Colors.BOLD}=== Cleaning up test environment ==={Colors.END}")
        shutil.rmtree(self.test_dir)
        if os.path.exists("data/main_index.json"):
            os.remove("data/main_index.json")
        print(f"{Colors.GREEN}Cleanup completed{Colors.END}")

if __name__ == "__main__":
    tester = IndexTester()
    try:
        tester.run_tests()
    finally:
        tester.cleanup()