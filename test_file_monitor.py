#!/usr/bin/env python3

import unittest
import tempfile
import os
import time
import shutil
import logging
from pathlib import Path
from datetime import datetime
from io import StringIO
import json
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from file_monitor import FileMonitor
from index_manager import FileIndexManager

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

class TestOutput:
    def __init__(self):
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'total': 0,
            'start_time': datetime.now(),
            'tests': []
        }
        
    def add_test_result(self, test_name, success, duration, output=None, error=None):
        self.test_results['tests'].append({
            'name': test_name,
            'success': success,
            'duration': duration,
            'output': output,
            'error': error,
            'timestamp': datetime.now().isoformat()
        })
        
        if success:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1
        self.test_results['total'] += 1
        
    def generate_pdf_report(self):
        """Generate a detailed PDF report of test results"""
        reports_dir = "test_reports"
        os.makedirs(reports_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(reports_dir, f"file_monitor_test_report_{timestamp}.pdf")
        
        doc = SimpleDocTemplate(
            filename,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name='TestHeader',
            parent=styles['Heading1'],
            fontSize=14,
            spaceAfter=10,
            textColor=colors.HexColor('#2F5597')
        ))
        
        styles.add(ParagraphStyle(
            name='TestName',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=6,
            textColor=colors.HexColor('#2F5597')
        ))
        
        # Build document content
        content = []
        
        # Add title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#2F5597')
        )
        content.append(Paragraph("File Monitor Test Report", title_style))
        
        # Add timestamp and summary
        content.append(Paragraph(
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            styles['Normal']
        ))
        content.append(Spacer(1, 20))
        
        # Add summary table
        summary_data = [
            ['Test Summary', ''],
            ['Total Tests', str(self.test_results['total'])],
            ['Passed', str(self.test_results['passed'])],
            ['Failed', str(self.test_results['failed'])],
            ['Success Rate', f"{(self.test_results['passed'] / self.test_results['total'] * 100):.1f}%"]
        ]
        
        summary_table = Table(summary_data, colWidths=[4*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2F5597')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#E9EDF4')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        content.append(summary_table)
        content.append(Spacer(1, 30))
        
        # Add detailed test results
        content.append(Paragraph("Detailed Test Results", styles['TestHeader']))
        content.append(Spacer(1, 10))
        
        test_data = [
            ['Test Name', 'Status', 'Duration', 'Output']
        ]
        
        for test in self.test_results['tests']:
            status = "✓ PASSED" if test['success'] else "✗ FAILED"
            output_text = test.get('output', '')
            if test.get('error'):
                output_text = f"Error: {test['error']}\n{output_text}"
            
            test_data.append([
                test['name'],
                status,
                f"{test['duration']:.2f}s",
                output_text
            ])
            
        test_table = Table(test_data, colWidths=[2.5*inch, 1*inch, 1*inch, 3*inch])
        test_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2F5597')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#E9EDF4')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('TEXTCOLOR', (1, 1), (1, -1), colors.green),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        for i, test in enumerate(self.test_results['tests'], 1):
            if not test['success']:
                test_table.setStyle(TableStyle([
                    ('TEXTCOLOR', (1, i), (1, i), colors.red)
                ]))
        
        content.append(test_table)
        
        doc.build(content)
        print(f"\n{Colors.GREEN}PDF report generated: {filename}{Colors.END}")
        return filename
        
    def generate_json_report(self):
        """Generate a JSON report of test results"""
        reports_dir = "test_reports"
        os.makedirs(reports_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(reports_dir, f"file_monitor_test_report_{timestamp}.json")
        
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_tests': self.test_results['total'],
                'passed_tests': self.test_results['passed'],
                'failed_tests': self.test_results['failed'],
                'success_rate': round((self.test_results['passed'] / self.test_results['total'] * 100), 2)
            },
            'tests': self.test_results['tests']
        }
        
        with open(filename, 'w') as f:
            json.dump(report_data, f, indent=2)
            
        print(f"{Colors.GREEN}JSON report generated: {filename}{Colors.END}")
        return filename

def wait_for_condition(condition_func, timeout=5, interval=0.1):
    """Wait for a condition to be true with timeout"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            if condition_func():
                return True
        except Exception:
            pass
        time.sleep(interval)
    return False

def normalize_path(path):
    """Normalize path for consistent comparison"""
    return str(Path(path).resolve())

class FileMonitorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_output = TestOutput()
        print(f"\n{Colors.BOLD}File Monitor Test Suite{Colors.END}")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
    def setUp(self):
        self.start_time = time.time()
        self.test_dir = normalize_path(tempfile.mkdtemp())
        if not os.path.exists('data'):
            os.makedirs('data')
        self.index_manager = FileIndexManager()
        
    def tearDown(self):
        try:
            if hasattr(self, 'monitor') and self.monitor.is_running():
                self.monitor.stop()
                time.sleep(0.5)
            if hasattr(self, 'test_dir') and os.path.exists(self.test_dir):
                shutil.rmtree(self.test_dir)
        except Exception as e:
            print(f"{Colors.RED}Error in tearDown: {e}{Colors.END}")
            
    def create_monitor(self, interval: float = 1.0) -> FileMonitor:
        """Helper to create a file monitor with specified interval"""
        monitor = FileMonitor(
            index_manager=self.index_manager,
            paths_to_monitor=[self.test_dir],
            monitored_extensions={'.txt', '.pdf'},
            interval=interval
        )
        return monitor
        
    def create_test_file(self, filename: str, content: str = "Test content") -> str:
        """Helper to create a test file"""
        filepath = normalize_path(os.path.join(self.test_dir, filename))
        with open(filepath, 'w') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        return filepath
        
    def test_file_creation(self):
        """Test that file creation is detected and indexed"""
        self.monitor = self.create_monitor()
        self.monitor.start()
        test_file = self.create_test_file("test.txt")
        
        def check_file_indexed():
            return test_file in self.index_manager.index_data["files"]
            
        self.assertTrue(
            wait_for_condition(check_file_indexed),
            f"File was not indexed: {test_file}"
        )
        
    def test_file_modification(self):
        """Test that file modification is detected and indexed"""
        self.monitor = self.create_monitor()
        self.monitor.start()
        test_file = self.create_test_file("test.txt")
        
        def check_initial_file():
            return test_file in self.index_manager.index_data["files"]
        
        self.assertTrue(
            wait_for_condition(check_initial_file),
            "Initial file was not indexed"
        )
        
        initial_modification_time = self.index_manager.index_data["files"][test_file]["modified"]
        time.sleep(1)
        
        with open(test_file, 'w') as f:
            f.write("Modified content")
            f.flush()
            os.fsync(f.fileno())
            
        def check_modification():
            if test_file not in self.index_manager.index_data["files"]:
                return False
            return self.index_manager.index_data["files"][test_file]["modified"] != initial_modification_time
            
        self.assertTrue(
            wait_for_condition(check_modification),
            "File modification was not detected"
        )
        
    def test_file_deletion(self):
        """Test that file deletion is detected and removed from index"""
        self.monitor = self.create_monitor()
        self.monitor.start()
        test_file = self.create_test_file("test.txt")
        
        def check_file_indexed():
            return test_file in self.index_manager.index_data["files"]
        
        self.assertTrue(
            wait_for_condition(check_file_indexed),
            "File was not initially indexed"
        )
        
        os.remove(test_file)
        
        def check_file_removed():
            return test_file not in self.index_manager.index_data["files"]
            
        self.assertTrue(
            wait_for_condition(check_file_removed),
            "File deletion was not detected"
        )
        
    def test_file_move(self):
        """Test that file moving/renaming is detected and properly handled"""
        self.monitor = self.create_monitor()
        self.monitor.start()
        src_file = self.create_test_file("source.txt")
        dst_file = normalize_path(os.path.join(self.test_dir, "destination.txt"))
        
        def check_source_indexed():
            return src_file in self.index_manager.index_data["files"]
        
        self.assertTrue(
            wait_for_condition(check_source_indexed),
            "Source file was not indexed"
        )
        
        os.rename(src_file, dst_file)
        
        def check_move_completed():
            return (src_file not in self.index_manager.index_data["files"] and
                   dst_file in self.index_manager.index_data["files"])
                   
        self.assertTrue(
            wait_for_condition(check_move_completed),
            "File move was not properly handled"
        )
        
    def test_extension_filtering(self):
        """Test that only monitored extensions are processed"""
        self.monitor = self.create_monitor()
        self.monitor.start()
        txt_file = self.create_test_file("test.txt")
        pdf_file = self.create_test_file("test.pdf")
        doc_file = self.create_test_file("test.doc")
        
        def check_files_filtered():
            return (txt_file in self.index_manager.index_data["files"] and
                   pdf_file in self.index_manager.index_data["files"] and
                   doc_file not in self.index_manager.index_data["files"])
                   
        self.assertTrue(
            wait_for_condition(check_files_filtered),
            "File extension filtering not working correctly"
        )
        
    def test_monitor_start_stop(self):
        """Test monitor start/stop functionality"""
        self.monitor = self.create_monitor()
        self.assertTrue(self.monitor.start(), "Monitor should start successfully")
        self.assertTrue(self.monitor.is_running(), "Monitor should be running after start")
        
        self.assertTrue(self.monitor.stop(), "Monitor stop should succeed")
        self.assertFalse(self.monitor.is_running(), "Monitor should not be running after stop")
        
    # Interval-specific test methods
    def test_default_interval(self):
        """Test that default interval is set correctly"""
        self.monitor = self.create_monitor()  # No interval specified
        self.assertEqual(self.monitor.get_interval(), 1.0)
        
    def test_custom_interval(self):
        """Test setting custom intervals"""
        intervals = [0.1, 0.5, 2.0, 5.0]
        for interval in intervals:
            with self.subTest(interval=interval):
                self.monitor = self.create_monitor(interval)
                self.assertEqual(self.monitor.get_interval(), interval)
                
    def test_minimum_interval(self):
        """Test that intervals below minimum are adjusted"""
        test_intervals = [0.01, 0.05, 0.09]
        for interval in test_intervals:
            with self.subTest(interval=interval):
                self.monitor = self.create_monitor(interval)
                self.assertEqual(self.monitor.get_interval(), 0.1)
                
    def test_change_interval_runtime(self):
        """Test changing interval while monitor is running"""
        self.monitor = self.create_monitor(1.0)
        self.monitor.start()
        
        test_intervals = [0.5, 2.0, 0.1]
        for interval in test_intervals:
            with self.subTest(interval=interval):
                self.assertTrue(self.monitor.set_interval(interval))
                self.assertEqual(self.monitor.get_interval(), interval)
                self.assertTrue(self.monitor.is_running())
                
    def test_file_detection_different_intervals(self):
        """Test file detection with different intervals"""
        intervals_and_timeouts = [
            (0.1, 0.3),  # Fast interval
            (0.5, 1.0),  # Medium interval
            (1.0, 2.0),  # Default interval
            (2.0, 3.0)   # Slow interval
        ]
        
        for interval, timeout in intervals_and_timeouts:
            with self.subTest(interval=interval):
                self.monitor = self.create_monitor(interval)
                self.monitor.start()
                
                test_file = self.create_test_file(f"test_{interval}.txt")
                
                def check_file_indexed():
                    return test_file in self.index_manager.index_data["files"]
                
                self.assertTrue(
                    wait_for_condition(check_file_indexed, timeout=timeout),
                    f"File not detected within {timeout}s with {interval}s interval"
                )
                
                self.monitor.stop()
                time.sleep(0.5)
                
    def test_interval_with_large_files(self):
        """Test different intervals with large file operations"""
        large_content = "X" * (1024 * 1024)  # 1MB of data
        
        test_intervals = [0.1, 0.5, 1.0]
        for interval in test_intervals:
            with self.subTest(interval=interval):
                self.monitor = self.create_monitor(interval)
                self.monitor.start()
                
                large_file = self.create_test_file(f"large_{interval}.txt", large_content)
                
                def check_file_indexed():
                    return large_file in self.index_manager.index_data["files"]
                
                self.assertTrue(
                    wait_for_condition(check_file_indexed, timeout=5.0),
                    f"Large file not detected with {interval}s interval"
                )
                
                self.assertEqual(
                    self.index_manager.index_data["files"][large_file]["size"],
                    len(large_content)
                )
                
                self.monitor.stop()
                time.sleep(0.5)
                
    def test_interval_persistence(self):
        """Test that interval settings persist across monitor restarts"""
        test_interval = 0.5
        
        self.monitor = self.create_monitor(test_interval)
        self.monitor.start()
        
        test_file = self.create_test_file("test.txt")
        
        def check_file_indexed():
            return test_file in self.index_manager.index_data["files"]
        
        self.assertTrue(wait_for_condition(check_file_indexed))
        
        # Stop and restart monitor
        self.monitor.stop()
        time.sleep(1.0)
        self.monitor.start()
        
        # Verify interval persisted
        self.assertEqual(self.monitor.get_interval(), test_interval)
        
        test_file2 = self.create_test_file("test2.txt")
        
        def check_file2_indexed():
            return test_file2 in self.index_manager.index_data["files"]
        
        self.assertTrue(
            wait_for_condition(check_file2_indexed),
            "File not detected after restart with same interval"
        )
        
    def run(self, result=None):
        test_name = self.id().split('.')[-1]
        print(f"\n{Colors.BOLD}Running test:{Colors.END} {test_name}")
        
        output = StringIO()
        success = True
        error = None
        
        try:
            super().run(result)
            success = not bool(result.failures) and not bool(result.errors)
        except Exception as e:
            success = False
            error = str(e)
            
        duration = time.time() - self.start_time
        status = f"{Colors.GREEN}✓ PASSED{Colors.END}" if success else f"{Colors.RED}✗ FAILED{Colors.END}"
        print(f"{status} ({duration:.2f}s)")
        
        self.test_output.add_test_result(
            test_name=test_name,
            success=success,
            duration=duration,
            output=output.getvalue(),
            error=error
        )
        
    @classmethod
    def tearDownClass(cls):
        # Generate reports
        cls.test_output.generate_pdf_report()
        cls.test_output.generate_json_report()
        
        # Print summary
        print("\n" + "="*70)
        print(f"{Colors.BOLD}Test Suite Summary:{Colors.END}")
        print("-"*70)
        
        for test in cls.test_output.test_results['tests']:
            status = f"{Colors.GREEN}✓{Colors.END}" if test['success'] else f"{Colors.RED}✗{Colors.END}"
            print(f"{status} {test['name']:<50} {test['duration']:.2f}s")
            
        print("-"*70)
        results = cls.test_output.test_results
        success_rate = (results['passed'] / results['total']) * 100
        print(f"{Colors.BOLD}Results:{Colors.END}")
        print(f"Total Tests: {results['total']}")
        print(f"Passed: {Colors.GREEN}{results['passed']}{Colors.END}")
        print(f"Failed: {Colors.RED}{results['failed']}{Colors.END}")
        print(f"Success Rate: {Colors.BOLD}{success_rate:.1f}%{Colors.END}")
        total_duration = sum(t['duration'] for t in results['tests'])
        print(f"Total Duration: {total_duration:.2f}s")
        print("="*70)

if __name__ == '__main__':
    unittest.main(verbosity=0)
