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
        raise ValidationError("No filename provided")

    if "." not in filename:
        raise ValidationError("File must have an extension")

    ext = filename.rsplit(".", 1)[1].lower()
    if ext not in allowed_extensions:
        raise ValidationError(f'File extension must be one of: {", ".join(allowed_extensions)}')

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
        raise ValidationError("No file provided")

    if not file.filename:
        raise ValidationError("No filename provided")

    # Validate extension
    validate_file_extension(file.filename, {"pdf"})

    # Note: Flask's MAX_CONTENT_LENGTH handles size validation automatically,
    # but we include this for completeness and better error messages
    if hasattr(file, "content_length") and file.content_length:
        max_bytes = max_size_mb * 1024 * 1024
        if file.content_length > max_bytes:
            raise ValidationError(f"File size exceeds maximum of {max_size_mb}MB")

    return True
