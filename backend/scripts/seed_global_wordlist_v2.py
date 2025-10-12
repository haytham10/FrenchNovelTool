"""
Improved seed script for global French wordlist with long-term architecture.

Features:
- Reads from external data file (not hardcoded)
- Idempotent (safe to re-run)
- Supports versioning
- Validates data quality
- Provides detailed reporting
"""
import sys
import os
from pathlib import Path
from typing import List, Dict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import WordList
from app.services.wordlist_service import WordListService

# Configuration
WORDLIST_DATA_DIR = Path(__file__).parent.parent / "data" / "wordlists"
FRENCH_2K_FILE = WORDLIST_DATA_DIR / "french_2k.txt"
WORDLIST_VERSION = "1.0.0"


def load_words_from_file(filepath: Path) -> List[str]:
    """
    Load words from a text file.

    Args:
        filepath: Path to the wordlist file

    Returns:
        List of words (excluding comments and empty lines)
    """
    if not filepath.exists():
        raise FileNotFoundError(f"Wordlist file not found: {filepath}")

    words = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue
            words.append(line)

    return words


def validate_wordlist_quality(words: List[str]) -> Dict:
    """
    Validate the quality of a wordlist.

    Args:
        words: List of words to validate

    Returns:
        Dict with validation results
    """
    issues = {"empty_words": [], "very_long_words": [], "numeric_words": [], "suspicious_chars": []}

    for idx, word in enumerate(words):
        if not word.strip():
            issues["empty_words"].append(idx)
        elif len(word) > 50:
            issues["very_long_words"].append((idx, word))
        elif word.isdigit():
            issues["numeric_words"].append((idx, word))
        elif any(char in word for char in ["<", ">", "{", "}", "[", "]"]):
            issues["suspicious_chars"].append((idx, word))

    return {
        "is_valid": all(len(v) == 0 for v in issues.values()),
        "issues": issues,
        "total_words": len(words),
    }


def seed_global_wordlist(force_recreate: bool = False):
    """
    Create or update the global default French 2K word list.

    Args:
        force_recreate: If True, delete existing global wordlist and recreate
    """
    app = create_app(skip_logging=True)

    with app.app_context():
        print("=" * 70)
        print("French 2K Global Wordlist Seeding")
        print("=" * 70)

        # Check if global default already exists
        existing = WordList.query.filter_by(is_global_default=True).first()

        if existing and not force_recreate:
            print(f"\n✓ Global default word list already exists:")
            print(f"  Name: {existing.name}")
            print(f"  ID: {existing.id}")
            print(f"  Words: {existing.normalized_count}")
            print(f"  Created: {existing.created_at}")
            print(f"\nTo recreate, run with --force flag")
            return

        if existing and force_recreate:
            print(f"\n⚠ Deleting existing global wordlist (ID: {existing.id})...")
            db.session.delete(existing)
            db.session.commit()
            print("✓ Deleted")

        # Load words from file
        print(f"\n📖 Loading words from {FRENCH_2K_FILE.name}...")
        try:
            words = load_words_from_file(FRENCH_2K_FILE)
            print(f"✓ Loaded {len(words)} words")
        except FileNotFoundError as e:
            print(f"✗ Error: {e}")
            return
        except Exception as e:
            print(f"✗ Error loading file: {e}")
            return

        # Validate quality
        print(f"\n🔍 Validating word list quality...")
        validation = validate_wordlist_quality(words)

        if not validation["is_valid"]:
            print("⚠ Quality issues found:")
            for issue_type, issue_list in validation["issues"].items():
                if issue_list:
                    print(f"  - {issue_type}: {len(issue_list)} instances")
                    if len(issue_list) <= 5:
                        for item in issue_list:
                            print(f"    • {item}")
            print("\n⚠ Proceeding with caution...")
        else:
            print("✓ Quality check passed")

        # Create wordlist using WordListService
        print(f"\n⚙️  Creating global wordlist...")
        wordlist_service = WordListService()

        try:
            wordlist, ingestion_report = wordlist_service.ingest_word_list(
                words=words,
                name=f"French 2K (v{WORDLIST_VERSION})",
                owner_user_id=None,  # Global list - no owner
                source_type="file",
                source_ref=str(FRENCH_2K_FILE),
                fold_diacritics=True,
            )

            # Mark as global default
            wordlist.is_global_default = True

            db.session.commit()

            print("✓ Global wordlist created successfully!")

            # Print detailed report
            print("\n" + "=" * 70)
            print("INGESTION REPORT")
            print("=" * 70)
            print(f"Wordlist ID:          {wordlist.id}")
            print(f"Name:                 {wordlist.name}")
            print(f"Source:               {wordlist.source_type}")
            print(f"Original count:       {ingestion_report['original_count']}")
            print(f"Normalized count:     {ingestion_report['normalized_count']}")
            print(f"Duplicates removed:   {len(ingestion_report['duplicates'])}")
            print(f"Multi-token entries:  {len(ingestion_report['multi_token_entries'])}")
            print(f"Variants expanded:    {ingestion_report['variants_expanded']}")
            print(f"Anomalies:            {len(ingestion_report['anomalies'])}")

            # Show samples
            print(f"\nSample normalized words (first 20):")
            for i, word in enumerate(wordlist.canonical_samples[:20], 1):
                print(f"  {i:2d}. {word}")

            # Show duplicates if any
            if ingestion_report["duplicates"]:
                print(f"\nSample duplicates (first 10):")
                for i, dup in enumerate(ingestion_report["duplicates"][:10], 1):
                    print(f"  {i:2d}. '{dup['word']}' → '{dup['normalized']}'")

            # Show multi-token entries if any
            if ingestion_report["multi_token_entries"]:
                print(f"\nSample multi-token entries (first 10):")
                for i, entry in enumerate(ingestion_report["multi_token_entries"][:10], 1):
                    print(f"  {i:2d}. '{entry['original']}' → head: '{entry['head_token']}'")

            # Show anomalies if any
            if ingestion_report["anomalies"]:
                print(f"\n⚠ Anomalies detected (first 10):")
                for i, anomaly in enumerate(ingestion_report["anomalies"][:10], 1):
                    print(f"  {i:2d}. {anomaly}")

            print("\n" + "=" * 70)
            print("✅ SEEDING COMPLETE")
            print("=" * 70)

        except Exception as e:
            print(f"✗ Error creating wordlist: {e}")
            db.session.rollback()
            raise


def main():
    """Main entry point with CLI argument support"""
    import argparse

    parser = argparse.ArgumentParser(description="Seed global French 2K wordlist")
    parser.add_argument(
        "--force", action="store_true", help="Force recreate even if wordlist exists"
    )

    args = parser.parse_args()

    try:
        seed_global_wordlist(force_recreate=args.force)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
