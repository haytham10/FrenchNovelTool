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

### Estimate PDF Cost

Fast metadata-only PDF cost estimation without full text extraction. Returns page count, file size, and estimated processing cost.

**Endpoint:** `POST /estimate-pdf`

**Rate Limit:** 30 requests per minute

**Authentication:** Required (JWT Bearer token)

**Request:**
- Content-Type: `multipart/form-data`
- Body:
  - `pdf_file`: PDF file (required, max 50MB)
  - `model_preference`: AI model to use (optional, default: 'balanced', values: 'balanced', 'quality', 'speed')

**Example:**
```bash
curl -X POST \
  http://localhost:5000/api/v1/estimate-pdf \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "pdf_file=@document.pdf" \
  -F "model_preference=balanced"
```

**Success Response:**
```json
{
  "page_count": 45,
  "file_size": 2457600,
  "image_count": 3,
  "estimated_tokens": 22550,
  "estimated_credits": 23,
  "model": "gemini-2.5-flash",
  "model_preference": "balanced",
  "pricing_rate": 1.0,
  "capped": false,
  "warning": null
}
```

**Response Fields:**
- `page_count`: Number of pages in the PDF
- `file_size`: File size in bytes
- `image_count`: Estimated number of images in the PDF
- `estimated_tokens`: Estimated token count for processing
- `estimated_credits`: Estimated credits required
- `model`: Actual Gemini model name to be used
- `model_preference`: User-facing model preference
- `pricing_rate`: Credits per 1,000 tokens for this model
- `capped`: True if page count exceeds maximum for estimation
- `warning`: Warning message if estimation is capped or uncertain

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

*422 Unprocessable Entity - Invalid or corrupted PDF*
```json
{
  "error": "Invalid or corrupted PDF file",
  "details": "startxref not found"
}
```

*429 Too Many Requests - Rate limit exceeded*
```json
{
  "error": "Rate limit exceeded. Please try again later."
}
```

**Status Codes:**
- `200 OK`: Estimation completed successfully
- `400 Bad Request`: Invalid request or file
- `422 Unprocessable Entity`: PDF is corrupted or cannot be read
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Estimation error

**Notes:**
- This endpoint does NOT create history entries
- This endpoint does NOT perform full text extraction
- Page count is capped at 1,000 for estimation purposes
- Estimation uses heuristic: ~500 tokens per page + 50 tokens per image
- Much faster than full text extraction (no Gemini API calls)

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

**Example:**
```bash
curl -X POST \
  http://localhost:5000/api/v1/process-pdf \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "pdf_file=@document.pdf" \
  -F "sentence_length_limit=12"
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
      "sentence_length_limit": 12
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

### Get History Detail

Retrieve detailed history entry with sentences and chunk information.

**Endpoint:** `GET /history/{entry_id}`

**Authentication:** Required (JWT Bearer token)

**Path Parameters:**
- `entry_id` (integer, required): ID of the history entry

**Response:**
```json
{
  "id": 1,
  "job_id": 42,
  "timestamp": "2025-10-02T14:30:00.000Z",
  "original_filename": "novel_chapter_1.pdf",
  "processed_sentences_count": 142,
  "spreadsheet_url": "https://docs.google.com/spreadsheets/d/SPREADSHEET_ID",
  "exported_to_sheets": true,
  "export_sheet_url": "https://docs.google.com/spreadsheets/d/SPREADSHEET_ID",
  "sentences": [
    {
      "normalized": "This is the first sentence.",
      "original": "This is the first sentence."
    },
    {
      "normalized": "This is the second sentence.",
      "original": "This is the second sentence."
    }
  ],
  "chunk_ids": [123, 124, 125],
  "chunks": [
    {
      "id": 123,
      "job_id": 42,
      "chunk_id": 0,
      "start_page": 0,
      "end_page": 4,
      "page_count": 5,
      "has_overlap": false,
      "status": "success",
      "attempts": 1,
      "max_retries": 3,
      "processed_at": "2025-10-02T14:28:00.000Z",
      "created_at": "2025-10-02T14:25:00.000Z",
      "updated_at": "2025-10-02T14:28:00.000Z"
    }
  ],
  "settings": {
    "sentence_length_limit": 12,
    "gemini_model": "balanced"
  }
}
```

**Status Codes:**
- `200 OK`: History detail retrieved successfully
- `401 Unauthorized`: Authentication required
- `404 Not Found`: History entry not found
- `500 Internal Server Error`: Database error

---

### Get History Chunks

Retrieve chunk-level processing details for a history entry.

**Endpoint:** `GET /history/{entry_id}/chunks`

**Authentication:** Required (JWT Bearer token)

**Path Parameters:**
- `entry_id` (integer, required): ID of the history entry

**Response:**
```json
{
  "chunks": [
    {
      "id": 123,
      "job_id": 42,
      "chunk_id": 0,
      "start_page": 0,
      "end_page": 4,
      "page_count": 5,
      "has_overlap": false,
      "status": "success",
      "attempts": 1,
      "max_retries": 3,
      "last_error": null,
      "last_error_code": null,
      "processed_at": "2025-10-02T14:28:00.000Z",
      "created_at": "2025-10-02T14:25:00.000Z",
      "updated_at": "2025-10-02T14:28:00.000Z"
    },
    {
      "id": 124,
      "job_id": 42,
      "chunk_id": 1,
      "start_page": 4,
      "end_page": 8,
      "page_count": 5,
      "has_overlap": true,
      "status": "failed",
      "attempts": 3,
      "max_retries": 3,
      "last_error": "API rate limit exceeded",
      "last_error_code": "RATE_LIMIT",
      "processed_at": null,
      "created_at": "2025-10-02T14:25:00.000Z",
      "updated_at": "2025-10-02T14:29:00.000Z"
    }
  ]
}
```

**Status Codes:**
- `200 OK`: Chunks retrieved successfully
- `401 Unauthorized`: Authentication required
- `404 Not Found`: History entry not found
- `500 Internal Server Error`: Database error

---

### Export History to Sheets

Export a historical job's results to Google Sheets.

**Endpoint:** `POST /history/{entry_id}/export`

**Authentication:** Required (JWT Bearer token)

**Rate Limit:** 5 requests per hour

**Path Parameters:**
- `entry_id` (integer, required): ID of the history entry

**Request:**
- Content-Type: `application/json`
- Body (optional):
```json
{
  "sheetName": "Novel Chapter 1 - Export",
  "folderId": "GOOGLE_DRIVE_FOLDER_ID"
}
```

**Parameters:**
- `sheetName` (string, optional): Name for the new Google Sheet
- `folderId` (string, optional): Google Drive folder ID to create the sheet in

**Response:**
```json
{
  "message": "Export successful",
  "spreadsheet_url": "https://docs.google.com/spreadsheets/d/SPREADSHEET_ID"
}
```

**Status Codes:**
- `200 OK`: Export successful
- `400 Bad Request`: No sentences available for this history entry
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Google Sheets access not authorized
- `404 Not Found`: History entry not found
- `500 Internal Server Error`: Export failed

---

### Get Settings

Retrieve current user settings.

**Endpoint:** `GET /settings`

**Authentication:** Required (JWT Bearer token)

**Response:**
```json
{
  "sentence_length_limit": 8
}
```

**Response Fields:**
- `sentence_length_limit`: Maximum words per sentence (integer, 3-50)

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
  "sentence_length_limit": 10
}
```

**Parameters:**
- `sentence_length_limit` (integer, required): Maximum words per sentence (3-50)

**Example:**
```bash
curl -X POST \
  http://localhost:5000/api/v1/settings \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sentence_length_limit": 10
  }'
```

**Success Response:**
```json
{
  "message": "Settings saved successfully",
  "settings": {
    "sentence_length_limit": 10
  }
}
```

**Error Responses:**

*400 Bad Request - Invalid data*
```json
{
  "error": "Invalid settings data",
  "details": {
    "sentence_length_limit": ["Must be between 3 and 50"]
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



---

## Credit System

The French Novel Tool uses a monthly credit system to manage usage. Credits are consumed based on document size and AI model used.

### Credit Allocation

- Users receive a monthly credit grant on the 1st of each month
- Default allocation: 10,000 credits per month
- Credits reset automatically at the start of each month
- Unused credits do not roll over to the next month

### Pricing

Credits are charged based on token usage and model selected:

| Model | Credits per 1,000 tokens |
|-------|-------------------------|
| Balanced (gemini-2.5-flash) | 1 |
| Speed (gemini-2.5-flash-lite) | 1 |
| Quality (gemini-2.5-pro) | 5 |

### Two-Phase Accounting

1. **Preflight Estimate**: Before processing, get a cost estimate and confirm
2. **Soft Reservation**: Credits are reserved when job is confirmed
3. **Finalization**: After processing, actual usage is calculated and credits are adjusted
4. **Refund**: If processing fails, reserved credits are fully refunded

### Get Credit Balance

Get current user's credit balance and summary.

**Endpoint:** `GET /me/credits`

**Authentication:** Required

**Response:**
```json
{
  "balance": 9500,
  "granted": 10000,
  "used": 500,
  "refunded": 0,
  "adjusted": 0,
  "month": "2025-10",
  "next_reset": "2025-11-01T00:00:00Z"
}
```

**Status Codes:**
- `200 OK`: Credit summary retrieved successfully
- `401 Unauthorized`: Authentication required

---

### Estimate Job Cost

Estimate credit cost for processing text before submitting a job.

**Endpoint:** `POST /estimate`

**Authentication:** Required

**Rate Limit:** 20 requests per minute

**Request:**
```json
{
  "text": "Content to process...",
  "model_preference": "balanced"
}
```

**Parameters:**
- `text` (string, required): Text content to estimate
- `model_preference` (string, required): Model to use - one of "balanced", "quality", "speed"

**Response:**
```json
{
  "model": "gemini-2.5-flash",
  "model_preference": "balanced",
  "estimated_tokens": 1200,
  "estimated_credits": 2,
  "pricing_rate": 1.0,
  "pricing_version": "v1.0",
  "estimation_method": "api",
  "current_balance": 9500,
  "allowed": true
}
```

**Fields:**
- `model`: Actual Gemini model name
- `model_preference`: User-friendly model preference
- `estimated_tokens`: Estimated token count
- `estimated_credits`: Estimated credits required
- `pricing_rate`: Credits per 1,000 tokens
- `pricing_version`: Pricing configuration version
- `estimation_method`: "api" (using Gemini countTokens) or "heuristic" (character-based)
- `current_balance`: User's current credit balance
- `allowed`: Whether user has sufficient credits

**Status Codes:**
- `200 OK`: Estimate calculated successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required

---

### Confirm Job

Confirm a job after reviewing the estimate. This reserves credits and creates a job entry.

**Endpoint:** `POST /jobs/confirm`

**Authentication:** Required

**Rate Limit:** 10 requests per hour

**Request:**
```json
{
  "estimated_credits": 2,
  "model_preference": "balanced",
  "processing_settings": {
    "original_filename": "chapter1.pdf",
    "estimated_tokens": 1200,
    "sentence_length_limit": 8,
    "ignore_dialogue": false
  }
}
```

**Parameters:**
- `estimated_credits` (integer, required): Credits to reserve (from estimate)
- `model_preference` (string, required): Model preference
- `processing_settings` (object, optional): Processing configuration snapshot

**Response:**
```json
{
  "job_id": 123,
  "status": "pending",
  "estimated_credits": 2,
  "reserved": true,
  "message": "Credits reserved successfully"
}
```

**Status Codes:**
- `201 Created`: Job created and credits reserved
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `402 Payment Required`: Insufficient credits

**Example Error (Insufficient Credits):**
```json
{
  "error": "Insufficient credits. Current: 100, Required: 500, Overdraft limit: -100",
  "error_code": "INSUFFICIENT_CREDITS",
  "reserved": false
}
```

---

### Finalize Job

Finalize a job after processing completes. Adjusts credits based on actual usage or refunds on failure.

**Endpoint:** `POST /jobs/{job_id}/finalize`

**Authentication:** Required

**Request:**
```json
{
  "actual_tokens": 1150,
  "success": true
}
```

**Parameters:**
- `actual_tokens` (integer, required): Actual tokens used during processing
- `success` (boolean, required): Whether processing succeeded
- `error_message` (string, optional): Error message if failed
- `error_code` (string, optional): Error code if failed

**Success Response:**
```json
{
  "job_id": 123,
  "status": "completed",
  "estimated_credits": 2,
  "actual_credits": 2,
  "adjustment": 0,
  "refunded": false,
  "message": "Job finalized successfully"
}
```

**Failure Response (with refund):**
```json
{
  "job_id": 123,
  "status": "failed",
  "estimated_credits": 2,
  "actual_credits": 0,
  "adjustment": 0,
  "refunded": true,
  "refund_amount": 2,
  "message": "Job failed, credits refunded"
}
```

**Status Codes:**
- `200 OK`: Job finalized successfully
- `400 Bad Request`: Invalid job status or request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Not authorized to finalize this job
- `404 Not Found`: Job not found

---

### Get Job Details

Get details of a specific job.

**Endpoint:** `GET /jobs/{job_id}`

**Authentication:** Required

**Response:**
```json
{
  "id": 123,
  "user_id": 1,
  "history_id": 456,
  "status": "completed",
  "original_filename": "chapter1.pdf",
  "model": "gemini-2.5-flash",
  "estimated_tokens": 1200,
  "actual_tokens": 1150,
  "estimated_credits": 2,
  "actual_credits": 2,
  "pricing_version": "v1.0",
  "pricing_rate": 1.0,
  "processing_settings": {},
  "created_at": "2025-10-03T10:00:00Z",
  "started_at": "2025-10-03T10:00:05Z",
  "completed_at": "2025-10-03T10:00:30Z",
  "error_message": null,
  "error_code": null
}
```

**Status Codes:**
- `200 OK`: Job details retrieved successfully
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Not authorized to view this job
- `404 Not Found`: Job not found

---

### List Jobs

Get list of user's jobs with optional filtering.

**Endpoint:** `GET /jobs`

**Authentication:** Required

**Query Parameters:**
- `limit` (integer, optional): Maximum number of jobs to return
- `status` (string, optional): Filter by status - one of "pending", "processing", "completed", "failed", "cancelled"

**Example:** `GET /jobs?limit=10&status=completed`

**Response:**
```json
[
  {
    "id": 123,
    "status": "completed",
    "original_filename": "chapter1.pdf",
    "estimated_credits": 2,
    "actual_credits": 2,
    "created_at": "2025-10-03T10:00:00Z",
    "completed_at": "2025-10-03T10:00:30Z"
  }
]
```

**Status Codes:**
- `200 OK`: Jobs retrieved successfully
- `401 Unauthorized`: Authentication required

---

### Get Credit Ledger

Get credit transaction history (audit trail).

**Endpoint:** `GET /credits/ledger`

**Authentication:** Required

**Query Parameters:**
- `month` (string, optional): Filter by month in YYYY-MM format
- `limit` (integer, optional): Maximum number of entries to return

**Example:** `GET /credits/ledger?month=2025-10&limit=50`

**Response:**
```json
[
  {
    "id": 1,
    "user_id": 1,
    "month": "2025-10",
    "delta_credits": 10000,
    "reason": "monthly_grant",
    "job_id": null,
    "pricing_version": "v1.0",
    "description": "Monthly credit grant for 2025-10",
    "timestamp": "2025-10-01T00:00:00Z"
  },
  {
    "id": 2,
    "user_id": 1,
    "month": "2025-10",
    "delta_credits": -2,
    "reason": "job_reserve",
    "job_id": 123,
    "pricing_version": "v1.0",
    "description": "Reserved for chapter1.pdf",
    "timestamp": "2025-10-03T10:00:00Z"
  }
]
```

**Ledger Reasons:**
- `monthly_grant`: Monthly credit allocation
- `job_reserve`: Credits reserved for a job
- `job_final`: Credit adjustment after job completion
- `job_refund`: Credits refunded for failed job
- `admin_adjustment`: Manual adjustment by administrator

**Status Codes:**
- `200 OK`: Ledger entries retrieved successfully
- `401 Unauthorized`: Authentication required

---

## Admin Operations

### Manual Credit Adjustment

Administrators can manually adjust user credits directly via database or admin panel.

**Database Method:**

```python
from app.services.credit_service import CreditService

# Grant bonus credits
CreditService.admin_adjustment(
    user_id=123,
    amount=5000,
    description="Promotional bonus credits",
    month="2025-10"
)

# Deduct credits (use negative amount)
CreditService.admin_adjustment(
    user_id=123,
    amount=-1000,
    description="Credit correction",
    month="2025-10"
)
```

**Note:** Admin UI for credit adjustments is planned for a future release.

---

## Vocabulary Coverage Tool

### Overview

The Vocabulary Coverage Tool helps language learners analyze and filter sentences based on high-frequency vocabulary. It supports two modes:

- **Coverage Mode**: Select a minimal set of sentences that covers all words in a vocabulary list
- **Filter Mode**: Find sentences with high vocabulary density (e.g., ≥95% common words) for efficient drilling

### Word List Management

#### List Word Lists

**Endpoint:** `GET /api/v1/wordlists`

**Authentication:** Required

**Response:**
```json
{
  "wordlists": [
    {
      "id": 1,
      "owner_user_id": null,
      "name": "French 2K (Global Default)",
      "source_type": "manual",
      "normalized_count": 1987,
      "canonical_samples": ["le", "de", "un", "etre", ...],
      "is_global_default": true,
      "created_at": "2024-01-15T12:00:00Z"
    },
    {
      "id": 2,
      "owner_user_id": 123,
      "name": "My Custom List",
      "source_type": "csv",
      "normalized_count": 500,
      "is_global_default": false,
      "created_at": "2024-01-16T10:00:00Z"
    }
  ]
}
```

#### Create Word List

**Endpoint:** `POST /api/v1/wordlists`

**Authentication:** Required

**Rate Limit:** 10 per hour

**Request (CSV upload):**
```
Content-Type: multipart/form-data

file: <CSV file>
name: "My French 3K List"
fold_diacritics: true
```

**Request (JSON):**
```json
{
  "name": "Custom Word List",
  "source_type": "manual",
  "words": ["le", "chat", "manger", "dormir", "maison"],
  "fold_diacritics": true
}
```

**Response:**
```json
{
  "wordlist": {
    "id": 3,
    "owner_user_id": 123,
    "name": "Custom Word List",
    "source_type": "manual",
    "normalized_count": 5,
    "canonical_samples": ["le", "chat", "manger", "dormir", "maison"],
    "is_global_default": false,
    "created_at": "2024-01-17T14:00:00Z"
  },
  "ingestion_report": {
    "original_count": 5,
    "normalized_count": 5,
    "duplicates": [],
    "multi_token_entries": [],
    "variants_expanded": 0,
    "anomalies": []
  }
}
```

#### Get Word List Details

**Endpoint:** `GET /api/v1/wordlists/:id`

**Authentication:** Required

**Response:**
```json
{
  "id": 1,
  "owner_user_id": null,
  "name": "French 2K (Global Default)",
  "source_type": "manual",
  "normalized_count": 1987,
  "canonical_samples": ["le", "de", "un", "etre", ...],
  "is_global_default": true,
  "created_at": "2024-01-15T12:00:00Z"
}
```

#### Update Word List

**Endpoint:** `PATCH /api/v1/wordlists/:id`

**Authentication:** Required (must be owner)

**Request:**
```json
{
  "name": "Updated List Name"
}
```

**Response:**
```json
{
  "id": 2,
  "name": "Updated List Name",
  ...
}
```

#### Delete Word List

**Endpoint:** `DELETE /api/v1/wordlists/:id`

**Authentication:** Required (must be owner)

**Response:**
```json
{
  "message": "WordList deleted successfully"
}
```

### Global Wordlist Management

#### Get Global Wordlist Statistics

**Endpoint:** `GET /api/v1/wordlists/global/stats`

**Authentication:** Required

**Description:** Get statistics about all global wordlists in the system.

**Response:**
```json
{
  "total_global_wordlists": 2,
  "has_default": true,
  "default_wordlist": {
    "id": 1,
    "name": "French 2K (v1.0.0)",
    "normalized_count": 1987
  },
  "all_global_wordlists": [
    {
      "id": 1,
      "name": "French 2K (v1.0.0)",
      "normalized_count": 1987,
      "is_default": true
    },
    {
      "id": 5,
      "name": "French 5K",
      "normalized_count": 4823,
      "is_default": false
    }
  ]
}
```

#### Get Global Default Wordlist

**Endpoint:** `GET /api/v1/wordlists/global/default`

**Authentication:** Required

**Description:** Get the current global default wordlist that's used when no specific wordlist is selected.

**Response:**
```json
{
  "id": 1,
  "owner_user_id": null,
  "name": "French 2K (v1.0.0)",
  "source_type": "file",
  "source_ref": "/app/data/wordlists/french_2k.txt",
  "normalized_count": 1987,
  "canonical_samples": ["le", "de", "un", "etre", ...],
  "is_global_default": true,
  "created_at": "2024-01-15T12:00:00Z",
  "updated_at": "2024-01-15T12:00:00Z"
}
```

**Error Response (404):**
```json
{
  "error": "No global default wordlist found"
}
```

#### List All Global Wordlists

**Endpoint:** `GET /api/v1/wordlists/global`

**Authentication:** Required

**Description:** List all global wordlists (those with `owner_user_id=null`). Ordered by default status and creation date.

**Response:**
```json
{
  "wordlists": [
    {
      "id": 1,
      "owner_user_id": null,
      "name": "French 2K (v1.0.0)",
      "source_type": "file",
      "normalized_count": 1987,
      "is_global_default": true,
      "created_at": "2024-01-15T12:00:00Z"
    },
    {
      "id": 5,
      "owner_user_id": null,
      "name": "French 5K",
      "source_type": "file",
      "normalized_count": 4823,
      "is_global_default": false,
      "created_at": "2024-02-01T10:00:00Z"
    }
  ],
  "total": 2
}
```

### Coverage Runs

#### Create Coverage Run

**Endpoint:** `POST /api/v1/coverage/run`

**Authentication:** Required

**Rate Limit:** 20 per hour

**Request (Filter Mode):**
```json
{
  "mode": "filter",
  "source_type": "job",
  "source_id": 123,
  "wordlist_id": 1,
  "config": {
    "min_in_list_ratio": 0.95,
    "len_min": 4,
    "len_max": 8,
    "target_count": 500
  }
}
```

**Request (Coverage Mode):**
```json
{
  "mode": "coverage",
  "source_type": "history",
  "source_id": 456,
  "wordlist_id": 1,
  "config": {
    "alpha": 0.5,
    "beta": 0.3,
    "gamma": 0.2
  }
}
```

**Parameters:**
- `mode`: "coverage" or "filter" (required)
- `source_type`: "job" or "history" (required)
- `source_id`: ID of job or history entry (required)
- `wordlist_id`: ID of word list to use (optional, uses user/global default if omitted)
- `config`: Mode-specific configuration (optional)

**Response:**
```json
{
  "coverage_run": {
    "id": 789,
    "user_id": 123,
    "mode": "filter",
    "source_type": "job",
    "source_id": 123,
    "wordlist_id": 1,
    "status": "pending",
    "progress_percent": 0,
    "created_at": "2024-01-17T15:00:00Z"
  },
  "task_id": "abc123-def456-..."
}
```

#### Get Coverage Run Status

**Endpoint:** `GET /api/v1/coverage/runs/:id`

**Authentication:** Required (must be owner)

**Query Parameters:**
- `page`: Page number for assignments (default: 1)
- `per_page`: Results per page (default: 50, max: 100)

**Response (Pending):**
```json
{
  "coverage_run": {
    "id": 789,
    "mode": "filter",
    "status": "processing",
    "progress_percent": 45,
    "created_at": "2024-01-17T15:00:00Z"
  },
  "assignments": [],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 0,
    "pages": 0
  }
}
```

**Response (Completed - Filter Mode):**
```json
{
  "coverage_run": {
    "id": 789,
    "mode": "filter",
    "status": "completed",
    "progress_percent": 100,
    "stats_json": {
      "total_sentences": 5000,
      "candidates_passed_filter": 1200,
      "selected_count": 500,
      "filter_acceptance_ratio": 0.24,
      "min_in_list_ratio": 0.95,
      "len_min": 4,
      "len_max": 8
    },
    "completed_at": "2024-01-17T15:05:00Z"
  },
  "assignments": [
    {
      "id": 1,
      "word_key": "chat",
      "sentence_index": 42,
      "sentence_text": "Le chat dort sur le tapis.",
      "sentence_score": 9.8,
      "in_list_ratio": 1.0
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 500,
    "pages": 10
  }
}
```

**Response (Completed - Coverage Mode):**
```json
{
  "coverage_run": {
    "id": 790,
    "mode": "coverage",
    "status": "completed",
    "stats_json": {
      "words_total": 2000,
      "words_covered": 1850,
      "words_uncovered": 150,
      "uncovered_words": ["xylophone", "zèbre", ...],
      "selected_sentence_count": 423,
      "total_sentences": 5000
    },
    "completed_at": "2024-01-17T15:10:00Z"
  },
  "assignments": [
    {
      "id": 1,
      "word_key": "chat",
      "word_original": "chat",
      "lemma": "chat",
      "matched_surface": "chat",
      "sentence_index": 42,
      "sentence_text": "Le chat dort bien.",
      "sentence_score": 0.95
    }
  ],
  "pagination": {...}
}
```

#### Swap Assignment (Coverage Mode)

**Endpoint:** `POST /api/v1/coverage/runs/:id/swap`

**Authentication:** Required (must be owner)

**Request:**
```json
{
  "word_key": "chat",
  "new_sentence_index": 100
}
```

**Response:**
```json
{
  "id": 1,
  "word_key": "chat",
  "sentence_index": 100,
  "sentence_text": "Un petit chat joue.",
  "manual_edit": true
}
```

#### Export Coverage Run

**Endpoint:** `POST /api/v1/coverage/runs/:id/export`

**Authentication:** Required (must be owner)

**Rate Limit:** 10 per hour

**Request:**
```json
{
  "sheet_name": "French Drilling - Week 1",
  "folder_id": "1ABC..."
}
```

**Response:**
```json
{
  "message": "Export functionality coming soon",
  "sheet_name": "French Drilling - Week 1"
}
```

**Note:** Export functionality is planned for a future release.

### User Settings Extension

The user settings endpoint now supports coverage-related settings:

**Endpoint:** `POST /api/v1/user/settings`

**Request:**
```json
{
  "sentence_length_limit": 8,
  "gemini_model": "speed",
  "default_wordlist_id": 1,
  "coverage_defaults": {
    "mode": "filter",
    "min_in_list_ratio": 0.95,
    "len_min": 4,
    "len_max": 8,
    "target_count": 500
  }
}
```

**Response:**
```json
{
  "message": "Settings saved successfully",
  "settings": {
    "sentence_length_limit": 8,
    "gemini_model": "speed",
    "default_wordlist_id": 1,
    "coverage_defaults": {
      "mode": "filter",
      "min_in_list_ratio": 0.95,
      "len_min": 4,
      "len_max": 8,
      "target_count": 500
    }
  }
}
```

### Configuration Options

#### Coverage Mode Config
```json
{
  "alpha": 0.5,           // Duplicate penalty weight
  "beta": 0.3,            // Quality weight
  "gamma": 0.2,           // Length penalty weight
  "target_sentence_length": 6,
  "max_sentences": 1000
}
```

#### Filter Mode Config
```json
{
  "min_in_list_ratio": 0.95,    // Minimum % of words in list (0.0-1.0)
  "len_min": 4,                  // Minimum sentence length (tokens)
  "len_max": 8,                  // Maximum sentence length (tokens)
  "target_count": 500,           // Number of sentences to select
  "frequency_weighting": true,   // Prefer higher-frequency words
  "diversity_penalty": 0.2       // Reduce near-duplicates
}
```

#### Normalization Config (Shared)
```json
{
  "normalize_mode": "lemma",      // Normalization method
  "fold_diacritics": true,        // Remove diacritics (café → cafe)
  "handle_elisions": true         // Handle l', d', etc.
}
```

---

## Error Handling

### Credit-Related Error Codes

- `INSUFFICIENT_CREDITS`: User does not have enough credits
- `JOB_NOT_FOUND`: Job ID does not exist
- `INVALID_JOB_STATUS`: Job is in wrong status for the requested operation

### Coverage-Related Error Codes

- `WORDLIST_NOT_FOUND`: Specified word list does not exist
- `NO_DEFAULT_WORDLIST`: No word list specified and no default found
- `INVALID_SOURCE`: Source job or history entry not found or invalid
- `NO_SENTENCES`: Source has no sentences to analyze

### HTTP Status Codes

- `402 Payment Required`: Insufficient credits (specific to credit system)
- All standard HTTP status codes apply (400, 401, 403, 404, 500, etc.)

---
