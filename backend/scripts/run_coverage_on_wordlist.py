"""Run CoverageService on a provided wordlist and sentences file.

Usage:
    python backend/scripts/run_coverage_on_wordlist.py --sentences /path/to/sentences.txt

Sentences file can be either:
 - JSON array of sentence strings (utf-8)
 - Plain text with one sentence per line

Outputs are written to ./logs/ by default:
 - learning_set.csv
 - coverage_stats.json
 - coverage_covered_*.txt and coverage_uncovered_*.txt (created by the service)

Notes:
 - For best results install a spaCy French model (e.g., fr_core_news_md) in the environment.
 - If spaCy is not present, the code will fall back to a very small tokenizer/lemmatizer with limited POS info which may reduce coverage.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

# Ensure backend package is importable when run from repo root
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.services.coverage_service import CoverageService


def load_wordlist(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_sentences(path):
    """Load sentences from a file.

    Supported formats:
    - JSON list of strings
    - CSV with two columns (Index, Sentence) or with a header containing 'Index'
    - Plain text with one sentence per line
    Returns a list of sentence strings (stripped).
    """
    import csv

    # Try JSON first
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = f.read()
            data = data.strip()
            if not data:
                return []
            if data[0] in ('[', '{'):
                obj = json.loads(data)
                if isinstance(obj, list):
                    return [str(s).strip() for s in obj if s is not None]
    except Exception:
        pass

    # Try CSV: prefer second column (sentence) if present
    try:
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = [row for row in reader if any(col.strip() for col in row)]
        if rows:
            # If header looks like "Index,Sentence" or contains 'index' in first row
            first = rows[0]
            if len(first) >= 2 and any(h.lower().startswith('index') for h in first):
                # skip header row
                return [r[1].strip() for r in rows[1:] if len(r) >= 2 and r[1].strip()]
            # If all rows have at least 2 columns and the first column looks numeric, use second column
            if all(len(r) >= 2 and r[0].strip().isdigit() for r in rows):
                return [r[1].strip() for r in rows if len(r) >= 2 and r[1].strip()]
            # Fallback: if single-column CSV, treat each row as a sentence
            if all(len(r) >= 1 for r in rows):
                return [r[0].strip() for r in rows if r[0].strip()]
    except Exception:
        pass

    # Plain text fallback: one sentence per non-empty line
    with open(path, 'r', encoding='utf-8') as f:
        lines = [ln.strip() for ln in f]
    return [ln for ln in lines if ln]


def write_learning_set_csv(out_dir, learning_set):
    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, 'learning_set.csv')
    with open(csv_path, 'w', encoding='utf-8') as f:
        f.write('rank,sentence_index,token_count,new_word_count,score,sentence_text\n')
        for item in learning_set:
            text = item.get('sentence_text', '').replace('"', '""')
            f.write(f"{item.get('rank')},{item.get('sentence_index')},{item.get('token_count')},{item.get('new_word_count',0)},{item.get('score',0)},\"{text}\"\n")
    return csv_path


def write_stats(out_dir, stats):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, 'coverage_stats.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sentences', '-s', required=True, help='Path to sentences file (JSON list or TXT lines)')
    parser.add_argument('--wordlist', '-w', default=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '2k_list.json')), help='Path to wordlist JSON (default: backend/2k_list.json)')
    parser.add_argument('--out', '-o', default=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logs')), help='Output directory (default: backend/logs)')
    parser.add_argument(
        '--max-sentences',
        type=int,
        default=0,
        help="Maximum number of sentences to select for the learning set. Set to 0 for no limit."
    )
    parser.add_argument('--min-tokens', type=int, default=4, help='Minimum token count to consider (default: 4)')
    parser.add_argument('--max-tokens', type=int, default=8, help='Maximum token count to consider (default: 8)')
    args = parser.parse_args()

    # Load inputs
    print('Loading wordlist from', args.wordlist)
    wordlist = load_wordlist(args.wordlist)
    if not isinstance(wordlist, list):
        print('Wordlist must be a JSON array of strings', file=sys.stderr)
        sys.exit(2)
    wordset = set([str(w).strip() for w in wordlist if w])
    print(f'Loaded {len(wordset)} words')

    print('Loading sentences from', args.sentences)
    sentences = load_sentences(args.sentences)
    print(f'Loaded {len(sentences)} sentences')

    # Instantiate service
    svc = CoverageService(wordset, config={
        'len_min': args.min_tokens,
        'len_max': args.max_tokens,
        'target_count': args.max_sentences,
    })

    print('Running coverage greedy selection...')
    assignments, stats = svc.coverage_mode_greedy(sentences)

    # Augment stats with timestamp and parameters
    stats['run_timestamp'] = datetime.now(timezone.utc).isoformat() + 'Z'
    stats['params'] = {
        'sentences_count': len(sentences),
        'words_total': len(wordset),
        'max_sentences': args.max_sentences,
        'min_tokens': args.min_tokens,
        'max_tokens': args.max_tokens
    }

    out_dir = args.out
    csv_path = write_learning_set_csv(out_dir, stats.get('learning_set', []))
    stats_path = write_stats(out_dir, stats)

    print('\nDone.')
    print('Learning set CSV:', csv_path)
    print('Stats JSON:', stats_path)
    print('Additional covered/uncovered files (if created) are in the same output directory.')


if __name__ == '__main__':
    main()
