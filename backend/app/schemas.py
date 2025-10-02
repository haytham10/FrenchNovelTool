"""Request/Response validation schemas using Marshmallow"""
from marshmallow import Schema, fields, validate


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


class UserSettingsSchema(Schema):
    """Schema for user settings validation"""
    sentence_length_limit = fields.Integer(
        required=True,
        validate=validate.Range(min=3, max=50)
    )
    # P1 advanced normalization fields
    gemini_model = fields.String(
        validate=validate.OneOf(['balanced', 'quality', 'speed']),
        load_default='balanced'
    )
    ignore_dialogue = fields.Boolean(load_default=False)
    preserve_formatting = fields.Boolean(load_default=True)
    fix_hyphenation = fields.Boolean(load_default=True)
    min_sentence_length = fields.Integer(
        validate=validate.Range(min=1, max=50),
        load_default=3
    )


class ProcessPdfOptionsSchema(Schema):
    """Schema for advanced PDF processing options"""
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
        validate=validate.Range(min=1, max=50),
        allow_none=True
    )


