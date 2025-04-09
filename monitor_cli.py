#!/usr/bin/env python3

import argparse
import os
import sys
import time
import signal
import logging
import json
from pathlib import Path
from typing import Set, List
from datetime import datetime
from file_monitor import FileMonitor
from index_manager import FileIndexManager

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

class MonitorCLI:
    def __init__(self):
        self.config_file = "monitor_config.json"
        self.index_manager = FileIndexManager()
        self.monitor = None
        self.load_config()
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
    def load_config(self) -> dict:
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
            except json.JSONDecodeError:
                self.config = self.get_default_config()
        else:
            self.config = self.get_default_config()
        return self.config
    
    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
            
    def get_default_config(self) -> dict:
        return {
            'paths': [],
            'extensions': ['.txt', '.pdf', '.doc', '.docx'],
            'interval': 1.0,  # Default check interval in seconds
            'recursive': True,
            'last_run': None
        }
        
    def validate_paths(self, paths: List[str]) -> List[str]:
        invalid_paths = []
        for path in paths:
            if not os.path.exists(path):
                invalid_paths.append(path)
        return invalid_paths
        
    def format_paths(self, paths: List[str]) -> str:
        return '\n  '.join(paths) if paths else "No paths configured"
        
    def format_extensions(self, extensions: Set[str]) -> str:
        return ', '.join(sorted(extensions)) if extensions else "All extensions"
        
    def start_monitoring(self, paths: List[str] = None, extensions: Set[str] = None, interval: float = None):
        if self.monitor and self.monitor.is_running():
            print(f"{Colors.YELLOW}Monitor is already running{Colors.END}")
            return False
            
        monitor_paths = paths or self.config['paths']
        monitor_extensions = set(extensions or self.config['extensions'])
        monitor_interval = interval or self.config['interval']
        
        if not monitor_paths:
            print(f"{Colors.RED}Error: No paths configured for monitoring{Colors.END}")
            return False
            
        invalid_paths = self.validate_paths(monitor_paths)
        if invalid_paths:
            print(f"{Colors.RED}Error: The following paths do not exist:{Colors.END}")
            print('  ' + '\n  '.join(invalid_paths))
            return False
            
        try:
            self.monitor = FileMonitor(
                index_manager=self.index_manager,
                paths_to_monitor=monitor_paths,
                monitored_extensions=monitor_extensions,
                interval=monitor_interval
            )
            
            if self.monitor.start():
                print(f"{Colors.GREEN}File monitor started successfully{Colors.END}")
                print(f"\nMonitoring paths:")
                print(f"  {self.format_paths(monitor_paths)}")
                print(f"\nMonitored extensions: {self.format_extensions(monitor_extensions)}")
                print(f"Check interval: {monitor_interval:.1f} seconds")
                
                self.config['paths'] = monitor_paths
                self.config['extensions'] = list(monitor_extensions)
                self.config['interval'] = monitor_interval
                self.config['last_run'] = datetime.now().isoformat()
                self.save_config()
                return True
            else:
                print(f"{Colors.RED}Failed to start file monitor{Colors.END}")
                return False
                
        except Exception as e:
            print(f"{Colors.RED}Error starting monitor: {str(e)}{Colors.END}")
            return False
            
    def stop_monitoring(self):
        if not self.monitor or not self.monitor.is_running():
            print(f"{Colors.YELLOW}Monitor is not running{Colors.END}")
            return False
            
        try:
            if self.monitor.stop():
                print(f"{Colors.GREEN}File monitor stopped successfully{Colors.END}")
                return True
            else:
                print(f"{Colors.RED}Failed to stop file monitor{Colors.END}")
                return False
                
        except Exception as e:
            print(f"{Colors.RED}Error stopping monitor: {str(e)}{Colors.END}")
            return False
            
    def set_interval(self, interval: float):
        """Set the monitoring check interval"""
        try:
            interval = float(interval)
            if interval < 0.1:
                print(f"{Colors.RED}Error: Interval must be at least 0.1 seconds{Colors.END}")
                return False
                
            self.config['interval'] = interval
            self.save_config()
            
            if self.monitor and self.monitor.is_running():
                if self.monitor.set_interval(interval):
                    print(f"{Colors.GREEN}Monitor interval updated to {interval:.1f} seconds{Colors.END}")
                    return True
                else:
                    print(f"{Colors.RED}Failed to update monitor interval{Colors.END}")
                    return False
            else:
                print(f"{Colors.GREEN}Configuration updated. New interval will be used when monitor is started.{Colors.END}")
                return True
                
        except ValueError:
            print(f"{Colors.RED}Error: Invalid interval value{Colors.END}")
            return False
            
    def show_status(self):
        print(f"\n{Colors.BOLD}File Monitor Status{Colors.END}")
        print("-" * 50)
        
        status = "Running" if (self.monitor and self.monitor.is_running()) else "Stopped"
        status_color = Colors.GREEN if status == "Running" else Colors.RED
        print(f"Status: {status_color}{status}{Colors.END}")
        
        print(f"\n{Colors.BOLD}Configuration:{Colors.END}")
        print(f"Monitored Paths:")
        print(f"  {self.format_paths(self.config['paths'])}")
        print(f"\nMonitored Extensions: {self.format_extensions(set(self.config['extensions']))}")
        print(f"Check Interval: {self.config['interval']:.1f} seconds")
        
        if self.config['last_run']:
            last_run = datetime.fromisoformat(self.config['last_run'])
            print(f"\nLast Started: {last_run.strftime('%Y-%m-%d %H:%M:%S')}")
            
        stats = self.index_manager.get_stats()
        print(f"\n{Colors.BOLD}Index Statistics:{Colors.END}")
        print(f"Total Files: {stats['total_files']}")
        print(f"Total Size: {self.format_size(stats['total_size'])}")
        if stats['type_distribution']:
            print("\nFile Type Distribution:")
            for ext, count in stats['type_distribution'].items():
                print(f"  {ext or 'no extension'}: {count} files")
                
        print("-" * 50)
        
    def format_size(self, size_in_bytes: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_in_bytes < 1024.0:
                return f"{size_in_bytes:.2f} {unit}"
            size_in_bytes /= 1024.0
        return f"{size_in_bytes:.2f} TB"

def signal_handler(signum, frame):
    print("\nShutting down...")
    if cli.monitor and cli.monitor.is_running():
        cli.stop_monitoring()
    sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description='File Monitor CLI')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Start command
    start_parser = subparsers.add_parser('start', help='Start file monitoring')
    start_parser.add_argument('--paths', nargs='+', help='Paths to monitor')
    start_parser.add_argument('--extensions', nargs='+', help='File extensions to monitor')
    start_parser.add_argument('--interval', type=float, help='Check interval in seconds')
    
    # Stop command
    subparsers.add_parser('stop', help='Stop file monitoring')
    
    # Status command
    subparsers.add_parser('status', help='Show monitoring status')
    
    # Configure command
    config_parser = subparsers.add_parser('config', help='Configure monitoring settings')
    config_parser.add_argument('--add-paths', nargs='+', help='Add paths to monitor')
    config_parser.add_argument('--remove-paths', nargs='+', help='Remove paths from monitoring')
    config_parser.add_argument('--add-extensions', nargs='+', help='Add extensions to monitor')
    config_parser.add_argument('--remove-extensions', nargs='+', help='Remove extensions from monitoring')
    config_parser.add_argument('--interval', type=float, help='Set check interval in seconds')
    
    args = parser.parse_args()
    
    if args.command == 'start':
        paths = args.paths or cli.config['paths']
        extensions = set(args.extensions or cli.config['extensions'])
        interval = args.interval or cli.config['interval']
        cli.start_monitoring(paths, extensions, interval)
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
            cli.stop_monitoring()
            
    elif args.command == 'stop':
        cli.stop_monitoring()
        
    elif args.command == 'status':
        cli.show_status()
        
    elif args.command == 'config':
        config_changed = False
        
        if args.interval is not None:
            if cli.set_interval(args.interval):
                config_changed = True
        
        if args.add_paths:
            cli.config['paths'].extend(args.add_paths)
            cli.config['paths'] = list(set(cli.config['paths']))
            config_changed = True
            
        if args.remove_paths:
            cli.config['paths'] = [p for p in cli.config['paths'] if p not in args.remove_paths]
            config_changed = True
            
        if args.add_extensions:
            exts = [ext if ext.startswith('.') else f'.{ext}' for ext in args.add_extensions]
            cli.config['extensions'].extend(exts)
            cli.config['extensions'] = list(set(cli.config['extensions']))
            config_changed = True
            
        if args.remove_extensions:
            exts = [ext if ext.startswith('.') else f'.{ext}' for ext in args.remove_extensions]
            cli.config['extensions'] = [e for e in cli.config['extensions'] if e not in exts]
            config_changed = True
            
        if config_changed:
            cli.save_config()
            print(f"{Colors.GREEN}Configuration updated successfully{Colors.END}")
        cli.show_status()
        
    else:
        parser.print_help()

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    cli = MonitorCLI()
    main()
