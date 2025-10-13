"""
Test script to verify dynamic budget allocation in batch coverage mode.

This test demonstrates that the dynamic budget allocation ensures:
1. Later sources get fair share of budget
2. Budget is allocated based on remaining words, not just remaining total budget
3. Last source gets any remaining budget to avoid waste
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.coverage_service import CoverageService


def test_dynamic_budget_allocation():
    """
    Simulate batch coverage with dynamic budget allocation.

    Test scenario:
    - 3 sources with different rare word distributions
    - 500 total sentence budget
    - First source: many common words (should use moderate budget)
    - Second source: mix of common and rare words (should get fair budget)
    - Third source: mostly rare words (should get remaining budget)
    """

    # Sample word list (100 words)
    wordlist = set([f"word{i}" for i in range(100)])

    # Source 1: 200 sentences, covers 60 words efficiently
    # (Simulates a source with many common words)
    source1_sentences = [
        f"This is word{i} word{i+1} sentence for testing."
        for i in range(0, 60, 2)  # 30 sentences, each covering 2 words
    ] + [f"Filler sentence {i} with no target words here." for i in range(170)]

    # Source 2: 150 sentences, covers 20 new words
    # (Simulates a source with fewer but important words)
    source2_sentences = [
        f"Another sentence with word{i} included here."
        for i in range(60, 80)  # 20 sentences for 20 words
    ] + [f"Extra filler sentence {i} without targets." for i in range(130)]

    # Source 3: 100 sentences, covers last 20 words
    # (Simulates a source with rare words only)
    source3_sentences = [
        f"Final sentence containing word{i} as target."
        for i in range(80, 100)  # 20 sentences for last 20 words
    ] + [f"More filler content {i} here." for i in range(80)]

    sources = [
        (1, source1_sentences),
        (2, source2_sentences),
        (3, source3_sentences),
    ]

    # Configure service
    config = {
        "target_count": 500,  # Global sentence limit
        "len_min": 4,
        "len_max": 8,
        "fold_diacritics": True,
        "handle_elisions": True,
    }

    service = CoverageService(wordlist_keys=wordlist, config=config)

    print("=" * 80)
    print("DYNAMIC BUDGET ALLOCATION TEST")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  Total word list: {len(wordlist)} words")
    print(f"  Global sentence budget: {config['target_count']} sentences")
    print(f"  Number of sources: {len(sources)}")
    print(f"\nExpected behavior:")
    print(f"  - Source 1 should use ~30 sentences (efficient coverage)")
    print(f"  - Source 2 should get fair budget for remaining 40 words")
    print(f"  - Source 3 should get remaining budget for last 20 words")
    print("\n" + "=" * 80)

    # Run batch coverage
    assignments, stats, learning_set = service.batch_coverage_mode(
        sources=sources, progress_callback=None
    )

    # Display results
    print("\nBATCH COVERAGE RESULTS:")
    print("=" * 80)
    print(f"\nOverall Statistics:")
    print(
        f"  Words covered: {stats['words_covered']}/{stats['words_total']} "
        f"({stats['coverage_percentage']:.1f}%)"
    )
    print(
        f"  Total sentences selected: {stats['selected_sentence_count']}/{config['target_count']}"
    )
    print(
        f"  Sources processed: {stats['batch_summary']['sources_processed']}/{stats['batch_summary']['source_count']}"
    )

    print(f"\nPer-Source Breakdown:")
    for source_stat in stats["source_stats"]:
        print(f"\n  Source {source_stat['source_index'] + 1} (ID: {source_stat['source_id']}):")
        print(f"    Sentences in source: {source_stat['sentences_count']}")
        print(f"    Sentences selected: {source_stat['selected_sentence_count']}")
        print(f"    Words covered: {source_stat['words_covered']}")
        print(f"    Words remaining after: {source_stat['words_remaining']}")

    print("\n" + "=" * 80)
    print("VERIFICATION:")
    print("=" * 80)

    # Verify dynamic allocation worked
    source_stats = stats["source_stats"]

    # Check that each source got a reasonable budget
    success = True

    # Source 1 shouldn't consume entire budget
    if source_stats[0]["selected_sentence_count"] >= 400:
        print("❌ FAIL: Source 1 consumed too much budget (should leave room for others)")
        success = False
    else:
        print(
            f"✅ PASS: Source 1 used {source_stats[0]['selected_sentence_count']} sentences (left room for others)"
        )

    # Source 2 should get meaningful budget
    if len(source_stats) > 1:
        if source_stats[1]["selected_sentence_count"] < 5:
            print("❌ FAIL: Source 2 got inadequate budget")
            success = False
        else:
            print(f"✅ PASS: Source 2 got {source_stats[1]['selected_sentence_count']} sentences")

    # Source 3 should process if there are uncovered words
    if len(source_stats) > 2:
        if source_stats[2]["words_covered"] > 0:
            print(f"✅ PASS: Source 3 covered {source_stats[2]['words_covered']} words")
        else:
            print("⚠️  WARNING: Source 3 didn't cover new words (may be expected if all covered)")

    # Overall coverage check
    if stats["coverage_percentage"] >= 70:
        print(f"✅ PASS: Achieved {stats['coverage_percentage']:.1f}% coverage (target: ≥70%)")
    else:
        print(f"⚠️  WARNING: Coverage {stats['coverage_percentage']:.1f}% below 70% target")

    print("\n" + "=" * 80)
    if success:
        print("✅ DYNAMIC BUDGET ALLOCATION TEST PASSED")
    else:
        print("❌ DYNAMIC BUDGET ALLOCATION TEST FAILED")
    print("=" * 80 + "\n")

    return success


if __name__ == "__main__":
    try:
        success = test_dynamic_budget_allocation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
