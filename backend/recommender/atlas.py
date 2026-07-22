"""TON ATLAS — l'objet qui remplace l'empreinte, et qui, lui, veut dire quelque chose.

POURQUOI L'EMPREINTE EST MORTE. Elle repliait ton vecteur de goût (384 dimensions) en
grille et le quantifiait. Elle était belle, déterministe, et Martin y tenait plus qu'à
tout le reste du produit. Mesuré le 22/07, elle ne montrait rien :

    rotation orthogonale de l'espace d'embedding
      écart max sur les 6000 similarités : 3,3e-16   -> le modèle est LE MÊME
      ordre complet des 6000 films       : identique
      cellules du glyphe qui changent    : 90,4 %

Et le repli « c'est une signature, pas un portrait » ne tenait pas non plus : en ajoutant
20 films PRIS DANS SON PROPRE GOÛT, le glyphe s'éloignait de lui-même de 0,663, contre
0,794 pour un inconnu — 83 % du chemin vers quelqu'un d'autre. Une signature doit être
stable pour la même personne. Celle-là identifiait l'état d'un vecteur un soir donné.

LE RENVERSEMENT. Au lieu de peindre TON vecteur dans une base arbitraire, on peint LE
CATALOGUE dans une base fixe et nommée, et on allume ce que tu as touché.

C'est tout, et ça change tout. Sous une rotation, les cosinus sont conservés, donc les
voisinages, donc le CONTENU de chaque cellule. Le dessin pourrait être redessiné ; ce que
chaque pixel désigne, non. On peut tapoter n'importe quelle tache et lire des titres :

    cellule de Casino          -> Casino, Le Parrain III, American Gangster…
    cellule de Se7en           -> Se7en, Le Crime de l'Orient-Express, Conversation secrète…
    cellule de Castle in the Sky -> Castle in the Sky, La Petite Sirène, Jumanji…

DEUX RÈGLES DURES, tenues par des tests :

  AUCUN PIXEL SANS CAUSE. Une cellule ne s'allume que si un film que tu as vraiment
  touché tombe dedans. Pas de halo, pas d'extrapolation sémantique, pas de pixel
  décoratif. (Le halo a été mesuré : à goût strictement fixe, il fait passer l'image de
  5 à 50 pixels selon son rayon. C'est la rampe de finesse déguisée en carte.)

  AUCUNE LÉGENDE STATISTIQUE. Pas de « ton plus gros amas est X », pas de « tu n'as
  jamais posé un pixel dans N territoires ». Mesuré sur 100 historiques ALÉATOIRES, ces
  deux phrases sortent 100 fois sur 100. Une image sans légende est le prix à payer, et
  il est correct.

Ce qui reste dicible : un titre, ta phrase, une date, le nom du territoire qui contient le
pixel. Des faits, tous vérifiables en tapotant.
"""
import os
from datetime import datetime, timezone

import numpy as np

from .carte import _LABELS, _N, _TERRITOIRES
from .oracle import profil
from .recommend import _E, _ID2IDX, _movies, _votes

# 48x32 = 1536 cellules. Mesuré : c'est la plus haute résolution où le continent se lit
# encore comme une masse (70,7 % de cellules non vides) et où un pixel contient encore une
# poignée de titres listables (médiane 4, p90 11). Au-delà, le socle part en confettis.
LARGEUR, HAUTEUR = 48, 32
NIVEAUX = 11
DEMI_VIE_JOURS = 30.0     # même constante que derive.py : ce qui « brûle » a moins d'un mois

_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "_atlas.npz")


def _cellules():
    """L'indice de cellule de chacun des 6000 films.

    On réutilise `carte._N` TEL QUEL. Piège mesuré : recadrer en min/max au lieu des
    percentiles 2-98 de carte.py fait changer de cellule à 97,1 % des films — toute
    mesure faite dans un autre cadrage serait à jeter.
    """
    x = np.clip((_N[:, 0] * LARGEUR).astype(int), 0, LARGEUR - 1)
    y = np.clip((_N[:, 1] * HAUTEUR).astype(int), 0, HAUTEUR - 1)
    return y * LARGEUR + x


_CELL = _cellules()


def _densite():
    """Où il y a des films, tout court. Le vide n'est pas une opinion."""
    n = np.bincount(_CELL, minlength=LARGEUR * HAUTEUR)
    return n > 0


_PLEINES = _densite()

# les cellules d'une même case, précalculées une fois : sinon on refait 1536 `np.where`
# à chaque requête
_PAR_CELL = [np.where(_CELL == c)[0] for c in range(LARGEUR * HAUTEUR)]


def _relief(p):
    """LE RELIEF — l'affinité de chaque endroit du cinéma avec TON goût.

    C'est ce qui manquait, et c'est ce qui rend la carte dense au lieu de vide. Avant,
    l'atlas n'affichait que les cellules touchées : 5 taches au début, 40 après un an —
    2,5 % de la grille. Une carte au trésor sans carte.

    Ici les 1086 cellules habitées portent toutes une valeur : `cos(ton profil, le centre
    de la cellule)`. Autrement dit, on ne montre plus seulement où tu es allé, on montre
    **à quoi ressemble le monde vu de ta position**. C'est exactement le calcul que fait
    l'oracle pour tirer ses cartes, rendu visible — donc rien de neuf n'est affirmé.

    Trois choses vérifiées avant de l'afficher :

      LISSE       corrélation entre cellules voisines 0,557, contre 0,006 après mélange
                  aléatoire. Le relief forme de vraies régions, pas du poivre et sel.
      SENSIBLE    ajouter 3 polars déplace 59,6 % des cellules d'un palier ; 3 comédies,
                  61,9 % — et pas les mêmes. Le relief RÉAGIT, et différemment selon quoi.
      HONNÊTE     ajouter des arêtes qui ne déplacent PAS le vecteur (colinéaires) change
                  0,0 % des cellules, à 3, 9, 18 et 36 arêtes. C'est le test exact qui
                  avait condamné la rampe de finesse de l'empreinte (82 % de la grille
                  changeait au seul mouvement du compteur). Ici : zéro.

    Et un cosinus est invariant par rotation — le relief passe donc aussi le test qui a
    tué le glyphe.
    """
    if p is None:
        return None
    sims = _E @ p
    aff = np.full(LARGEUR * HAUTEUR, np.nan)
    for c in range(LARGEUR * HAUTEUR):
        idx = _PAR_CELL[c]
        if len(idx):
            aff[c] = sims[idx].mean()
    ok = ~np.isnan(aff)
    if not ok.any():
        return None
    lo, hi = np.nanpercentile(aff, 3), np.nanpercentile(aff, 97)
    q = np.clip((aff - lo) / max(hi - lo, 1e-9), 0, 1)
    # paliers 1 à 6 : on laisse 0 au vide et 7 à 10 aux endroits où tu es allé
    out = np.zeros(LARGEUR * HAUTEUR, dtype=int)
    out[ok] = 1 + np.floor(q[ok] * 5 + 0.5).astype(int)
    return out


def _phares(cell, k=3):
    """Les films les plus connus d'une cellule — ce qu'on montre quand on la tapote."""
    idx = np.where(_CELL == cell)[0]
    if not len(idx):
        return []
    ordre = idx[np.argsort(-_votes[idx])][:k]
    return [_movies[i]["title"] for i in ordre]


def _territoire(cell):
    """Le territoire majoritaire d'une cellule, s'il y en a un.

    HDBSCAN laisse 33,8 % du catalogue en bruit : une cellule peut n'appartenir à aucun
    territoire, et on le dit plutôt que de la rattacher au voisin.
    """
    idx = np.where(_CELL == cell)[0]
    labs = [int(_LABELS[i]) for i in idx if _LABELS[i] >= 0]
    if not labs:
        return None
    lab = max(set(labs), key=labs.count)
    t = _TERRITOIRES.get(lab)
    return t["nom"] if t else None


def _quand(a):
    try:
        return datetime.fromisoformat((a or {}).get("date") or "")
    except (TypeError, ValueError):
        return None


def _extrait(texte, mots=7):
    """Quelques mots de TON texte brut. Jamais la version relue par un LLM : c'est ta
    voix qui légende la carte, pas celle d'un modèle."""
    t = " ".join((texte or "").split())
    if not t:
        return None
    bouts = t.split(" ")
    return " ".join(bouts[:mots]) + ("…" if len(bouts) > mots else "")


def atlas(graines, aretes):
    """Le continent, et ce que tu y as allumé. Chaque pixel a une cause nommée."""
    ars = sorted([a for a in (aretes or [])], key=lambda a: a.get("date") or "")
    maintenant = max((_quand(a) for a in ars if _quand(a)), default=None)
    origine = min((_quand(a) for a in ars if _quand(a)), default=None)

    # une cellule -> la cause la PLUS RÉCENTE qui l'a allumée
    causes = {}

    def poser(film_id, titre, quand, extrait):
        i = _ID2IDX.get(film_id)
        if i is None:
            return
        c = int(_CELL[i])
        vieux = causes.get(c)
        if vieux is None or (quand and vieux["_q"] and quand >= vieux["_q"]) or vieux["_q"] is None:
            causes[c] = {"film_id": film_id, "titre": titre, "extrait": extrait,
                         "_q": quand, "date": quand.isoformat() if quand else None}

    # les graines n'ont pas de date : on les date à l'ORIGINE de l'histoire, comme dans
    # derive._profil_recent. Elles sont le point de départ, pas un événement d'aujourd'hui.
    for gid in graines or []:
        i = _ID2IDX.get(gid)
        if i is not None:
            poser(gid, _movies[i]["title"], origine, None)
    for a in ars:
        poser(a.get("film_id"), a.get("titre"), _quand(a), _extrait(a.get("texte")))

    cellules = []
    for c, cause in sorted(causes.items()):
        age = None
        if maintenant and cause["_q"]:
            age = max(0.0, (maintenant - cause["_q"]).total_seconds() / 86400.0)
        # LE PALIER EST TEMPOREL, et seulement temporel. Ce n'est pas une intensité de
        # goût : c'est 0,5^(âge / 30 jours) quantifié. Une seule sémantique, vraie par
        # construction — les arêtes sont horodatées et append-only.
        chaleur = 1.0 if age is None else 0.5 ** (age / DEMI_VIE_JOURS)
        # PLANCHER À 7. Le relief occupe les paliers 1 à 6 ; une terre où tu es allé doit
        # rester au-dessus de lui POUR TOUJOURS. Sans ce plancher, un film raconté il y a
        # six mois se noyait dans le relief et redevenait indiscernable d'un endroit où
        # tu n'as jamais mis les pieds. Ce qui s'éteint, c'est la braise, pas le souvenir.
        palier = 7 + int(round(chaleur * (NIVEAUX - 1 - 7)))
        cellules.append({
            "c": c,
            "n": int((_CELL == c).sum()),
            "territoire": _territoire(c),
            "phares": _phares(c),
            "cause": {"film_id": cause["film_id"], "titre": cause["titre"],
                      "date": cause["date"], "extrait": cause["extrait"]},
            "age_jours": None if age is None else round(age, 2),
            "palier": palier,
            "braise": bool(age is not None and age < DEMI_VIE_JOURS),
        })

    relief = _relief(profil(graines, ars))
    if relief is None:
        relief = np.where(_PLEINES, 1, 0)

    return {
        "largeur": LARGEUR, "hauteur": HAUTEUR, "niveaux": NIVEAUX,
        # LE RELIEF remplace l'ancien socle de densité. Celui-ci était identique pour
        # tout le monde et n'affirmait rien ; il ne montrait donc rien non plus. Le
        # relief, lui, est ton point de vue sur le catalogue — et il bouge quand ton
        # goût bouge, et seulement quand il bouge (mesuré : 0,0 % sur le témoin).
        "socle": [int(x) for x in relief],
        "cellules": cellules,
        "cellules_pleines": int(_PLEINES.sum()),
        "films": len(_movies),
        # aucune part, aucun pourcentage, aucun comptage de territoires : mesuré, ces
        # phrases-là sortent 100 fois sur 100 sur des historiques tirés au hasard
    }
