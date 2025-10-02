"""Service for managing processing history"""
from app import db
from app.models import History


class HistoryService:
    """Service for tracking PDF processing history"""
    
    def add_entry(
        self,
        user_id,
        original_filename,
        processed_sentences_count,
        spreadsheet_url=None,
        error_message=None
    ):
        """
        Add a new history entry for a processed PDF.
        
        Args:
            user_id: ID of the user who processed the PDF
            original_filename: Name of the original PDF file
            processed_sentences_count: Number of sentences processed
            spreadsheet_url: URL of exported Google Sheet (optional)
            error_message: Error message if processing failed (optional)
            
        Returns:
            History: The created history entry
        """
        history_entry = History(
            user_id=user_id,
            original_filename=original_filename,
            processed_sentences_count=processed_sentences_count,
            spreadsheet_url=spreadsheet_url,
            error_message=error_message
        )
        db.session.add(history_entry)
        db.session.commit()
        return history_entry

    def get_user_entries(self, user_id, limit=None):
        """
        Retrieve history entries for a specific user, ordered by most recent first.
        
        Args:
            user_id: ID of the user
            limit: Maximum number of entries to return (optional)
            
        Returns:
            list[History]: List of history entries for the user
        """
        query = History.query.filter_by(user_id=user_id).order_by(History.timestamp.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def get_entry_by_id(self, entry_id, user_id):
        """
        Get a specific history entry by ID, ensuring it belongs to the user.
        
        Args:
            entry_id: ID of the history entry
            user_id: ID of the user
            
        Returns:
            History: The history entry or None if not found
        """
        return History.query.filter_by(id=entry_id, user_id=user_id).first()
    
    def delete_entry(self, entry_id, user_id):
        """
        Delete a history entry, ensuring it belongs to the user.
        
        Args:
            entry_id: ID of the history entry to delete
            user_id: ID of the user
            
        Returns:
            bool: True if deleted, False if not found
        """
        entry = History.query.filter_by(id=entry_id, user_id=user_id).first()
        if entry:
            db.session.delete(entry)
            db.session.commit()
            return True
        return False
