"""Quality Gate service: validates sentences returned by the LLM.

This module provides a small API used by the Battleship Phase 1.3 agent.
It tries to use spaCy if available; if not, it falls back to a lightweight tokenizer
and a naive verb check using a small verb list. The Phase 1.3 agent should
replace the fallback with spaCy in production.
"""
from typing import List

try:
    import spacy
    from spacy.language import Language

    _nlp: Language | None = spacy.load("fr_core_news_sm")
except Exception:  # pragma: no cover - fallback when spaCy model not present
    _nlp = None


class QualityGate:
    def __init__(self):
        self._nlp = _nlp

    def has_verb(self, sentence: str) -> bool:
        """Return True if sentence contains a verb.

        If spaCy is available uses POS tags. Otherwise, uses a naive verb lookup.
        """
        if self._nlp:
            doc = self._nlp(sentence)
            for tok in doc:
                if tok.pos_ == "VERB":
                    return True
            return False

        # Fallback naive check (comprehensive verb list for better coverage)
        # Include common infinitives, conjugated forms, auxiliaries, and patterns
        naive_verbs = {
            # Core auxiliaries and être/avoir forms
            "être", "avoir", "fait", "faire", "aller", "venir", "dire", "voir", "prendre",
            "est", "sont", "était", "étaient", "sera", "seront", "suis", "sommes", "êtes",
            "a", "ai", "as", "ont", "avait", "avaient", "aura", "auront", "avons", "avez",
            
            # Common action verbs (infinitive and conjugated)
            "pouvoir", "peut", "peuvent", "pouvait", "pouvaient", "pourra", "pourront",
            "vouloir", "veut", "veux", "voulait", "voulaient", "voudra", "voudront",
            "devoir", "doit", "devait", "devaient", "devra", "devront",
            "savoir", "sait", "savait", "savaient", "saura", "sauront",
            "falloir", "faut", "fallait", "faudra",
            
            # Movement and action verbs
            "aller", "va", "vais", "allait", "allaient", "ira", "iront",
            "venir", "vient", "venait", "venaient", "viendra", "viendront",
            "partir", "part", "partait", "partaient", "partira", "partiront",
            "arriver", "arrive", "arrivait", "arrivaient", "arrivera", "arriveront",
            "rester", "reste", "restait", "restaient", "restera", "resteront",
            "entrer", "entre", "entrait", "entraient", "entrera", "entreront",
            "sortir", "sort", "sortait", "sortaient", "sortira", "sortiront",
            "monter", "monte", "montait", "montaient", "montera", "monteront",
            "descendre", "descend", "descendait", "descendaient", "descendra", "descendront",
            "marcher", "marche", "marchait", "marchaient", "marchera", "marcheront",
            "courir", "court", "courait", "couraient", "courra", "courront",
            
            # Communication and perception
            "dire", "dit", "disait", "disaient", "dira", "diront",
            "parler", "parle", "parlait", "parlaient", "parlera", "parleront",
            "entendre", "entend", "entendait", "entendaient", "entendra", "entendront",
            "écouter", "écoute", "écoutait", "écoutaient", "écoutera", "écouteront",
            "voir", "voit", "voyait", "voyaient", "verra", "verront",
            "regarder", "regarde", "regardait", "regardaient", "regardera", "regarderont",
            "lire", "lit", "lis", "lisent", "lisez", "lisons", "lisait", "lisaient", "lira", "liront",
            "écrire", "écrit", "écris", "écrivent", "écrivez", "écrivons", "écrivait", "écrivaient", "écrira", "écriront",
            
            # Daily actions
            "manger", "mange", "mangeait", "mangeaient", "mangera", "mangeront",
            "boire", "boit", "buvait", "buvaient", "boira", "boiront",
            "dormir", "dort", "dormait", "dormaient", "dormira", "dormiront",
            "jouer", "joue", "joues", "jouent", "jouez", "jouons", "jouait", "jouaient", "jouera", "joueront",
            "travailler", "travaille", "travaillait", "travaillaient", "travaillera", "travailleront",
            "étudier", "étudie", "étudiait", "étudiaient", "étudiera", "étudieront",
            "apprendre", "apprend", "apprenait", "apprenaient", "apprendra", "apprendront",
            "comprendre", "comprend", "comprenait", "comprenaient", "comprendra", "comprendront",
            "connaître", "connaît", "connaissait", "connaissaient", "connaîtra", "connaîtront",
            
            # Manipulation and possession
            "prendre", "prend", "prenait", "prenaient", "prendra", "prendront",
            "donner", "donne", "donnait", "donnaient", "donnera", "donneront",
            "mettre", "met", "mettait", "mettaient", "mettra", "mettront",
            "porter", "porte", "portait", "portaient", "portera", "porteront",
            "tenir", "tient", "tenait", "tenaient", "tiendra", "tiendront",
            "laisser", "laisse", "laissait", "laissaient", "laissera", "laisseront",
            "garder", "garde", "gardait", "gardaient", "gardera", "garderont",
            "chercher", "cherche", "cherchait", "cherchaient", "cherchera", "chercheront",
            "trouver", "trouve", "trouvait", "trouvaient", "trouvera", "trouveront",
            "perdre", "perd", "perdait", "perdaient", "perdra", "perdront",
            
            # Emotional and mental states
            "aimer", "aime", "aimait", "aimaient", "aimera", "aimeront",
            "détester", "déteste", "détestait", "détestaient", "détestera", "détesteront",
            "penser", "pense", "pensait", "pensaient", "pensera", "penseront",
            "croire", "croit", "croyait", "croyaient", "croira", "croiront",
            "espérer", "espère", "espérait", "espéraient", "espérera", "espéreront",
            "sentir", "sent", "sentait", "sentaient", "sentira", "sentiront",
            "oublier", "oublie", "oubliait", "oubliaient", "oubliera", "oublieront",
            "souvenir", "souvient", "souvenait", "souvenaient", "souviendra", "souviendront",
            
            # States and changes
            "devenir", "devient", "devenait", "devenaient", "deviendra", "deviendront",
            "rester", "reste", "restait", "restaient", "restera", "resteront",
            "changer", "change", "changeait", "changeaient", "changera", "changeront",
            "grandir", "grandit", "grandissait", "grandissaient", "grandira", "grandiront",
            "vieillir", "vieillit", "vieillissait", "vieillissaient", "vieillira", "vieilliront",
            "mourir", "meurt", "mourait", "mouraient", "mourra", "mourront",
            "naître", "naît", "naissait", "naissaient", "naîtra", "naîtront",
            "vivre", "vit", "vivait", "vivaient", "vivra", "vivront",
            
            # Question and modal forms  
            "savez", "sais", "savons", "devez", "dois", "devons", "voulez", "veux", "voulons",
            "pouvez", "peux", "pouvons", "allez", "allons", "venez", "venons",
            
            # Additional missing conjugations
            "voulais", "mangeons", "partent", "partez", "pars", "partons",
            "manges", "mangez", "mangent", "mangeais", "mangeait", "mangiez",
            "buvons", "buvez", "boivent", "bois", "buvais", "buvait", "buvions", "buviez",
            "cours", "courez", "courons", "courais", "courait", "courions", "couriez",
            "dormez", "dormons", "dors", "dormais", "dormait", "dormions", "dormiez", "dormaient",
            "jouons", "jouez", "joues", "jouais", "jouait", "jouions", "jouiez",
            "travailles", "travaillez", "travaillons", "travaillais", "travaillait", "travaillions", "travailliez",
            "étudies", "étudiez", "étudions", "étudiais", "étudiait", "étudiions", "étudiiez",
            "apprends", "apprenez", "apprenons", "apprenais", "apprenait", "apprenions", "appreniez",
            "comprends", "comprenez", "comprenons", "comprenais", "comprenait", "comprenions", "compreniez",
            "connais", "connaissez", "connaissons", "connaissais", "connaissait", "connaissions", "connaissiez",
            "prends", "prenez", "prenons", "prenais", "prenait", "prenions", "preniez",
            "donnes", "donnez", "donnons", "donnais", "donnait", "donnions", "donniez",
            "mets", "mettez", "mettons", "mettais", "mettait", "mettions", "mettiez",
            "portes", "portez", "portons", "portais", "portait", "portions", "portiez",
            "tiens", "tenez", "tenons", "tenais", "tenait", "tenions", "teniez",
            "laisses", "laissez", "laissons", "laissais", "laissait", "laissions", "laissiez",
            "gardes", "gardez", "gardons", "gardais", "gardait", "gardions", "gardiez",
            "cherches", "cherchez", "cherchons", "cherchais", "cherchait", "cherchions", "cherchiez",
            "trouves", "trouvez", "trouvons", "trouvais", "trouvait", "trouvions", "trouviez",
            "perds", "perdez", "perdons", "perdais", "perdait", "perdions", "perdiez",
            "aimes", "aimez", "aimons", "aimais", "aimait", "aimions", "aimiez",
            "détestes", "détestez", "détestons", "détestais", "détestait", "détestions", "détestiez",
            "penses", "pensez", "pensons", "pensais", "pensait", "pensions", "pensiez",
            "crois", "croyez", "croyons", "croyais", "croyait", "croyions", "croyiez",
            "espères", "espérez", "espérons", "espérais", "espérait", "espérions", "espériez",
            "sens", "sentez", "sentons", "sentais", "sentait", "sentions", "sentiez",
            "oublies", "oubliez", "oublions", "oubliais", "oubliait", "oubliions", "oubliiez",
            "deviens", "devenez", "devenons", "devenais", "devenait", "devenions", "deveniez",
            "restes", "restez", "restons", "restais", "restait", "restions", "restiez",
            "changes", "changez", "changeons", "changeais", "changeait", "changions", "changiez",
            "grandis", "grandissez", "grandissons", "grandissais", "grandissait", "grandissions", "grandissiez",
            "vieillis", "vieillissez", "vieillissons", "vieillissais", "vieillissait", "vieillissions", "vieillissiez",
            "meurs", "mourez", "mourons", "mourais", "mourait", "mourions", "mouriez",
            "nais", "naissez", "naissons", "naissais", "naissait", "naissions", "naissiez",
            "vis", "vivez", "vivons", "vivais", "vivait", "vivions", "viviez",
            
            # Future tenses
            "viendras", "viendrai", "viendra", "viendrez", "viendrons", "viendront",
            "partirai", "partiras", "partira", "partirez", "partirons", "partiront",
            "finirai", "finiras", "finira", "finirez", "finirons", "finiront",
            
            # Communication verbs
            "dis", "disez", "disons", "disais", "disait", "disions", "disiez",
            "répond", "réponds", "répondez", "répondons", "répondais", "répondait", "répondions", "répondiez",
            "murmure", "murmures", "murmurez", "murmurons", "murmurais", "murmurait", "murmurions", "murmuriez",
            "murmura", "murmurai", "murmuras", "murmurâmes", "murmurâtes", "murmurèrent",
            
            # Past simple (passé simple) - common in literature
            "mangea", "mangeai", "mangeas", "mangeâmes", "mangeâtes", "mangèrent",
            "finit", "finis", "finîmes", "finîtes", "finirent",
            "parla", "parlai", "parlas", "parlâmes", "parlâtes", "parlèrent"
        }
        # Improved tokenization: handle hyphens (for inversion questions like "voulait-il")
        # Split on both whitespace and hyphens, then clean punctuation
        words = sentence.lower().replace('-', ' ').split()
        tokens = [t.strip(".,;:!?()\"'«»") for t in words]
        return any(tok in naive_verbs for tok in tokens)

    def token_count(self, sentence: str) -> int:
        """Return token count for the sentence.

        Uses spaCy tokenization when available, otherwise splits on whitespace.
        """
        if self._nlp:
            doc = self._nlp(sentence)
            # filter punctuation tokens
            return sum(1 for t in doc if not t.is_punct and not t.is_space)
        return len([t for t in sentence.split() if t.strip()])

    def validate_sentences(self, sentences: List[str]) -> List[str]:
        """Validate a list of candidate sentences and return only those that pass.

        Rules:
        - Must contain a verb
        - Must have token count between 4 and 8 (inclusive)
        """
        results: List[str] = []
        for s in sentences:
            try:
                if not isinstance(s, str):
                    continue
                tc = self.token_count(s)
                if tc < 4 or tc > 8:
                    continue
                if not self.has_verb(s):
                    continue
                results.append(s)
            except Exception:
                # On any unexpected error skip the sentence (defensive)
                continue
        return results


quality_gate = QualityGate()
