"""J3 — la logique de reco : profil -> top-k  (content-based, cosinus).

Charge films + embeddings UNE fois (à l'import). `recommend(liked_ids, k)` calcule le
vecteur profil (moyenne des films aimés), le compare à tout le catalogue par similarité
cosinus (produit scalaire, vecteurs normalisés), retire les films déjà aimés, renvoie le
top-k.

Pas besoin du modèle ici : le profil est la moyenne de vecteurs DÉJÀ calculés -> rapide,
léger, aucune dépendance lourde à la requête.

CLI (le "moment magique" du roadmap) :
    python recommend.py
"""
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")

_movies = json.load(open(os.path.join(DATA_DIR, "movies.json"), encoding="utf-8"))
_E = np.load(os.path.join(DATA_DIR, "embeddings.npy"))  # (n, 384), normalisés
_ID2IDX = {m["id"]: i for i, m in enumerate(_movies)}
_TITLE2ID = {m["title"].lower(): m["id"] for m in _movies}

_FIELDS = ("id", "title", "year", "genres", "poster_url", "overview", "runtime", "director",
           "imdb_rating", "imdb_rank")

# Plancher de votes pour les RECOS : on ne recommande pas les films trop obscurs
# (le catalogue les garde, ils restent cherchables — c'est juste l'output reco qui est propre).
# Réglable : monter pour un top plus "grand public", descendre pour laisser des perles.
RECO_MIN_VOTES = 1000
_votes = np.array([(m.get("vote_count") or 0) for m in _movies])

# Filtre de catalogue pour l'OUTPUT (reco + onboarding) : on écarte des films selon leur
# langue d'origine (le cinéma indien, "relou") et, si tu veux, certains genres. Le catalogue
# les garde (ils restent cherchables), c'est juste ce qu'on te PROPOSE qui est nettoyé.
BLOCK_LANGS = {"hi", "ta", "te", "ml", "kn", "bn", "mr", "pa", "gu", "or"}  # langues indiennes
# Ajoute-en si besoin : "ja" = anime, "tr", "th"... Ensemble vide = ne rien bloquer.
# (On NE bloque PAS "ja" : on garde l'anime / Miyazaki.)
BLOCK_GENRES = set()   # blocage dur par genre si besoin (vide = aucun)

# Filtre "trop enfant" : on vire les films FAMILY mal notés (ex. Le Voyage d'Arlo, 6.7),
# mais on garde les classiques d'animation acclamés (Toy Story 7.9, Miyazaki 8+).
KIDS_GENRE = "Family"
KIDS_MAX_RATING = 7.5   # un Family en dessous = trop gamin ; monte/descends pour ajuster


def _is_kids(m):
    return (KIDS_GENRE in (m.get("genres") or [])) and ((m.get("vote_average") or 0) < KIDS_MAX_RATING)


_blocked = np.array([
    (m.get("original_language") in BLOCK_LANGS)
    or bool(set(m.get("genres") or []) & BLOCK_GENRES)
    or _is_kids(m)
    for m in _movies
])


def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n else v


def recommend(liked_ids, disliked_ids=None, k=10, min_votes=RECO_MIN_VOTES, beta=0.35):
    """Reco qui APPREND de tes choix : elle utilise les films aimés ET rejetés.

    profil = dir(aimés) − beta·dir(rejetés), avec les deux centres NORMALISÉS pour que
    le rejet nudge (beta faible) au lieu d'écraser — sinon un rejet proche de tes goûts
    annule tout le signal. Sans rejets, on retombe sur le simple centre des aimés.
    Chaque "tu préfères A ou B" de l'onboarding remplit `disliked_ids` (le B non choisi).
    """
    idxs = [_ID2IDX[i] for i in liked_ids if i in _ID2IDX]
    if not idxs:
        return []
    neg = [_ID2IDX[i] for i in (disliked_ids or []) if i in _ID2IDX]

    profile = _unit(_E[idxs].mean(axis=0))
    if neg:
        profile = profile - beta * _unit(_E[neg].mean(axis=0))   # apprend de tes rejets (doucement)
    norm = np.linalg.norm(profile)
    if norm == 0:
        return []
    profile = profile / norm
    sims = _E @ profile
    sims[idxs] = -1.0                    # on ne recommande pas ce qui est déjà aimé
    if neg:
        sims[neg] = -1.0                 # ni ce que tu as rejeté
    sims[_votes < min_votes] = -1.0      # ni les films trop obscurs
    sims[_blocked] = -1.0                # ni les langues/genres exclus (cinéma indien, etc.)
    order = np.argsort(-sims)[:k]
    return [
        {**{f: _movies[j].get(f) for f in _FIELDS}, "score": round(float(sims[j]), 4)}
        for j in order
    ]


def ids_from_titles(titles):
    """Utilitaire (CLI/tests) : titres -> ids TMDB."""
    return [_TITLE2ID[t.lower()] for t in titles if t.lower() in _TITLE2ID]


if __name__ == "__main__":
    liked = ["Se7en", "Zodiac", "Prisoners", "Fight Club", "Shutter Island"]
    print(f"Films aimés : {', '.join(liked)}\n")
    print("Top-10 recommandés :")
    for r in recommend(ids_from_titles(liked), k=10):
        print(f"  {r['score']:.2f}  {r['title']} ({r['year']})  —  {', '.join(r['genres'] or [])}")
