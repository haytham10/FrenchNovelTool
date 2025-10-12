"""
Script to refresh/populate words_json for existing wordlists.
Useful for wordlists created before the words_json field was added.

Usage:
    python scripts/refresh_wordlists.py [--wordlist-id ID] [--all]
"""
import sys
import os
import argparse
import logging

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db
from app.models import WordList, User
from app.services.wordlist_service import WordListService

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def refresh_wordlist(wordlist_id: int, app):
    """Refresh a single wordlist"""
    with app.app_context():
        wordlist = WordList.query.get(wordlist_id)
        if not wordlist:
            logger.error(f"WordList {wordlist_id} not found")
            return False

        logger.info(f"Refreshing WordList {wordlist_id}: {wordlist.name}")
        logger.info(f"  Source: {wordlist.source_type}, Ref: {wordlist.source_ref}")
        logger.info(
            f"  Current words_json: {len(wordlist.words_json) if wordlist.words_json else 0} words"
        )
        logger.info(
            f"  Canonical samples: {len(wordlist.canonical_samples) if wordlist.canonical_samples else 0} words"
        )

        # Get user with Google access if needed
        user = None
        if wordlist.source_type == "google_sheet":
            # Try to find a user with Google access token
            if wordlist.owner_user_id:
                user = User.query.get(wordlist.owner_user_id)
            else:
                # Global wordlist - find any admin with Google access
                user = User.query.filter(User.google_access_token.isnot(None)).first()

            if not user or not user.google_access_token:
                logger.error(f"  Cannot refresh: no user with Google access token found")
                return False

        try:
            wordlist_service = WordListService()
            # Use default include_header=True for script-run refreshes
            refresh_report = wordlist_service.refresh_wordlist_from_source(
                wordlist, user, include_header=True
            )
            db.session.commit()

            logger.info(f"  ✓ Refresh successful: {refresh_report}")
            return True
        except Exception as e:
            db.session.rollback()
            logger.exception(f"  ✗ Refresh failed: {e}")
            return False


def refresh_all_wordlists(app):
    """Refresh all wordlists that need it"""
    with app.app_context():
        # Find wordlists without words_json
        wordlists = WordList.query.filter(
            db.or_(
                WordList.words_json.is_(None), db.func.json_array_length(WordList.words_json) == 0
            )
        ).all()

        logger.info(f"Found {len(wordlists)} wordlists to refresh")

        success_count = 0
        for wordlist in wordlists:
            if refresh_wordlist(wordlist.id, app):
                success_count += 1

        logger.info(f"Refreshed {success_count}/{len(wordlists)} wordlists successfully")


def main():
    parser = argparse.ArgumentParser(description="Refresh wordlist words_json from source")
    parser.add_argument("--wordlist-id", type=int, help="Specific wordlist ID to refresh")
    parser.add_argument(
        "--all", action="store_true", help="Refresh all wordlists without words_json"
    )

    args = parser.parse_args()

    if not args.wordlist_id and not args.all:
        parser.print_help()
        sys.exit(1)

    app = create_app()

    if args.wordlist_id:
        success = refresh_wordlist(args.wordlist_id, app)
        sys.exit(0 if success else 1)
    elif args.all:
        refresh_all_wordlists(app)
        sys.exit(0)


if __name__ == "__main__":
    main()
