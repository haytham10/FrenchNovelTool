"""Seed script to populate the canonical 2K French word list as a global default"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, db
from app.models import WordList
from app.services.wordlist_service import WordListService


# Top 2000 most common French words (sample - would need full list in production)
FRENCH_2K_WORDS = [
    # Articles
    "le", "la", "les", "un", "une", "des", "du", "de",
    # Common verbs
    "être", "avoir", "faire", "dire", "pouvoir", "aller", "voir", "savoir", "vouloir", "venir",
    "devoir", "prendre", "trouver", "donner", "parler", "aimer", "passer", "mettre", "croire", "demander",
    "rester", "répondre", "entendre", "tenir", "porter", "vivre", "connaître", "regarder", "suivre", "penser",
    "tomber", "laisser", "paraître", "arriver", "sentir", "rendre", "ouvrir", "montrer", "comprendre", "devenir",
    # Common nouns
    "homme", "femme", "enfant", "jour", "temps", "main", "chose", "vie", "oeil", "monde",
    "maison", "pays", "père", "mère", "frère", "soeur", "ami", "ville", "moment", "côté",
    "tête", "coeur", "fois", "mort", "porte", "part", "roi", "fils", "voix", "terre",
    "chambre", "route", "soir", "matin", "heure", "place", "état", "guerre", "dieu", "eau",
    # Common adjectives
    "bon", "grand", "petit", "nouveau", "vieux", "jeune", "beau", "long", "gros", "haut",
    "fort", "autre", "premier", "dernier", "seul", "même", "tout", "certain", "propre", "tel",
    # Common adverbs and prepositions
    "bien", "plus", "encore", "déjà", "aussi", "très", "toujours", "jamais", "peut-être", "ainsi",
    "dans", "sur", "pour", "par", "avec", "sans", "sous", "entre", "vers", "depuis",
    # Pronouns
    "je", "tu", "il", "elle", "nous", "vous", "ils", "elles", "on", "ce",
    "qui", "que", "quoi", "où", "dont", "lequel", "laquelle", "lesquels", "lesquelles",
    # Numbers
    "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf", "dix",
    # More common words to reach closer to 2000 (sample)
    "alors", "vraiment", "maintenant", "aujourd'hui", "hier", "demain", "avant", "après", "pendant", "toujours",
    "jamais", "souvent", "rarement", "parfois", "quelquefois", "autrefois", "longtemps", "bientôt", "tard", "tôt",
    "beaucoup", "peu", "assez", "trop", "moins", "autant", "davantage", "environ", "presque", "plutôt",
    "surtout", "notamment", "d'ailleurs", "pourtant", "cependant", "néanmoins", "toutefois", "donc", "ainsi", "alors",
    "enfin", "ensuite", "puis", "d'abord", "enfin", "finalement", "soudain", "tout à coup", "aussitôt", "immédiatement",
    # Additional common verbs
    "appeler", "commencer", "continuer", "arrêter", "finir", "essayer", "chercher", "travailler", "jouer", "perdre",
    "gagner", "acheter", "vendre", "payer", "recevoir", "offrir", "servir", "courir", "marcher", "monter",
    "descendre", "sortir", "entrer", "rentrer", "retourner", "partir", "revenir", "arriver", "rester", "attendre",
    # Additional common nouns
    "année", "mois", "semaine", "nuit", "soleil", "lune", "ciel", "air", "mer", "montagne",
    "arbre", "fleur", "animal", "chien", "chat", "oiseau", "poisson", "pain", "vin", "livre",
    "papier", "lettre", "mot", "nom", "nombre", "couleur", "forme", "son", "musique", "chanson",
    # Additional adjectives
    "blanc", "noir", "rouge", "bleu", "vert", "jaune", "brun", "gris", "rose", "violet",
    "clair", "foncé", "léger", "lourd", "dur", "doux", "chaud", "froid", "sec", "humide",
    "plein", "vide", "ouvert", "fermé", "large", "étroit", "profond", "peu profond", "haut", "bas",
    # More words (would need comprehensive 2K list in production)
    "parce que", "comme", "si", "quand", "lorsque", "puisque", "tandis que", "pendant que", "dès que", "aussitôt que",
    "avant que", "après que", "jusqu'à ce que", "afin que", "pour que", "de peur que", "à moins que", "bien que", "quoique", "sans que",
]


def seed_french_2k_wordlist():
    """Create and populate the global default French 2K word list"""
    app = create_app()
    
    with app.app_context():
        # Check if global default already exists
        existing = WordList.query.filter_by(is_global_default=True).first()
        if existing:
            print(f"Global default word list already exists: {existing.name} (ID: {existing.id})")
            return
        
        # Create the word list using WordListService
        wordlist_service = WordListService()
        
        print(f"Creating global default French 2K word list with {len(FRENCH_2K_WORDS)} words...")
        
        wordlist, ingestion_report = wordlist_service.ingest_word_list(
            words=FRENCH_2K_WORDS,
            name="French 2K Default",
            owner_user_id=None,  # Global list (no owner)
            source_type='manual',
            source_ref='seed_script',
            fold_diacritics=True
        )
        
        # Mark as global default
        wordlist.is_global_default = True
        
        db.session.commit()
        
        print(f"✅ Successfully created global default word list: {wordlist.name}")
        print(f"   ID: {wordlist.id}")
        print(f"   Original count: {ingestion_report['original_count']}")
        print(f"   Normalized count: {ingestion_report['normalized_count']}")
        print(f"   Duplicates: {len(ingestion_report['duplicates'])}")
        print(f"   Multi-token entries: {len(ingestion_report['multi_token_entries'])}")
        print(f"   Variants expanded: {ingestion_report['variants_expanded']}")
        print(f"   Anomalies: {len(ingestion_report['anomalies'])}")
        
        if ingestion_report['duplicates']:
            print(f"\n   Sample duplicates:")
            for dup in ingestion_report['duplicates'][:5]:
                print(f"     - {dup['word']} -> {dup['normalized']}")
        
        if ingestion_report['multi_token_entries']:
            print(f"\n   Sample multi-token entries:")
            for entry in ingestion_report['multi_token_entries'][:5]:
                print(f"     - {entry['original']} -> {entry['head_token']}")


if __name__ == '__main__':
    seed_french_2k_wordlist()
