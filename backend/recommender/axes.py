"""CE QUE TU REGARDES DANS UN FILM — le portrait qui se LIT.

MANIFESTE §4 : « Ce que tu MENTIONNES compte autant que la valence : parler d'ambiguïté
morale sur Seven et de satire sur Fight Club, jamais du rythme — c'est TON axe
d'attention. Ton goût, c'est ce que tu regardes DANS les films. »

L'empreinte (le glyphe) est unique et déterministe, mais muette : elle ne dit rien de
lisible sur qui tu es. Ce module fournit la moitié manquante — on projette tes ressentis
sur des axes NOMMÉS, et le portrait devient une phrase au lieu d'une image.

Le signal le plus intéressant n'est pas ce dont tu parles le plus : c'est ce dont tu ne
parles JAMAIS. Deux personnes peuvent adorer les mêmes films en ne regardant pas du tout
la même chose dedans.

Lexical et déterministe en v1 — comme la valence, c'est un plancher assumé. La suite
serait une projection sur les axes du Tag Genome.
"""
import re
import unicodedata

# Axes volontairement peu nombreux et NOMMÉS en français : un portrait doit se lire.
AXES = {
    "atmosphère": {
        "libelle": "l'atmosphère",
        "phrase": "l'ambiance et le climat d'un film",
        "mots": ("ambiance", "atmosphere", "climat", "poisseux", "poisseuse", "oppressant",
                 "oppressante", "immersion", "univers", "ton", "lourde", "lourd", "malaise",
                 "angoisse", "tension", "tendu", "glacial", "etouffant", "sombre"),
    },
    "image": {
        "libelle": "l'image",
        "phrase": "la photo, les couleurs, les décors",
        "mots": ("couleur", "couleurs", "image", "images", "plan", "plans", "photo",
                 "photographie", "lumiere", "decor", "decors", "esthetique", "visuel",
                 "cadre", "cadrage", "beau", "belle", "belles", "sublime", "magnifique"),
    },
    "rythme": {
        "libelle": "le rythme",
        "phrase": "le tempo, la longueur, le montage",
        "mots": ("rythme", "lent", "lente", "lenteur", "rapide", "nerveux", "longueur",
                 "traine", "tempo", "montage", "long", "longue", "court", "courte",
                 "dynamique", "sec", "seche"),
    },
    "intrigue": {
        "libelle": "l'intrigue",
        "phrase": "le scénario, les retournements, la fin",
        "mots": ("intrigue", "scenario", "twist", "retournement", "revelation", "fin",
                 "denouement", "enquete", "mystere", "suspense", "histoire", "recit",
                 "surprise", "indice"),
    },
    "personnages": {
        "libelle": "les personnages",
        "phrase": "le jeu, l'interprétation, les rôles",
        "mots": ("personnage", "personnages", "acteur", "acteurs", "actrice", "jeu",
                 "interpretation", "casting", "role", "roles", "incarne", "protagoniste",
                 "heros", "duo", "performance"),
    },
    "morale": {
        "libelle": "l'ambiguïté morale",
        "phrase": "les dilemmes, la justice, la culpabilité",
        "mots": ("morale", "moral", "ambiguite", "ambigu", "ambigue", "dilemme", "justice",
                 "culpabilite", "coupable", "jugement", "ethique", "verite", "mensonge",
                 "trahison", "vengeance"),
    },
    "émotion": {
        "libelle": "l'émotion",
        "phrase": "ce que le film te fait ressentir",
        "mots": ("emu", "emue", "bouleverse", "bouleversee", "touche", "touchee", "pleure",
                 "emotion", "poignant", "poignante", "sensible", "coeur", "larmes",
                 "melancolie", "nostalgie", "amour", "tendresse"),
    },
    "son": {
        "libelle": "le son",
        "phrase": "la musique, la bande-son, le silence",
        "mots": ("musique", "bande", "son", "sonore", "silence", "theme", "melodie",
                 "bruit", "bruitage", "chanson", "partition"),
    },
    "structure": {
        "libelle": "la construction",
        "phrase": "la narration, la temporalité, la forme",
        "mots": ("temporalite", "structure", "narration", "flashback", "chronologie",
                 "construction", "forme", "boucle", "ellipse", "parallele", "huis"),
    },
    "mise en scène": {
        "libelle": "la mise en scène",
        "phrase": "le travail du réalisateur",
        "mots": ("realisation", "realise", "realisee", "realisateur", "mise", "scene",
                 "camera", "maitrise", "maitrisee", "virtuose", "geste", "style"),
    },
}

MIN_ARETES_FIABLE = 4


def _norm(t):
    t = unicodedata.normalize("NFD", (t or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.findall(r"[a-z']+", t)


def _de(libelle):
    """« le rythme » -> « du rythme », « les personnages » -> « des personnages ».

    Les libellés portent leur article pour se lire seuls (« tu regardes le rythme ») ;
    après « de », il faut donc contracter, sinon on écrit « jamais de le rythme ».
    """
    if libelle.startswith("l'"):
        return "de " + libelle
    if libelle.startswith("le "):
        return "du " + libelle[3:]
    if libelle.startswith("la "):
        return "de la " + libelle[3:]
    if libelle.startswith("les "):
        return "des " + libelle[4:]
    return "de " + libelle


def portrait(aretes):
    """Projette les ressentis sur les axes nommés. Renvoie un portrait LISIBLE.

    On lit le texte BRUT (jamais le corrigé) : c'est le vocabulaire de la personne qui
    porte le signal, pas celui d'un modèle de relecture.
    """
    ars = [a for a in (aretes or []) if (a.get("texte") or "").strip()]
    scores = {k: 0 for k in AXES}
    exemples = {k: [] for k in AXES}

    for a in ars:
        jetons = _norm(a.get("texte"))
        vus = set()
        for cle, ax in AXES.items():
            for j in jetons:
                if j in ax["mots"] and j not in vus:
                    scores[cle] += 1
                    vus.add(j)
                    if len(exemples[cle]) < 4:
                        exemples[cle].append(j)

    total = sum(scores.values())
    classe = sorted(AXES, key=lambda k: -scores[k])
    cites = [k for k in classe if scores[k] > 0]
    jamais = [k for k in classe if scores[k] == 0]

    # LA phrase — c'est elle le portrait. Le silence est aussi parlant que la mention.
    if not ars:
        phrase = None
    elif not cites:
        phrase = ("Tu as écrit, mais avec des mots que je ne sais pas encore rattacher à "
                  "un axe. Continue : c'est en écrivant que le portrait se dessine.")
    else:
        forts = [AXES[k]["libelle"] for k in cites[:2]]
        tete = " et ".join(forts)
        phrase = f"Tu regardes d'abord {tete}."
        if len(cites) > 2:
            phrase += f" Ensuite {AXES[cites[2]]['libelle']}."
        muets = [_de(AXES[k]["libelle"]) for k in jamais[:3]]
        if muets and len(ars) >= 2:
            phrase += (" Tu ne parles jamais " + ", ".join(muets) +
                       " — c'est ce silence qui te distingue le plus.")

    return {
        "aretes": len(ars),
        "fiable": len(ars) >= MIN_ARETES_FIABLE,
        "phrase": phrase,
        "axes": [{"cle": k, "libelle": AXES[k]["libelle"], "quoi": AXES[k]["phrase"],
                  "n": scores[k], "part": round(scores[k] / total, 3) if total else 0.0,
                  "mots": exemples[k]}
                 for k in classe],
        "cites": cites,
        "jamais": jamais,
    }
