#!/usr/bin/env python3

import time
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
from typing import Optional, Set
from datetime import datetime
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class IndexFileHandler(FileSystemEventHandler):
    def __init__(self, index_manager, monitored_extensions: Optional[Set[str]] = None):
        self.index_manager = index_manager
        self.monitored_extensions = {ext.lower() if ext.startswith('.') else f'.{ext.lower()}'
                                   for ext in (monitored_extensions or [])}
        self._lock = threading.Lock()
        self._pending_events = {}
        
    def should_process_file(self, path: str) -> bool:
        if not self.monitored_extensions:
            return True
        return Path(path).suffix.lower() in self.monitored_extensions
    
    def _normalize_path(self, path: str) -> str:
        return str(Path(path).resolve())
    
    def _wait_for_file_ready(self, path: str, timeout: float = 2.0) -> bool:
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                if os.path.exists(path):
                    with open(path, 'rb') as f:
                        f.read(1)
                        return True
            except (OSError, IOError):
                pass
            time.sleep(0.1)
        return False
        
    def on_created(self, event):
        if event.is_directory:
            return
            
        path = self._normalize_path(event.src_path)
        if not self.should_process_file(path):
            return
            
        if not self._wait_for_file_ready(path):
            logging.warning(f"File not ready for processing: {path}")
            return
            
        with self._lock:
            try:
                logging.info(f"File created: {path}")
                if os.path.exists(path):
                    success = self.index_manager.add_file(path)
                    if not success:
                        logging.error(f"Failed to add file to index: {path}")
            except Exception as e:
                logging.error(f"Error processing created file {path}: {str(e)}")
    
    def on_modified(self, event):
        if event.is_directory:
            return
            
        path = self._normalize_path(event.src_path)
        if not self.should_process_file(path):
            return
            
        current_time = time.time()
        if path in self._pending_events:
            if current_time - self._pending_events[path] < 1.0:
                return
        self._pending_events[path] = current_time
        
        if not self._wait_for_file_ready(path):
            return
            
        with self._lock:
            try:
                logging.info(f"File modified: {path}")
                if os.path.exists(path):
                    self.index_manager.remove_file(path)
                    success = self.index_manager.add_file(path)
                    if not success:
                        logging.error(f"Failed to update file in index: {path}")
            except Exception as e:
                logging.error(f"Error processing modified file {path}: {str(e)}")
        
        if path in self._pending_events:
            del self._pending_events[path]
    
    def on_deleted(self, event):
        if event.is_directory:
            return
            
        path = self._normalize_path(event.src_path)
        if not self.should_process_file(path):
            return
            
        with self._lock:
            try:
                logging.info(f"File deleted: {path}")
                success = self.index_manager.remove_file(path)
                if not success:
                    logging.error(f"Failed to remove file from index: {path}")
            except Exception as e:
                logging.error(f"Error processing deleted file {path}: {str(e)}")
    
    def on_moved(self, event):
        if event.is_directory:
            return
            
        src_path = self._normalize_path(event.src_path)
        dest_path = self._normalize_path(event.dest_path)
        
        with self._lock:
            try:
                logging.info(f"File moved/renamed: {src_path} -> {dest_path}")
                
                if self.should_process_file(src_path):
                    self.index_manager.remove_file(src_path)
                
                if self.should_process_file(dest_path):
                    if self._wait_for_file_ready(dest_path):
                        success = self.index_manager.add_file(dest_path)
                        if not success:
                            logging.error(f"Failed to add moved file to index: {dest_path}")
            except Exception as e:
                logging.error(f"Error processing moved file {src_path} -> {dest_path}: {str(e)}")

class FileMonitor:
    def __init__(self, index_manager, paths_to_monitor, monitored_extensions=None, interval=1.0):
        """
        Initialize the file monitor
        
        Args:
            index_manager: Instance of FileIndexManager
            paths_to_monitor: List of paths to monitor for changes
            monitored_extensions: Optional set of file extensions to monitor (e.g., {'.txt', '.pdf'})
            interval: Time interval in seconds between file system checks (default: 1.0)
        """
        self.index_manager = index_manager
        self.paths_to_monitor = [Path(p).resolve() for p in paths_to_monitor]
        self.monitored_extensions = set(monitored_extensions) if monitored_extensions else set()
        self.interval = max(0.1, float(interval))  # Minimum interval of 0.1 seconds
        self.event_handler = IndexFileHandler(index_manager, self.monitored_extensions)
        self._observer = None
        self._started = False
        
    def _create_observer(self):
        if self._observer is not None:
            try:
                self._observer.stop()
                self._observer.join()
            except Exception:
                pass
        self._observer = Observer(timeout=self.interval)
        
    def validate_paths(self):
        invalid_paths = []
        for path in self.paths_to_monitor:
            if not path.exists():
                invalid_paths.append(path)
        return invalid_paths
        
    def start(self):
        if self._started:
            logging.warning("File monitor is already running")
            return False
            
        invalid_paths = self.validate_paths()
        if invalid_paths:
            paths_str = '\n  '.join(str(p) for p in invalid_paths)
            logging.error(f"The following paths do not exist:\n  {paths_str}")
            return False
            
        try:
            self._create_observer()
            
            for path in self.paths_to_monitor:
                logging.info(f"Starting monitoring for path: {path}")
                self._observer.schedule(self.event_handler, str(path), recursive=True)
            
            self._observer.start()
            self._started = True
            logging.info(f"File monitor started successfully (check interval: {self.interval:.1f}s)")
            time.sleep(0.1)
            return True
            
        except Exception as e:
            logging.error(f"Failed to start file monitor: {str(e)}")
            self._started = False
            return False
        
    def stop(self):
        if not self._started:
            logging.warning("File monitor is not running")
            return False
            
        try:
            self._observer.stop()
            self._observer.join()
            self._started = False
            logging.info("File monitor stopped successfully")
            return True
            
        except Exception as e:
            logging.error(f"Failed to stop file monitor: {str(e)}")
            return False
        
    def is_running(self):
        return self._started
    
    def get_interval(self):
        """Get the current check interval"""
        return self.interval
    
    def set_interval(self, interval: float):
        """
        Set a new check interval
        
        Args:
            interval: Time interval in seconds between file system checks
        
        Returns:
            bool: True if interval was changed successfully
        """
        try:
            new_interval = max(0.1, float(interval))
            if new_interval == self.interval:
                return True
                
            # Store the new interval
            self.interval = new_interval
            
            # Restart the observer if running
            if self.is_running():
                self.stop()
                return self.start()
            return True
            
        except Exception as e:
            logging.error(f"Failed to set interval: {str(e)}")
            return False

def create_test_file_monitor(index_manager, test_dir, interval=1.0):
    monitor = FileMonitor(
        index_manager=index_manager,
        paths_to_monitor=[test_dir],
        monitored_extensions={'.txt', '.pdf', '.py', '.jpg'},
        interval=interval
    )
    return monitor

if __name__ == "__main__":
    from index_manager import FileIndexManager
    
    try:
        index_manager = FileIndexManager()
        monitor = FileMonitor(
            index_manager=index_manager,
            paths_to_monitor=["./test_data"],
            monitored_extensions={'.txt', '.pdf', '.doc', '.docx'},
            interval=1.0
        )
        
        if monitor.start():
            print("Monitor started successfully. Press Ctrl+C to stop.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping file monitor...")
                monitor.stop()
                print("Monitor stopped successfully.")
        else:
            print("Failed to start monitor.")
            
    except Exception as e:
        print(f"Error: {str(e)}")
