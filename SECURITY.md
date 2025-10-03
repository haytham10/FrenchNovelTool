# Security Policy

## Reporting a Vulnerability
If you discover a security issue, please email haytham4523@gmail.com or open a private GitHub security advisory. We will respond as quickly as possible.

## Data Handling
- All uploaded PDFs are processed in-memory or stored temporarily for processing only.
- PDFs are not retained after processing is complete, except for minimal metadata (filename, processing status, and user association) in the database for history/audit purposes.
- Processed text and results are only stored as long as needed to complete the export to Google Sheets.
- No PDF content is shared with third parties except Google Gemini AI (for normalization) and Google Sheets (for export), using secure, authenticated API calls.
- User OAuth tokens are encrypted at rest and never shared.

## Deletion Policy
- PDFs and their extracted text are deleted from server storage immediately after processing/export.
- Users can delete their processing history at any time, which removes all associated metadata.

## Infrastructure
- All API endpoints are protected by JWT authentication and rate limiting.
- HTTPS is required in production deployments.
- Regular dependency updates and security reviews are performed.
