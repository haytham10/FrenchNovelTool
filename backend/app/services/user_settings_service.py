"""Service for managing user settings"""
from app import db
from app.models import UserSettings


class UserSettingsService:
    """Service for managing user settings stored in database"""
    
    def get_user_settings(self, user_id):
        """
        Get settings for a specific user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            dict: User settings dictionary
        """
        settings = UserSettings.query.filter_by(user_id=user_id).first()
        
        if not settings:
            # Create default settings for user
            settings = UserSettings(
                user_id=user_id,
                sentence_length_limit=8
            )
            db.session.add(settings)
            db.session.commit()
        
        return settings.to_dict()
    
    def save_user_settings(self, user_id, settings_dict):
        """
        Save settings for a specific user.
        
        Args:
            user_id: ID of the user
            settings_dict: Dictionary with settings values
            
        Returns:
            dict: Updated user settings dictionary
        """
        settings = UserSettings.query.filter_by(user_id=user_id).first()
        
        if settings:
            # Update existing settings
            settings.sentence_length_limit = settings_dict.get('sentence_length_limit', settings.sentence_length_limit)
        else:
            # Create new settings
            settings = UserSettings(
                user_id=user_id,
                sentence_length_limit=settings_dict.get('sentence_length_limit', 8)
            )
            db.session.add(settings)
        
        db.session.commit()
        return settings.to_dict()
