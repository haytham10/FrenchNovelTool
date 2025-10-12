"""
Global Wordlist Manager - Utility for managing global wordlists.

This module provides a centralized way to manage global wordlists with
proper versioning, automatic seeding, and administrative capabilities.
"""
import logging
import time
from typing import Optional, List, Dict
from pathlib import Path
from sqlalchemy.exc import IntegrityError, OperationalError
from app import db
from app.models import WordList
from app.services.wordlist_service import WordListService

logger = logging.getLogger(__name__)


class GlobalWordlistManager:
    """Manages global wordlists with versioning and automatic seeding."""
    
    # Configuration
    DEFAULT_WORDLIST_NAME = "French 2K"
    DEFAULT_VERSION = "1.0.0"
    # Use absolute path from project root
    WORDLIST_DATA_DIR = Path(__file__).parent.parent.parent / 'data' / 'wordlists'
    
    @staticmethod
    def ensure_global_default_exists() -> WordList:
        """
        Ensure that a global default wordlist exists.
        If none exists, create one from the default data file.
        
        This method is idempotent and safe to call on every app startup.
        Uses PostgreSQL advisory locks to prevent race conditions between workers.
        
        Returns:
            WordList: The global default wordlist
        """
        # First quick check without lock
        existing = WordList.query.filter_by(is_global_default=True).first()
        
        if existing:
            logger.info(f"Global default wordlist exists: {existing.name} (ID: {existing.id})")
            return existing
        
        logger.warning("No global default wordlist found. Attempting to create one...")
        
        # Use PostgreSQL advisory lock to ensure only one worker creates the wordlist
        # Lock ID: arbitrary number for global wordlist initialization
        ADVISORY_LOCK_ID = 123456789
        
        try:
            # Try to acquire advisory lock (non-blocking)
            # Returns True if lock acquired, False if another worker holds it
            lock_acquired = db.session.execute(
                db.text("SELECT pg_try_advisory_lock(:lock_id)"),
                {"lock_id": ADVISORY_LOCK_ID}
            ).scalar()
            
            if not lock_acquired:
                # Another worker is creating the wordlist
                logger.info("Another worker is creating the global wordlist. Waiting...")
                
                # Wait for the other worker to finish (blocking lock)
                db.session.execute(
                    db.text("SELECT pg_advisory_lock(:lock_id)"),
                    {"lock_id": ADVISORY_LOCK_ID}
                )
                
                # Lock acquired - other worker finished. Check if wordlist exists now.
                existing = WordList.query.filter_by(is_global_default=True).first()
                
                # Release lock
                db.session.execute(
                    db.text("SELECT pg_advisory_unlock(:lock_id)"),
                    {"lock_id": ADVISORY_LOCK_ID}
                )
                
                if existing:
                    logger.info(f"Global wordlist created by another worker: {existing.name} (ID: {existing.id})")
                    return existing
                else:
                    logger.error("Lock released but no global wordlist found. This shouldn't happen.")
                    raise RuntimeError("Global wordlist initialization failed (inconsistent state)")
            
            # Lock acquired - this worker will create the wordlist
            try:
                # Double-check (paranoid mode)
                existing = WordList.query.filter_by(is_global_default=True).first()
                if existing:
                    logger.info(f"Global default found during locked section: {existing.name} (ID: {existing.id})")
                    return existing
                
                # Create from default data file
                wordlist = GlobalWordlistManager.create_from_file(
                    filepath=GlobalWordlistManager.WORDLIST_DATA_DIR / 'french_2k.txt',
                    name=f"{GlobalWordlistManager.DEFAULT_WORDLIST_NAME} (v{GlobalWordlistManager.DEFAULT_VERSION})",
                    set_as_default=True
                )
                
                logger.info(f"Created global default wordlist: {wordlist.name} (ID: {wordlist.id})")
                return wordlist
                
            finally:
                # Always release the lock
                db.session.execute(
                    db.text("SELECT pg_advisory_unlock(:lock_id)"),
                    {"lock_id": ADVISORY_LOCK_ID}
                )
                
        except Exception as e:
            logger.error(f"Error during global wordlist initialization: {e}")
            
            # Check one more time if it exists (in case of race condition)
            existing = WordList.query.filter_by(is_global_default=True).first()
            if existing:
                logger.info(f"Found global default after error: {existing.name} (ID: {existing.id})")
                return existing
            
            raise
    
    @staticmethod
    def create_from_file(
        filepath: Path,
        name: str,
        set_as_default: bool = False,
        version: Optional[str] = None
    ) -> WordList:
        """
        Create a global wordlist from a file.
        
        Args:
            filepath: Path to the wordlist file
            name: Name for the wordlist
            set_as_default: Whether to set this as the global default
            version: Optional version string
            
        Returns:
            WordList: The created wordlist
        """
        if not filepath.exists():
            raise FileNotFoundError(f"Wordlist file not found: {filepath}")
        
        # Load words from file
        words = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                words.append(line)
        
        if not words:
            raise ValueError(f"No words found in file: {filepath}")
        
        logger.info(f"Loaded {len(words)} words from {filepath}")
        
        # If setting as default, unmark any existing defaults
        if set_as_default:
            existing_default = WordList.query.filter_by(is_global_default=True).first()
            if existing_default:
                logger.info(f"Unmarking existing default: {existing_default.name}")
                existing_default.is_global_default = False
        
        # Create wordlist
        wordlist_service = WordListService()
        wordlist, ingestion_report = wordlist_service.ingest_word_list(
            words=words,
            name=name,
            owner_user_id=None,  # Global - no owner
            source_type='file',
            source_ref=str(filepath),
            fold_diacritics=True
        )
        
        # Set as default if requested
        if set_as_default:
            wordlist.is_global_default = True
        
        db.session.commit()
        
        logger.info(
            f"Created global wordlist '{name}': "
            f"{ingestion_report['normalized_count']} normalized words "
            f"from {ingestion_report['original_count']} original words"
        )
        
        return wordlist
    
    @staticmethod
    def get_global_default() -> Optional[WordList]:
        """
        Get the current global default wordlist.
        
        Returns:
            WordList or None if no global default exists
        """
        return WordList.query.filter_by(is_global_default=True).first()
    
    @staticmethod
    def set_global_default(wordlist_id: int) -> WordList:
        """
        Set a wordlist as the global default.
        
        Args:
            wordlist_id: ID of the wordlist to set as default
            
        Returns:
            WordList: The newly set default wordlist
        """
        # Get the wordlist
        wordlist = db.session.get(WordList, wordlist_id)
        if not wordlist:
            raise ValueError(f"Wordlist not found: {wordlist_id}")
        
        # Must be a global wordlist (no owner)
        if wordlist.owner_user_id is not None:
            raise ValueError("Only global wordlists (owner_user_id=None) can be set as default")
        
        # Unmark existing default
        existing_default = WordList.query.filter_by(is_global_default=True).first()
        if existing_default and existing_default.id != wordlist_id:
            logger.info(f"Unmarking existing default: {existing_default.name}")
            existing_default.is_global_default = False
        
        # Set new default
        wordlist.is_global_default = True
        db.session.commit()
        
        logger.info(f"Set global default wordlist: {wordlist.name} (ID: {wordlist.id})")
        return wordlist
    
    @staticmethod
    def list_global_wordlists() -> List[WordList]:
        """
        List all global wordlists (those with no owner).
        
        Returns:
            List of global WordList objects
        """
        return WordList.query.filter_by(owner_user_id=None).order_by(
            WordList.is_global_default.desc(),
            WordList.created_at.desc()
        ).all()
    
    @staticmethod
    def get_stats() -> Dict:
        """
        Get statistics about global wordlists.
        
        Returns:
            Dict with statistics
        """
        global_wordlists = GlobalWordlistManager.list_global_wordlists()
        default = GlobalWordlistManager.get_global_default()
        
        return {
            'total_global_wordlists': len(global_wordlists),
            'has_default': default is not None,
            'default_wordlist': {
                'id': default.id,
                'name': default.name,
                'normalized_count': default.normalized_count
            } if default else None,
            'all_global_wordlists': [
                {
                    'id': wl.id,
                    'name': wl.name,
                    'normalized_count': wl.normalized_count,
                    'is_default': wl.is_global_default
                }
                for wl in global_wordlists
            ]
        }
    
    @staticmethod
    def cleanup_duplicate_defaults() -> Dict:
        """
        Clean up duplicate default wordlists (emergency utility).
        
        This can happen if workers raced during initialization before the
        advisory lock fix was implemented.
        
        Keeps the oldest default and unmarks/deletes duplicates.
        
        Returns:
            Dict with cleanup statistics
        """
        # Find all wordlists marked as default
        defaults = WordList.query.filter_by(is_global_default=True).order_by(
            WordList.id.asc()  # Oldest first
        ).all()
        
        if len(defaults) <= 1:
            logger.info(f"No duplicate defaults found ({len(defaults)} default wordlist)")
            return {
                'duplicates_found': False,
                'duplicates_removed': 0,
                'kept_wordlist_id': defaults[0].id if defaults else None
            }
        
        logger.warning(f"Found {len(defaults)} duplicate default wordlists. Cleaning up...")
        
        # Keep the first one (oldest)
        kept = defaults[0]
        duplicates = defaults[1:]
        
        # Unmark duplicates
        for duplicate in duplicates:
            logger.info(f"Removing default flag from duplicate: {duplicate.name} (ID: {duplicate.id})")
            duplicate.is_global_default = False
        
        db.session.commit()
        
        result = {
            'duplicates_found': True,
            'duplicates_removed': len(duplicates),
            'kept_wordlist_id': kept.id,
            'kept_wordlist_name': kept.name,
            'duplicate_ids': [d.id for d in duplicates]
        }
        
        logger.info(f"Cleanup complete. Kept {kept.name} (ID: {kept.id}), unmarked {len(duplicates)} duplicates")
        
        return result

