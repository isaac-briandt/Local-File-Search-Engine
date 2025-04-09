#!/usr/bin/env python3
import json
import os
import hashlib
import time
import shutil
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union

class FileIndexManager:
    def __init__(self, index_path: str = "data/main_index.json"):
        self.index_path = index_path
        self._ensure_data_directory()
        self.index_data = self._load_or_create_index()

    def _ensure_data_directory(self):
        """Ensure the data directory exists"""
        directory = os.path.dirname(self.index_path)
        if directory and not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
                print(f"Created directory: {directory}")
            except OSError as e:
                raise RuntimeError(f"Could not create directory {directory}: {e}")

    def _load_or_create_index(self) -> Dict[str, Any]:
        """Load existing index or create a new one if it doesn't exist."""
        if os.path.exists(self.index_path):
            try:
                with open(self.index_path, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                print(f"Warning: Index file corrupt, creating new index. Error: {e}")
            except OSError as e:
                print(f"Warning: Could not read index file, creating new index. Error: {e}")

        return {
            "files": {},
            "index_meta": {
                "last_updated": datetime.now().isoformat(),
                "version": "1.0",
                "total_files": 0
            }
        }

    def _save_index(self):
        """Save the index to disk atomically."""
        temp_path = f"{self.index_path}.tmp"
        backup_path = f"{self.index_path}.bak"
        
        try:
            # Create backup if original exists
            if os.path.exists(self.index_path):
                try:
                    os.replace(self.index_path, backup_path)
                except OSError as e:
                    print(f"Warning: Could not create backup: {e}")

            # Write to temporary file
            with open(temp_path, 'w') as f:
                json.dump(self.index_data, f, indent=2)

            # Atomic rename
            os.replace(temp_path, self.index_path)

            # Remove backup if everything succeeded
            if os.path.exists(backup_path):
                os.remove(backup_path)
                
        except Exception as e:
            # Try to restore from backup if something went wrong
            if os.path.exists(backup_path):
                try:
                    os.replace(backup_path, self.index_path)
                    print("Restored index from backup after error")
                except OSError:
                    print("Warning: Could not restore from backup")
            raise RuntimeError(f"Failed to save index: {e}")
        finally:
            # Clean up temporary file if it exists
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def save_index_to_report(self, report_dir: str) -> str:
        """
        Save a copy of the current index to the test reports directory.
        Returns the path to the saved index file.
        """
        if not os.path.exists(report_dir):
            os.makedirs(report_dir)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_index_path = os.path.join(report_dir, f"main_index_{timestamp}.json")

        try:
            with open(report_index_path, 'w') as f:
                json.dump(self.index_data, f, indent=2)
            return report_index_path
        except Exception as e:
            print(f"Warning: Could not save index to report directory: {e}")
            return None
            
    def _parse_date(self, date_str: str) -> datetime:
        """Parse a date string into a datetime object."""
        try:
            # Try ISO format first
            return datetime.fromisoformat(date_str)
        except ValueError:
            try:
                # Try common date formats
                formats = [
                    "%Y-%m-%d",
                    "%Y/%m/%d",
                    "%d-%m-%Y",
                    "%d/%m/%Y",
                    "%Y-%m-%d %H:%M:%S",
                    "%Y/%m/%d %H:%M:%S"
                ]
                for fmt in formats:
                    try:
                        return datetime.strptime(date_str, fmt)
                    except ValueError:
                        continue
                raise ValueError(f"Could not parse date: {date_str}")
            except ValueError as e:
                raise ValueError(f"Invalid date format: {e}")

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate MD5 hash of a file."""
        hasher = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except OSError as e:
            raise RuntimeError(f"Could not calculate hash for {file_path}: {e}")

    def add_file(self, file_path: str) -> bool:
        """Add or update a file in the index."""
        if not os.path.exists(file_path):
            return False

        try:
            stat = os.stat(file_path)
            file_info = {
                "type": os.path.splitext(file_path)[1].lower(),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "checksum": self._calculate_file_hash(file_path),
                "filename": os.path.basename(file_path)
            }

            self.index_data["files"][file_path] = file_info
            self.index_data["index_meta"]["total_files"] = len(self.index_data["files"])
            self.index_data["index_meta"]["last_updated"] = datetime.now().isoformat()
            self._save_index()
            return True
        except Exception as e:
            print(f"Error adding file {file_path}: {e}")
            return False

    def remove_file(self, file_path: str) -> bool:
        """Remove a file from the index."""
        if file_path in self.index_data["files"]:
            try:
                del self.index_data["files"][file_path]
                self.index_data["index_meta"]["total_files"] = len(self.index_data["files"])
                self.index_data["index_meta"]["last_updated"] = datetime.now().isoformat()
                self._save_index()
                return True
            except Exception as e:
                print(f"Error removing file {file_path}: {e}")
                return False
        return False

    def search_by_type(self, file_type: str, sort_by: str = None, sort_order: str = "desc") -> Dict[str, Any]:
        """
        Search for files by type with sorting options.
        
        Args:
            file_type: File extension to search for
            sort_by: Field to sort by ("date", "size", "name")
            sort_order: Sort direction ("asc" or "desc")
        """
        if not file_type.startswith('.'):
            file_type = f'.{file_type}'
        file_type = file_type.lower()
        
        # Get matching files
        results = {
            path: info for path, info in self.index_data["files"].items()
            if info["type"] == file_type
        }

        # Apply sorting
        return self._apply_sorting(results, sort_by, sort_order)

    def search_by_size(self, min_size: int = 0, max_size: Optional[int] = None,
                      sort_by: str = None, sort_order: str = "desc") -> Dict[str, Any]:
        """
        Search for files within a size range with sorting options.
        
        Args:
            min_size: Minimum file size in bytes
            max_size: Maximum file size in bytes (optional)
            sort_by: Field to sort by ("date", "size", "name")
            sort_order: Sort direction ("asc" or "desc")
        """
        # Get files within size range
        results = {
            path: info for path, info in self.index_data["files"].items()
            if min_size <= info["size"] and (max_size is None or info["size"] <= max_size)
        }

        # Apply sorting
        return self._apply_sorting(results, sort_by, sort_order)

    def search_by_date(self, start_date: Optional[Union[str, datetime]] = None,
                      end_date: Optional[Union[str, datetime]] = None,
                      sort_by: str = None, sort_order: str = "desc") -> Dict[str, Any]:
        """
        Search for files modified within a date range with sorting options.
        
        Args:
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            sort_by: Field to sort by ("date", "size", "name")
            sort_order: Sort direction ("asc" or "desc")
        """
        try:
            # Convert string dates to datetime if necessary
            if isinstance(start_date, str):
                start_date = self._parse_date(start_date)
            if isinstance(end_date, str):
                end_date = self._parse_date(end_date)
                
            # Convert to ISO format strings for comparison
            start_iso = start_date.isoformat() if start_date else None
            end_iso = end_date.isoformat() if end_date else None
            
            # Get files within date range
            results = {
                path: info for path, info in self.index_data["files"].items()
                if (start_iso is None or info["modified"] >= start_iso) and
                   (end_iso is None or info["modified"] <= end_iso)
            }

            # Apply sorting
            return self._apply_sorting(results, sort_by, sort_order)
            
        except ValueError as e:
            raise ValueError(f"Date format error: {e}")

    def _apply_sorting(self, results: Dict[str, Any], sort_by: str = None, sort_order: str = "desc") -> Dict[str, Any]:
        """Sort search results by specified criteria."""
        if not sort_by or not results:
            return results

        reverse = sort_order.lower() == "desc"
        
        if sort_by == "date":
            # Sort by modification date
            sorted_items = sorted(
                results.items(),
                key=lambda x: x[1]["modified"],
                reverse=reverse
            )
        elif sort_by == "size":
            # Sort by file size
            sorted_items = sorted(
                results.items(),
                key=lambda x: x[1]["size"],
                reverse=reverse
            )
        elif sort_by == "name":
            # Sort by filename
            sorted_items = sorted(
                results.items(),
                key=lambda x: x[1]["filename"].lower(),
                reverse=reverse
            )
        else:
            # Default to no sorting
            return results

        return dict(sorted_items)

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics including file type distribution."""
        files = self.index_data["files"]
        total_size = sum(info["size"] for info in files.values())
        
        # Count file types
        type_counter = {}
        for info in files.values():
            ext = info["type"]
            type_counter[ext] = type_counter.get(ext, 0) + 1
        
        # Calculate average file size
        avg_size = total_size / len(files) if files else 0
        
        return {
            "total_files": len(files),
            "total_size": total_size,
            "average_size": int(avg_size),
            "type_distribution": dict(sorted(type_counter.items())),
            "last_updated": self.index_data["index_meta"]["last_updated"]
        }

if __name__ == "__main__":
    # Example usage
    index = FileIndexManager()
    print("File Index Manager initialized")
    