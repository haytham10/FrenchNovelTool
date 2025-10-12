#!/usr/bin/env python
"""Test script to verify wordlist parsing from Google Sheets format"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.services.wordlist_service import WordListService

# Sample data from the Google Sheet (Column B)
sample_words = [
    "Un|Une",      # Row 1
    "À",           # Row 2
    "En",          # Row 3
    "Le|La",       # Row 4
    "Et",          # Row 5
    "Être",        # Row 6
    "De",          # Row 7
    "Avoir",       # Row 8
    "Que",         # Row 9
    "Ne",          # Row 10
    "Dans",        # Row 11
    "Ce|Cette",    # Row 12
    "Il",          # Row 13
    "Qui",         # Row 14
    "Pas",         # Row 15
    "Pour",        # Row 16
    "Sur",         # Row 17
    "Se",          # Row 18
    "Son",         # Row 19
    "Plus",        # Row 20
]

def test_word_normalization():
    """Test individual word normalization"""
    print("=" * 60)
    print("Testing Word Normalization")
    print("=" * 60)
    
    service = WordListService()
    
    for word in sample_words:
        variants = service.split_variants(word)
        print(f"\nOriginal: '{word}'")
        print(f"  Variants: {variants}")
        
        for variant in variants:
            normalized = service.normalize_word(variant, fold_diacritics=True)
            print(f"    '{variant}' -> '{normalized}'")

def test_wordlist_ingestion():
    """Test full wordlist ingestion"""
    print("\n" + "=" * 60)
    print("Testing Full Wordlist Ingestion")
    print("=" * 60)
    
    service = WordListService()
    
    # Don't actually save to DB, just process
    ingestion_report = {
        'original_count': len(sample_words),
        'normalized_count': 0,
        'duplicates': [],
        'multi_token_entries': [],
        'variants_expanded': 0,
        'anomalies': []
    }
    
    normalized_keys = set()
    
    for idx, raw_word in enumerate(sample_words):
        if not raw_word or not raw_word.strip():
            continue
        
        # Split variants
        variants = service.split_variants(raw_word)
        if len(variants) > 1:
            ingestion_report['variants_expanded'] += len(variants) - 1
        
        for variant in variants:
            # Check for multi-token
            tokens = variant.split()
            if len(tokens) > 1:
                ingestion_report['multi_token_entries'].append({
                    'original': variant,
                    'head_token': service.extract_head_token(variant)
                })
                variant = service.extract_head_token(variant)
            
            # Normalize
            normalized = service.normalize_word(variant, fold_diacritics=True)
            
            if not normalized:
                ingestion_report['anomalies'].append({
                    'word': raw_word,
                    'issue': 'empty_after_normalization'
                })
                continue
            
            # Check for duplicates
            if normalized in normalized_keys:
                ingestion_report['duplicates'].append({
                    'word': variant,
                    'normalized': normalized
                })
            else:
                normalized_keys.add(normalized)
    
    ingestion_report['normalized_count'] = len(normalized_keys)
    
    print(f"\nIngestion Report:")
    print(f"  Original Count: {ingestion_report['original_count']}")
    print(f"  Normalized Count: {ingestion_report['normalized_count']}")
    print(f"  Variants Expanded: {ingestion_report['variants_expanded']}")
    print(f"  Multi-token Entries: {len(ingestion_report['multi_token_entries'])}")
    print(f"  Duplicates: {len(ingestion_report['duplicates'])}")
    print(f"  Anomalies: {len(ingestion_report['anomalies'])}")
    
    print(f"\nNormalized Keys (first 30):")
    for key in sorted(list(normalized_keys))[:30]:
        print(f"  - {key}")

def test_sheets_parsing_simulation():
    """Simulate Google Sheets parsing"""
    print("\n" + "=" * 60)
    print("Simulating Google Sheets Column B Parsing")
    print("=" * 60)
    
    # Simulate what comes from Google Sheets (with potential issues)
    raw_sheet_data = [
        ["Un|Une"],       # Row 1
        ["À"],            # Row 2  
        ["En"],           # Row 3
        ["Le|La"],        # Row 4
        ["Et"],           # Row 5
        ["Être"],         # Row 6
        ["1 De"],         # Row 7 - with leading number
        ["Avoir"],        # Row 8
        [" Que "],        # Row 9 - with spaces
        ["Ne"],           # Row 10
        [""],             # Row 11 - empty
        ["Ce|Cette"],     # Row 12
    ]
    
    print("\nProcessing sheet data:")
    words = []
    
    for idx, row in enumerate(raw_sheet_data):
        if not row or not row[0]:
            print(f"  Row {idx+1}: [empty] -> skipped")
            continue
        
        cell = str(row[0]).strip()
        
        # Remove leading numeric indices
        import re
        original_cell = cell
        cell = re.sub(r'^\s*\d+\s*[-.:)\]]*\s*', '', cell)
        
        if original_cell != cell:
            print(f"  Row {idx+1}: '{original_cell}' -> '{cell}' (removed leading number)")
        else:
            print(f"  Row {idx+1}: '{cell}'")
        
        if cell:
            words.append(cell)
    
    print(f"\nExtracted {len(words)} words: {words}")

if __name__ == '__main__':
    test_word_normalization()
    test_wordlist_ingestion()
    test_sheets_parsing_simulation()
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
