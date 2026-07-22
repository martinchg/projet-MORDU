"""LA CARTE DU GOÛT — projeter 384 dimensions sur un plan, y nommer les territoires,
et t'y situer.

Le moteur manipule des vecteurs de 384 dimensions ; personne ne se représente ça. On
projette donc le catalogue en 2D. Ce n'est pas une décoration : c'est la seule façon de
MONTRER ce que le moteur fait, donc de pouvoir lui faire confiance.

Trois décisions, chacune mesurée :

1. PaCMAP plutôt qu'une ACP. L'ACP ne conservait que 7,9 % des 10 plus proches voisins
   (11,9 % de variance sur deux axes) : la carte mentait. PaCMAP monte à 10,9 % — 6,8x
   mieux — parce qu'il optimise ensemble des paires voisines, mi-proches et lointaines,
   là où t-SNE/UMAP ne gardent que le local et TriMap que le global.

2. HDBSCAN plutôt que k-moyennes : la densité décide du nombre de territoires, et les
   films inclassables restent du « bruit » au lieu d'être forcés dans une case. Un
   territoire doit exister, pas être décrété.

3. Territoires NOMMÉS automatiquement par leurs motifs sur-représentés. Un nuage de
   points est illisible ; une carte de territoires nommés se lit d'un coup d'œil.

La projection ne dépend pas de l'utilisateur : calculée une fois, mise en cache sur
disque. Seule la mise en avant change d'une personne à l'autre.
"""
import os
from collections import Counter

import numpy as np

from .oracle import _IDF, _MOTIFS_BLOQUES, _MOTIFS_FR, _GENRE_FR, profil
from .recommend import _E, _ID2IDX, _blocked, _movies, _votes

_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "_carte.npz")
N_VOISINS_CARTE = 40


def _projeter():
    """PaCMAP 2D du catalogue + clusters de densité, mis en cache."""
    if os.path.exists(_CACHE):
        try:
            d = np.load(_CACHE)
            if d["P"].shape[0] == len(_movies):
                return d["P"], d["labels"]
        except Exception:
            pass
    import pacmap
    from sklearn.cluster import HDBSCAN
    P = pacmap.PaCMAP(n_components=2, n_neighbors=12, MN_ratio=0.5,
                      FP_ratio=2.0, random_state=42).fit_transform(_E)
    labels = HDBSCAN(min_cluster_size=18, min_samples=5).fit(P).labels_
    np.savez(_CACHE, P=P, labels=labels)
    return P, labels


_P, _LABELS = _projeter()
# Normalisation par PERCENTILES et non par min/max : PaCMAP produit quelques points très
# excentrés qui, sinon, écrasent les 1000 autres dans un quart de la carte. On cadre sur
# 2-98 % et on rogne le reste — mieux vaut quelques films au bord qu'une carte illisible.
_LO, _HI = np.percentile(_P, 2, axis=0), np.percentile(_P, 98, axis=0)
_N = np.clip((_P - _LO) / np.maximum(_HI - _LO, 1e-9), 0.0, 1.0)


def _nommer_territoires():
    """Chaque cluster est nommé par ce qui l'y DISTINGUE, pas par ce qui y domine.

    « drame » est majoritaire dans la moitié des clusters et ne dit rien ; « huis clos »
    n'apparaît que dans un seul et le nomme. On compare donc la part d'un motif dans le
    cluster à sa part globale (un lift), pondérée par sa rareté.
    """
    global_kw = Counter()
    for m in _movies:
        for k in set(m.get("keywords") or []):
            global_kw[k] += 1
    total = max(len(_movies), 1)

    territoires = {}
    for lab in sorted(set(int(x) for x in _LABELS)):
        if lab < 0:
            continue
        idx = np.where(_LABELS == lab)[0]
        n = len(idx)
        kw, gen = Counter(), Counter()
        for i in idx:
            m = _movies[i]
            for k in set(m.get("keywords") or []):
                if k not in _MOTIFS_BLOQUES and k in _MOTIFS_FR:
                    kw[k] += 1
            for g in m.get("genres") or []:
                gen[g] += 1

        scores = []
        for k, c in kw.items():
            if c < max(3, n * 0.12):
                continue
            lift = (c / n) / max(global_kw.get(k, 1) / total, 1e-6)
            scores.append((lift * _IDF.get(k, 1.0), k))
        scores.sort(reverse=True)
        mots = [_MOTIFS_FR[k] for _, k in scores[:3]]
        genre = gen.most_common(1)[0][0] if gen else None

        territoires[lab] = {
            "id": lab,
            "nom": " · ".join(mots) if mots else (_GENRE_FR.get(genre, genre or "—")),
            "genre": _GENRE_FR.get(genre, genre) if genre else None,
            "n": int(n),
            "x": round(float(_N[idx, 0].mean()), 4),
            "y": round(float(_N[idx, 1].mean()), 4),
        }
    return territoires


_TERRITOIRES = _nommer_territoires()


def territoire_de(film_id):
    """Le territoire nommé où tombe un film, ou None s'il est dans le bruit.

    HDBSCAN laisse volontairement des points non classés (label -1) : ce sont les films
    isolés, et les forcer dans un cluster voisin inventerait une appartenance.
    """
    i = _ID2IDX.get(film_id)
    if i is None:
        return None
    return _TERRITOIRES.get(int(_LABELS[i]))


def carte(graines=None, aretes=None):
    """Le territoire complet + ta position dedans."""
    tiens = set(graines or []) | {a["film_id"] for a in (aretes or [])}

    centre, voisins, mien_par_terr = None, set(), Counter()
    p = profil(graines, aretes)
    sims = None
    if p is not None:
        sims = _E @ p
        # barycentre pondéré par l'affinité au cube : le point le plus représentatif de
        # ton goût, et non la moyenne molle du catalogue
        w = np.clip(sims, 0, None) ** 3
        if w.sum() > 0:
            c = (_N * w[:, None]).sum(axis=0) / w.sum()
            centre = [round(float(c[0]), 4), round(float(c[1]), 4)]
        pris = 0
        for i in np.argsort(-sims):
            if _movies[i]["id"] in tiens or _blocked[i] or _votes[i] < 1000:
                continue
            voisins.add(_movies[i]["id"])
            pris += 1
            if pris >= N_VOISINS_CARTE:
                break

    pts = []
    for i, m in enumerate(_movies):
        mid, lab = m["id"], int(_LABELS[i])
        k = 2 if mid in tiens else (1 if mid in voisins else 0)
        if k == 2 and lab >= 0:
            mien_par_terr[lab] += 1
        pts.append({"id": mid, "t": m["title"], "x": round(float(_N[i, 0]), 4),
                    "y": round(float(_N[i, 1]), 4), "k": k, "z": lab})

    terrs = []
    for t in _TERRITOIRES.values():
        t = dict(t)
        t["tiens"] = int(mien_par_terr.get(t["id"], 0))
        if sims is not None:
            idx = np.where(_LABELS == t["id"])[0]
            t["affinite"] = round(float(sims[idx].mean()), 3)
        terrs.append(t)
    terrs.sort(key=lambda x: -x.get("affinite", 0))

    return {"points": pts, "centre": centre, "territoires": terrs,
            "films": len(pts), "clusters": len(terrs)}
