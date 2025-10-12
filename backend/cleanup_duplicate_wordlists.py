#!/usr/bin/env python
"""
Cleanup script for duplicate global wordlists.

Run this script to remove duplicate default wordlists that may have been
created due to race conditions during multi-worker startup.

Usage:
    python cleanup_duplicate_wordlists.py
"""
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.services.global_wordlist_manager import GlobalWordlistManager
from app.models import WordList


def main():
    """Clean up duplicate default wordlists."""
    print("=" * 70)
    print("Global Wordlist Cleanup Utility")
    print("=" * 70)
    print()
    
    app = create_app()
    
    with app.app_context():
        # Show current state
        print("Current state:")
        print("-" * 70)
        
        all_defaults = WordList.query.filter_by(is_global_default=True).all()
        print(f"Found {len(all_defaults)} wordlist(s) marked as default:")
        for wl in all_defaults:
            print(f"  - ID {wl.id}: {wl.name} ({wl.normalized_count} words)")
        print()
        
        if len(all_defaults) <= 1:
            print("✓ No duplicates found. Everything looks good!")
            return
        
        # Confirm cleanup
        print("⚠️  Multiple default wordlists detected!")
        print()
        print(f"This script will:")
        print(f"  1. Keep the oldest wordlist (ID {all_defaults[0].id})")
        print(f"  2. Unmark {len(all_defaults) - 1} duplicate(s) as non-default")
        print()
        
        response = input("Proceed with cleanup? (yes/no): ").strip().lower()
        
        if response not in ['yes', 'y']:
            print("Cleanup cancelled.")
            return
        
        # Run cleanup
        print()
        print("Running cleanup...")
        result = GlobalWordlistManager.cleanup_duplicate_defaults()
        
        print()
        print("Cleanup complete!")
        print("-" * 70)
        print(f"✓ Kept default: {result['kept_wordlist_name']} (ID: {result['kept_wordlist_id']})")
        print(f"✓ Unmarked {result['duplicates_removed']} duplicate(s)")
        
        if result['duplicate_ids']:
            print(f"  Duplicate IDs: {', '.join(map(str, result['duplicate_ids']))}")
        
        print()
        print("You can now safely delete the unmarked wordlists if desired:")
        for wl_id in result['duplicate_ids']:
            print(f"  DELETE FROM word_lists WHERE id = {wl_id};")
        print()


if __name__ == '__main__':
    main()
