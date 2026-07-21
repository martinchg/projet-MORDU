"""MON PROFIL — ce que l'oracle a compris de toi, rendu lisible.

Manque criant relevé à l'usage : MORDU accumulait des arêtes sans jamais montrer ce
qu'il en tirait. Un moteur qui apprend sans rien restituer est une boîte noire, et une
boîte noire n'inspire pas confiance — or la confiance est TOUT le produit ici.

C'est aussi l'application directe du §4 du manifeste (la triangulation) : la personne,
c'est ce qui est INVARIANT à travers ses arêtes. On calcule donc ce qui revient.

Volontairement honnête sur sa propre faiblesse : avec deux arêtes, on le DIT plutôt que
d'inventer un portrait. Pas de faux profilage.
"""
import re
from collections import Counter

import numpy as np

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
    t = re.sub(r"[^\wàâäéèêëîïôöùûüç' ]", " ", (texte or "").lower())
    return [m for m in t.split() if len(m) >= 4 and m not in _VIDES]


def empreinte(graines, aretes, largeur=24):
    """TON EMPREINTE — le vecteur profil (384D) rendu en glyphe.

    Ton goût EST déjà un objet mathématique unique : plutôt que de le résumer en barres,
    on le montre tel quel, replié en grille et quantifié sur la palette dither.
    Déterministe : même goût, même glyphe.

    Et il obéit au principe du produit : il est GROSSIER au début et se RÉSOUT à mesure
    que tu racontes. La résolution est portée par la TAILLE DES BLOCS, pas par le nombre
    de couleurs — première version testée, faire varier les seuls paliers de palette ne
    se voyait pas : le glyphe restait du bruit, en plus ou moins coloré. En agrégeant le
    vecteur par blocs (8x5 au départ, 24x16 à terme), on voit vraiment une image passer
    du flou au net, exactement comme les affiches.
    """
    p = profil(graines, aretes)
    if p is None:
        return None
    v = np.asarray(p, dtype=float)
    hauteur = int(np.ceil(len(v) / largeur))
    pad = np.zeros(hauteur * largeur)
    pad[: len(v)] = v
    g = pad.reshape(hauteur, largeur)

    # normalisation robuste : les extrêmes d'un embedding écraseraient tout le reste
    lo, hi = np.percentile(g, 3), np.percentile(g, 97)
    g = np.clip((g - lo) / max(hi - lo, 1e-9), 0, 1)

    n = len(aretes or [])
    finesse = min(1.0, n / 12.0)

    # RÉSOLUTION : on agrège par blocs. bloc 3 -> très grossier, bloc 1 -> plein détail.
    bloc = int(round(3 - 2 * finesse))          # 3, 2, puis 1
    bloc = max(1, bloc)
    if bloc > 1:
        hh, ww = hauteur // bloc, largeur // bloc
        reduit = g[: hh * bloc, : ww * bloc].reshape(hh, bloc, ww, bloc).mean(axis=(1, 3))
        # on ré-étale pour garder la même taille d'image, d'où les gros pixels
        g = np.repeat(np.repeat(reduit, bloc, axis=0), bloc, axis=1)
        g = np.pad(g, ((0, hauteur - g.shape[0]), (0, largeur - g.shape[1])), mode="edge")

    niveaux = int(4 + round(finesse * 7))       # de 4 à 11 paliers
    q = np.floor(g * (niveaux - 1) + 0.5).astype(int)

    return {"largeur": largeur, "hauteur": hauteur, "niveaux": niveaux,
            "bloc": bloc, "finesse": round(finesse, 3), "aretes": n,
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
    }
