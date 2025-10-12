#!/usr/bin/env python3
"""
Extended test for Quality Gate with edge cases and French sentence patterns
"""

import sys
import os

# Add the backend app to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    from app.services.quality_gate import QualityGate
    print("✅ Successfully imported QualityGate service")
    qg = QualityGate()
    
    def validate_single_sentence(sentence):
        """Test a single sentence and return validation info"""
        reasons = []
        
        # Check word count
        word_count = qg.token_count(sentence)
        if word_count < 4:
            reasons.append(f"Too short ({word_count} words, min 4)")
        elif word_count > 8:
            reasons.append(f"Too long ({word_count} words, max 8)")
        
        # Check verb
        if not qg.has_verb(sentence):
            reasons.append("No verb found")
        
        # Use the actual validate_sentences method to check if it passes overall
        valid_sentences = qg.validate_sentences([sentence])
        is_valid = len(valid_sentences) > 0
        
        return is_valid, reasons
    
    # Test French question inversions (common in literature)
    inversion_tests = [
        "Voulait-il vraiment partir maintenant ?",
        "Pouvait-elle comprendre cette situation ?", 
        "Savaient-ils ce qui arrivait ?",
        "Était-ce vraiment la vérité ?",
        "Avait-il fini son travail ?",
    ]
    
    print("=== FRENCH QUESTION INVERSIONS ===")
    for sentence in inversion_tests:
        is_valid, reasons = validate_single_sentence(sentence)
        status = "✅" if is_valid else "❌"
        print(f"{status} {sentence}")
        if not is_valid:
            print(f"   Reasons: {', '.join(reasons)}")
    
    # Test various verb forms and tenses
    tense_tests = [
        "Je mangeais du pain hier.",  # Imperfect
        "Tu viendras demain matin.",  # Future
        "Il a fini ses devoirs.",     # Past compound
        "Nous partirons ensemble.",   # Future
        "Vous comprenez la leçon.",   # Present
        "Elles dormaient profondément.",  # Imperfect  
    ]
    
    print("\n=== FRENCH VERB TENSES ===")
    for sentence in tense_tests:
        is_valid, reasons = validate_single_sentence(sentence)
        status = "✅" if is_valid else "❌"
        print(f"{status} {sentence}")
        if not is_valid:
            print(f"   Reasons: {', '.join(reasons)}")
    
    # Test common dialogue patterns from novels
    dialogue_tests = [
        "« Bonjour », dit-il doucement.",     # Should fail (too short for "Bonjour")
        "Il dit bonjour à son ami.",          # Should pass
        "« Vous voulez partir ? »",           # Should pass 
        "Elle répond avec un sourire.",       # Should pass
        "« Non », murmura-t-elle tristement.", # Should pass
    ]
    
    print("\n=== DIALOGUE PATTERNS ===")
    for sentence in dialogue_tests:
        is_valid, reasons = validate_single_sentence(sentence)
        status = "✅" if is_valid else "❌"
        print(f"{status} {sentence}")
        if not is_valid:
            print(f"   Reasons: {', '.join(reasons)}")
            
    # Summary test with batch validation
    print("\n=== BATCH VALIDATION TEST ===")
    all_test_sentences = inversion_tests + tense_tests + dialogue_tests
    valid_sentences = qg.validate_sentences(all_test_sentences)
    
    print(f"Input sentences: {len(all_test_sentences)}")
    print(f"Valid sentences: {len(valid_sentences)}")
    print(f"Pass rate: {len(valid_sentences)/len(all_test_sentences)*100:.1f}%")
    
    print("\nValid sentences returned by batch validation:")
    for i, sentence in enumerate(valid_sentences, 1):
        print(f"  {i}. {sentence}")
        
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("Cannot test with actual QualityGate service")