# API Documentation

French Novel Tool API v1.0

Base URL: `http://localhost:5000/api/v1` (development)

## Overview

The French Novel Tool API provides endpoints for processing French PDF documents using AI, managing processing history, and exporting results to Google Sheets.

## Authentication

Currently, no authentication is required. This will be added in future versions.

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

**Request:**
- Content-Type: `multipart/form-data`
- Body:
  - `pdf_file`: PDF file (required, max 50MB)

**Example:**
```bash
curl -X POST \
  http://localhost:5000/api/v1/process-pdf \
  -F "pdf_file=@document.pdf"
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

**Rate Limit:** 20 requests per hour

**Request:**
- Content-Type: `application/json`
- Body:
```json
{
  "sentences": ["Sentence 1", "Sentence 2", "..."],
  "sheetName": "My French Novel",
  "folderId": "optional-google-drive-folder-id"
}
```

**Parameters:**
- `sentences` (array, required): Array of sentences to export (1-10000 items, each 1-5000 chars)
- `sheetName` (string, required): Name for the spreadsheet (1-255 chars)
- `folderId` (string, optional): Google Drive folder ID to place spreadsheet in

**Example:**
```bash
curl -X POST \
  http://localhost:5000/api/v1/export-to-sheet \
  -H "Content-Type: application/json" \
  -d '{
    "sentences": ["Première phrase.", "Deuxième phrase."],
    "sheetName": "French Novel Export",
    "folderId": "1abc2def3ghi4jkl5mno"
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

**Response:**
```json
[
  {
    "id": 1,
    "timestamp": "2025-10-02T14:30:00.000Z",
    "original_filename": "novel_chapter_1.pdf",
    "processed_sentences_count": 142,
    "spreadsheet_url": "https://docs.google.com/spreadsheets/d/SPREADSHEET_ID",
    "error_message": null
  },
  {
    "id": 2,
    "timestamp": "2025-10-02T15:45:00.000Z",
    "original_filename": "novel_chapter_2.pdf",
    "processed_sentences_count": 0,
    "spreadsheet_url": null,
    "error_message": "Failed to process PDF: File corrupted"
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

**Status Codes:**
- `200 OK`: History retrieved successfully
- `500 Internal Server Error`: Database error

---

### Get Settings

Retrieve current user settings.

**Endpoint:** `GET /settings`

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
- `500 Internal Server Error`: Database error

---

### Update Settings

Update user settings.

**Endpoint:** `POST /settings`

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
  -H "Content-Type: application/json" \
  -d '{"sentence_length_limit": 10}'
```

**Success Response:**
```json
{
  "message": "Settings saved successfully"
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
- `500 Internal Server Error`: Database error

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

## Common Status Codes

- `200 OK`: Request successful
- `400 Bad Request`: Invalid request or validation error
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


