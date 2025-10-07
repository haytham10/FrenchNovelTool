"""Request/Response validation schemas using Marshmallow"""
from marshmallow import Schema, fields, validate, pre_load


class GoogleAuthSchema(Schema):
    """Schema for Google OAuth authentication"""
    token = fields.String(required=True, validate=validate.Length(min=1))


class HeaderConfigSchema(Schema):
    """Schema for custom header configuration"""
    name = fields.String(required=True)
    enabled = fields.Boolean(required=True)
    order = fields.Integer(required=True)


class ShareSettingsSchema(Schema):
    """Schema for sharing settings"""
    addCollaborators = fields.Boolean(required=False)
    collaboratorEmails = fields.List(fields.String(), required=False)
    publicLink = fields.Boolean(required=False)


class ExportToSheetSchema(Schema):
    """Schema for export to sheet request validation"""
    sentences = fields.List(
        fields.String(validate=validate.Length(min=1, max=5000)),
        required=True,
        validate=validate.Length(min=1, max=10000)
    )
    sheetName = fields.String(
        required=True,
        validate=validate.Length(min=1, max=255)
    )
    folderId = fields.String(
        allow_none=True,
        validate=validate.Length(max=255)
    )
    # P1 new fields
    mode = fields.String(
        validate=validate.OneOf(['new', 'append']),
        load_default='new'
    )
    existingSheetId = fields.String(
        allow_none=True,
        validate=validate.Length(max=255)
    )
    tabName = fields.String(
        allow_none=True,
        validate=validate.Length(max=255)
    )
    createNewTab = fields.Boolean(load_default=False)
    headers = fields.List(fields.Nested(HeaderConfigSchema), allow_none=True)
    columnOrder = fields.List(fields.String(), allow_none=True)
    sharing = fields.Nested(ShareSettingsSchema, allow_none=True)
    sentenceIndices = fields.List(fields.Integer(), allow_none=True)

    @pre_load
    def _normalize_headers(self, data, **kwargs):
        """Allow frontend to send headers as simple strings by normalizing
        them into the expected object form {name, enabled, order} before
        validation.
        """
        try:
            headers = data.get('headers') if isinstance(data, dict) else None
            if headers and isinstance(headers, list):
                new_headers = []
                for idx, h in enumerate(headers):
                    # If frontend sent a simple string, convert it
                    if isinstance(h, str):
                        new_headers.append({'name': h, 'enabled': True, 'order': idx})
                    elif isinstance(h, dict):
                        # Ensure required keys exist with sensible defaults
                        if 'name' in h:
                            if 'enabled' not in h:
                                h['enabled'] = True
                            if 'order' not in h:
                                h['order'] = idx
                            new_headers.append(h)
                        else:
                            # Skip malformed header entries (will fail validation later)
                            new_headers.append(h)
                data['headers'] = new_headers
        except Exception:
            # Don't break validation on unexpected types; let Marshmallow report errors
            pass
        return data


class UserSettingsSchema(Schema):
    """Schema for user settings validation"""
    sentence_length_limit = fields.Integer(
        required=True,
        validate=validate.Range(min=3, max=50)
    )
    gemini_model = fields.String(
        load_default='speed',
        validate=validate.OneOf(['balanced', 'quality', 'speed'])
    )
    ignore_dialogue = fields.Boolean(load_default=False)
    preserve_formatting = fields.Boolean(load_default=True)
    fix_hyphenation = fields.Boolean(load_default=True)
    min_sentence_length = fields.Integer(
        load_default=2,
        validate=validate.Range(min=1, max=10)
    )
    default_wordlist_id = fields.Integer(allow_none=True, validate=validate.Range(min=1))
    coverage_defaults = fields.Dict(allow_none=True)


class ProcessPdfOptionsSchema(Schema):
    """Schema for basic PDF processing options"""
    sentence_length_limit = fields.Integer(
        validate=validate.Range(min=3, max=50),
        allow_none=True
    )
    gemini_model = fields.String(
        validate=validate.OneOf(['balanced', 'quality', 'speed']),
        allow_none=True
    )
    ignore_dialogue = fields.Boolean(allow_none=True)
    preserve_formatting = fields.Boolean(allow_none=True)
    fix_hyphenation = fields.Boolean(allow_none=True)
    min_sentence_length = fields.Integer(
        validate=validate.Range(min=1, max=10),
        allow_none=True
    )


class EstimateRequestSchema(Schema):
    """Schema for credit estimate request"""
    text = fields.String(required=True, validate=validate.Length(min=1))
    model_preference = fields.String(
        required=True,
        validate=validate.OneOf(['balanced', 'quality', 'speed'])
    )


class JobConfirmSchema(Schema):
    """Schema for job confirmation request"""
    estimated_credits = fields.Integer(required=True, validate=validate.Range(min=1))
    model_preference = fields.String(
        required=True,
        validate=validate.OneOf(['balanced', 'quality', 'speed'])
    )
    processing_settings = fields.Dict(required=False)


class JobFinalizeSchema(Schema):
    """Schema for job finalization request"""
    job_id = fields.Integer(required=True, validate=validate.Range(min=1))
    actual_tokens = fields.Integer(required=True, validate=validate.Range(min=0))
    success = fields.Boolean(required=True)
    error_message = fields.String(allow_none=True)
    error_code = fields.String(allow_none=True)


class EstimatePdfSchema(Schema):
    """Schema for PDF metadata estimation request (input validation)"""
    # File is validated separately via validate_pdf_file()
    # This schema validates optional form fields
    model_preference = fields.String(
        load_default='speed',
        validate=validate.OneOf(['balanced', 'quality', 'speed'])
    )


class EstimatePdfResponseSchema(Schema):
    """Schema for PDF metadata estimation response"""
    page_count = fields.Integer(required=True)
    file_size = fields.Integer(required=True)
    image_count = fields.Integer(required=True)
    estimated_tokens = fields.Integer(required=True)
    estimated_credits = fields.Integer(required=True)
    model = fields.String(required=True)
    model_preference = fields.String(required=True)
    pricing_rate = fields.Float(required=True)
    capped = fields.Boolean(required=True)  # True if page count exceeds cap
    warning = fields.String(allow_none=True)  # Warning message if capped


class WordListCreateSchema(Schema):
    """Schema for creating a word list"""
    name = fields.String(required=True, validate=validate.Length(min=1, max=255))
    source_type = fields.String(
        required=True,
        validate=validate.OneOf(['csv', 'google_sheet', 'manual'])
    )
    source_ref = fields.String(allow_none=True, validate=validate.Length(max=512))
    words = fields.List(fields.String(), allow_none=True)  # For manual/CSV upload
    fold_diacritics = fields.Boolean(load_default=True)


class WordListUpdateSchema(Schema):
    """Schema for updating a word list"""
    name = fields.String(validate=validate.Length(min=1, max=255))


class CoverageRunCreateSchema(Schema):
    """Schema for creating a coverage run"""
    mode = fields.String(
        required=True,
        validate=validate.OneOf(['coverage', 'filter'])
    )
    source_type = fields.String(
        required=True,
        validate=validate.OneOf(['job', 'history'])
    )
    source_id = fields.Integer(required=True, validate=validate.Range(min=1))
    wordlist_id = fields.Integer(allow_none=True, validate=validate.Range(min=1))
    config = fields.Dict(allow_none=True)


class CoverageSwapSchema(Schema):
    """Schema for swapping word assignments in coverage mode"""
    word_key = fields.String(required=True, validate=validate.Length(min=1))
    new_sentence_index = fields.Integer(required=True, validate=validate.Range(min=0))


class CoverageExportSchema(Schema):
    """Schema for exporting coverage results to Google Sheets"""
    sheet_name = fields.String(required=True, validate=validate.Length(min=1, max=255))
    folder_id = fields.String(allow_none=True, validate=validate.Length(max=255))

