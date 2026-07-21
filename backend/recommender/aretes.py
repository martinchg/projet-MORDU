"""LES ARÊTES — le ressenti comme propriété de la PAIRE (user, film). Cf. MANIFESTE §4.

Un ressenti n'appartient ni à la personne ni au film : c'est une arête d'un graphe
biparti, avec du texte dessus. D'où les règles, non négociables :

- Append-only. On n'écrase jamais, on n'agrège JAMAIS à l'écriture. Les profils
  (personne, film) sont des vues recalculables — la donnée brute reste la vérité.
- JSONL, pas de base de données. Tant qu'un seul humain écrit dedans, une DB serait de
  l'over-engineering (le ROADMAP l'interdit explicitement).
- Tout état honnête est une clé valide : « abandonné à 40 min » est une arête précieuse,
  pas un échec. On ne punit que le silence.

Le fichier vit dans data/ (git-ignoré) : ce que tu écris reste chez toi.
"""
import json
import os
import re
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
ARETES_PATH = os.path.join(DATA_DIR, "aretes.jsonl")
ETAT_PATH = os.path.join(DATA_DIR, "etat.json")

# Valence dérivée du TEXTE, jamais d'une étoile (le manifeste bannit les notes : une note
# est une évaluation, pas une envie). Lexique volontairement grossier en v0 — il sera
# remplacé par une projection sur les axes du Tag Genome. C'est un plancher, pas une fin.
_POS = ("adoré", "adorée", "adore", "génial", "geniale", "géniale", "magnifique",
        "sublime", "excellent", "excellente", "bouleversé", "bouleversant", "puissant",
        "puissante", "brillant", "brillante", "superbe", "aimé", "kiffé", "hypnotique",
        "marquant", "marquante", "chef-d'œuvre", "incroyable", "fascinant", "fascinante",
        "prenant", "prenante", "tendu", "tendue", "réussi", "réussie", "happé", "happée",
        "scotché", "scotchée", "cueilli", "captivant", "captivante", "envoûtant",
        "troublant", "troublante", "vertigineux", "somptueux", "somptueuse", "juste",
        "maîtrisé", "maitrise", "élégant", "subtil", "subtile", "poignant", "poignante",
        "drôle", "hilarant", "haletant", "haletante", "inoubliable", "sidérant",
        "impressionnant", "solide", "efficace", "beau", "belle", "fort", "forte")
_NEG = ("ennuyeux", "ennuyeuse", "ennui", "chiant", "chiante", "nul", "nulle", "raté",
        "ratée", "déçu", "déçue", "decu", "décevant", "décevante", "lourd", "lourde",
        "prétentieux", "prétentieuse", "pretentieux", "creux", "creuse", "longuet",
        "mou", "molle", "détesté", "déteste", "insupportable", "bâclé", "bâclée",
        "bavard", "poussif", "poussive", "laborieux", "laborieuse", "convenu",
        "prévisible", "caricatural", "grotesque", "interminable", "pénible", "penible",
        "fade", "plat", "plate", "vain", "vaine", "gênant", "gênante", "surfait")
_ABANDON = re.compile(r"\babandonn|\barrêté|\barrete|pas fini|pas terminé|coupé au bout"
                      r"|\blâché|\blache l|tenu \d+ min", re.I)

# Frontières de mots OBLIGATOIRES : en sous-chaîne, « beau » matche « beaucoup »,
# « fort » matche « effort », « mou » matche « mouvement ». Ces faux positifs
# inversaient le signe de la valence — donc corrompaient le profil.
def _compte(mots, t):
    n = 0
    for w in mots:
        if re.search(r"(?<![\w'’])" + re.escape(w) + r"(?![\w'’])", t):
            n += 1
    return n


def valence(texte):
    """-1..1 depuis le texte. Grossier mais PRUDENT — et c'est délibéré.

    Un lexique de mots ne fait pas de l'analyse de sentiment : « le rythme est un peu
    mou mais la fin m'a cueilli » est un avis positif, qu'un comptage naïf classait
    à -1. Or la valence pilote le vecteur profil : un signe faux ÉLOIGNE l'oracle d'un
    film aimé. On amortit donc fortement, on part d'un a priori légèrement positif
    (l'utilisateur a choisi ce film et l'a regardé), et seul un signal explicite
    (abandon, rejet net) fait basculer dans le négatif.

    Remplacement prévu : projection du texte sur les axes du Tag Genome (MANIFESTE §7).
    C'est un plancher, pas une fin.
    """
    t = (texte or "").lower()
    pos = _compte(_POS, t)
    neg = _compte(_NEG, t)
    abandon = bool(_ABANDON.search(t))

    apriori = 0.35                   # il l'a choisi et regardé jusqu'au bout
    if pos or neg:
        # le texte l'emporte d'autant plus qu'il porte de signaux : un mot isolé nuance,
        # trois mots convergents tranchent.
        score = (pos - neg) / float(pos + neg)
        confiance = (pos + neg) / (pos + neg + 1.5)
        v = apriori * (1 - confiance) + score * confiance
    else:
        v = apriori
    if abandon:
        v = min(v, -0.4)             # l'abandon est le seul signal négatif franc
    return max(-1.0, min(1.0, round(v, 3)))


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ajouter(film_id, texte, titre=None, registre=None, extra=None):
    """Écrit une arête. Retourne l'arête écrite."""
    os.makedirs(DATA_DIR, exist_ok=True)
    a = {
        "film_id": int(film_id),
        "titre": titre,
        "texte": (texte or "").strip(),
        "valence": valence(texte),
        "abandonne": bool(_ABANDON.search(texte or "")),
        "registre": registre,          # quel axe avait été choisi ce soir-là
        "date": _now(),
    }
    if extra:
        a.update(extra)
    with open(ARETES_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(a, ensure_ascii=False) + "\n")
    return a


def toutes():
    """Relit toutes les arêtes (la source de vérité)."""
    if not os.path.exists(ARETES_PATH):
        return []
    out = []
    with open(ARETES_PATH, encoding="utf-8") as f:
        for ligne in f:
            ligne = ligne.strip()
            if not ligne:
                continue
            try:
                out.append(json.loads(ligne))
            except json.JSONDecodeError:
                continue          # une ligne corrompue ne doit jamais tuer la lecture
    return out


def films_racontes():
    return {a["film_id"] for a in toutes()}


# --- L'état du rituel (la serrure) --------------------------------------------------
def lire_etat():
    try:
        with open(ETAT_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def ecrire_etat(e):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(ETAT_PATH, "w", encoding="utf-8") as f:
        json.dump(e, f, ensure_ascii=False, indent=1)


def en_attente():
    """Le film choisi mais pas encore raconté — c'est LUI qui verrouille le tirage."""
    return lire_etat().get("en_attente")


def poser_choix(film_id, titre=None, registre=None):
    # On MET À JOUR l'état, on ne le remplace pas : écrire {"en_attente": …} tout court
    # effaçait les graines de l'onboarding (donc le profil) au premier choix.
    e = lire_etat()
    e["en_attente"] = {"film_id": int(film_id), "titre": titre,
                       "registre": registre, "date": _now()}
    ecrire_etat(e)


def liberer():
    e = lire_etat()
    e.pop("en_attente", None)
    ecrire_etat(e)


def graines():
    """Films-graines de l'onboarding (« 3 films adorés + pourquoi »)."""
    return lire_etat().get("graines", [])


# --- La boîte aux lettres (MANIFESTE §6) --------------------------------------------
# Ce n'est PAS une watchlist. Une watchlist est une file que TU consultes pour choisir
# — retour du choix, retour de la dette, mort du principe. La boîte est une SOURCE que
# l'oracle pondère : on y dépose, on n'y pioche jamais.
def boite():
    return lire_etat().get("boite", [])


def deposer(film_id, titre=None, source=None):
    e = lire_etat()
    b = e.get("boite", [])
    if not any(x["film_id"] == int(film_id) for x in b):
        b.append({"film_id": int(film_id), "titre": titre, "source": source,
                  "date": _now()})
    e["boite"] = b
    ecrire_etat(e)
    return b[-1] if b else None


def retirer_boite(film_id):
    e = lire_etat()
    e["boite"] = [x for x in e.get("boite", []) if x["film_id"] != int(film_id)]
    ecrire_etat(e)


def poser_graines(ids):
    e = lire_etat()
    e["graines"] = [int(i) for i in ids]
    ecrire_etat(e)
