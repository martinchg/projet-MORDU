"""LA DÉRIVE — mesurer un goût qui bouge, pas un goût figé.

Martin : « ce que j'aime dans l'empreinte, c'est que ÇA ÉVOLUE — si tu t'es adouci,
grandi. » Le portrait en phrase (axes.py) décrit un INSTANTANÉ : c'est pour ça qu'il
paraît banal. Tout le monde peut écrire « tu regardes l'image ». Personne ne peut écrire
TA trajectoire, parce qu'elle n'appartient qu'à toi.

Rien de neuf n'est stocké. Les arêtes sont horodatées et append-only (MANIFESTE §4), donc
l'histoire est DÉJÀ dans les données : on rejoue le profil sur chaque préfixe et on
regarde ce qui a changé entre deux états.

Quatre mesures, toutes dérivées de ce qui existe déjà :

  CAP        de combien ton vecteur a tourné depuis le départ (degrés sur la sphère)
  OUVERTURE  l'écart moyen entre ton centre et tes films — tu t'élargis ou tu te resserres
  AUDACE     dans quelle bande tu piochais (connu / écart / pari), et si ça monte
  ATTENTION  ce dont tu PARLES, première moitié contre seconde — tes mots, pas les miens

Le garde-fou compte autant que les mesures : deux points ne font pas une trajectoire, et
cinq ressentis écrits le même après-midi sont une salve, pas une évolution. Les deux cas
sont détectés et DITS. Rien n'est pire ici qu'un récit inventé : le produit tout entier
tient sur le fait que MORDU ne raconte pas de salades.
"""
import math
from collections import Counter

import numpy as np

from .axes import AXES, _de, _norm
from .oracle import profil
from .profil_vue import empreinte
from .recommend import _E, _ID2IDX

# Une bande = une prise de risque. C'est le seul endroit du produit où le risque est déjà
# quantifié : l'oracle range chaque carte, et l'arête garde la bande où tu as pioché.
_RISQUE = {"connu": 0.0, "ecart": 0.5, "pari": 1.0}

MIN_ARETES = 3          # en dessous : aucune trajectoire n'est défendable
MIN_POUR_SCINDER = 4    # pour comparer deux moitiés, il en faut deux de taille >= 2
SALVE_HEURES = 6        # tout écrit dans la même fenêtre = une séance, pas une évolution


def _angle(u, v):
    """Angle en degrés entre deux vecteurs unitaires. Plus lisible qu'un cosinus :
    « tu as tourné de 14° » se comprend, « ta similarité est de 0,97 » non."""
    if u is None or v is None:
        return None
    c = float(np.clip(np.dot(u, v), -1.0, 1.0))
    return math.degrees(math.acos(c))


def _vecteurs_du_set(graines, aretes):
    """Les vecteurs des films que tu as touchés — graines et arêtes confondues."""
    ids = list(graines or []) + [a.get("film_id") for a in (aretes or [])]
    idxs = [_ID2IDX[i] for i in ids if i in _ID2IDX]
    return _E[idxs] if idxs else None


def _ouverture(p, graines, aretes):
    """L'écart moyen entre ton centre et tes films. Grandit = tu t'élargis.

    C'est la mesure qui répond littéralement à « est-ce que je me suis ouvert ». Elle est
    robuste : ajouter un film proche du centre la fait baisser, un film lointain la fait
    monter, et elle ne dépend d'aucun seuil arbitraire.
    """
    V = _vecteurs_du_set(graines, aretes)
    if p is None or V is None or len(V) < 2:
        return None
    return float(np.mean([_angle(p, v) for v in V]))


def _horodatage(a):
    return (a or {}).get("date") or ""


def _heures(d1, d2):
    """Écart en heures entre deux dates ISO. Renvoie None si l'une manque."""
    from datetime import datetime
    try:
        a = datetime.fromisoformat(d1)
        b = datetime.fromisoformat(d2)
    except (TypeError, ValueError):
        return None
    return abs((b - a).total_seconds()) / 3600.0


def _attention(ars):
    """Ce dont tu parles, en parts par axe. Texte BRUT : ce sont TES mots qui portent le
    signal, pas ceux d'une relecture LLM (même raison qu'en §4 pour le vocabulaire)."""
    scores = {k: 0 for k in AXES}
    for a in ars:
        jetons = _norm(a.get("texte"))
        vus = set()
        for cle, ax in AXES.items():
            for j in jetons:
                if j in ax["mots"] and j not in vus:
                    scores[cle] += 1
                    vus.add(j)
    total = sum(scores.values())
    if not total:
        return None
    return {k: v / total for k, v in scores.items()}


def _derive_attention(ars):
    """Compare la première moitié de tes ressentis à la seconde.

    C'est la mesure la plus lisible des quatre, et la plus difficile à contester : elle ne
    dit pas ce que tu aimes, elle dit ce que tu t'es mis à REGARDER. « Tu parlais image,
    tu parles maintenant personnages » n'est vrai que de toi.
    """
    if len(ars) < MIN_POUR_SCINDER:
        return None
    coupe = len(ars) // 2
    av, ap = _attention(ars[:coupe]), _attention(ars[coupe:])
    if not av or not ap:
        return None
    deltas = sorted(((ap[k] - av[k], k) for k in AXES), reverse=True)
    gagne, perdu = deltas[0], deltas[-1]
    # un mouvement sous 15 points de part est du bruit d'échantillonnage, pas une dérive
    return {
        "gagne": {"cle": gagne[1], "libelle": AXES[gagne[1]]["libelle"],
                  "delta": round(gagne[0], 3)} if gagne[0] >= 0.15 else None,
        "perdu": {"cle": perdu[1], "libelle": AXES[perdu[1]]["libelle"],
                  "delta": round(perdu[0], 3)} if perdu[0] <= -0.15 else None,
        "avant": {k: round(v, 3) for k, v in av.items() if v > 0},
        "apres": {k: round(v, 3) for k, v in ap.items() if v > 0},
    }


def _audace(ars):
    """La bande où tu piochais, première moitié contre seconde."""
    reg = [a.get("registre") for a in ars if a.get("registre") in _RISQUE]
    if len(reg) < MIN_POUR_SCINDER:
        return None
    coupe = len(reg) // 2
    av = sum(_RISQUE[r] for r in reg[:coupe]) / max(coupe, 1)
    ap = sum(_RISQUE[r] for r in reg[coupe:]) / max(len(reg) - coupe, 1)
    return {"avant": round(av, 3), "apres": round(ap, 3), "delta": round(ap - av, 3),
            "bandes": dict(Counter(reg))}


def _territoires(ars):
    """Quel territoire de la carte chaque arête a touché, et QUAND tu y es entré."""
    try:
        from .carte import territoire_de
    except Exception:
        return []
    vus, ordre = {}, []
    for i, a in enumerate(ars):
        t = territoire_de(a.get("film_id"))
        if not t or t["id"] in vus:
            continue
        vus[t["id"]] = True
        ordre.append({"n": i + 1, "nom": t["nom"], "titre": a.get("titre"),
                      "date": a.get("date")})
    return ordre


def _verdict(cap, ouv_av, ouv_ap, aud, att, n, salve):
    """LA phrase. Elle doit être vraie avant d'être belle — donc beaucoup de refus."""
    bouts = []

    if ouv_av and ouv_ap:
        r = ouv_ap / ouv_av
        if r >= 1.08:
            bouts.append("tu t'es élargi")
        elif r <= 0.92:
            bouts.append("tu t'es resserré")
        else:
            bouts.append("tu as tenu ton cap")

    if aud and aud["delta"] >= 0.2:
        bouts.append("et tu oses davantage")
    elif aud and aud["delta"] <= -0.2:
        bouts.append("et tu reviens vers ce que tu connais")

    if not bouts:
        return None

    phrase = bouts[0][0].upper() + bouts[0][1:]
    if len(bouts) > 1:
        phrase += " " + " ".join(bouts[1:])
    phrase += "."

    if att and att.get("gagne"):
        g = att["gagne"]["libelle"]
        if att.get("perdu"):
            # _de() contracte : « le rythme » -> « du rythme ». Sans ça on écrit
            # « tu parlais le rythme ».
            phrase += (f" Tu parlais {_de(att['perdu']['libelle'])}, "
                       f"tu parles maintenant {_de(g)}.")
        else:
            phrase += f" {g[0].upper()}{g[1:]} a pris de la place dans tes mots."

    if salve:
        phrase += (" À nuancer : tout ça a été écrit dans la même séance — c'est une "
                   "salve, pas encore une trajectoire dans le temps.")
    elif n < 6:
        phrase += f" Sur {n} ressentis seulement — la tendance est fragile."

    return phrase


def derive(graines, aretes, avec_empreintes=True):
    """TON histoire réelle, mesurée. Pas une simulation."""
    ars = sorted(aretes or [], key=_horodatage)
    n = len(ars)

    # --- rejouer le profil sur chaque préfixe -------------------------------------
    etapes, precedent, chemin = [], None, 0.0
    p0 = None
    for k in range(n + 1):
        prefixe = ars[:k]
        p = profil(graines, prefixe)
        if p is None:
            continue
        if p0 is None:
            p0 = p
        pas = _angle(precedent, p) if precedent is not None else 0.0
        chemin += pas or 0.0
        e = {
            "n": k,
            "date": prefixe[-1].get("date") if prefixe else None,
            "titre": prefixe[-1].get("titre") if prefixe else None,
            "registre": prefixe[-1].get("registre") if prefixe else None,
            "pas": round(pas or 0.0, 2),
            "cap": round(_angle(p0, p) or 0.0, 2),
            "ouverture": round(_ouverture(p, graines, prefixe) or 0.0, 2),
        }
        if avec_empreintes:
            e["empreinte"] = empreinte(graines, prefixe)
        etapes.append(e)
        precedent = p

    # --- salve ou trajectoire ? ----------------------------------------------------
    salve = False
    if n >= 2:
        h = _heures(_horodatage(ars[0]), _horodatage(ars[-1]))
        salve = h is not None and h <= SALVE_HEURES

    ouv = [e["ouverture"] for e in etapes if e["ouverture"]]
    ouv_av, ouv_ap = (ouv[0], ouv[-1]) if len(ouv) >= 2 else (None, None)
    net = etapes[-1]["cap"] if etapes else 0.0
    aud = _audace(ars)
    att = _derive_attention(ars)

    assez = n >= MIN_ARETES
    return {
        "n": n,
        "assez": assez,
        "manque": max(0, MIN_ARETES - n),
        "salve": salve,
        "etapes": etapes,
        "chemin": round(chemin, 2),
        "net": round(net, 2),
        # >1,4 : tu as zigzagué pour finir près du départ — de l'exploration, pas une dérive
        "sinuosite": round(chemin / net, 2) if net > 1e-6 else None,
        "ouverture": {"avant": ouv_av, "apres": ouv_ap,
                      "delta": round(ouv_ap - ouv_av, 2) if ouv_av and ouv_ap else None},
        "audace": aud,
        "attention": att,
        "territoires": _territoires(ars),
        "verdict": _verdict(net, ouv_av, ouv_ap, aud, att, n, salve) if assez else None,
    }
