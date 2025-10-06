from flask import Flask
from app.services.gemini_service import GeminiService

app = Flask(__name__)
# Minimal required config values used by GeminiService
app.config['GEMINI_API_KEY'] = 'test'
app.config['GEMINI_MAX_RETRIES'] = 3
app.config['GEMINI_RETRY_DELAY'] = 1
app.config['GEMINI_ALLOW_LOCAL_FALLBACK'] = False

phrases = [
    "le standard d'Elvis Presley,",
    "et froide",
    "dans la rue sombre",
    "It's Now or Never,",
    "Pour toujours et à jamais",
    "Avec le temps",
    "Dans quinze ans",
    "De retour dans la chambre",
]

with app.app_context():
    service = GeminiService(sentence_length_limit=8)
    for p in phrases:
        print(p, '->', service._is_likely_fragment(p))
