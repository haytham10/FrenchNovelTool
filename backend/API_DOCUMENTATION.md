# API Documentation

French Novel Tool API v1.0

Base URL: `http://localhost:5000/api/v1` (development)

## Overview

The French Novel Tool API provides endpoints for processing French PDF documents using AI, managing processing history, and exporting results to Google Sheets.

## Authentication

The API uses JWT (JSON Web Token) authentication with Google OAuth 2.0. Most endpoints require authentication.

### Authentication Flow

1. User authenticates via Google OAuth 2.0 through the frontend
2. Backend validates the Google token and creates a JWT access token
3. Frontend includes the JWT token in subsequent requests via the `Authorization` header

### Using Authentication

Include the JWT token in the `Authorization` header:

```
Authorization: Bearer YOUR_JWT_TOKEN
```

### Token Refresh

Access tokens expire after 1 hour. Use the refresh token endpoint to obtain a new access token:

**Endpoint:** `POST /auth/refresh`

**Request:**
```json
{
  "refresh_token": "YOUR_REFRESH_TOKEN"
}
```

**Response:**
```json
{
  "access_token": "NEW_ACCESS_TOKEN",
  "refresh_token": "NEW_REFRESH_TOKEN"
}
```

### Unauthenticated Endpoints

The following endpoints do not require authentication:
- `GET /health` - Health check

## Rate Limiting

- Default: 100 requests per hour per IP
- Configurable via `RATELIMIT_DEFAULT` environment variable
- Rate limit headers are included in responses:
  - `X-RateLimit-Limit`: Maximum requests allowed
  - `X-RateLimit-Remaining`: Requests remaining
  - `X-RateLimit-Reset`: Time when limit resets (Unix timestamp)

## Endpoints

### Health Check

Check if the API is running and healthy.

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "service": "French Novel Tool API",
  "version": "1.0.0"
}
```

**Status Codes:**
- `200 OK`: Service is healthy

---

### Process PDF

Upload and process a PDF file to extract and normalize French sentences.

**Endpoint:** `POST /process-pdf`

**Rate Limit:** 10 requests per hour

**Authentication:** Required (JWT Bearer token)

**Request:**
- Content-Type: `multipart/form-data`
- Body:
  - `pdf_file`: PDF file (required, max 50MB)
  - `sentence_length_limit`: Target sentence length in words (optional, 3-50, defaults to user settings)
  - `ai_provider`: AI provider to use - `gemini` or `openai` (optional, defaults to user settings or `gemini`)
  - `gemini_model`: AI model preference - `balanced`, `quality`, or `speed` (optional, defaults to user settings)
    - For Gemini: uses gemini-2.0-flash-exp for all modes
    - For OpenAI: `balanced` → gpt-4o-mini, `quality` → gpt-4o, `speed` → gpt-3.5-turbo
  - `ignore_dialogue`: Skip normalizing dialogue sections (optional, boolean, defaults to user settings)
  - `preserve_formatting`: Keep original quotes and punctuation (optional, boolean, defaults to user settings)
  - `fix_hyphenation`: Rejoin hyphenated words split across lines (optional, boolean, defaults to user settings)
  - `min_sentence_length`: Minimum sentence length in words (optional, 1-50, defaults to user settings)

**Example with Gemini:**
```bash
curl -X POST \
  http://localhost:5000/api/v1/process-pdf \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "pdf_file=@document.pdf" \
  -F "sentence_length_limit=12" \
  -F "ai_provider=gemini" \
  -F "gemini_model=quality" \
  -F "ignore_dialogue=false" \
  -F "preserve_formatting=true" \
  -F "fix_hyphenation=true" \
  -F "min_sentence_length=3"
```

**Example with OpenAI:**
```bash
curl -X POST \
  http://localhost:5000/api/v1/process-pdf \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "pdf_file=@document.pdf" \
  -F "sentence_length_limit=12" \
  -F "ai_provider=openai" \
  -F "gemini_model=balanced" \
  -F "ignore_dialogue=false" \
  -F "preserve_formatting=true" \
  -F "fix_hyphenation=true" \
  -F "min_sentence_length=3"
```

**Success Response:**
```json
{
  "sentences": [
    "Voici la première phrase.",
    "Voici la deuxième phrase courte.",
    "Cette phrase était longue mais a été divisée."
  ]
}
```

**Error Responses:**

*400 Bad Request - No file provided*
```json
{
  "error": "No PDF file provided"
}
```

*400 Bad Request - Invalid file type*
```json
{
  "error": "File extension must be one of: pdf"
}
```

*413 Payload Too Large - File too large*
```json
{
  "error": "File size exceeds maximum allowed (50MB)"
}
```

*429 Too Many Requests - Rate limit exceeded*
```json
{
  "error": "Rate limit exceeded. Please try again later."
}
```

*500 Internal Server Error - Processing failed*
```json
{
  "error": "Failed to process PDF: [error details]"
}
```

**Status Codes:**
- `200 OK`: PDF processed successfully
- `400 Bad Request`: Invalid request or file
- `413 Payload Too Large`: File exceeds size limit
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Processing error

---

### Export to Google Sheets

Export processed sentences to a Google Sheets spreadsheet.

**Endpoint:** `POST /export-to-sheet`

**Rate Limit:** 5 requests per hour

**Authentication:** Required (JWT Bearer token)

**Request:**
- Content-Type: `application/json`
- Body:
```json
{
  "sentences": ["Sentence 1", "Sentence 2", "..."],
  "sheetName": "My French Novel",
  "folderId": "optional-google-drive-folder-id",
  "mode": "new",
  "existingSheetId": "existing-spreadsheet-id",
  "tabName": "Sheet1",
  "createNewTab": false,
  "headers": [
    {"name": "Index", "enabled": true, "order": 0},
    {"name": "Sentence", "enabled": true, "order": 1}
  ],
  "columnOrder": ["Index", "Sentence"],
  "sharing": {
    "addCollaborators": true,
    "collaboratorEmails": ["user@example.com"],
    "publicLink": false
  },
  "sentenceIndices": [0, 1, 2]
}
```

**Parameters:**
- `sentences` (array, required): Array of sentences to export (1-10000 items, each 1-5000 chars)
- `sheetName` (string, required): Name for the spreadsheet (1-255 chars)
- `folderId` (string, optional): Google Drive folder ID to place spreadsheet in
- `mode` (string, optional): Export mode - `new` (default) or `append`
- `existingSheetId` (string, optional): ID of existing spreadsheet (required if mode is `append`)
- `tabName` (string, optional): Name of tab to append to (defaults to `Sheet1` if mode is `append`)
- `createNewTab` (boolean, optional): Create new tab if it doesn't exist (defaults to false)
- `headers` (array, optional): Custom header configuration (currently uses default Index/Sentence)
- `columnOrder` (array, optional): Custom column ordering
- `sharing` (object, optional): Sharing settings for new spreadsheets
  - `addCollaborators` (boolean): Whether to add collaborators
  - `collaboratorEmails` (array): List of email addresses to share with
  - `publicLink` (boolean): Enable anyone-with-link access
- `sentenceIndices` (array, optional): Specific sentence indices to export (exports only these if provided)

**Example (New Spreadsheet):**
```bash
curl -X POST \
  http://localhost:5000/api/v1/export-to-sheet \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sentences": ["Première phrase.", "Deuxième phrase."],
    "sheetName": "French Novel Export",
    "folderId": "1abc2def3ghi4jkl5mno",
    "sharing": {
      "addCollaborators": true,
      "collaboratorEmails": ["colleague@example.com"],
      "publicLink": false
    }
  }'
```

**Example (Append to Existing):**
```bash
curl -X POST \
  http://localhost:5000/api/v1/export-to-sheet \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sentences": ["Nouvelle phrase 1.", "Nouvelle phrase 2."],
    "sheetName": "Not used in append mode",
    "mode": "append",
    "existingSheetId": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
    "tabName": "Chapter 2",
    "createNewTab": true
  }'
```

**Success Response:**
```json
{
  "spreadsheet_url": "https://docs.google.com/spreadsheets/d/SPREADSHEET_ID"
}
```

**Error Responses:**

*400 Bad Request - Invalid data*
```json
{
  "error": "Invalid request data",
  "details": {
    "sentences": ["Field is required"],
    "sheetName": ["Length must be between 1 and 255"]
  }
}
```

*429 Too Many Requests*
```json
{
  "error": "Rate limit exceeded. Please try again later."
}
```

*500 Internal Server Error*
```json
{
  "error": "Failed to create spreadsheet: [error details]"
}
```

**Status Codes:**
- `200 OK`: Export successful
- `400 Bad Request`: Invalid request data
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Export error

---

### Get History

Retrieve processing history entries.

**Endpoint:** `GET /history`

**Authentication:** Required (JWT Bearer token)

**Query Parameters:**
- `limit` (integer, optional): Maximum number of entries to return

**Response:**
```json
[
  {
    "id": 1,
    "timestamp": "2025-10-02T14:30:00.000Z",
    "original_filename": "novel_chapter_1.pdf",
    "processed_sentences_count": 142,
    "spreadsheet_url": "https://docs.google.com/spreadsheets/d/SPREADSHEET_ID",
    "error_message": null,
    "failed_step": null,
    "error_code": null,
    "error_details": null,
    "settings": {
      "sentence_length_limit": 12,
      "gemini_model": "balanced",
      "ignore_dialogue": false,
      "preserve_formatting": true,
      "fix_hyphenation": true,
      "min_sentence_length": 3
    }
  },
  {
    "id": 2,
    "timestamp": "2025-10-02T15:45:00.000Z",
    "original_filename": "novel_chapter_2.pdf",
    "processed_sentences_count": 0,
    "spreadsheet_url": null,
    "error_message": "Failed to process PDF: File corrupted",
    "failed_step": "extract",
    "error_code": "INVALID_PDF",
    "error_details": null,
    "settings": null
  }
]
```

**Response Fields:**
- `id`: Unique identifier
- `timestamp`: ISO 8601 timestamp
- `original_filename`: Name of processed file
- `processed_sentences_count`: Number of sentences processed
- `spreadsheet_url`: Google Sheets URL (null if not exported or failed)
- `error_message`: Error message (null if successful)
- `failed_step`: Processing step where error occurred (`upload`, `extract`, `analyze`, `normalize`, `export`)
- `error_code`: Structured error code (`INVALID_PDF`, `GEMINI_API_ERROR`, `QUOTA_EXCEEDED`, etc.)
- `error_details`: Additional error context as JSON
- `settings`: Processing settings used for this run

**Status Codes:**
- `200 OK`: History retrieved successfully
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Database error

---

### Get Settings

Retrieve current user settings.

**Endpoint:** `GET /settings`

**Authentication:** Required (JWT Bearer token)

**Response:**
```json
{
  "sentence_length_limit": 8,
  "gemini_model": "balanced",
  "ignore_dialogue": false,
  "preserve_formatting": true,
  "fix_hyphenation": true,
  "min_sentence_length": 3
}
```

**Response Fields:**
- `sentence_length_limit`: Maximum words per sentence (integer, 3-50)
- `gemini_model`: AI model preference (`balanced`, `quality`, or `speed`)
- `ignore_dialogue`: Skip normalizing dialogue sections (boolean)
- `preserve_formatting`: Keep original quotes and punctuation (boolean)
- `fix_hyphenation`: Rejoin hyphenated words split across lines (boolean)
- `min_sentence_length`: Minimum sentence length in words (integer, 1-50)

**Status Codes:**
- `200 OK`: Settings retrieved successfully
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Database error

---

### Update Settings

Update user settings.

**Endpoint:** `POST /settings`

**Authentication:** Required (JWT Bearer token)

**Request:**
- Content-Type: `application/json`
- Body:
```json
{
  "sentence_length_limit": 10,
  "gemini_model": "quality",
  "ignore_dialogue": false,
  "preserve_formatting": true,
  "fix_hyphenation": true,
  "min_sentence_length": 3
}
```

**Parameters:**
- `sentence_length_limit` (integer, required): Maximum words per sentence (3-50)
- `gemini_model` (string, optional): AI model - `balanced`, `quality`, or `speed`
- `ignore_dialogue` (boolean, optional): Skip normalizing dialogue sections
- `preserve_formatting` (boolean, optional): Keep original quotes and punctuation
- `fix_hyphenation` (boolean, optional): Rejoin hyphenated words split across lines
- `min_sentence_length` (integer, optional): Minimum sentence length in words (1-50)

**Example:**
```bash
curl -X POST \
  http://localhost:5000/api/v1/settings \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sentence_length_limit": 10,
    "gemini_model": "quality",
    "ignore_dialogue": false,
    "preserve_formatting": true,
    "fix_hyphenation": true,
    "min_sentence_length": 3
  }'
```

**Success Response:**
```json
{
  "message": "Settings saved successfully",
  "settings": {
    "sentence_length_limit": 10,
    "gemini_model": "quality",
    "ignore_dialogue": false,
    "preserve_formatting": true,
    "fix_hyphenation": true,
    "min_sentence_length": 3
  }
}
```

**Error Responses:**

*400 Bad Request - Invalid data*
```json
{
  "error": "Invalid settings data",
  "details": {
    "sentence_length_limit": ["Must be between 3 and 50"],
    "gemini_model": ["Must be one of: balanced, quality, speed"]
  }
}
```

**Status Codes:**
- `200 OK`: Settings updated successfully
- `400 Bad Request`: Invalid settings data
- `401 Unauthorized`: Authentication required
- `500 Internal Server Error`: Database error

---

### Retry Processing

Retry a failed processing job from the step where it failed.

**Endpoint:** `POST /history/{entry_id}/retry`

**Rate Limit:** 5 requests per hour

**Authentication:** Required (JWT Bearer token)

**URL Parameters:**
- `entry_id` (integer, required): ID of the history entry to retry

**Response:**
```json
{
  "message": "Retry functionality requires re-uploading the PDF file",
  "entry_id": 123,
  "settings": {
    "sentence_length_limit": 12,
    "gemini_model": "balanced",
    "ignore_dialogue": false,
    "preserve_formatting": true,
    "fix_hyphenation": true,
    "min_sentence_length": 3
  }
}
```

**Response Fields:**
- `message`: Instruction message
- `entry_id`: ID of the entry being retried
- `settings`: Original processing settings to use for retry

**Error Responses:**

*400 Bad Request - Entry did not fail*
```json
{
  "error": "Entry did not fail - nothing to retry"
}
```

*404 Not Found - Entry not found*
```json
{
  "error": "History entry not found"
}
```

**Status Codes:**
- `200 OK`: Retry information retrieved
- `400 Bad Request`: Entry did not fail
- `401 Unauthorized`: Authentication required
- `404 Not Found`: Entry not found
- `500 Internal Server Error`: Server error

**Note:** Currently returns the settings for manual retry. Full automatic retry with stored files is planned for future releases.

---

### Duplicate Processing Run

Get the settings from a previous processing run to duplicate it with a new file.

**Endpoint:** `POST /history/{entry_id}/duplicate`

**Rate Limit:** 5 requests per hour

**Authentication:** Required (JWT Bearer token)

**URL Parameters:**
- `entry_id` (integer, required): ID of the history entry to duplicate

**Response:**
```json
{
  "message": "Use these settings to process a new PDF",
  "settings": {
    "sentence_length_limit": 12,
    "gemini_model": "balanced",
    "ignore_dialogue": false,
    "preserve_formatting": true,
    "fix_hyphenation": true,
    "min_sentence_length": 3
  },
  "original_filename": "novel_chapter_1.pdf"
}
```

**Response Fields:**
- `message`: Instruction message
- `settings`: Processing settings to use for duplication
- `original_filename`: Name of the original file

**Error Responses:**

*400 Bad Request - No settings found*
```json
{
  "error": "No settings found for this entry"
}
```

*404 Not Found - Entry not found*
```json
{
  "error": "History entry not found"
}
```

**Status Codes:**
- `200 OK`: Duplicate settings retrieved
- `400 Bad Request`: No settings available
- `401 Unauthorized`: Authentication required
- `404 Not Found`: Entry not found
- `500 Internal Server Error`: Server error

---

### Delete History Entry

Delete a specific processing history entry.

**Endpoint:** `DELETE /history/{entry_id}`

**Authentication:** Required (JWT Bearer token)

**URL Parameters:**
- `entry_id` (integer, required): ID of the history entry to delete

**Response:**
```json
{
  "message": "History entry deleted"
}
```

**Error Responses:**

*404 Not Found - Entry not found*
```json
{
  "error": "History entry not found"
}
```

**Status Codes:**
- `200 OK`: Entry deleted successfully
- `401 Unauthorized`: Authentication required
- `404 Not Found`: Entry not found
- `500 Internal Server Error`: Server error

---

## Error Handling

All errors follow a consistent format:

```json
{
  "error": "Error message description"
}
```

Or with validation details:

```json
{
  "error": "Error message",
  "details": {
    "field_name": ["Validation error message"]
  }
}
```

### Error Codes

When processing fails, the history entry includes structured error codes to help identify the issue:

| Error Code | Description | Failed Step |
|------------|-------------|-------------|
| `INVALID_PDF` | PDF file is corrupted or unreadable | `extract` |
| `GEMINI_API_ERROR` | Error communicating with Gemini AI | `normalize` |
| `QUOTA_EXCEEDED` | API quota or rate limit exceeded | `normalize` |
| `PROCESSING_ERROR` | General processing error | `normalize` |
| `SHEETS_API_ERROR` | Error creating or updating Google Sheets | `export` |
| `PERMISSION_ERROR` | Insufficient permissions for operation | varies |

### Processing Steps

The following steps are tracked for error reporting and retry functionality:

- `upload`: File upload and validation
- `extract`: PDF text extraction
- `analyze`: Text analysis and preparation
- `normalize`: AI-powered sentence normalization
- `export`: Export to Google Sheets

## Common Status Codes

- `200 OK`: Request successful
- `400 Bad Request`: Invalid request or validation error
- `401 Unauthorized`: Authentication required or token invalid
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `413 Payload Too Large`: File or request body too large
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server-side error

## Environment Configuration

The API behavior can be configured via environment variables:

- `MAX_FILE_SIZE`: Maximum upload size in bytes (default: 50MB)
- `RATELIMIT_ENABLED`: Enable/disable rate limiting (default: True)
- `RATELIMIT_DEFAULT`: Default rate limit (default: "100 per hour")
- `GEMINI_MAX_RETRIES`: Max retries for Gemini API (default: 3)
- `CORS_ORIGINS`: Allowed CORS origins (comma-separated)

## Changelog

### v1.0.0 (2025-10-02)
- Initial API release
- PDF processing endpoint
- Google Sheets export
- History tracking
- User settings management
- Rate limiting
- Input validation

---

For questions or issues, please open a GitHub issue or contact the maintainers.


