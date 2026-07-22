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
#
# PURGE DES HOMOGRAPHES (22/07) — un audit a montré que ce lexique décrivait n'importe
# quoi. Sur les vraies données, l'axe dominant affiché était « l'image », allumé deux fois
# sur trois par le mot « belles »… venu de « de très belles femmes qui donnent envie de
# rester ». L'axe décrivait des actrices. Autres pièges mesurés :
#
#     « le héros perd SON sang froid »        -> le son     (possessif)
#     « TON film est sorti trop tard »        -> l'ambiance (possessif)
#     « une HISTOIRE d'amour sans intérêt »   -> l'intrigue (trop générique)
#     « à la FIN j'étais fatigué »            -> l'intrigue
#     « le PLAN du braquage »                 -> l'image
#
# Deux règles depuis : aucun mot vide de sens hors contexte, et aucun mot de VALENCE
# (« beau », « belle », « sublime ») — sinon l'axe le plus stable n'est qu'un compliment.
# Ce qui a besoin de son contexte passe en EXPRESSION, cherchée dans le texte suivi.
AXES = {
    "atmosphère": {
        "libelle": "l'atmosphère",
        "phrase": "l'ambiance et le climat d'un film",
        "mots": ("ambiance", "atmosphere", "climat", "poisseux", "poisseuse", "oppressant",
                 "oppressante", "immersion", "univers", "malaise",
                 "angoisse", "tension", "tendu", "glacial", "etouffant"),
        "expr": ("le ton", "un ton", "du film est lourde", "atmosphere lourde"),
    },
    "image": {
        "libelle": "l'image",
        "phrase": "la photo, les couleurs, les décors",
        "mots": ("couleur", "couleurs", "photographie", "lumiere", "decor", "decors",
                 "esthetique", "cadrage", "colorimetrie", "teinte", "teintes"),
        "expr": ("la photo", "l'image", "les images", "un plan", "les plans",
                 "plan sequence", "le cadre", "visuellement"),
    },
    "rythme": {
        "libelle": "le rythme",
        "phrase": "le tempo, la longueur, le montage",
        "mots": ("rythme", "lent", "lente", "lenteur", "rapide", "nerveux", "longueur",
                 "traine", "tempo", "montage", "dynamique"),
        "expr": ("trop long", "un peu long", "trop longue", "ca traine", "trop court"),
    },
    "intrigue": {
        "libelle": "l'intrigue",
        "phrase": "le scénario, les retournements, la fin",
        "mots": ("intrigue", "scenario", "twist", "retournement", "revelation",
                 "denouement", "enquete", "mystere", "suspense", "recit", "indice"),
        "expr": ("la fin", "le final", "une surprise"),
    },
    "personnages": {
        "libelle": "les personnages",
        "phrase": "le jeu, l'interprétation, les rôles",
        "mots": ("personnage", "personnages", "acteur", "acteurs", "actrice", "actrices",
                 "interpretation", "casting", "role", "roles", "incarne", "protagoniste",
                 "heros", "performance"),
        "expr": ("le jeu", "son jeu", "leur jeu", "le duo"),
    },
    "morale": {
        "libelle": "l'ambiguïté morale",
        "phrase": "les dilemmes, la justice, la culpabilité",
        "mots": ("morale", "moral", "ambiguite", "ambigu", "ambigue", "dilemme", "justice",
                 "culpabilite", "coupable", "jugement", "ethique", "mensonge",
                 "trahison", "vengeance"),
        "expr": ("la verite",),
    },
    "émotion": {
        "libelle": "l'émotion",
        "phrase": "ce que le film te fait ressentir",
        "mots": ("emu", "emue", "bouleverse", "bouleversee", "pleure",
                 "emotion", "poignant", "poignante", "larmes",
                 "melancolie", "nostalgie", "tendresse", "bouleversant"),
        "expr": ("m'a touche", "ca m'a touche", "au coeur", "en plein coeur"),
    },
    "son": {
        "libelle": "le son",
        "phrase": "la musique, la bande-son, le silence",
        "mots": ("musique", "sonore", "silence", "melodie", "bruitage", "chanson",
                 "partition", "themes"),
        "expr": ("bande son", "bande originale", "le son", "du son", "la bande",
                 "le theme"),
    },
    "structure": {
        "libelle": "la construction",
        "phrase": "la narration, la temporalité, la forme",
        "mots": ("temporalite", "structure", "narration", "flashback", "chronologie",
                 "construction", "boucle", "ellipse", "temporalites"),
        "expr": ("huis clos", "en parallele", "la forme"),
    },
    "mise en scène": {
        "libelle": "la mise en scène",
        "phrase": "le travail du réalisateur",
        "mots": ("realisation", "realise", "realisee", "realisateur", "realisatrice",
                 "camera", "maitrise", "maitrisee", "virtuose"),
        "expr": ("mise en scene", "le geste", "son style", "un style"),
    },
}

MIN_ARETES_FIABLE = 4


def _norm(t):
    t = unicodedata.normalize("NFD", (t or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.findall(r"[a-z']+", t)


def _suivi(jetons):
    """Le texte remis à plat, apostrophes comprises, pour y chercher des EXPRESSIONS.
    « l'image » est un seul jeton après _norm ; on garde donc la forme suivie telle
    quelle et on cherche dedans avec des bornes de mots."""
    return " " + " ".join(jetons) + " "


def _touches(texte):
    """Les axes touchés par un texte, avec les formes qui les ont déclenchés.

    Un axe ne compte QU'UNE FOIS par ressenti, quel que soit le nombre de mots trouvés :
    sinon un texte long l'emporte sur un texte juste, et la mesure devient un compteur
    de longueur.
    """
    jetons = _norm(texte)
    suite = _suivi(jetons)
    # DÉ-ÉLISION, mais UNIQUEMENT pour l'ensemble des mots vus. « l'intrigue » sort de
    # _norm en UN seul jeton : le mot « intrigue » n'était donc jamais reconnu, alors que
    # « une intrigue » l'était. Mesuré avant correctif :
    #     _touches("l'intrigue est faible")   -> {}
    #     _touches("une intrigue faible")     -> {'intrigue'}
    #
    # Le correctif NAÏF — dé-éliser dans le flux de jetons — rouvre exactement la famille
    # d'homographes que l'en-tête de ce fichier déclare avoir purgée, mesuré :
    #     « il parle d'un ton sec »   -> atmosphère     (« ton » possessif)
    #     « d'un plan à l'autre »     -> image
    #     « qu'un plan suffise »      -> image
    # parce que « d'un » y devient « un » et décale toute la suite.
    #
    # D'où la séparation stricte : on enrichit `vus` (recherche de mots isolés), et
    # `suite` reste bâtie sur les jetons ORIGINAUX — donc les EXPRESSIONS multi-mots
    # continuent de voir le texte tel qu'il a été écrit.
    vus = set(jetons)
    for j in jetons:
        if "'" in j:
            tete, _, queue = j.partition("'")
            if tete in ("l", "d", "n", "j", "m", "t", "s", "c", "qu") and queue:
                vus.add(queue)
    touche = {}
    for cle, ax in AXES.items():
        formes = [m for m in ax["mots"] if m in vus]
        formes += [e for e in ax.get("expr", ()) if f" {e} " in suite]
        if formes:
            touche[cle] = formes
    return touche


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
        # un axe = un point par RESSENTI, pas par occurrence : sinon le texte le plus
        # bavard gagne, et on mesure la longueur au lieu de l'attention
        for cle, formes in _touches(a.get("texte")).items():
            scores[cle] += 1
            for f in formes:
                if len(exemples[cle]) < 4 and f not in exemples[cle]:
                    exemples[cle].append(f)

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
