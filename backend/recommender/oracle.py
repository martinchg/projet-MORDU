"""L'ORACLE — 3 cartes aux axes orthogonaux (cf. MANIFESTE.md §1, §3, §10).

MORDU ne montre pas un catalogue : il tend TROIS films — trois directions, trois
arguments. Choisir une carte, ce n'est pas classer des films, c'est déclarer son envie
du soir. Conséquences gravées dans le manifeste et respectées ici :

- Les trois axes sont ORTHOGONAUX : jamais trois thrillers (sinon c'est un mini-menu).
  Garanti par un plancher de dissimilarité entre les cartes retenues.
- La carte non choisie n'est JAMAIS un rejet -> elle ne part jamais en `disliked_ids`.
  (Piège hérité de l'onboarding « ça ou ça » : ici, interdit.)
- L'exploration est ANNONCÉE : chaque carte porte son registre (connu / écart / pari).
- Invitation, jamais dette : un écart part TOUJOURS d'une arête existante de l'user
  (« tu as aimé 12 hommes en colère -> Témoin à charge »), jamais d'un canon absolu.

Le profil vient des ARÊTES (ressentis) et des films-graines, jamais d'une note.

CLI :
    python oracle.py
"""
import json
import os
import random
import re

import numpy as np

from .recommend import (  # noqa: F401  (on réutilise le catalogue déjà chargé)
    _E, _ID2IDX, _blocked, _movies, _votes, _unit, RECO_MIN_VOTES,
)

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")

# --- Réglages des trois registres ---------------------------------------------------
# Bandes en PERCENTILES, pas en valeurs absolues : la distribution des similarités dépend
# du profil (ici, médiane ~0.46, max ~0.83 — un seuil en dur serait faux pour un autre
# goût). En percentiles, les trois registres gardent leur sens pour n'importe qui.
BANDES = {
    "connu":  (96, 100),   # le haut du panier
    "ecart":  (78, 93),    # voisin, sans rupture
    "pari":   (45, 72),    # franchement ailleurs — mais TOUJOURS relié par une ancre
}
# Plancher d'orthogonalité : deux cartes ne peuvent pas se ressembler plus que ça.
MAX_SIM_ENTRE_CARTES = 0.55
# Taille du vivier dans lequel on tire au sort (évite de resservir le même trio).
# Étroit pour « connu » — on veut le meilleur match, pas le 12ᵉ ; large pour « pari »,
# où la surprise est le but. Un vivier uniforme sortait Shelter en terrain connu.
VIVIER_PAR_REGISTRE = {"connu": 5, "ecart": 9, "pari": 14}
VIVIER = 12
# Un « pari » sans lien avec ton goût n'est pas une invitation, c'est un jet de dé
# (MANIFESTE : invitation ≠ dette). On exige donc une ancre pour TOUTE carte.
ANCRE_OBLIGATOIRE = True

_HOOKS_PATH = os.path.join(DATA_DIR, "hooks.json")
_DOMAINES_PATH = os.path.join(DATA_DIR, "domaines.json")


def _load_canons():
    """film_id -> [(nom, type)] des domaines dont ce film est un ESSENTIEL.

    Le canon n'est PAS une checklist affichée (MANIFESTE §7 : pas de jauge, pas de
    dette) — c'est un ingrédient invisible de l'arbitrage. Un essentiel de quelqu'un
    dont tu as déjà vu un film est une invitation ; un essentiel sorti d'une liste
    absolue serait une dette. D'où : on ne s'en sert QUE si la personne apparaît déjà
    dans tes références.
    """
    try:
        with open(_DOMAINES_PATH, encoding="utf-8") as f:
            doms = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    out = {}
    for d in doms:
        for film in d.get("canon") or []:
            out.setdefault(film["id"], []).append((d["name"], d["type"]))
    return out


_CANON = _load_canons()
BONUS_CANON = 0.035   # léger : le canon nuance le classement, il ne le dicte pas

# Un fait de box-office n'est PAS croustillant : « il a rapporté 100 125 643 dollars »
# n'accroche personne et abîme l'organe de confiance. Mieux vaut aucun fait qu'un fait
# plat — la carte tient déjà debout sur son argument.
_HOOK_PLAT = re.compile(
    r"box[- ]office|recettes|a rapport[ée]|dollars|entrées en france|budget de"
    r"|grossed|million de dollars|prix du ticket", re.I)


def _hook_valable(h):
    """Filtre les faits ternes. Un hook faible vaut moins que pas de hook du tout."""
    if not isinstance(h, dict):
        return None
    txt = (h.get("hook") or "").strip()
    if not txt or len(txt) < 40:
        return None
    if _HOOK_PLAT.search(txt):
        # on tente un candidat de repli avant d'abandonner
        for c in (h.get("candidates") or []):
            t = c.get("hook") if isinstance(c, dict) else (c if isinstance(c, str) else "")
            if t and len(t) >= 40 and not _HOOK_PLAT.search(t):
                return t.strip()
        return None
    return txt


def _essentiel_de(film, refs):
    """Le film est-il un essentiel d'une personne déjà présente dans tes arêtes ?"""
    noms = set()
    for r in refs:
        noms |= set(r.get("director") or [])
        noms |= set((r.get("cast") or [])[:6])
    for nom, typ in _CANON.get(film.get("id"), []):
        if nom in noms:
            return nom, typ
    return None


def _load_hooks():
    """Faits croustillants pré-générés (offline). Absents = on dégrade proprement."""
    try:
        with open(_HOOKS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


_hooks = _load_hooks()

_CARTE_FIELDS = ("id", "title", "year", "genres", "poster_url", "poster_path", "overview",
                 "runtime", "director", "cast", "keywords", "tagline", "imdb_rating",
                 "providers_fr", "trailer_key", "vote_average")


# --- Profil -------------------------------------------------------------------------
def profil(seed_ids, aretes=None):
    """Vecteur de goût = graines + arêtes (ressentis), pondérées par leur valence.

    Une arête est un ressenti : {film_id, valence (-1..1), ...}. Pas de note, pas
    d'étoile — la valence est dérivée du texte en aval (v0 : fournie par l'appelant).
    """
    poids, idxs = [], []
    for i in seed_ids or []:
        if i in _ID2IDX:
            idxs.append(_ID2IDX[i])
            poids.append(1.0)
    for a in aretes or []:
        i = a.get("film_id")
        if i in _ID2IDX:
            idxs.append(_ID2IDX[i])
            # une arête vécue pèse plus qu'une graine déclarative
            poids.append(1.5 * float(a.get("valence", 1.0)))
    if not idxs:
        return None
    W = np.array(poids, dtype=float)[:, None]
    return _unit((_E[idxs] * W).sum(axis=0))


# --- Rareté des motifs (IDF) --------------------------------------------------------
# Un motif partagé ne se vaut pas : « based on novel » relie la moitié du catalogue et ne
# dit rien ; « serial killer » relie trois films et dit tout. On pondère donc chaque
# mot-clé par sa rareté, et une ancre ne compte que si elle est DISTINCTIVE.
def _idf_motifs():
    df = {}
    for m in _movies:
        for k in set(m.get("keywords") or []):
            df[k] = df.get(k, 0) + 1
    n = len(_movies)
    return {k: float(np.log(n / (1 + v))) for k, v in df.items()}


_IDF = _idf_motifs()
IDF_MIN = 3.5          # en dessous : motif trop banal pour servir d'argument
FORCE_ANCRE_MIN = 3.5  # score minimal pour considérer qu'une carte est « reliée »

# TMDB mêle trois choses dans `keywords` : de vrais motifs (« serial killer »), des
# ÉTIQUETTES D'HUMEUR générées (« baffled », « bold », « admiring ») et des méta de
# production (« reboot », « based on tv series »). Seuls les motifs font un argument :
# « baffled et brutality » ne veut rien dire. On bloque le reste.
_MOTIFS_BLOQUES = {
    # humeurs / adjectifs générés
    "dramatic", "bold", "aggressive", "playful", "hilarious", "admiring", "enthusiastic",
    "absurd", "inspirational", "romantic", "complex", "hopeful", "cheerful", "anxious",
    "adoring", "whimsical", "nostalgic", "complicated", "awestruck", "baffled", "cliché",
    "emotional", "intense", "funny", "sad", "dark", "serious", "light", "quirky",
    # méta de production
    "based on tv series", "based on video game", "based on novel or book", "spin off",
    "prequel", "sequel", "reboot", "remake", "live action and animation", "based on comic",
    "based on true story", "duringcreditsstinger", "aftercreditsstinger", "woman director",
}

# Le projet est en français : un argument qui sort « concentration camp et world war ii »
# est une faute. On traduit les motifs courants ; ceux qu'on ne sait pas dire sont
# dépriorisés plutôt que recrachés en anglais.
_MOTIFS_FR = {
    "serial killer": "tueur en série", "psychopath": "psychopathe", "detective": "enquête",
    "investigation": "investigation", "whodunit": "whodunit", "crime scene": "scène de crime",
    "neo-noir": "néo-noir", "psychological thriller": "thriller psychologique",
    "psychological horror": "horreur psychologique", "supernatural horror": "horreur surnaturelle",
    "slasher": "slasher", "monster": "monstre", "creature": "créature", "ghost": "fantôme",
    "vampire": "vampire", "zombie": "zombie", "demon": "démon", "witch": "sorcière",
    "kidnapping": "enlèvement", "torture": "torture", "rape": "viol", "betrayal": "trahison",
    "obsession": "obsession", "revenge": "vengeance", "vigilante": "justicier",
    "assassin": "tueur à gages", "gangster": "gangster", "organized crime": "crime organisé",
    "heist": "casse", "police": "police", "shootout": "fusillade", "escape": "évasion",
    "on the run": "cavale", "race against time": "course contre la montre",
    "conspiracy": "complot", "spy": "espionnage", "secret identity": "identité secrète",
    "anti hero": "anti-héros", "action hero": "héros d'action", "fight": "combat",
    "battle": "bataille", "war": "guerre", "world war ii": "Seconde Guerre mondiale",
    "concentration camp": "camp de concentration", "soldier": "soldat",
    "time travel": "voyage dans le temps", "super power": "super-pouvoirs",
    "alien invasion": "invasion extraterrestre", "space travel": "voyage spatial",
    "space opera": "space opera", "spacecraft": "vaisseau spatial", "space": "espace",
    "robot": "robot", "scientist": "scientifique", "dystopia": "dystopie",
    "post-apocalyptic future": "futur post-apocalyptique", "saving the world": "sauver le monde",
    "fantasy world": "monde imaginaire", "wizard": "magie", "dragon": "dragon",
    "fairy tale": "conte", "princess": "princesse", "anthropomorphism": "animaux qui parlent",
    "cartoon": "dessin animé", "anime": "anime", "animals": "animaux",
    "dark comedy": "comédie noire", "satire": "satire", "romcom": "comédie romantique",
    "romance": "romance", "love": "amour", "eroticism": "érotisme",
    "sibling relationship": "fratrie", "parent child relationship": "lien parent-enfant",
    "father son relationship": "relation père-fils", "father daughter relationship": "relation père-fille",
    "mother daughter relationship": "relation mère-fille", "daughter": "filiation",
    "friends": "amitié", "rivalry": "rivalité", "bullying": "harcèlement",
    "high school": "lycée", "school": "école", "teenage girl": "adolescence",
    "coming of age": "passage à l'âge adulte", "drugs": "drogue", "alcoholic": "alcoolisme",
    "dying and death": "la mort", "tragedy": "tragédie", "suicide": "suicide",
    "biography": "biographie", "period drama": "drame d'époque", "sports": "sport",
    "boxing": "boxe", "music": "musique", "christmas": "Noël", "survival": "survie",
    "good versus evil": "le bien contre le mal", "mission": "mission", "prison": "prison",
    "courtroom": "prétoire", "journalism": "journalisme", "politics": "politique",
    "1940s": "les années 40", "1960s": "les années 60", "1970s": "les années 70",
    "1980s": "les années 80", "19th century": "le XIXe siècle",
    "london, england": "Londres", "paris, france": "Paris",
    "new york city": "New York", "san francisco, california": "San Francisco",
    "los angeles, california": "Los Angeles", "japan": "le Japon",
}


_GENRE_FR = {
    "Animation": "l'animation", "Comedy": "la comédie", "Drama": "le drame",
    "Thriller": "le thriller", "Horror": "l'horreur", "Science Fiction": "la SF",
    "Fantasy": "le fantastique", "Crime": "le film criminel", "Mystery": "le mystère",
    "Romance": "la romance", "Adventure": "l'aventure", "Action": "l'action",
    "Family": "le film familial", "War": "le film de guerre", "Western": "le western",
    "History": "le film historique", "Music": "le film musical",
    "Documentary": "le documentaire", "TV Movie": "le téléfilm",
}


def _motif_fr(k):
    """Motif en français si on sait le dire, sinon None (on préfère l'ignorer)."""
    return _MOTIFS_FR.get(k)


_RE_SUITE = re.compile(
    r"(?:"
    r"\b(?:part|vol\.?|volume|chapter|chapitre|episode|épisode)\s+"
    r"(?:\d+|[ivx]+|one|two|three|four|five|deux|trois)\b"
    r"|\s(?:II|III|IV|V|VI|VII|VIII|IX|X|XI|XII)$"      # chiffres romains finaux
    r"|\s\d{1,2}$"                                       # « Machin 2 »
    r"|\b(?:reloaded|revolutions|resurrection|returns)\b"
    r")", re.IGNORECASE)


_TITRES = {(m.get("title") or "").strip().lower() for m in _movies}


def _est_suite(film):
    """Repère les suites/volets. Proposer « Scream VI » ou « Sicario: Day of the
    Soldado » à quelqu'un qui n'a pas vu les précédents est une faute produit.

    Deux détections :
    1. les marqueurs explicites (chiffres romains/arabes finaux, « Part », « Vol. ») —
       ancrés en FIN de titre, sinon « X-Men » ou « 1917 » sautent à tort ;
    2. les suites NOMMÉES (« Sicario: Day of the Soldado ») : si le segment avant les
       deux-points est lui-même un film du catalogue, c'est un volet ultérieur.
    """
    t = (film.get("title") or "").strip()
    if _RE_SUITE.search(t):
        return True
    if ":" in t:
        base = t.split(":", 1)[0].strip().lower()
        if len(base) >= 3 and base in _TITRES and base != t.lower():
            return True
    return False


# --- Fabrique d'arguments -----------------------------------------------------------
def _ancre(film, refs):
    """Trouve le LIEN concret entre un film et ce que l'user a aimé (l'invitation).

    Retourne (type, valeur, film_source, force) — jamais « parce que vous avez
    regardé » : on veut de la matière (un réal, un acteur, un motif rare).
    """
    f_dir = set(film.get("director") or [])
    f_cast = set((film.get("cast") or [])[:6])
    f_kw = set(film.get("keywords") or [])
    meilleur = None

    def garde(cand):
        nonlocal meilleur
        if meilleur is None or cand[3] > meilleur[3]:
            meilleur = cand

    for r in refs:
        inter_dir = f_dir & set(r.get("director") or [])
        if inter_dir:
            garde(("real", sorted(inter_dir)[0], r, 10.0))
            continue
        inter_cast = f_cast & set((r.get("cast") or [])[:6])
        if inter_cast:
            garde(("acteur", sorted(inter_cast)[0], r, 6.0))
        inter_kw = f_kw & set(r.get("keywords") or [])
        # on ne garde que des motifs DISTINCTIFS, non-bruités, et qu'on sait dire en
        # français (sinon l'argument sort en anglais au milieu d'une phrase française)
        rares = sorted(
            (k for k in inter_kw
             if _IDF.get(k, 0) >= IDF_MIN
             and k not in _MOTIFS_BLOQUES
             and _motif_fr(k)),
            key=lambda k: -_IDF.get(k, 0))
        if rares:
            force = sum(_IDF[k] for k in rares[:2])
            garde(("motif", [_motif_fr(k) for k in rares[:2]], r, force))

    if meilleur is None:
        # Repli de genre : faible, mais TOUJOURS concret et toujours ancré dans une
        # arête existante. Sans lui, un excellent match sans mot-clé rare partagé
        # (Coraline pour un amateur de Miyazaki) serait éjecté au profit d'un moins
        # bon qui a un motif commun — la sémantique doit primer sur le mot-clé.
        f_g = set(film.get("genres") or [])
        for r in refs:
            inter = f_g & set(r.get("genres") or [])
            if inter:
                g = sorted(inter, key=lambda x: -len(x))[0]
                garde(("genre", _GENRE_FR.get(g, g.lower()), r, 2.0))
                break
    return meilleur


def _an(film):
    """`year` est stocké en chaîne (parfois vide/partielle) -> int sûr, 0 si inconnu."""
    try:
        return int(str(film.get("year") or "")[:4])
    except ValueError:
        return 0


def _contraste(film, refs):
    """Ce qui DIFFÉRENCIE le film des références — le « mais » de l'argument."""
    if not refs:
        return None
    rt = film.get("runtime") or 0
    rts = [r.get("runtime") or 0 for r in refs if r.get("runtime")]
    moy_rt = sum(rts) / len(rts) if rts else 0
    if rt and moy_rt:
        if rt <= moy_rt - 25:
            return "un rythme plus sec"
        if rt >= moy_rt + 25:
            return "une coupe plus ample"
    an = _an(film)
    ans = [a for a in (_an(r) for r in refs) if a]
    moy_an = sum(ans) / len(ans) if ans else 0
    if an and moy_an:
        if an <= moy_an - 18:
            return "une facture d'une autre époque"
        if an >= moy_an + 18:
            return "une facture nettement plus moderne"
    g = set(film.get("genres") or [])
    gr = set()
    for r in refs:
        gr |= set(r.get("genres") or [])
    neuf = g - gr
    if neuf:
        trad = {"Comedy": "une veine comique", "Animation": "le geste animé",
                "Documentary": "le régime documentaire", "Romance": "un cœur romanesque",
                "Horror": "une charge horrifique", "Science Fiction": "un versant SF",
                "Fantasy": "un versant fantastique", "War": "un cadre de guerre",
                "Western": "un cadre de western", "Music": "une pulsation musicale"}
        for n in neuf:
            if n in trad:
                return trad[n]
    return None


# Plusieurs moules par type d'ancre : trois fois la même tournure dans un tirage, ça
# sonne robot. On fait tourner (variante dérivée du tirage, donc stable pour un seed).
_MOULES = {
    "real": [
        "L'univers de {v}, comme dans {t}",
        "Encore {v}, après {t}",
        "La patte de {v} — celle de {t}",
    ],
    "acteur": [
        "{v}, que tu as vu dans {t}",
        "{v} de nouveau, après {t}",
        "Retrouver {v}, croisé dans {t}",
    ],
    "motif": [
        "Le terrain de {t} — {v}",
        "{v} : la veine de {t}",
        "Même sillon que {t} — {v}",
    ],
    "genre": [
        "Le registre de {t} — {v}",
        "{v}, comme {t}",
        "Toujours {v}, après {t}",
    ],
}


def _argument(film, refs, registre, anc=None, variante=0):
    """Construit la phrase d'accroche. Jamais « parce que vous avez regardé ».

    Forme visée (celle du manifeste) : <ce qui relie> MAIS <ce qui diffère>.
    Pour un pari, le « mais » porte la charge : c'est l'axe du risque, annoncé.
    """
    anc = anc if anc is not None else _ancre(film, refs)
    con = _contraste(film, refs)
    bout = None
    if anc:
        typ, val, src, _f = anc
        v = " et ".join(val) if isinstance(val, list) else str(val)
        moules = _MOULES[typ]
        bout = moules[variante % len(moules)].format(v=v, t=src.get("title"))

    if bout and con:
        liaison = "mais cette fois" if registre == "pari" else "mais avec"
        phrase = f"{bout}, {liaison} {con}."
    elif bout:
        phrase = f"{bout}."
    elif con:
        phrase = f"Un pas de côté : {con}."
    else:
        phrase = {"connu": "Droit dans ton axe.",
                  "ecart": "Voisin de ce que tu aimes, par un autre chemin.",
                  "pari": "Rien à voir avec tes habitudes — c'est le pari."}[registre]

    # Le canon en INVITATION : on le mentionne seulement si la personne est déjà dans
    # tes arêtes. « Un essentiel de Fincher, et tu ne l'as pas vu » invite ; « il FAUT
    # avoir vu Citizen Kane » endette. La nuance est toute la ligne du manifeste.
    ess = _essentiel_de(film, refs)
    if ess:
        quoi = {"director": "de", "actor": "de", "studio": "de"}.get(ess[1], "de")
        phrase += f" Un essentiel {quoi} {ess[0]}, que tu n'as pas encore vu."

    # le fait croustillant, s'il existe (organe de confiance)
    h = _hooks.get(str(film.get("id"))) or _hooks.get(film.get("id"))
    croustillant = _hook_valable(h)
    return phrase, croustillant


REGISTRES = {
    "connu": {"label": "TERRAIN CONNU", "annonce": "Ce soir, je reste dans ton axe."},
    "ecart": {"label": "PAS DE CÔTÉ", "annonce": "Un écart tempéré — voisin, mais pas pareil."},
    "pari":  {"label": "LE PARI", "annonce": "Je te sors de ta zone. Fais-moi confiance."},
}


def _carte(idx, sim, registre, refs, anc=None, variante=0):
    m = _movies[idx]
    phrase, croustillant = _argument(m, refs, registre, anc, variante)
    return {
        **{f: m.get(f) for f in _CARTE_FIELDS},
        "registre": registre,
        "label": REGISTRES[registre]["label"],
        "annonce": REGISTRES[registre]["annonce"],
        "argument": phrase,
        "croustillant": croustillant,
        "affinite": round(float(sim), 4),
    }


def tirage(seed_ids=None, aretes=None, exclure=None, min_votes=RECO_MIN_VOTES, seed=None):
    """Rend les 3 cartes. Aucune n'est un rejet ; aucune ne revient si déjà vue.

    `exclure` = films déjà vus / déjà proposés / déjà racontés (arêtes).
    """
    rng = random.Random(seed)
    p = profil(seed_ids, aretes)
    if p is None:
        return []

    sims = _E @ p
    dispo = np.ones(len(_movies), dtype=bool)
    dispo &= _votes >= min_votes
    dispo &= ~_blocked
    for i in (exclure or []):
        if i in _ID2IDX:
            dispo[_ID2IDX[i]] = False
    for i in (seed_ids or []):
        if i in _ID2IDX:
            dispo[_ID2IDX[i]] = False
    for a in (aretes or []):
        i = a.get("film_id")
        if i in _ID2IDX:
            dispo[_ID2IDX[i]] = False

    # les films de référence servent à FABRIQUER l'argument (le lien concret)
    ref_idx = [_ID2IDX[i] for i in (seed_ids or []) if i in _ID2IDX]
    ref_idx += [_ID2IDX[a["film_id"]] for a in (aretes or [])
                if a.get("film_id") in _ID2IDX]
    refs = [_movies[i] for i in ref_idx]

    # seuils réels de CE profil (les bandes sont en percentiles — cf. BANDES)
    ref_sims = sims[dispo]
    if len(ref_sims) == 0:
        return []

    cartes, pris, sources = [], [], set()
    for registre, (plo, phi) in BANDES.items():
        lo, hi = np.percentile(ref_sims, plo), np.percentile(ref_sims, phi)
        bande = np.where(dispo & (sims >= lo) & (sims <= hi))[0]
        if len(bande) == 0:
            bande = np.where(dispo & (sims <= hi))[0]
        if len(bande) == 0:
            continue

        # orthogonalité : on écarte ce qui ressemble trop aux cartes déjà retenues
        if pris:
            proche = (_E[bande] @ _E[pris].T).max(axis=1)
            libre = bande[proche < MAX_SIM_ENTRE_CARTES]
            if len(libre):
                bande = libre

        # pas de suites orphelines (« Vol. II » sans le I)
        sans_suite = [int(i) for i in bande if not _est_suite(_movies[i])]
        if sans_suite:
            bande = np.array(sans_suite)

        # La SÉMANTIQUE décide ; l'ancre départage et fournit l'argument.
        # Filtrer d'abord sur l'ancre éjectait Coraline (excellent match, aucun motif
        # rare partagé) au profit de Transformers, qui avait « robot » en commun : le
        # mot-clé partagé n'est pas le goût. INVITATION reste garantie — le repli de
        # genre ancre toujours la carte dans une arête existante.
        tete = [int(i) for i in bande[np.argsort(-sims[bande])][: VIVIER * 2]]
        ancres = {i: _ancre(_movies[i], refs) for i in tete}
        # PAS de filtre sur la force de l'ancre : préférer les ancres fortes éjectait
        # Coraline (2ᵉ par affinité, ancrée seulement par le genre) au profit de
        # Dungeons & Dragons (« amitié » en commun). Le repli de genre garantit que
        # presque tout film est argumentable — la force ne sert plus qu'à départager.
        pool = [i for i in tete if ancres[i]] or tete
        # trois cartes qui renvoient toutes à Se7en, c'est un tirage myope
        neuf = [i for i in pool if ancres.get(i) and ancres[i][2].get("id") not in sources]
        pool = neuf or pool

        def _rang(i):
            # à affinité voisine, un film mieux tenu passe devant : recommander un
            # obscur mal noté coûte de la confiance, et la confiance est tout ici.
            note = _movies[i].get("imdb_rating") or _movies[i].get("vote_average") or 6.5
            s = sims[i] + 0.02 * (float(note) - 6.5)
            if _essentiel_de(_movies[i], refs):
                s += BONUS_CANON      # un essentiel de quelqu'un que tu connais déjà
            return -s

        pool.sort(key=_rang)
        ordre = pool[: VIVIER_PAR_REGISTRE.get(registre, VIVIER)]

        choix = int(rng.choice(ordre))
        pris.append(choix)
        dispo[choix] = False
        a = ancres.get(choix)
        if a:
            sources.add(a[2].get("id"))
        cartes.append(_carte(choix, sims[choix], registre, refs, a, len(cartes)))
    return cartes


if __name__ == "__main__":
    from .recommend import ids_from_titles
    seeds = ids_from_titles(["Se7en", "Zodiac", "Prisoners", "Fight Club", "Shutter Island"])
    print("Graines : Se7en, Zodiac, Prisoners, Fight Club, Shutter Island\n")
    for c in tirage(seed_ids=seeds, seed=7):
        print(f"[{c['label']}]  {c['title']} ({c['year']})  · affinité {c['affinite']:.2f}")
        print(f"   {c['annonce']}")
        print(f"   → {c['argument']}")
        if c["croustillant"]:
            print(f"   ✦ {c['croustillant'][:150]}")
        print()
