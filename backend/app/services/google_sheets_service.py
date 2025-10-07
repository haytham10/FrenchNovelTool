"""Service for Google Sheets and Drive API interactions"""
import os
import re
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from flask import current_app

logger = logging.getLogger(__name__)


class GoogleSheetsService:
    """Service for creating and managing Google Sheets exports using user OAuth credentials"""
    def fetch_words_from_spreadsheet(self, creds, spreadsheet_id: str, sheet_title: str | None = None,
                                     column: str = 'B', include_header: bool = True) -> list[str]:
        """Fetch a list of words from a Google Spreadsheet column.

        Args:
            creds: Authorized user credentials
            spreadsheet_id: The spreadsheet ID
            sheet_title: Optional specific sheet/tab title; if None, use the first sheet
            column: Column letter to read from (default 'B')
            include_header: Whether to include the first row (header) in the results

        Returns:
            List of non-empty strings from the specified column
        """
        sheets_service = build('sheets', 'v4', credentials=creds)

        # Determine the target sheet title if not provided
        if not sheet_title:
            try:
                spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
                sheets = spreadsheet.get('sheets', [])
                if not sheets:
                    raise ValueError('Spreadsheet has no sheets')
                sheet_title = sheets[0]['properties']['title']
            except Exception as e:
                current_app.logger.error(f'Failed to read spreadsheet metadata: {e}')
                raise

        def _read_column(col: str) -> list[list[str]]:
            rng = f"{sheet_title}!{col}:{col}"
            res = sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=rng
            ).execute()
            return res.get('values', [])

        # Read values from the preferred column
        values = _read_column(column)

        # Flatten and clean
        words: list[str] = []
        
        # Skip first row if it looks like a header
        start_index = 0
        if values and len(values) > 0:
            first_cell = str(values[0][0]).strip().lower()
            # Common header patterns
            if first_cell in ('index', 'word', 'mot', 'term', 'french', 'uni|une', 'a|an'):
                start_index = 1
                logger.info(f"Skipping header row: {values[0][0]}")
        
        for idx, row in enumerate(values):
            if idx < start_index:
                continue
            if not row:
                continue
            
            cell = str(row[0]).strip()
            if not cell:
                continue

            # Remove leading numeric indices that may be present in the same cell (e.g. "1 Un|Une")
            # This handles cases where index and word are in the same cell
            cell = re.sub(r'^\s*\d+\s*[-.:)\]]*\s*', '', cell)

            # Skip if it's just a number (standalone index)
            if re.match(r'^\d+$', cell):
                continue
            
            # Skip common header labels (but be more conservative)
            lower = cell.lower()
            if lower in ('index', 'word', 'mot', 'term', 'sentence', 'sentence_text', 'word_text', 'part of speech', 'pos', 'translation', 'english'):
                continue

            # Valid word - add it (variants will be split by WordListService)
            if cell:
                words.append(cell)
        
        # If almost nothing found, try fallback column (common layout: A=french, B=english)
        if len(words) < 10 and column.upper() == 'B':
            logger.info("Few words detected in column B, attempting fallback to column A")
            values_a = _read_column('A')
            words_a: list[str] = []
            if values_a:
                # Reuse same cleaning logic for column A
                start_index_a = 0
                if values_a and len(values_a) > 0:
                    first_cell_a = str(values_a[0][0]).strip().lower()
                    if first_cell_a in ('index', 'word', 'mot', 'term', 'french', 'uni|une', 'a|an'):
                        start_index_a = 1
                        logger.info(f"Skipping header row in A: {values_a[0][0]}")
                for idx, row in enumerate(values_a):
                    if idx < start_index_a:
                        continue
                    if not row:
                        continue
                    cell = str(row[0]).strip()
                    if not cell:
                        continue
                    cell = re.sub(r'^\s*\d+\s*[-.:)\]]*\s*', '', cell)
                    if re.match(r'^\d+$', cell):
                        continue
                    lower = cell.lower()
                    if lower in ('index', 'word', 'mot', 'term', 'sentence', 'sentence_text', 'word_text', 'part of speech', 'pos', 'translation', 'english'):
                        continue
                    if cell:
                        words_a.append(cell)
            if len(words_a) > len(words):
                logger.info(f"Using fallback column A with {len(words_a)} words (B had {len(words)})")
                words = words_a

        logger.info(f"Extracted {len(words)} words from column {column}. Sample: {words[:5]}")
        return words
    
    def export_to_sheet(self, creds, sentences, sheet_name="French Novel Sentences", folder_id=None,
                       mode='new', existing_sheet_id=None, tab_name=None, create_new_tab=False,
                       headers=None, column_order=None, sharing=None, sentence_indices=None):
        sheets_service = build('sheets', 'v4', credentials=creds)
        drive_service = build('drive', 'v3', credentials=creds)

        # Filter sentences if specific indices provided
        if sentence_indices:
            sentences = [sentences[i] for i in sentence_indices if i < len(sentences)]
        
        # Handle append mode
        if mode == 'append' and existing_sheet_id:
            spreadsheet_id = existing_sheet_id
            target_tab = tab_name or 'Sheet1'
            
            # Get spreadsheet to check if tab exists
            try:
                spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
                sheets = spreadsheet.get('sheets', [])
                
                # Find target sheet
                sheet_id = None
                for sheet in sheets:
                    if sheet['properties']['title'] == target_tab:
                        sheet_id = sheet['properties']['sheetId']
                        break
                
                # Create new tab if requested and doesn't exist
                if sheet_id is None and create_new_tab:
                    add_sheet_request = {
                        'requests': [{
                            'addSheet': {
                                'properties': {
                                    'title': target_tab
                                }
                            }
                        }]
                    }
                    response = sheets_service.spreadsheets().batchUpdate(
                        spreadsheetId=spreadsheet_id, 
                        body=add_sheet_request
                    ).execute()
                    sheet_id = response['replies'][0]['addSheet']['properties']['sheetId']
                elif sheet_id is None:
                    raise ValueError(f"Tab '{target_tab}' not found and create_new_tab is False")
                
                # Get existing data to append after last row
                range_name = f"{target_tab}!A:B"
                result = sheets_service.spreadsheets().values().get(
                    spreadsheetId=spreadsheet_id, 
                    range=range_name
                ).execute()
                existing_rows = len(result.get('values', []))
                
                # Prepare values (no header row for append)
                values = [[i+1, sentence] for i, sentence in enumerate(sentences, start=existing_rows)]
                
            except Exception as e:
                current_app.logger.error(f'Error appending to sheet: {str(e)}')
                raise ValueError(f"Failed to append to sheet: {str(e)}")
        else:
            # Create new spreadsheet
            spreadsheet = {
                'properties': {
                    'title': sheet_name
                }
            }
            spreadsheet = sheets_service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId').execute()
            spreadsheet_id = spreadsheet.get('spreadsheetId')
            sheet_id = 0  # Default sheet ID
            target_tab = 'Sheet1'

            if folder_id:
                # Move the file to the specified folder
                file_id = spreadsheet_id
                # Retrieve the existing parents to remove them
                file = drive_service.files().get(fileId=file_id, fields='parents').execute()
                previous_parents = ",".join(file.get('parents'))
                # Move the file to the new folder
                drive_service.files().update(
                    fileId=file_id,
                    addParents=folder_id,
                    removeParents=previous_parents,
                    fields='id, parents'
                ).execute()

            # Prepare headers with custom headers if provided
            if headers and column_order:
                # Build header row based on enabled headers and order
                enabled_headers = sorted(
                    [h for h in headers if h.get('enabled', True)],
                    key=lambda x: x.get('order', 0)
                )
                header_row = [h['name'] for h in enabled_headers]
                # For simplicity, we'll stick with Index and Sentence for now
                # Full custom column support would require more complex mapping
                header_row = ["Index", "Sentence"]
            else:
                header_row = ["Index", "Sentence"]
            
            values = [header_row] + [[i+1, sentence] for i, sentence in enumerate(sentences)]

        body = {
            'values': values
        }
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id, range='A1', 
            valueInputOption='RAW', body=body).execute()

        requests = [
            {
                'repeatCell': {
                    'range': {
                        'sheetId': 0,
                        'startRowIndex': 0,
                        'endRowIndex': 1
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {
                                'red': 0.2, 
                                'green': 0.6, 
                                'blue': 0.8
                            },
                            'textFormat': {
                                'foregroundColor': {
                                    'red': 1, 
                                    'green': 1, 
                                    'blue': 1
                                },
                                'bold': True
                            }
                        }
                    },
                    'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                }
            },
            {
                'autoResizeDimensions': {
                    'dimensions': {
                        'sheetId': 0,
                        'dimension': 'ROWS',
                        'startIndex': 0,
                        'endIndex': len(values)
                    }
                }
            },
            {
                'autoResizeDimensions': {
                    'dimensions': {
                        'sheetId': 0,
                        'dimension': 'COLUMNS',
                        'startIndex': 0,
                        'endIndex': 2
                    }
                }
            }
        ]

        body = {
            'requests': requests
        }
        sheets_service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()

        # Handle sharing settings
        if sharing and mode != 'append':  # Only apply sharing for new sheets
            try:
                # Add collaborators
                if sharing.get('addCollaborators') and sharing.get('collaboratorEmails'):
                    for email in sharing['collaboratorEmails']:
                        if email and email.strip():
                            permission = {
                                'type': 'user',
                                'role': 'writer',
                                'emailAddress': email.strip()
                            }
                            drive_service.permissions().create(
                                fileId=spreadsheet_id,
                                body=permission,
                                sendNotificationEmail=False
                            ).execute()
                
                # Enable anyone with link access
                if sharing.get('publicLink'):
                    permission = {
                        'type': 'anyone',
                        'role': 'reader'
                    }
                    drive_service.permissions().create(
                        fileId=spreadsheet_id,
                        body=permission
                    ).execute()
            except Exception as e:
                current_app.logger.warning(f'Failed to apply sharing settings: {str(e)}')
                # Don't fail the export if sharing fails

        return f'https://docs.google.com/spreadsheets/d/{spreadsheet_id}'