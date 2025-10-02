"""Service for Google Sheets and Drive API interactions"""
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from flask import current_app


class GoogleSheetsService:
    """Service for creating and managing Google Sheets exports using user OAuth credentials"""
    
    def export_to_sheet(self, creds, sentences, sheet_name="French Novel Sentences", folder_id=None):
        sheets_service = build('sheets', 'v4', credentials=creds)
        drive_service = build('drive', 'v3', credentials=creds)

        spreadsheet = {
            'properties': {
                'title': sheet_name
            }
        }
        spreadsheet = sheets_service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId').execute()
        spreadsheet_id = spreadsheet.get('spreadsheetId')

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

        values = [["Index", "Sentence"]] + [[i+1, sentence] for i, sentence in enumerate(sentences)]

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

        return f'https://docs.google.com/spreadsheets/d/{spreadsheet_id}'