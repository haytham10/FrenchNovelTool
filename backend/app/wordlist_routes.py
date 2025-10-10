from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from .services.wordlist_service import WordlistService

wordlist_bp = Blueprint('wordlist_bp', __name__)

@wordlist_bp.route('/api/v1/wordlists', methods=['GET'])
@jwt_required()
def get_wordlists():
    user_id = int(get_jwt_identity())
    
    # This combines global and user-specific wordlists
    wordlists = WordlistService.get_user_wordlists(user_id)
    
    # Convert to JSON serializable format
    wordlists_json = [wl.to_dict() for wl in wordlists]
    
    return jsonify(wordlists=wordlists_json)
