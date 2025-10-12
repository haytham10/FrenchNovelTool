#!/usr/bin/env python3
"""
Test the complete repair pipeline - simulate how the enhanced Quality Gate
will perform in the actual PDF processing pipeline
"""

import sys
import os

# Add the backend app to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    from app.services.quality_gate import QualityGate
    print("✅ Successfully imported QualityGate service")
    
    # Simulate realistic sentences that might come from PDF extraction and Gemini normalization
    # Mix of good sentences and sentences that would previously fail
    realistic_test_batch = [
        # Good sentences that should pass
        "Il marche dans la rue.",
        "Elle mange une pomme rouge.",
        "Vous voulez partir maintenant ?",
        "Nous allons au cinéma ensemble.",
        "Tu penses à ton travail.",
        "Ils jouent dans le jardin.",
        "Je lis un livre intéressant.", 
        "Vous comprenez cette leçon ?",
        "Elle répond à sa question.",
        "Il dort profondément dans son lit.",
        
        # Question inversions (should now pass)
        "Voulait-il vraiment partir ?",
        "Peut-elle comprendre cela ?",
        "Savez-vous la réponse ?",
        "Était-ce la bonne solution ?",
        
        # Various verb tenses (should now pass)
        "Je mangeais du pain hier.",
        "Tu viendras demain matin.",
        "Il finit ses devoirs.",
        "Nous partirons bientôt ensemble.",
        "Vous dormiez très bien.",
        "Elles parlaient de leur travail.",
        
        # Dialogue patterns (should now pass) 
        "Il dit bonjour poliment.",
        "Elle murmure quelques mots.",
        "« Vous voulez partir ? »",
        "« Oui », répond-il calmement.",
        
        # Should still fail (no verbs)
        "Dans la rue sombre.",
        "Avec beaucoup de courage.",
        "Pendant les vacances d'été.",
        
        # Should still fail (too short)
        "Très bien.",
        "Absolument.",
        "Parfait !",
        
        # Should still fail (too long)
        "Il marche lentement dans la rue en regardant attentivement toutes les vitrines des magasins.",
        "Elle mange une pomme rouge très délicieuse avec beaucoup de plaisir dans le jardin.",
        
        # Edge cases that should pass
        "Pour perdre du poids rapidement.",  # Infinitive verb
        "Avant de partir en voyage.", # Infinitive verb
        "Après avoir fini son travail.", # Past infinitive
    ]
    
    qg = QualityGate()
    
    print(f"\n=== REALISTIC BATCH PROCESSING TEST ===")
    print(f"Total sentences to process: {len(realistic_test_batch)}")
    
    # Test individual validation (for detailed analysis)
    valid_count = 0
    verb_failures = 0
    length_failures = 0
    
    print("\nDetailed validation results:")
    for i, sentence in enumerate(realistic_test_batch, 1):
        # Check individual criteria
        word_count = qg.token_count(sentence)
        has_verb = qg.has_verb(sentence)
        
        # Overall validation using batch method
        batch_result = qg.validate_sentences([sentence])
        is_valid = len(batch_result) > 0
        
        status = "✅" if is_valid else "❌"
        
        issues = []
        if word_count < 4:
            issues.append(f"too short ({word_count})")
            length_failures += 1
        elif word_count > 8:
            issues.append(f"too long ({word_count})")
            length_failures += 1
        if not has_verb:
            issues.append("no verb")
            verb_failures += 1
            
        issue_str = f" ({', '.join(issues)})" if issues else ""
        
        print(f"  {i:2d}. {status} {sentence}{issue_str}")
        
        if is_valid:
            valid_count += 1
    
    # Batch validation test
    print(f"\n=== BATCH VALIDATION SUMMARY ===")
    valid_sentences = qg.validate_sentences(realistic_test_batch)
    
    print(f"Input sentences: {len(realistic_test_batch)}")
    print(f"Valid sentences: {len(valid_sentences)}")
    print(f"Pass rate: {len(valid_sentences)/len(realistic_test_batch)*100:.1f}%")
    print(f"Individual validation matches batch: {valid_count == len(valid_sentences)}")
    
    print(f"\nFailure analysis:")
    print(f"  Verb detection failures: {verb_failures}")
    print(f"  Length requirement failures: {length_failures}")
    print(f"  Total failures: {len(realistic_test_batch) - len(valid_sentences)}")
    
    # Expected quality analysis
    expected_valid = 29  # Based on manual analysis of the test sentences
    actual_valid = len(valid_sentences)
    
    print(f"\n=== QUALITY ANALYSIS ===")
    print(f"Expected valid sentences: ~{expected_valid}")
    print(f"Actually valid sentences: {actual_valid}")
    
    if actual_valid >= expected_valid * 0.9:  # 90% of expected
        print("✅ Quality Gate performance is EXCELLENT")
        print("✅ Ready for production - should significantly improve sentence yield")
    elif actual_valid >= expected_valid * 0.8:  # 80% of expected  
        print("⚠️  Quality Gate performance is GOOD but could be improved")
    else:
        print("❌ Quality Gate performance needs more work")
    
    print(f"\nSample valid sentences (first 10):")
    for i, sentence in enumerate(valid_sentences[:10], 1):
        print(f"  {i}. {sentence}")
        
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("Cannot test with actual QualityGate service")