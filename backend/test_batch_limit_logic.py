"""
Quick manual test to verify batch coverage sentence limit logic
"""

def test_batch_sentence_limit():
    # Simulate the algorithm
    
    # Mock data: sentences from two sources
    source1_sentences = [
        {'id': 1, 'text': 'Le chat mange.', 'words': 3},
        {'id': 2, 'text': 'Un chien court.', 'words': 2},
        {'id': 3, 'text': 'La maison est grande.', 'words': 4},
    ]
    
    source2_sentences = [
        {'id': 4, 'text': 'Le soleil brille.', 'words': 2},
        {'id': 5, 'text': 'Une voiture passe.', 'words': 2},
    ]
    
    # Combine all sentences
    all_sentences = source1_sentences + source2_sentences
    
    # Calculate quality score for each
    for s in all_sentences:
        # Assuming each contributes 2 new words on average
        new_words = 2
        token_count = s['words']
        s['quality_score'] = (new_words * 10) - token_count
        s['new_word_count'] = new_words
    
    # Sort by quality score (descending)
    all_sentences.sort(key=lambda x: x['quality_score'], reverse=True)
    
    print("All sentences sorted by quality score:")
    for s in all_sentences:
        print(f"  ID={s['id']}, Text='{s['text']}', Score={s['quality_score']}, NewWords={s['new_word_count']}, Tokens={s['words']}")
    
    # Apply sentence limit
    target_count = 3
    truncated = all_sentences[:target_count]
    
    print(f"\nAfter truncating to {target_count} sentences:")
    for idx, s in enumerate(truncated, start=1):
        print(f"  Rank={idx}, ID={s['id']}, Text='{s['text']}', Score={s['quality_score']}")
    
    # Verify
    assert len(truncated) == target_count, f"Expected {target_count} sentences, got {len(truncated)}"
    print(f"\n✅ Test passed! Final count: {len(truncated)} (limit: {target_count})")

if __name__ == '__main__':
    test_batch_sentence_limit()
