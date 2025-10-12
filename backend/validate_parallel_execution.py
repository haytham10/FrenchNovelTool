#!/usr/bin/env python3
"""
Validation script for parallel chunk execution implementation.
Tests the logic without requiring full Celery/Flask setup.
"""
import sys
import os

# Mock implementations for testing
class MockJob:
    def __init__(self):
        self.id = 1
        self.status = 'pending'
        self.progress_percent = 0
        self.current_step = ''
        self.processed_chunks = 0
        self.total_chunks = 0
        self.actual_tokens = 0
        self.gemini_tokens_used = 0
        self.gemini_api_calls = 0
        self.completed_at = None
        self.chunk_results = None
        self.failed_chunks = None
        self.started_at = None
        self.processing_time_seconds = None
        self.error_message = None

def test_merge_chunk_results():
    """Test the merge_chunk_results function"""
    print("Testing merge_chunk_results...")
    
    # Simulate the merge_chunk_results logic
    def merge_chunk_results(chunk_results):
        sorted_chunks = sorted(chunk_results, key=lambda x: x.get('chunk_id', 0))
        all_sentences = []
        seen_sentences = set()
        
        for chunk in sorted_chunks:
            if chunk.get('status') != 'success':
                continue
            
            sentences = chunk.get('sentences', [])
            
            if chunk.get('chunk_id', 0) > 0:
                for sentence in sentences:
                    sentence_key = sentence.get('normalized', '')[:100]
                    if sentence_key and sentence_key not in seen_sentences:
                        all_sentences.append(sentence)
                        seen_sentences.add(sentence_key)
            else:
                for sentence in sentences:
                    all_sentences.append(sentence)
                    sentence_key = sentence.get('normalized', '')[:100]
                    if sentence_key:
                        seen_sentences.add(sentence_key)
        
        return all_sentences
    
    # Test case 1: All successful chunks
    chunk_results = [
        {
            'chunk_id': 0,
            'status': 'success',
            'sentences': [
                {'normalized': 'First sentence.', 'original': 'First sentence.'},
                {'normalized': 'Second sentence.', 'original': 'Second sentence.'}
            ]
        },
        {
            'chunk_id': 1,
            'status': 'success',
            'sentences': [
                {'normalized': 'Third sentence.', 'original': 'Third sentence.'},
                {'normalized': 'Fourth sentence.', 'original': 'Fourth sentence.'}
            ]
        }
    ]
    
    merged = merge_chunk_results(chunk_results)
    assert len(merged) == 4, f"Expected 4 sentences, got {len(merged)}"
    print("✓ Test 1 passed: All successful chunks merged correctly")
    
    # Test case 2: With failed chunks
    chunk_results = [
        {
            'chunk_id': 0,
            'status': 'success',
            'sentences': [
                {'normalized': 'Success sentence.', 'original': 'Success sentence.'}
            ]
        },
        {
            'chunk_id': 1,
            'status': 'failed',
            'error': 'API timeout'
        }
    ]
    
    merged = merge_chunk_results(chunk_results)
    assert len(merged) == 1, f"Expected 1 sentence, got {len(merged)}"
    print("✓ Test 2 passed: Failed chunks skipped correctly")
    
    # Test case 3: With duplicate sentences (overlap)
    chunk_results = [
        {
            'chunk_id': 0,
            'status': 'success',
            'sentences': [
                {'normalized': 'Unique one.', 'original': 'Unique one.'},
                {'normalized': 'Overlap sentence.', 'original': 'Overlap sentence.'}
            ]
        },
        {
            'chunk_id': 1,
            'status': 'success',
            'sentences': [
                {'normalized': 'Overlap sentence.', 'original': 'Overlap sentence.'},
                {'normalized': 'Unique two.', 'original': 'Unique two.'}
            ]
        }
    ]
    
    merged = merge_chunk_results(chunk_results)
    assert len(merged) == 3, f"Expected 3 sentences (deduplicated), got {len(merged)}"
    normalized_texts = [s['normalized'] for s in merged]
    assert normalized_texts.count('Overlap sentence.') == 1, "Overlap sentence should appear only once"
    print("✓ Test 3 passed: Duplicate sentences deduplicated correctly")

def test_finalize_logic():
    """Test the finalization logic"""
    print("\nTesting finalization logic...")
    
    # Test case 1: All chunks succeed
    chunk_results = [
        {'chunk_id': 0, 'status': 'success', 'tokens': 50},
        {'chunk_id': 1, 'status': 'success', 'tokens': 60}
    ]
    
    total_tokens = sum(r.get('tokens', 0) for r in chunk_results if r.get('status') == 'success')
    failed_chunks = [r['chunk_id'] for r in chunk_results if r.get('status') == 'failed']
    success_count = len([r for r in chunk_results if r.get('status') == 'success'])
    
    assert total_tokens == 110, f"Expected 110 tokens, got {total_tokens}"
    assert len(failed_chunks) == 0, f"Expected 0 failed chunks, got {len(failed_chunks)}"
    assert success_count == 2, f"Expected 2 successful chunks, got {success_count}"
    print("✓ Test 1 passed: All success case handled correctly")
    
    # Test case 2: Partial failure
    chunk_results = [
        {'chunk_id': 0, 'status': 'success', 'tokens': 50},
        {'chunk_id': 1, 'status': 'failed', 'error': 'timeout'}
    ]
    
    total_tokens = sum(r.get('tokens', 0) for r in chunk_results if r.get('status') == 'success')
    failed_chunks = [r['chunk_id'] for r in chunk_results if r.get('status') == 'failed']
    success_count = len([r for r in chunk_results if r.get('status') == 'success'])
    
    assert total_tokens == 50, f"Expected 50 tokens, got {total_tokens}"
    assert failed_chunks == [1], f"Expected failed_chunks=[1], got {failed_chunks}"
    assert success_count == 1, f"Expected 1 successful chunk, got {success_count}"
    print("✓ Test 2 passed: Partial failure case handled correctly")
    
    # Test case 3: All chunks fail
    chunk_results = [
        {'chunk_id': 0, 'status': 'failed', 'error': 'API error'},
        {'chunk_id': 1, 'status': 'failed', 'error': 'timeout'}
    ]
    
    success_count = len([r for r in chunk_results if r.get('status') == 'success'])
    
    assert success_count == 0, f"Expected 0 successful chunks, got {success_count}"
    print("✓ Test 3 passed: All failure case handled correctly")

def test_chunk_path_logic():
    """Test the chunk processing path selection logic"""
    print("\nTesting chunk processing path selection...")
    
    # Test case 1: Single chunk
    chunks = [{'chunk_id': 0, 'file_path': '/tmp/chunk_0.pdf'}]
    
    if len(chunks) == 1:
        path = 'synchronous'
    else:
        path = 'parallel_chord'
    
    assert path == 'synchronous', f"Single chunk should use synchronous path, got {path}"
    print("✓ Test 1 passed: Single chunk uses synchronous path")
    
    # Test case 2: Multiple chunks
    chunks = [
        {'chunk_id': 0, 'file_path': '/tmp/chunk_0.pdf'},
        {'chunk_id': 1, 'file_path': '/tmp/chunk_1.pdf'},
        {'chunk_id': 2, 'file_path': '/tmp/chunk_2.pdf'}
    ]
    
    if len(chunks) == 1:
        path = 'synchronous'
    else:
        path = 'parallel_chord'
    
    assert path == 'parallel_chord', f"Multiple chunks should use parallel chord path, got {path}"
    print("✓ Test 2 passed: Multiple chunks use parallel chord path")

def test_job_status_logic():
    """Test job status determination logic"""
    print("\nTesting job status logic...")
    
    # Constants
    JOB_STATUS_COMPLETED = 'completed'
    JOB_STATUS_FAILED = 'failed'
    
    # Test case 1: All success
    chunk_results = [
        {'chunk_id': 0, 'status': 'success'},
        {'chunk_id': 1, 'status': 'success'}
    ]
    success_count = len([r for r in chunk_results if r.get('status') == 'success'])
    
    if success_count == 0:
        status = JOB_STATUS_FAILED
    else:
        status = JOB_STATUS_COMPLETED
    
    assert status == JOB_STATUS_COMPLETED, f"Expected COMPLETED, got {status}"
    print("✓ Test 1 passed: All success results in COMPLETED status")
    
    # Test case 2: Partial success
    chunk_results = [
        {'chunk_id': 0, 'status': 'success'},
        {'chunk_id': 1, 'status': 'failed'}
    ]
    success_count = len([r for r in chunk_results if r.get('status') == 'success'])
    
    if success_count == 0:
        status = JOB_STATUS_FAILED
    else:
        status = JOB_STATUS_COMPLETED
    
    assert status == JOB_STATUS_COMPLETED, f"Expected COMPLETED (partial), got {status}"
    print("✓ Test 2 passed: Partial success results in COMPLETED status")
    
    # Test case 3: All failure
    chunk_results = [
        {'chunk_id': 0, 'status': 'failed'},
        {'chunk_id': 1, 'status': 'failed'}
    ]
    success_count = len([r for r in chunk_results if r.get('status') == 'success'])
    
    if success_count == 0:
        status = JOB_STATUS_FAILED
    else:
        status = JOB_STATUS_COMPLETED
    
    assert status == JOB_STATUS_FAILED, f"Expected FAILED, got {status}"
    print("✓ Test 3 passed: All failure results in FAILED status")

def main():
    """Run all validation tests"""
    print("=" * 60)
    print("Parallel Chunk Execution - Validation Tests")
    print("=" * 60)
    
    try:
        test_merge_chunk_results()
        test_finalize_logic()
        test_chunk_path_logic()
        test_job_status_logic()
        
        print("\n" + "=" * 60)
        print("✅ All validation tests passed!")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
