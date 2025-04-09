#!/usr/bin/env python3
import argparse
import os
import sys
import shutil
from datetime import datetime
from index_manager import FileIndexManager

def format_size(size_in_bytes):
    """Convert size in bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f} TB"

def format_date(date_str):
    """Format ISO date string to a more readable format"""
    try:
        date = datetime.fromisoformat(date_str)
        return date.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return date_str

def clear_test_reports():
    """Clear all test reports from the test_reports directory"""
    report_dir = "test_reports"
    if os.path.exists(report_dir):
        try:
            shutil.rmtree(report_dir)
            print(f"Successfully cleared all test reports from {report_dir}/")
            return True
        except Exception as e:
            print(f"Error clearing test reports: {e}")
            return False
    else:
        print(f"No test reports directory found at {report_dir}/")
        return True

def main():
    parser = argparse.ArgumentParser(description='File Index Manager CLI')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Add file command
    add_parser = subparsers.add_parser('add', help='Add file to index')
    add_parser.add_argument('path', help='Path to file')

    # Remove file command
    remove_parser = subparsers.add_parser('remove', help='Remove file from index')
    remove_parser.add_argument('path', help='Path to file')

    # Search by type command
    type_parser = subparsers.add_parser('search-type', help='Search files by type')
    type_parser.add_argument('type', help='File type (extension)')
    type_parser.add_argument('--sort-by', choices=['date', 'size', 'name'],
                           help='Sort results by field')
    type_parser.add_argument('--sort-order', choices=['asc', 'desc'], default='desc',
                           help='Sort order (default: desc)')

    # Search by size command
    size_parser = subparsers.add_parser('search-size', help='Search files by size range')
    size_parser.add_argument('min_size', type=int, help='Minimum size in bytes')
    size_parser.add_argument('--max-size', type=int, help='Maximum size in bytes')
    size_parser.add_argument('--sort-by', choices=['date', 'size', 'name'],
                           help='Sort results by field')
    size_parser.add_argument('--sort-order', choices=['asc', 'desc'], default='desc',
                           help='Sort order (default: desc)')

    # Search by date command
    date_parser = subparsers.add_parser('search-date', help='Search files by modification date range')
    date_parser.add_argument('--start', help='Start date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)')
    date_parser.add_argument('--end', help='End date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)')
    date_parser.add_argument('--sort-by', choices=['date', 'size', 'name'],
                           help='Sort results by field')
    date_parser.add_argument('--sort-order', choices=['asc', 'desc'], default='desc',
                           help='Sort order (default: desc)')

    # Stats command
    subparsers.add_parser('stats', help='Show index statistics')

    # Clear test reports command
    clear_parser = subparsers.add_parser('clear-reports', 
                                        help='Clear all test reports from test_reports directory')
    clear_parser.add_argument('--force', action='store_true',
                             help='Clear without confirmation')

    args = parser.parse_args()
    exit_code = 0

    try:
        if args.command == 'clear-reports':
            if not args.force:
                response = input("Are you sure you want to clear all test reports? [y/N] ").lower()
                if response != 'y':
                    print("Operation cancelled.")
                    return
            if clear_test_reports():
                print("Test reports cleared successfully.")
            else:
                print("Failed to clear test reports.")
                exit_code = 1

        elif args.command == 'add':
            index = FileIndexManager()
            if index.add_file(args.path):
                print(f"Added file: {args.path}")
            else:
                print(f"Error: Could not add file {args.path}")
                exit_code = 1

        elif args.command == 'remove':
            index = FileIndexManager()
            if index.remove_file(args.path):
                print(f"Removed file: {args.path}")
            else:
                print(f"Error: File not found in index {args.path}")
                exit_code = 1

        elif args.command == 'search-type':
            index = FileIndexManager()
            results = index.search_by_type(
                args.type,
                sort_by=args.sort_by,
                sort_order=args.sort_order
            )
            print(f"\nFound {len(results)} files of type {args.type}:")
            for path, info in results.items():
                print(f"\nFile: {path}")
                print(f"  Size: {format_size(info['size'])}")
                print(f"  Modified: {format_date(info['modified'])}")

        elif args.command == 'search-size':
            index = FileIndexManager()
            results = index.search_by_size(
                args.min_size,
                args.max_size,
                sort_by=args.sort_by,
                sort_order=args.sort_order
            )
            size_range = f"{format_size(args.min_size)}-{format_size(args.max_size) if args.max_size else 'unlimited'}"
            print(f"\nFound {len(results)} files in size range {size_range}:")
            for path, info in results.items():
                print(f"\nFile: {path}")
                print(f"  Type: {info['type']}")
                print(f"  Size: {format_size(info['size'])}")
                print(f"  Modified: {format_date(info['modified'])}")

        elif args.command == 'search-date':
            index = FileIndexManager()
            if not args.start and not args.end:
                print("Error: Please specify at least one of --start or --end dates")
                exit_code = 1
            else:
                try:
                    results = index.search_by_date(
                        args.start,
                        args.end,
                        sort_by=args.sort_by,
                        sort_order=args.sort_order
                    )
                    date_range = f"from {args.start if args.start else 'any'} to {args.end if args.end else 'any'}"
                    print(f"\nFound {len(results)} files modified {date_range}:")
                    for path, info in results.items():
                        print(f"\nFile: {path}")
                        print(f"  Type: {info['type']}")
                        print(f"  Size: {format_size(info['size'])}")
                        print(f"  Modified: {format_date(info['modified'])}")
                except ValueError as e:
                    print(f"Error: {str(e)}")
                    exit_code = 1

        elif args.command == 'stats':
            index = FileIndexManager()
            stats = index.get_stats()
            print("\nIndex Statistics:")
            print(f"Total Files: {stats['total_files']}")
            print(f"Total Size: {format_size(stats['total_size'])}")
            print(f"Average File Size: {format_size(stats['average_size'])}")
            print("\nFile Type Distribution:")
            if stats['type_distribution']:
                for ext, count in stats['type_distribution'].items():
                    print(f"  {ext or 'no extension'}: {count} files")
            else:
                print("  No files indexed")
            print(f"\nLast Updated: {format_date(stats['last_updated'])}")

        else:
            parser.print_help()
            exit_code = 1

    except Exception as e:
        print(f"Error: {str(e)}")
        exit_code = 1

    sys.exit(exit_code)

if __name__ == "__main__":
    main()