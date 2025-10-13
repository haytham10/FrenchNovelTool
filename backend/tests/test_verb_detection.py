#!/usr/bin/env python3
"""
Test the expanded verb list in Quality Gate service
"""

import sys
import os

# Add the backend app to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Test sentences from the user's Google Sheets data  
test_sentences = [
    "Savez-vous ce que vous allez faire ?",
    "Logiquement, vous devriez être heureux.",
    "On peut être sensible sans fragilité.", 
    "Vous devez la prendre au sérieux.",
    "Avoir un enfant ?",
    "Vous voulez la prendre dans vos bras.",
    "Il voulait être responsable.",
    "Son pouvoir de séduction était grand.",
    "Il devait être impeccable.",
    "C'était un être hybride.",
    "Il voulait faire demi-tour.",
    "Voulait-il savoir vraiment ?",  # Previously failed
    "Il mange une pomme rouge délicieuse.",  # Previously failed
    "Elle marchait lentement vers la maison.",  # Previously failed
]

# Additional test cases for edge scenarios
edge_cases = [
    "Dans la rue sombre.",  # No verb, should fail
    "Avec le succès et l'argent.",  # No verb, should fail
    "Pour perdre dix kilos vite.",  # Has verb "perdre", should pass
    "Si tu restes avec elle,",  # Has verb "restes", incomplete but has verb
    "Bonjour.",  # No verb, too short, should fail
]

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
    
    print("\n=== TESTING USER'S SENTENCES ===")
    valid_count = 0
    total_count = len(test_sentences)
    
    for sentence in test_sentences:
        is_valid, reasons = validate_single_sentence(sentence)
        status = "✅" if is_valid else "❌"
        reason_str = " | ".join(reasons) if reasons else ""
        print(f"{status} {sentence}")
        if not is_valid:
            print(f"   Reasons: {reason_str}")
        else:
            valid_count += 1
    
    print(f"\nUSER SENTENCES: {valid_count}/{total_count} valid ({valid_count/total_count*100:.1f}%)")
    
    print("\n=== TESTING EDGE CASES ===")
    
    for sentence in edge_cases:
        is_valid, reasons = validate_single_sentence(sentence)
        status = "✅" if is_valid else "❌"
        reason_str = " | ".join(reasons) if reasons else ""
        print(f"{status} {sentence}")
        if reasons:
            print(f"   Reasons: {reason_str}")
    
    # Test specific verb detection
    print("\n=== VERB DETECTION TEST ===")
    verb_test_cases = [
        ("Il mange", "mange"),
        ("Elle marchait", "marchait"), 
        ("Voulait-il", "voulait"),
        ("Tu voulais", "voulais"),
        ("Nous mangeons", "mangeons"),
        ("Ils partent", "partent"),
    ]
    
    for sentence, expected_verb in verb_test_cases:
        has_verb = qg.has_verb(sentence)
        status = "✅" if has_verb else "❌"
        print(f"{status} '{sentence}' -> Expected '{expected_verb}': {has_verb}")
        
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("Cannot test with actual QualityGate service")