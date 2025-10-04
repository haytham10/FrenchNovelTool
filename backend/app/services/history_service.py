"""Service for managing processing history"""
from app import db
from app.models import History, JobChunk


class HistoryService:
    """Service for tracking PDF processing history"""
    
    def add_entry(
        self,
        user_id,
        original_filename,
        processed_sentences_count,
        spreadsheet_url=None,
        error_message=None,
        failed_step=None,
        error_code=None,
        error_details=None,
        processing_settings=None,
        job_id=None,
        sentences=None,
        chunk_ids=None
    ):
        """
        Add a new history entry for a processed PDF.
        
        Args:
            user_id: ID of the user who processed the PDF
            original_filename: Name of the original PDF file
            processed_sentences_count: Number of sentences processed
            spreadsheet_url: URL of exported Google Sheet (optional)
            error_message: Error message if processing failed (optional)
            failed_step: Step where processing failed (optional)
            error_code: Error code for categorizing errors (optional)
            error_details: Additional error context as JSON (optional)
            processing_settings: Settings used for processing (optional)
            job_id: ID of the job that created this history (optional)
            sentences: Processed sentences array (optional)
            chunk_ids: Array of JobChunk IDs for drill-down (optional)
            
        Returns:
            History: The created history entry
        """
        history_entry = History(
            user_id=user_id,
            original_filename=original_filename,
            processed_sentences_count=processed_sentences_count,
            spreadsheet_url=spreadsheet_url,
            error_message=error_message,
            failed_step=failed_step,
            error_code=error_code,
            error_details=error_details,
            processing_settings=processing_settings,
            job_id=job_id,
            sentences=sentences,
            chunk_ids=chunk_ids,
            exported_to_sheets=False
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
    
    def get_entry_with_details(self, entry_id, user_id):
        """
        Get history entry with full details including sentences and chunk breakdown.
        
        Args:
            entry_id: ID of the history entry
            user_id: ID of the user
            
        Returns:
            dict: Full history details or None if not found
        """
        entry = self.get_entry_by_id(entry_id, user_id)
        if not entry:
            return None
        
        result = entry.to_dict_with_sentences()
        
        # Add chunk details if available
        if entry.chunk_ids and entry.job_id:
            chunks = JobChunk.query.filter(
                JobChunk.job_id == entry.job_id,
                JobChunk.id.in_(entry.chunk_ids)
            ).all()
            result['chunks'] = [chunk.to_dict() for chunk in chunks]
        else:
            result['chunks'] = []
        
        return result
    
    def get_chunk_details(self, entry_id, user_id):
        """
        Get chunk-level details for a history entry.
        
        Args:
            entry_id: ID of the history entry
            user_id: ID of the user
            
        Returns:
            list[dict]: List of chunk details or empty list
        """
        entry = self.get_entry_by_id(entry_id, user_id)
        if not entry or not entry.chunk_ids or not entry.job_id:
            return []
        
        chunks = JobChunk.query.filter(
            JobChunk.job_id == entry.job_id,
            JobChunk.id.in_(entry.chunk_ids)
        ).order_by(JobChunk.chunk_id).all()
        
        return [chunk.to_dict() for chunk in chunks]
    
    def mark_exported(self, entry_id, user_id, export_url):
        """
        Mark a history entry as exported to sheets.
        
        Args:
            entry_id: ID of the history entry
            user_id: ID of the user
            export_url: URL of the exported sheet
            
        Returns:
            History: Updated history entry or None if not found
        """
        entry = self.get_entry_by_id(entry_id, user_id)
        if not entry:
            return None
        
        entry.exported_to_sheets = True
        entry.export_sheet_url = export_url
        # Also update legacy spreadsheet_url if not already set
        if not entry.spreadsheet_url:
            entry.spreadsheet_url = export_url
        
        db.session.commit()
        return entry
    
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
