# Wordlist Data Directory

This directory contains reference wordlist data files for the French Novel Tool.

## Files

### french_2k.txt

The French 2K wordlist containing approximately 2000 of the most common French words.

**Format:**
- One word per line
- Lines starting with `#` are comments
- Empty lines are ignored
- Supports variant notation with `|` or `/` (e.g., `bon|bonne`)

**Usage:**
This file is automatically loaded when seeding the global default wordlist using the seed script:

```bash
python scripts/seed_global_wordlist_v2.py
```

**Version:** 1.0.0

**Normalization:**
Words are normalized during ingestion:
- Diacritics removed (é → e, à → a, etc.)
- Case-folded (uppercase → lowercase)
- Elisions handled (l'homme → homme)
- Multi-token phrases reduced to head token (au revoir → au)

## Adding New Wordlists

To add a new global wordlist:

1. Create a new `.txt` file in this directory
2. Follow the format above
3. Use the `GlobalWordlistManager.create_from_file()` method:

```python
from pathlib import Path
from app.services.global_wordlist_manager import GlobalWordlistManager

wordlist = GlobalWordlistManager.create_from_file(
    filepath=Path('data/wordlists/french_5k.txt'),
    name='French 5K (v1.0.0)',
    set_as_default=False,  # True to make it the default
    version='1.0.0'
)
```

## Quality Guidelines

When creating wordlist files:

- ✅ Use authentic, commonly-used words
- ✅ Organize by categories (verbs, nouns, adjectives, etc.)
- ✅ Include comments to document sections
- ✅ Avoid duplicates (normalized forms are deduplicated automatically)
- ✅ Test with small samples before committing large lists
- ❌ Avoid very long phrases (> 3-4 words)
- ❌ Avoid numbers-only entries
- ❌ Avoid special characters like <, >, {, }, [, ]

## Versioning

Each wordlist should have a version number in its name (e.g., "v1.0.0").

When updating a wordlist:
1. Increment the version number
2. Document changes in commit message
3. Consider creating a new file rather than modifying existing ones for major changes
