# Coverage Tool - Word List Parsing Fix

## Problem
The vocabulary coverage tool was not properly parsing word lists from Google Sheets with the format:
- Column A: Index (1, 2, 3, ...)
- Column B: French word with variants (Un|Une, Le|La, etc.)
- Column C: English translation
- Column D: Part of Speech

## Solution

### 1. **Improved Google Sheets Parsing** (`google_sheets_service.py`)

#### Changes Made:
- Added logging import for better debugging
- Enhanced header detection to skip common header patterns
- Better handling of leading numbers in cells
- More conservative filtering to avoid skipping valid words
- Added detailed logging of extracted words

#### Key Features:
```python
# Automatically detects and skips headers
if first_cell in ('index', 'word', 'mot', 'term', 'french', 'uni|une', 'a|an'):
    start_index = 1

# Removes leading numbers (e.g., "1 Un|Une" -> "Un|Une")
cell = re.sub(r'^\s*\d+\s*[-.:)\]]*\s*', '', cell)

# Skips standalone index numbers
if re.match(r'^\d+$', cell):
    continue

# Logs extraction results
logger.info(f"Extracted {len(words)} words from column {column}. Sample: {words[:5]}")
```

### 2. **Enhanced Word Normalization** (`wordlist_service.py`)

#### Changes Made:
- Fixed order of operations: handle elisions BEFORE removing apostrophes
- Added support for removing leading numbers in word normalization
- Improved variant splitting to handle commas in addition to pipes and slashes
- Better handling of quoted strings from spreadsheets

#### Normalization Process:
1. Trim whitespace and remove zero-width characters
2. Remove surrounding quotes/apostrophes
3. Remove leading numbers (e.g., "1. avoir" -> "avoir")
4. Handle elisions (l', d', j', etc.) - extract the word after the elision
5. Remove internal apostrophes for non-elision words
6. Convert to lowercase (casefold)
7. Remove diacritics (optional, default true)

#### Variant Splitting:
```python
# Splits on |, /, or comma
variants = re.split(r'\s*[|/,]\s*', word)

# Example: "Un|Une" -> ["Un", "Une"]
# Example: "avoir/être" -> ["avoir", "être"]
```

### 3. **Example Processing**

#### Input (from Google Sheet):
```
Column B:
Un|Une
À
En
Le|La
Et
Être
De
Avoir
...
```

#### Processing Steps:
1. **Fetch from Sheet**: Extract all values from Column B
2. **Filter**: Remove headers, empty cells, standalone numbers
3. **Split Variants**: "Un|Une" becomes ["Un", "Une"]
4. **Normalize Each Variant**:
   - "Un" -> "un"
   - "Une" -> "une"
   - "À" -> "a" (diacritics removed)
   - "Être" -> "etre"

#### Result:
- Original count: 20 words with variants
- Normalized count: 23 unique normalized words
- All variants properly expanded and normalized

### 4. **Testing**

Run the test script to verify parsing:
```bash
cd backend
python test_wordlist_parsing.py
```

Expected output:
- Variant splitting working correctly
- Normalization handling diacritics and elisions
- Google Sheets format properly parsed
- No anomalies or errors

## Usage in Production

### Creating a Word List from Google Sheets:

1. **Via API**:
```bash
POST /api/v1/wordlists
Content-Type: application/json

{
  "name": "French 2K Words",
  "source_type": "google_sheet",
  "source_ref": "15BL8bFX5KTbXguLzF44wZ8NXluoKXdGfYSc4cHBuEj0",
  "fold_diacritics": true
}
```

2. **Via Frontend Settings**:
- Paste Google Sheets URL
- Enter a name for the word list
- Click "Import from Sheets"

### Expected Behavior:
- Reads from Column B by default
- Automatically detects and skips header row
- Expands pipe-separated variants (Un|Une -> Un, Une)
- Normalizes each word (removes diacritics, handles elisions)
- Stores full normalized word list in `words_json` field
- Stores sample of 20 words in `canonical_samples` field

## Configuration

### Column Selection:
Default: Column B (contains French words)

Can be customized in code:
```python
words = sheets_service.fetch_words_from_spreadsheet(
    creds,
    spreadsheet_id=sheet_id,
    column='B',  # Change to 'A', 'C', etc. as needed
    include_header=True
)
```

### Normalization Options:
- `fold_diacritics`: Remove accents (é->e, à->a) - default True
- `handle_elisions`: Extract word after elision (l'homme -> homme) - always True

## Troubleshooting

### Issue: Words not being imported
**Solution**: Check that words are in Column B and not Column A

### Issue: Variants not being split
**Solution**: Ensure variants are separated by | or / (e.g., "Un|Une" not "Un Une")

### Issue: Headers being included as words
**Solution**: The service now auto-detects common headers. If custom header, ensure it's in the skip list.

### Issue: Leading numbers in words
**Solution**: Now automatically handled (e.g., "1 Un|Une" -> "Un|Une")

## Files Modified

1. `backend/app/services/google_sheets_service.py`:
   - Added logging
   - Improved header detection
   - Better cell cleaning and filtering

2. `backend/app/services/wordlist_service.py`:
   - Fixed normalization order (elisions before apostrophe removal)
   - Enhanced variant splitting
   - Added leading number removal

3. `backend/test_wordlist_parsing.py` (new):
   - Test script to verify parsing functionality

## Verification

To verify the fix is working:

1. Check logs for word extraction:
```
INFO - Extracted 2000 words from column B. Sample: ['Un|Une', 'À', 'En', ...]
```

2. Check ingestion report:
```json
{
  "original_count": 2000,
  "normalized_count": 2500,
  "variants_expanded": 500,
  "duplicates": [],
  "anomalies": []
}
```

3. Verify word list in database:
```python
wordlist = WordList.query.get(id)
print(f"Words in list: {len(wordlist.words_json)}")
print(f"Sample: {wordlist.canonical_samples[:10]}")
```

## Next Steps

If using a different Google Sheets format:
1. Identify which column contains the words
2. Update the `column` parameter in the API call
3. If custom headers, add them to the skip list in `google_sheets_service.py`
4. Test with the test script before deploying
