#!/usr/bin/env python3
"""
Wordlist Validator - Validate wordlist data files for quality issues.

Usage:
    python scripts/validate_wordlist.py data/wordlists/french_2k.txt
"""
import sys
from pathlib import Path
from typing import List, Dict, Tuple


def load_words_from_file(filepath: Path) -> List[str]:
    """Load words from a text file, excluding comments and empty lines."""
    words = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            words.append((line_num, line))
    return words


def validate_wordlist(filepath: Path) -> Tuple[bool, Dict]:
    """
    Validate a wordlist file for common issues.
    
    Returns:
        Tuple of (is_valid, issues_dict)
    """
    if not filepath.exists():
        return False, {'error': f'File not found: {filepath}'}
    
    words = load_words_from_file(filepath)
    
    issues = {
        'empty_words': [],
        'very_long_words': [],
        'numeric_words': [],
        'suspicious_chars': [],
        'whitespace_issues': [],
        'potential_duplicates': []
    }
    
    seen_normalized = {}
    
    for line_num, word in words:
        # Empty check
        if not word.strip():
            issues['empty_words'].append(line_num)
            continue
        
        # Very long words (likely phrases or errors)
        if len(word) > 50:
            issues['very_long_words'].append((line_num, word))
        
        # Numeric-only
        if word.replace('|', '').replace('/', '').replace(',', '').isdigit():
            issues['numeric_words'].append((line_num, word))
        
        # Suspicious characters
        if any(char in word for char in ['<', '>', '{', '}', '[', ']', '@', '&']):
            issues['suspicious_chars'].append((line_num, word))
        
        # Leading/trailing whitespace
        if word != word.strip():
            issues['whitespace_issues'].append((line_num, repr(word)))
        
        # Check for potential duplicates (case-insensitive)
        normalized = word.lower().strip()
        if normalized in seen_normalized:
            issues['potential_duplicates'].append(
                (line_num, word, seen_normalized[normalized])
            )
        else:
            seen_normalized[normalized] = (line_num, word)
    
    is_valid = all(
        len(v) == 0 
        for k, v in issues.items() 
        if k != 'potential_duplicates'  # Duplicates are informational, not errors
    )
    
    return is_valid, {
        'total_words': len(words),
        'issues': issues,
        'is_valid': is_valid
    }


def print_validation_report(filepath: Path, result: Dict):
    """Print a formatted validation report."""
    print("=" * 70)
    print(f"Wordlist Validation Report: {filepath.name}")
    print("=" * 70)
    print(f"\nTotal words: {result['total_words']}")
    
    if result['is_valid']:
        print("\n✅ VALIDATION PASSED - No issues found")
        return
    
    print("\n⚠️  VALIDATION ISSUES FOUND:\n")
    
    issues = result['issues']
    
    if issues['empty_words']:
        print(f"❌ Empty words: {len(issues['empty_words'])} line(s)")
        for line_num in issues['empty_words'][:5]:
            print(f"   Line {line_num}")
        if len(issues['empty_words']) > 5:
            print(f"   ... and {len(issues['empty_words']) - 5} more")
        print()
    
    if issues['very_long_words']:
        print(f"⚠️  Very long words (>50 chars): {len(issues['very_long_words'])}")
        for line_num, word in issues['very_long_words'][:5]:
            print(f"   Line {line_num}: {word[:50]}...")
        if len(issues['very_long_words']) > 5:
            print(f"   ... and {len(issues['very_long_words']) - 5} more")
        print()
    
    if issues['numeric_words']:
        print(f"⚠️  Numeric-only entries: {len(issues['numeric_words'])}")
        for line_num, word in issues['numeric_words'][:5]:
            print(f"   Line {line_num}: {word}")
        if len(issues['numeric_words']) > 5:
            print(f"   ... and {len(issues['numeric_words']) - 5} more")
        print()
    
    if issues['suspicious_chars']:
        print(f"⚠️  Suspicious characters: {len(issues['suspicious_chars'])}")
        for line_num, word in issues['suspicious_chars'][:5]:
            print(f"   Line {line_num}: {word}")
        if len(issues['suspicious_chars']) > 5:
            print(f"   ... and {len(issues['suspicious_chars']) - 5} more")
        print()
    
    if issues['whitespace_issues']:
        print(f"⚠️  Whitespace issues: {len(issues['whitespace_issues'])}")
        for line_num, word in issues['whitespace_issues'][:5]:
            print(f"   Line {line_num}: {word}")
        if len(issues['whitespace_issues']) > 5:
            print(f"   ... and {len(issues['whitespace_issues']) - 5} more")
        print()
    
    if issues['potential_duplicates']:
        print(f"ℹ️  Potential duplicates (case-insensitive): {len(issues['potential_duplicates'])}")
        for line_num, word, (orig_line, orig_word) in issues['potential_duplicates'][:5]:
            print(f"   Line {line_num}: '{word}' (duplicate of line {orig_line}: '{orig_word}')")
        if len(issues['potential_duplicates']) > 5:
            print(f"   ... and {len(issues['potential_duplicates']) - 5} more")
        print()
    
    print("=" * 70)


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/validate_wordlist.py <wordlist_file>")
        print("\nExample:")
        print("  python scripts/validate_wordlist.py data/wordlists/french_2k.txt")
        sys.exit(1)
    
    filepath = Path(sys.argv[1])
    
    is_valid, result = validate_wordlist(filepath)
    print_validation_report(filepath, result)
    
    sys.exit(0 if is_valid else 1)


if __name__ == '__main__':
    main()
