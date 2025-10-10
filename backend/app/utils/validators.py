"""Utility validators for common validation tasks"""
from marshmallow import ValidationError


def validate_file_extension(filename, allowed_extensions):
    """
    Validate file extension against allowed extensions.
    
    Args:
        filename: The filename to validate
        allowed_extensions: Set or list of allowed extensions (without dot)
        
    Raises:
        ValidationError: If filename is invalid or extension not allowed
        
    Returns:
        True if valid
    """
    if not filename:
        raise ValidationError('No filename provided')
    
    if '.' not in filename:
        raise ValidationError('File must have an extension')
    
    ext = filename.rsplit('.', 1)[1].lower()
    if ext not in allowed_extensions:
        raise ValidationError(
            f'File extension must be one of: {", ".join(allowed_extensions)}'
        )
    
    return True


def validate_pdf_file(file, max_size_mb=50):
    """
    Validate uploaded PDF file.
    
    Args:
        file: Werkzeug FileStorage object
        max_size_mb: Maximum file size in megabytes
        
    Raises:
        ValidationError: If file is invalid
        
    Returns:
        True if valid
    """
    if not file:
        raise ValidationError('No file provided')
    
    if not file.filename:
        raise ValidationError('No filename provided')
    
    # Validate extension
    validate_file_extension(file.filename, {'pdf'})
    
    # Note: Flask's MAX_CONTENT_LENGTH handles size validation automatically,
    # but we include this for completeness and better error messages
    if hasattr(file, 'content_length') and file.content_length:
        max_bytes = max_size_mb * 1024 * 1024
        if file.content_length > max_bytes:
            raise ValidationError(f'File size exceeds maximum of {max_size_mb}MB')
    
    return True


def validate_coverage_run_payload(data):
    """
    Validates the payload for starting a coverage analysis run.
    """
    if not isinstance(data, dict):
        return False, "Invalid payload format: expected a JSON object."

    mode = data.get('mode')
    if mode not in ['filter', 'coverage', 'batch']:
        return False, "Invalid 'mode'. Must be one of 'filter', 'coverage', 'batch'."

    sources = data.get('sources')
    if not isinstance(sources, list):
        return False, "'sources' must be a list."

    if not sources:
        return False, "At least one source is required."

    for source in sources:
        if not isinstance(source, dict) or 'type' not in source or 'id' not in source:
            return False, "Each source must be an object with 'type' and 'id'."
        if source['type'] not in ['history', 'wordlist', 'global']:
            return False, f"Invalid source type: {source['type']}"

    if mode in ['filter', 'coverage']:
        if len(sources) > 1:
            return False, f"{mode.capitalize()} mode only supports a single source."
        if sources[0]['type'] != 'history':
            return False, f"{mode.capitalize()} mode requires a 'history' source."
        if 'word_list_id' not in data or not isinstance(data['word_list_id'], int):
            return False, "'word_list_id' is required and must be an integer for filter/coverage modes."

    if mode == 'filter':
        min_len = data.get('min_sentence_length')
        max_len = data.get('max_sentence_length')
        coverage_percent = data.get('coverage_percentage')

        if not all(isinstance(i, int) for i in [min_len, max_len]):
            return False, "Sentence length limits must be integers."
        if not (isinstance(coverage_percent, (int, float))):
            return False, "Coverage percentage must be a number."
        if not (0 < coverage_percent <= 1):
            return False, "Coverage percentage must be between 0 and 1."
        if not (1 <= min_len <= max_len):
            return False, "Invalid sentence length range."

    return True, None


