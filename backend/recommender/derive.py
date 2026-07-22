"""LA DÉRIVE — mesurer un goût qui bouge, sans inventer de mouvement.

Martin : « ce que j'aime dans l'empreinte, c'est que ÇA ÉVOLUE — si tu t'es adouci,
grandi. » Le portrait en phrase décrit un INSTANTANÉ : c'est pour ça qu'il paraît banal.
Tout le monde peut lire « tu regardes l'image ». Personne d'autre ne peut lire SA
trajectoire.

CE FICHIER A ÉTÉ RÉÉCRIT APRÈS AUDIT (22/07), et ce qu'il a fallu jeter compte plus que
ce qui reste. Première version : quatre mesures (cap, ouverture, audace, attention) et un
verdict en français. Passée sur 40 historiques 100 % ALÉATOIRES — films au hasard, textes
au hasard, registres au hasard :

    verdict non nul                          40/40   à n = 4, 8, 12 et 20
    « tu t'es élargi »                       60/60   sur du bruit pur
    « tu parlais de X, tu parles de Y »      52/60
    « tu oses davantage »                    35/60

Elle ne se taisait que parce que Martin n'a que 2 arêtes ; elle se serait armée à la 3e.
Les causes sont structurelles, pas des réglages :

  - l'OUVERTURE (écart moyen centre <-> films) monte mécaniquement quand on ajoute un
    film, quel qu'il soit : +7° entre 5 et 40 films sans qu'aucun goût ne bouge ;
  - le CAP en degrés mesure la dilution d'un barycentre. Témoin mesuré : ajouter un film
    AU HASARD fait tourner le profil de 20,9° en médiane (p5-p95 : 18,0-23,6). Le premier
    vrai ressenti de Martin l'a fait tourner de 19,9° — le 30e percentile du pur bruit ;
  - l'ATTENTION moitié contre moitié : à 3-4 mots-clés par texte, 15 points de part valent
    UN mot ;
  - l'AUDACE est confondue : c'est l'oracle qui compose l'offre, et il ANNONCE le registre
    sur la carte — on renvoie une étiquette lue vingt secondes plus tôt ;
  - la SINUOSITÉ (chemin / vol d'oiseau) décroît en k^-0,5 pour tout le monde : la phrase
    de repli était celle que l'humanité entière aurait reçue.

Le profil cumulé est une moyenne : il converge par construction, et il est INVARIANT À
L'ORDRE. Il ne peut donc contenir aucune information temporelle. C'est la racine de tout.

Ce qui reste tient sur deux idées qui, elles, sont vraies :

  LA BRAISE   deux profils au lieu d'un — celui de TOUJOURS, et celui de MAINTENANT
              (décroissance exponentielle, demi-vie 30 jours). Le second ne converge
              jamais. Leur écart cellule par cellule est le seul mouvement réel.
  LE SILENCE  un axe dont tu n'avais JAMAIS parlé et dont tu viens de parler. C'est un
              ÉVÉNEMENT, pas une tendance : zéro statistique, donc zéro faux positif. Et
              ce sont TES mots — il n'y a rien à réfuter.

Tout le reste est de la donnée brute, montrée sans conclusion tirée dessus.
"""
import math
import re
import unicodedata
from datetime import datetime

import numpy as np

from .axes import AXES, _de, _touches
from .oracle import profil
from .recommend import _E, _ID2IDX, _unit

DEMI_VIE_JOURS = 30.0   # ~10-13 films à la cadence réelle d'un spectateur
SALVE_HEURES = 6        # tout écrit dans la même fenêtre = une séance, pas une évolution
ECHANTILLON_NUL = 400


def _quand(a):
    try:
        return datetime.fromisoformat((a or {}).get("date") or "")
    except (TypeError, ValueError):
        return None


def _angle(u, v):
    """Angle en degrés entre deux vecteurs unitaires."""
    if u is None or v is None:
        return None
    return math.degrees(math.acos(float(np.clip(np.dot(u, v), -1.0, 1.0))))


def _profil_recent(graines, aretes, maintenant):
    """Le profil pondéré par l'ANCIENNETÉ : ce que tu racontes en ce moment.

    Même films, mêmes valences, poids multiplié par 0,5^(âge / demi-vie). Les graines
    n'ont pas de date : on les date à la première arête, c'est-à-dire à l'origine de
    l'histoire. Conséquence assumée — avec deux arêtes écrites à 70 minutes d'écart, le
    profil récent est IDENTIQUE au profil de toujours et l'écart est nul. C'est le
    comportement voulu : il n'y a rien à montrer, donc on ne montre rien.
    """
    ars = [a for a in (aretes or []) if _quand(a)]
    if not ars or maintenant is None:
        return None
    origine = min(_quand(a) for a in ars)
    S = np.zeros(_E.shape[1])
    for i in graines or []:
        if i in _ID2IDX:
            age = (maintenant - origine).total_seconds() / 86400.0
            S += _E[_ID2IDX[i]] * 0.5 ** (age / DEMI_VIE_JOURS)
    for a in ars:
        i = a.get("film_id")
        v = float(a.get("valence", 1.0))
        # MÊME FILTRE QUE profil() : les rejets ne sont pas soustraits, ils forment un pôle
        # à part. Sans ce `v > 0`, la braise décrivait un état que le moteur n'a jamais eu
        # — mesuré à 12,05° d'écart dès UNE arête négative. Bug dormant tant que rien
        # n'est détesté, armé au premier « je n'ai pas aimé » (valence -0,19).
        if i in _ID2IDX and v > 0:
            age = (maintenant - _quand(a)).total_seconds() / 86400.0
            S += (1.5 * v * 0.5 ** (age / DEMI_VIE_JOURS)) * _E[_ID2IDX[i]]
    return _unit(S) if S.any() else None


# --- LE TÉMOIN ----------------------------------------------------------------------
# Un pas en degrés ne veut rien dire seul : ajouter n'importe quel film fait tourner un
# barycentre. On compare donc chaque pas à ce qu'auraient fait 400 autres films depuis le
# MÊME état. C'est le percentile qui porte l'information, jamais le degré.
def _base(graines, aretes):
    S = np.zeros(_E.shape[1])
    for i in graines or []:
        if i in _ID2IDX:
            S += _E[_ID2IDX[i]]
    for a in aretes or []:
        i = a.get("film_id")
        v = float(a.get("valence", 1.0))
        if i in _ID2IDX and v > 0:      # même filtre que profil(), cf. _profil_recent
            S += (1.5 * v) * _E[_ID2IDX[i]]
    return S


def _pas_percentile(S, poids, pas, graine):
    """Où tombe ce pas parmi ceux qu'auraient produits 400 films au hasard."""
    if not S.any() or pas is None:
        return None
    p_av = _unit(S)
    rng = np.random.default_rng(graine)
    pick = rng.choice(len(_E), size=min(ECHANTILLON_NUL, len(_E)), replace=False)
    P = S + poids * _E[pick]
    P /= np.maximum(np.linalg.norm(P, axis=1, keepdims=True), 1e-12)
    nul = np.degrees(np.arccos(np.clip(P @ p_av, -1.0, 1.0)))
    return round(float((nul < pas).mean()), 3)


def _forme_originale(texte, forme):
    """Le lexique est écrit sans accents ; on cite la personne, donc on lui rend SON mot.

    Sans ça l'écran affichait « tu as écrit "realise" » alors qu'elle avait écrit
    « réalisé ». Citer quelqu'un en abîmant son orthographe décrédibilise tout le reste.
    """
    def plier(s):
        s = unicodedata.normalize("NFD", s.lower())
        return "".join(c for c in s if unicodedata.category(c) != "Mn")

    # un mot à la fois : autoriser l'espace dans le motif le rendait glouton et il
    # avalait la phrase entière
    bruts = re.findall(r"[^\W\d_]+", texte or "", re.UNICODE)
    plies = [plier(b) for b in bruts]
    k = len(forme.split())
    for i in range(len(bruts) - k + 1):
        if " ".join(plies[i:i + k]) == forme:
            return " ".join(bruts[i:i + k])
    return forme


def _silences_rompus(ars):
    """LE SILENCE QUI SE ROMPT — le seul énoncé qui tient dès la première arête.

    MANIFESTE §5 : « le signal le plus fort n'est pas ce dont on parle le plus, c'est ce
    dont on ne parle JAMAIS ». Le moment où ce silence casse est donc l'événement le plus
    chargé du produit — et il n'était mesuré nulle part.

    C'est un ÉVÉNEMENT, pas une tendance : un axe passe de zéro à cité. Il n'y a pas
    d'hypothèse nulle à tester, donc pas de faux positif possible. Et il cite les mots de
    la personne : rien à réfuter.

    Le premier ressenti ne compte pas : tout y est forcément une première fois.
    """
    vus, evts = set(), []
    for i, a in enumerate(ars):
        touche = _touches(a.get("texte"))
        for cle, formes in touche.items():
            formes = [_forme_originale(a.get("texte"), f) for f in formes]
            if cle not in vus and i > 0:
                evts.append({"n": i + 1, "axe": cle, "libelle": AXES[cle]["libelle"],
                             # _de() contracte : « le son » -> « du son ». Sans ça la
                             # phrase donne « tu parlais de le son ».
                             "de": _de(AXES[cle]["libelle"]),
                             "mot": formes[0], "titre": a.get("titre"),
                             "date": a.get("date"), "avant": i})
            vus.add(cle)
    return evts


def derive(graines, aretes):
    """TON histoire réelle. Aucune phrase qui n'ait passé son test du hasard."""
    ars = sorted([a for a in (aretes or [])], key=lambda a: a.get("date") or "")
    n = len(ars)

    maintenant = max((_quand(a) for a in ars if _quand(a)), default=None)
    p_tjs = profil(graines, ars)
    if p_tjs is None:
        return {"n": n, "etapes": [], "braise": None, "silences": [], "salve": False}

    etapes = []
    precedent = None
    for k in range(n + 1):
        prefixe = ars[:k]
        p = profil(graines, prefixe)
        if p is None:
            continue
        pas = _angle(precedent, p) if precedent is not None else 0.0
        e = {
            "n": k,
            "date": prefixe[-1].get("date") if prefixe else None,
            "titre": prefixe[-1].get("titre") if prefixe else None,
            "pas": round(pas or 0.0, 2),
        }
        if k > 0:
            w = 1.5 * float(ars[k - 1].get("valence", 1.0))
            e["pas_pct"] = _pas_percentile(_base(graines, ars[:k - 1]), w, pas, graine=k)
        etapes.append(e)
        precedent = p

    # --- LA BRAISE ------------------------------------------------------------------
    # LA BRAISE N'EST PLUS PEINTE. Elle l'était sur le glyphe, dont la disposition
    # dépendait d'une base arbitraire (voir atlas.py) ; c'est l'atlas qui porte désormais
    # le « récent contre ancien », cellule par cellule et film par film. Ce qui reste ici
    # est le seul nombre qui survivait à une rotation : l'ANGLE entre ce que tu racontes
    # en ce moment et tout ce que tu as raconté.
    braise = None
    p_rec = _profil_recent(graines, ars, maintenant)
    if p_rec is not None:
        braise = {"ecart": round(_angle(p_tjs, p_rec) or 0.0, 2)}

    # --- salve ou trajectoire ? -------------------------------------------------------
    salve = False
    if n >= 2:
        d0, d1 = _quand(ars[0]), _quand(ars[-1])
        if d0 and d1:
            salve = abs((d1 - d0).total_seconds()) / 3600.0 <= SALVE_HEURES

    jours = 0.0
    if n >= 2:
        d0, d1 = _quand(ars[0]), _quand(ars[-1])
        if d0 and d1:
            jours = round(abs((d1 - d0).total_seconds()) / 86400.0, 1)

    return {
        "n": n,
        "jours": jours,
        "salve": salve,
        "etapes": etapes,
        "braise": braise,
        "silences": _silences_rompus(ars),
        # AUCUN verdict. Le seul énoncé que ces données autorisent aujourd'hui est un
        # constat de fait (la salve), et il est déjà là. Voir l'en-tête du module.
        "verdict": None,
    }
