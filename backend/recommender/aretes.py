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
# MORDU_ETAT_DIR permet d'isoler l'état (arêtes + serrure) pour les tests et le debug.
# Sans lui, tester revenait à écrire dans les VRAIES données de l'utilisateur : j'ai
# manqué d'écraser un choix en cours avec un cycle « renoncer / tester / restaurer ».
# Les données d'une personne ne sont pas un bac à sable.
DATA_DIR = os.environ.get("MORDU_ETAT_DIR") or os.path.join(HERE, "data")
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

# NÉGATION. « Je ne suis pas déçu » est POSITIF, et mon comptage naïf le classait
# négatif : c'est l'échec classique de l'analyse de sentiment par lexique, et il est
# arrivé sur un vrai ressenti. On regarde donc les quelques mots qui PRÉCÈDENT chaque
# terme trouvé ; s'il y a une négation, on inverse sa polarité.
_NEGATION = re.compile(r"\b(?:pas|plus|jamais|aucun|aucune|sans|ni|rien)\b", re.I)
_PORTEE_NEGATION = 4          # en nombre de mots avant le terme


# Frontières de mots OBLIGATOIRES : en sous-chaîne, « beau » matche « beaucoup »,
# « fort » matche « effort », « mou » matche « mouvement ». Ces faux positifs
# inversaient le signe de la valence — donc corrompaient le profil.
# On tolère en revanche les accords : « belles » doit matcher « belle », sinon on rate
# la moitié des adjectifs d'un vrai texte français.
def _trouver(mots, t):
    """Renvoie les positions (en mots) des termes trouvés, accords compris."""
    jetons = re.findall(r"[\w'’àâäéèêëîïôöùûüç-]+", t.lower())
    positions = []
    for i, jeton in enumerate(jetons):
        for w in mots:
            if jeton == w or (jeton.startswith(w) and jeton[len(w):] in ("s", "e", "es")):
                positions.append(i)
                break
    return jetons, positions


def _compte_signe(t):
    """(positifs, négatifs) en tenant compte des négations qui inversent."""
    jetons = re.findall(r"[\w'’àâäéèêëîïôöùûüç-]+", t.lower())
    pos = neg = 0
    for i, jeton in enumerate(jetons):
        signe = 0
        for w in _POS:
            if jeton == w or (jeton.startswith(w) and jeton[len(w):] in ("s", "e", "es")):
                signe = 1
                break
        if not signe:
            for w in _NEG:
                if jeton == w or (jeton.startswith(w) and jeton[len(w):] in ("s", "e", "es")):
                    signe = -1
                    break
        if not signe:
            continue
        avant = " ".join(jetons[max(0, i - _PORTEE_NEGATION):i])
        if _NEGATION.search(avant):
            signe = -signe            # « pas déçu » -> positif ; « pas génial » -> négatif
        if signe > 0:
            pos += 1
        else:
            neg += 1
    return pos, neg


def _compte(mots, t):
    return len(_trouver(mots, t)[1])


# LE VERDICT — la valence DITE, pas devinée.
#
# Le manifeste enterre les notes : 4 contre 4,5 ne dit pas quel film on lance ce soir
# (§2). Ceci n'est PAS une note. C'est une VALENCE grossière — cinq crans sémantiques,
# jamais un chiffre affiché — et la valence est exactement ce que le moteur calcule déjà
# en interne, aujourd'hui par un lexique (valence() ci-dessous). Or ce lexique est un
# plancher assumé : mesuré, il n'atteint qu'une trentaine de valeurs distinctes, et deux
# ressentis très différents tombent souvent sur la même. Laisser la personne DÉCLARER son
# verdict est strictement plus fiable que le déduire de ses mots.
#
# Le texte reste primordial : c'est lui qui porte CE QUE tu regardes (tes axes, §4). Le
# verdict ne fait qu'expliciter la valence — il ne remplace pas le texte, il remplace la
# DEVINETTE de valence.
VERDICTS = {
    "adoré": 1.0,
    "aimé": 0.6,
    "bof": 0.1,
    "pas aimé": -0.6,
    "détesté": -1.0,
    "abandonné": -0.7,
}


def valence_de(arete):
    """La valence d'une arête : DITE si un verdict est posé, sinon devinée du texte.

    C'est le seul point où le verdict prime. Partout ailleurs le texte brut reste la
    source de vérité (le vocabulaire du profil, les axes d'attention).
    """
    v = arete.get("verdict")
    if v in VERDICTS:
        return VERDICTS[v]
    base = arete.get("corrige") or arete.get("texte")
    return valence(base)


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
    pos, neg = _compte_signe(t)
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
        "valence": valence(texte),     # figée à titre indicatif ; toutes() la RECALCULE
        "abandonne": bool(_ABANDON.search(texte or "")),
        "registre": registre,          # quel axe avait été choisi ce soir-là
        "date": _now(),
    }
    if extra:
        a.update(extra)
    # si un verdict explicite est fourni, la valence indicative suit — mais c'est
    # toutes()/valence_de qui fait foi à la lecture
    if a.get("verdict") in VERDICTS:
        a["valence"] = VERDICTS[a["verdict"]]
    with open(ARETES_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(a, ensure_ascii=False) + "\n")
    return a


def toutes():
    """Relit toutes les arêtes (la source de vérité).

    La VALENCE est RECALCULÉE à la lecture, jamais celle figée au moment de l'écriture.
    C'est le §4 du manifeste appliqué : le texte est la donnée brute, tout le reste est
    une vue. Conséquence concrète : corriger le lexique corrige aussi le PASSÉ — sinon
    un ressenti mal noté le resterait à jamais et continuerait à fausser le profil.
    """
    if not os.path.exists(ARETES_PATH):
        return []
    out = []
    with open(ARETES_PATH, encoding="utf-8") as f:
        for ligne in f:
            ligne = ligne.strip()
            if not ligne:
                continue
            try:
                a = json.loads(ligne)
            except json.JSONDecodeError:
                continue          # une ligne corrompue ne doit jamais tuer la lecture
            # La VALENCE se calcule sur le texte CORRIGÉ s'il existe : le lexique
            # reconnaît mal « génail ». Le texte BRUT, lui, reste intact — c'est lui
            # qui alimente « les mots que tu emploies » dans le profil, parce que ton
            # vocabulaire est la donnée qu'aucun modèle ne doit réécrire.
            base = a.get("corrige") or a.get("texte")
            # le VERDICT explicite prime sur le lexique (voir valence_de) ; sinon on
            # devine du texte, comme avant.
            a["valence"] = valence_de(a)
            a["abandonne"] = a.get("verdict") == "abandonné" or bool(_ABANDON.search(base or ""))
            out.append(a)
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


def palmares():
    """Le track record de l'ORACLE (MANIFESTE §9) — pas le tien.

    C'est tout le design : la série appartient à la machine. Tu ne peux jamais être
    en retard ni échouer ; c'est elle qui joue sa crédibilité à chaque verdict. On
    compte les paris que TU as jugés justes en cochant après coup.
    """
    ars = [a for a in toutes() if a.get("pari")]
    juges = [a for a in ars if a.get("pari_juste") is not None]
    bons = sum(1 for a in juges if a.get("pari_juste"))
    return {"paris": len(ars), "juges": len(juges), "bons": bons,
            "score": round(bons / len(juges), 2) if juges else None}


def poser_choix(film_id, titre=None, registre=None, pari=None, ecartes=None):
    """Arme la serrure sur le film choisi, et GARDE LES DEUX AUTRES CARTES.

    `ecartes` = les deux films qu'on te montrait au même moment et que tu n'as pas pris.

    ATTENTION AU CONTRESENS — ce ne sont PAS des rejets (MANIFESTE §3 : jamais dans les
    disliked). Ne pas choisir un film un mardi soir ne dit rien de ton goût pour lui ;
    c'est même toute la thèse du produit contre le versus « A ou B ». Ils ne touchent donc
    ni le profil, ni la répulsion.

    Ils sont conservés pour une seule raison, et elle est méthodologique : ils sont le bon
    TÉMOIN. Aujourd'hui, mesurer « de combien ce film t'a déplacé » se compare à 400 films
    tirés uniformément dans le catalogue — or l'oracle ne propose jamais uniformément, donc
    le match est truqué. Le vrai contrefactuel, c'est « et si tu avais pris l'une des deux
    autres, ce soir-là ». Sans ces deux ids, cette comparaison est IMPOSSIBLE À
    RECONSTRUIRE APRÈS COUP : c'est pour ça qu'on les écrit maintenant, même si rien ne
    les exploite encore.
    """
    # On MET À JOUR l'état, on ne le remplace pas : écrire {"en_attente": …} tout court
    # effaçait les graines de l'onboarding (donc le profil) au premier choix.
    e = lire_etat()
    e["en_attente"] = {"film_id": int(film_id), "titre": titre,
                       "registre": registre, "pari": pari, "date": _now(),
                       "ecartes": [int(i) for i in (ecartes or [])
                                   if int(i) != int(film_id)]}
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
