"""Service for managing vocabulary word lists with normalization and ingestion"""
import logging
import re
import unicodedata
from typing import Dict, List, Set, Tuple, Optional
from datetime import datetime
from app import db
from app.models import WordList, CoverageRun, UserSettings
from app.utils.metrics import wordlists_created_total, wordlist_ingestion_errors_total

logger = logging.getLogger(__name__)


class WordListService:
    """Handles word list ingestion, normalization, and storage"""
    
    def __init__(self):
        """Initialize the word list service"""
        pass
    
    @staticmethod
    def normalize_word(word: str, fold_diacritics: bool = True) -> str:
        """
        Normalize a single word to its canonical form.

        Args:
            word: Input word to normalize
            fold_diacritics: Whether to remove diacritics (default True)

        Returns:
            Normalized word key
        """
        if not word:
            return ""

        # Trim whitespace
        word = word.strip()

        # Remove zero-width characters
        word = re.sub(r'[\u200b-\u200f\ufeff]', '', word)

        # Remove surrounding quotes and apostrophes which often appear in spreadsheets
        word = word.strip('"' + "'" + ' ')
        
        # Remove leading numbers and punctuation (e.g. "1. avoir" -> "avoir")
        word = re.sub(r'^\d+[.:\-)]?\s*', '', word)

        # Handle elisions BEFORE removing apostrophes (l', d', j', n', s', t', c', qu')
        # Extract the lexical head after elision
        elision_pattern = r"^(?:l'|d'|j'|n'|s'|t'|c'|qu')\s*(.+)$"
        match = re.match(elision_pattern, word, re.IGNORECASE)
        if match:
            word = match.group(1)
        else:
            # Remove internal apostrophes only if not an elision (aujourd'hui -> aujourdhui)
            word = word.replace("'", "")

        # Unicode casefold for case-insensitive matching
        word = word.casefold()

        # Fold diacritics if requested
        if fold_diacritics:
            # Decompose and remove combining marks
            word = ''.join(
                c for c in unicodedata.normalize('NFD', word)
                if unicodedata.category(c) != 'Mn'
            )

        return word.strip()
    
    @staticmethod
    def split_variants(word: str) -> List[str]:
        """
        Split a word on | and / to get variants.
        Also handles comma-separated variants.
        
        Args:
            word: Input word potentially containing variants (e.g. "Un|Une", "avoir/être")
            
        Returns:
            List of variant words
        """
        # Split on |, /, or comma (with optional spaces)
        variants = re.split(r'\s*[|/,]\s*', word)
        return [v.strip() for v in variants if v.strip()]
    
    @staticmethod
    def extract_head_token(phrase: str) -> str:
        """
        For multi-token entries, extract the head lexical token.
        Default policy: return first token.
        
        Args:
            phrase: Multi-token phrase
            
        Returns:
            Head token
        """
        tokens = phrase.split()
        return tokens[0] if tokens else phrase
    
    def ingest_word_list(
        self,
        words: List[str],
        name: str,
        owner_user_id: Optional[int] = None,
        source_type: str = 'manual',
        source_ref: Optional[str] = None,
        fold_diacritics: bool = True
    ) -> Tuple[WordList, Dict]:
        """
        Ingest a list of words, normalize them, and create a WordList.
        
        Args:
            words: List of raw words from input
            name: Name for the word list
            owner_user_id: User ID of owner (None for global)
            source_type: 'csv', 'google_sheet', or 'manual'
            source_ref: Reference to source (file name, Sheet ID, etc.)
            fold_diacritics: Whether to remove diacritics
            
        Returns:
            Tuple of (WordList object, ingestion_report dict)
        """
        ingestion_report = {
            'original_count': len(words),
            'normalized_count': 0,
            'duplicates': [],
            'multi_token_entries': [],
            'variants_expanded': 0,
            'anomalies': []
        }
        
        normalized_keys: Set[str] = set()
        alias_map: Dict[str, str] = {}  # surface -> normalized_key
        samples: List[str] = []
        
        for idx, raw_word in enumerate(words):
            if not raw_word or not raw_word.strip():
                continue
            
            # Split variants
            variants = self.split_variants(raw_word)
            if len(variants) > 1:
                ingestion_report['variants_expanded'] += len(variants) - 1
            
            for variant in variants:
                # Check for multi-token
                tokens = variant.split()
                if len(tokens) > 1:
                    ingestion_report['multi_token_entries'].append({
                        'original': variant,
                        'head_token': self.extract_head_token(variant)
                    })
                    # Use head token for now
                    variant = self.extract_head_token(variant)
                
                # Normalize
                normalized = self.normalize_word(variant, fold_diacritics=fold_diacritics)
                
                if not normalized:
                    ingestion_report['anomalies'].append({
                        'word': raw_word,
                        'issue': 'empty_after_normalization'
                    })
                    continue
                
                # Check for duplicates
                if normalized in normalized_keys:
                    ingestion_report['duplicates'].append({
                        'word': variant,
                        'normalized': normalized
                    })
                else:
                    normalized_keys.add(normalized)
                
                # Build alias map
                alias_map[variant.casefold()] = normalized
        
        # Store samples (first 20 normalized keys)
        samples = sorted(list(normalized_keys))[:20]
        
        ingestion_report['normalized_count'] = len(normalized_keys)
        
        # Create WordList object with full normalized list
        wordlist = WordList(
            owner_user_id=owner_user_id,
            name=name,
            source_type=source_type,
            source_ref=source_ref,
            normalized_count=len(normalized_keys),
            canonical_samples=samples,
            words_json=sorted(list(normalized_keys)),  # Store full list
            is_global_default=False
        )
        
        db.session.add(wordlist)
        db.session.flush()  # Get the ID without committing
        
        # Update metrics
        wordlists_created_total.labels(source_type=source_type).inc()
        
        logger.info(f"Ingested word list '{name}' with {len(normalized_keys)} normalized words")
        
        return wordlist, ingestion_report
    
    @staticmethod
    def get_user_wordlists(user_id: int, include_global: bool = True) -> List[WordList]:
        """
        Get all word lists accessible to a user.
        
        Args:
            user_id: User ID
            include_global: Whether to include global lists
            
        Returns:
            List of WordList objects
        """
        query = WordListService.get_user_wordlists_query(user_id, include_global)
        return query.all()
    
    @staticmethod
    def get_user_wordlists_query(user_id: int, include_global: bool = True):
        """
        Get query for word lists accessible to a user.
        
        Args:
            user_id: User ID
            include_global: Whether to include global lists
            
        Returns:
            SQLAlchemy query object
        """
        if include_global:
            # Include user's own lists and global lists
            query = WordList.query.filter(
                db.or_(
                    WordList.owner_user_id == user_id,
                    WordList.owner_user_id.is_(None)
                )
            )
        else:
            # Only user's own lists
            query = WordList.query.filter_by(owner_user_id=user_id)
        
        return query.order_by(WordList.is_global_default.desc(), WordList.created_at.desc())
    
    @staticmethod
    def get_global_default_wordlist() -> Optional[WordList]:
        """Get the global default word list."""
        return WordList.query.filter_by(is_global_default=True).first()
    
    def refresh_wordlist_from_source(self, wordlist: WordList, user=None, force: bool = False) -> Dict:
        """
        Refresh/populate words_json for a wordlist from its original source.
        Useful for wordlists created before words_json was added.
        
        Args:
            wordlist: WordList object to refresh
            user: User object (required if source is Google Sheets)
            
        Returns:
            Dict with refresh report
        """
        if wordlist.words_json and len(wordlist.words_json) > 0 and not force:
            logger.info(f"WordList {wordlist.id} already has words_json with {len(wordlist.words_json)} words (force={force})")
            return {
                'status': 'already_populated',
                'word_count': len(wordlist.words_json)
            }
        
        words = []
        
        if wordlist.source_type == 'google_sheet' and wordlist.source_ref:
            if not user or not user.google_access_token:
                raise ValueError("Google Sheets source requires authenticated user with Google access")
            
            try:
                from app.services.auth_service import AuthService
                from app.services.google_sheets_service import GoogleSheetsService
                
                auth_service = AuthService()
                creds = auth_service.get_user_credentials(user)
                sheets_service = GoogleSheetsService()
                
                # Fetch from sheet (auto-detect A/B with fallback)
                words = sheets_service.fetch_words_from_spreadsheet(
                    creds,
                    spreadsheet_id=wordlist.source_ref,
                    include_header=True
                )
                logger.info(f"Fetched {len(words)} words from Google Sheet {wordlist.source_ref}")
            except Exception as e:
                logger.exception(f"Failed to refresh wordlist {wordlist.id} from Google Sheets: {e}")
                raise ValueError(f"Failed to fetch from Google Sheet: {str(e)}")
        
        elif wordlist.canonical_samples:
            # Use canonical samples as fallback
            words = wordlist.canonical_samples
            logger.warning(f"WordList {wordlist.id} using canonical_samples ({len(words)} words) as fallback")
        else:
            raise ValueError(f"WordList {wordlist.id} has no source to refresh from")
        
        if not words:
            raise ValueError("No words found to refresh wordlist")
        
        # Re-ingest to normalize with diagnostics
        normalized_keys = set()
        duplicates = []
        anomalies = []
        variants_total = 0
        multi_token_count = 0
        raw_count = 0

        for word in words:
            raw_count += 1
            if not word or not word.strip():
                continue
            variants = self.split_variants(word)
            variants_total += max(0, len(variants) - 1)

            for variant in variants:
                # Handle multi-token
                tokens = variant.split()
                if len(tokens) > 1:
                    multi_token_count += 1
                    variant_to_use = self.extract_head_token(variant)
                else:
                    variant_to_use = variant

                normalized = self.normalize_word(variant_to_use, fold_diacritics=True)
                if not normalized:
                    anomalies.append({'word': word, 'variant': variant, 'issue': 'empty_after_normalization'})
                    continue

                if normalized in normalized_keys:
                    duplicates.append({'original': variant, 'normalized': normalized})
                else:
                    normalized_keys.add(normalized)
        
        # Update wordlist
        wordlist.words_json = sorted(list(normalized_keys))
        wordlist.normalized_count = len(normalized_keys)
        if not wordlist.canonical_samples:
            wordlist.canonical_samples = sorted(list(normalized_keys))[:20]
        wordlist.updated_at = datetime.utcnow()
        
        logger.info(f"Refreshed WordList {wordlist.id} with {len(normalized_keys)} normalized words (raw_rows={raw_count}, variants_total={variants_total}, multi_token_count={multi_token_count}, duplicates={len(duplicates)})")

        return {
            'status': 'refreshed',
            'word_count': len(normalized_keys),
            'raw_rows': raw_count,
            'variants_expanded': variants_total,
            'multi_token_count': multi_token_count,
            'duplicates': len(duplicates),
            'anomalies': anomalies,
            'source': wordlist.source_type
        }
    
    @staticmethod
    def delete_wordlist(wordlist_id: int, user_id: int) -> bool:
        """
        Delete a word list (only if owned by user).
        
        Args:
            wordlist_id: ID of word list to delete
            user_id: User ID requesting deletion
            
        Returns:
            True if deleted, False if not found or not authorized
        """
        # Only allow deletion by the owner (global lists cannot be deleted by regular users)
        wordlist = WordList.query.filter_by(id=wordlist_id, owner_user_id=user_id).first()
        if not wordlist:
            return False

        # Null out references in user settings that point to this wordlist
        try:
            UserSettings.query.filter(UserSettings.default_wordlist_id == wordlist_id).update(
                { 'default_wordlist_id': None }, synchronize_session=False
            )
        except Exception:
            # If the UserSettings model/table is not present or update fails, continue and let commit handle it
            pass

        # Null out references in coverage runs (preserve runs, just remove link)
        try:
            CoverageRun.query.filter(CoverageRun.wordlist_id == wordlist_id).update(
                { 'wordlist_id': None }, synchronize_session=False
            )
        except Exception:
            pass

        # Now delete the wordlist itself
        db.session.delete(wordlist)
        return True
