"""Request/Response validation schemas using Marshmallow"""
from marshmallow import Schema, fields, validate


class GoogleAuthSchema(Schema):
    """Schema for Google OAuth authentication"""
    token = fields.String(required=True, validate=validate.Length(min=1))


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


class UserSettingsSchema(Schema):
    """Schema for user settings validation"""
    sentence_length_limit = fields.Integer(
        required=True,
        validate=validate.Range(min=3, max=50)
    )


