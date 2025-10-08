import time
from app.services.coverage_service import CoverageService

wordlist = {'chat', 'chien', 'manger', 'dormir', 'le', 'la', 'un'}

sentences = [
    "Le chat mange.",
    "Le chien dort.",
]

service = CoverageService(wordlist)

start = time.time()
assignments, stats = service.coverage_mode_greedy(sentences)
end = time.time()

print("Coverage Mode Test:")
print(f"Total words in list: {stats['words_total']}")
print(f"Words covered: {stats['words_covered']}")
print(f"Sentences selected: {stats['selected_sentence_count']}")
print(f"Learning set size: {stats['learning_set_count']}")
print(f"Elapsed time: {end-start:.4f}s")
print()
print("Learning set:")
for entry in stats['learning_set']:
    print(f"  {entry['rank']}. {entry['sentence_text']} (score: {entry['score']:.2f})")
