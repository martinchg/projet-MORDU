"""MON PROFIL — ce que l'oracle a compris de toi, rendu lisible.

Manque criant relevé à l'usage : MORDU accumulait des arêtes sans jamais montrer ce
qu'il en tirait. Un moteur qui apprend sans rien restituer est une boîte noire, et une
boîte noire n'inspire pas confiance — or la confiance est TOUT le produit ici.

C'est aussi l'application directe du §4 du manifeste (la triangulation) : la personne,
c'est ce qui est INVARIANT à travers ses arêtes. On calcule donc ce qui revient.

Volontairement honnête sur sa propre faiblesse : avec deux arêtes, on le DIT plutôt que
d'inventer un portrait. Pas de faux profilage.
"""
import os
import re
import unicodedata
from collections import Counter

import numpy as np

from .axes import portrait as _portrait
from .oracle import _IDF, IDF_MIN, _MOTIFS_BLOQUES, _MOTIFS_FR, _GENRE_FR, profil
from .recommend import _E, _ID2IDX, _movies


# Mots vides : sans eux, le « vocabulaire » d'un ressenti n'est que des articles.
_VIDES = set("""le la les un une des du de d l et ou mais donc or ni car que qui quoi
dont ou a au aux ce cet cette ces son sa ses mon ma mes ton ta tes leur leurs il elle
ils elles on nous vous je tu me te se y en est sont etait etaient ete plus moins tres
trop peu bien mal pas ne non oui pour par sur sous dans avec sans chez vers apres avant
tout tous toute toutes meme aussi encore deja alors ainsi comme si quand fait faire
fais on cela ca c j n s t qu lui leur y avoir avait ete etre suis es sommes etes
film films j'ai c'est n'est d'un d'une l'on qu'il qu'elle
deux trois fois tres plus moins assez vraiment beaucoup peut etre sorte genre chose
truc alors donc apres avant pendant depuis toujours jamais souvent parfois quelque
quelques autre autres certain certains grand grande petit petite bon bonne mauvais
lui elle cela celui celle ceux dire dit voir vu vus faire fait sais sait peu""".split())


def _sans_article(s):
    """« l'animation » -> « animation ». NE PAS utiliser lstrip() : il retire des
    CARACTÈRES, pas un préfixe — « l\'animation » y devenait « nimation »."""
    for a in ("l'", "la ", "le ", "les ", "un ", "une "):
        if s.startswith(a):
            return s[len(a):]
    return s


def _mots(texte):
    """Les mots de contenu d'un ressenti, accents PLIÉS.

    _VIDES est écrit sans accents ; sans le pli, « très », « même », « déjà » et « après »
    ne matchaient aucune entrée et remontaient en tête du nuage « les mots qui te
    reviennent ». Mesuré sur les vraies données : les trois mots communs aux deux seuls
    ressentis étaient « belles », « même », « très ». Un nuage de mots vides.
    """
    t = unicodedata.normalize("NFD", (texte or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^\w' ]", " ", t)
    return [m for m in t.split() if len(m) >= 4 and m not in _VIDES]


_ORDRE_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "data", "_ordre_dims.npy")


def _ordre_dimensions():
    """Range les 384 dimensions pour que les corrélées soient voisines. LISSAGE PUREMENT
    COSMÉTIQUE — et il a fallu un audit externe pour l'admettre.

    Ce que ça fait vraiment : sans ordonnancement le glyphe est du poivre et sel, avec il
    a des régions. La corrélation entre cellules voisines passe de 0,079 à 0,242.

    CE QUE ÇA NE FAIT PAS, mesuré le 22/07 : ça ne révèle AUCUNE structure du goût. En
    appliquant une rotation orthogonale aléatoire Q à l'espace (E' = E·Q, p' = p·Q), les
    6000 similarités sont conservées à 3,3e-16 près et le top-20 des recommandations est
    identique — le modèle est rigoureusement le même. Or le glyphe change à 90,4 %, et le
    même ordonnancement atteint 0,238 de corrélation dans cette base tirée au hasard,
    contre 0,242 dans la vraie.

    Autrement dit : il obtient le même résultat sur n'importe quelles coordonnées. Les
    « régions » qu'il dessine sont un artefact de la procédure de tri, pas une propriété
    de la personne. Elles n'ont donc pas le droit d'être COMMENTÉES à l'écran — dire
    « ces taches sont des régions de ton goût qui ont bougé ensemble » était faux, et
    c'est retiré.

    Ce qui survit : à modèle fixé, même goût -> même image, goût différent -> image
    différente. C'est une empreinte au sens d'un SCEAU, pas au sens d'une carte. Elle
    identifie ; elle n'explique rien, et on ne doit rien lui faire dire.

    Calculé une fois, mis en cache : l'ordre ne dépend que du catalogue.
    """
    from .recommend import _E
    if os.path.exists(_ORDRE_CACHE):
        try:
            o = np.load(_ORDRE_CACHE)
            if len(o) == _E.shape[1]:
                return o
        except Exception:
            pass
    try:
        from scipy.cluster.hierarchy import leaves_list, linkage, optimal_leaf_ordering
        from scipy.spatial.distance import squareform
        C = np.abs(np.corrcoef(_E.T))
        np.fill_diagonal(C, 1.0)
        D = 1.0 - C
        np.fill_diagonal(D, 0.0)
        D = (D + D.T) / 2
        cond = squareform(D, checks=False)
        o = leaves_list(optimal_leaf_ordering(linkage(cond, method="average"), cond))
    except Exception:
        o = np.arange(_E.shape[1])          # sans scipy : ordre naturel, ça marche quand même
    np.save(_ORDRE_CACHE, o)
    return o


_ORDRE = None


NIVEAUX = 11          # les 11 couleurs de la palette, une fois pour toutes
LARGEUR = 24          # 24 x 16 = 384 cellules = 384 dimensions, une cellule par dimension


def grille(p, lo=None, hi=None, largeur=LARGEUR):
    """Un vecteur 384D -> la grille quantifiée, plus les bornes utilisées.

    Séparé d'empreinte() pour que DEUX vecteurs (le profil de toujours et le profil
    récent) puissent être quantifiés sur les MÊMES bornes. Sans bornes partagées, chacun
    se renormalise sur lui-même et les comparer n'a aucun sens.
    """
    global _ORDRE
    if _ORDRE is None:
        _ORDRE = _ordre_dimensions()
    v = np.asarray(p, dtype=float)[_ORDRE]      # dimensions corrélées côte à côte
    hauteur = int(np.ceil(len(v) / largeur))
    pad = np.zeros(hauteur * largeur)
    pad[: len(v)] = v
    g = pad.reshape(hauteur, largeur)
    # normalisation robuste : les extrêmes d'un embedding écraseraient tout le reste
    if lo is None or hi is None:
        lo, hi = float(np.percentile(g, 3)), float(np.percentile(g, 97))
    g = np.clip((g - lo) / max(hi - lo, 1e-9), 0, 1)
    q = np.floor(g * (NIVEAUX - 1) + 0.5).astype(int)
    return q, hauteur, lo, hi


def empreinte(graines, aretes, largeur=LARGEUR):
    """TON EMPREINTE — le vecteur profil (384D) rendu en glyphe.

    Ton goût EST déjà un objet mathématique unique : plutôt que de le résumer en barres,
    on le montre tel quel, replié en grille et quantifié sur la palette dither.
    Déterministe : même goût, même glyphe.

    LA RAMPE DE FINESSE A ÉTÉ SUPPRIMÉE (22/07, après mesure). Le glyphe agrégeait par
    blocs de 3 -> 2 -> 1 et passait de 4 à 11 paliers selon le NOMBRE d'arêtes. En
    figeant le profil et en ne faisant varier que le compteur, jusqu'à 82,6 % de la
    grille changeait de couleur À GOÛT STRICTEMENT IDENTIQUE — sept transitions sur
    douze au-dessus de 45 %. Un vrai pas de goût, lui, en déplace la moitié.

    L'artefact était donc plus gros que le signal : ce qu'on prenait pour « l'empreinte
    qui évolue » était un compteur d'arêtes dessiné en pixels, c'est-à-dire une jauge de
    complétion — précisément ce que le §8 du manifeste enterre. Retirer le pourcentage
    n'aurait pas retiré la jauge ; il fallait retirer la rampe.

    L'évolution est désormais portée par une mesure qui en est vraiment une : la BRAISE
    (voir derive.py), l'écart entre ce que tu racontes en ce moment et tout ce que tu as
    raconté. Elle, elle naît vide et grandit avec la vie.
    """
    p = profil(graines, aretes)
    if p is None:
        return None
    q, hauteur, lo, hi = grille(p, largeur=largeur)
    return {"largeur": largeur, "hauteur": hauteur, "niveaux": NIVEAUX,
            "aretes": len(aretes or []), "lo": lo, "hi": hi,
            "cellules": [int(x) for x in q.flatten()]}


def construire(graines, aretes, palmares=None):
    """Agrège les arêtes en un portrait. Tout est recalculable : rien n'est stocké."""
    ids = list(graines or []) + [a["film_id"] for a in (aretes or [])]
    films = [_movies[_ID2IDX[i]] for i in ids if i in _ID2IDX]
    n = len(films)

    genres, motifs, reals, acteurs = Counter(), Counter(), Counter(), Counter()
    for f in films:
        for g in f.get("genres") or []:
            genres[g] += 1
        for k in set(f.get("keywords") or []):
            if _IDF.get(k, 0) >= IDF_MIN and k not in _MOTIFS_BLOQUES and k in _MOTIFS_FR:
                motifs[k] += _IDF[k]          # pondéré par la rareté : un motif rare pèse
        for d in f.get("director") or []:
            reals[d] += 1
        for c in (f.get("cast") or [])[:5]:
            acteurs[c] += 1

    # ce que TU écris : ton axe d'attention (§4 — « ce que tu mentionnes est ton goût »)
    vocab = Counter()
    for a in aretes or []:
        # TOUJOURS le texte brut, jamais le corrigé : si un LLM réécrit tes phrases,
        # ce nuage afficherait SON vocabulaire et plus le tien. C'est précisément ce
        # que ce bloc est censé montrer.
        for m in _mots(a.get("texte")):
            vocab[m] += 1

    # profil géométrique : les films du catalogue les plus proches de ton vecteur
    voisins = []
    p = profil(graines, aretes)
    if p is not None:
        sims = _E @ p
        deja = {i for i in ids}
        ordre = sorted(range(len(_movies)), key=lambda i: -sims[i])
        for i in ordre:
            if _movies[i]["id"] in deja:
                continue
            voisins.append({"id": _movies[i]["id"], "title": _movies[i]["title"],
                            "poster_path": _movies[i].get("poster_path"),
                            "genres": _movies[i].get("genres"),
                            "affinite": round(float(sims[i]), 3)})
            if len(voisins) >= 8:
                break

    duree = [f.get("runtime") for f in films if f.get("runtime")]
    annees = []
    for f in films:
        try:
            annees.append(int(str(f.get("year") or "")[:4]))
        except ValueError:
            pass

    return {
        "films": n,
        "aretes": len(aretes or []),
        # honnêteté : en dessous de 5 arêtes, un « portrait » serait de l'invention
        "fiable": len(aretes or []) >= 5,
        "genres": [{"nom": _sans_article(_GENRE_FR.get(g, g)), "brut": g, "n": c}
                   for g, c in genres.most_common(6)],
        "motifs": [{"nom": _MOTIFS_FR[k], "poids": round(v, 1)}
                   for k, v in motifs.most_common(8)],
        "realisateurs": [{"nom": r, "n": c} for r, c in reals.most_common(5)],
        "acteurs": [{"nom": a, "n": c} for a, c in acteurs.most_common(5)],
        "vocabulaire": [{"mot": m, "n": c} for m, c in vocab.most_common(12) if c >= 1],
        "voisins": voisins,
        "duree_moyenne": round(sum(duree) / len(duree)) if duree else None,
        "annee_moyenne": round(sum(annees) / len(annees)) if annees else None,
        "palmares": palmares or {},
        "empreinte": empreinte(graines, aretes),
        "portrait": _portrait(aretes),
    }
