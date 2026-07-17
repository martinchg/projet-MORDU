"""J4 — API MORDU (FastAPI).

Expose le moteur de reco :
  GET  /api/movies      -> catalogue (compact), avec ?search= et ?limit=
  POST /api/recommend   -> body {liked_ids: [...], k: 10} -> top-k films proches

Lancer (depuis backend/, venv activé) :
    uvicorn main:app --reload      # http://127.0.0.1:8000  (docs : /docs)
"""
import json
import os
import random
import urllib.request

import numpy as np
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from recommender.recommend import recommend, _movies, _E, _votes, _blocked

app = FastAPI(title="MORDU API")

# CORS ouvert pour le dev (le front — mobile Expo — parle à FastAPI:8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# champs compacts renvoyés pour le catalogue (le front n'a pas besoin de tout)
_CATALOG_FIELDS = ("id", "title", "year", "genres", "poster_url", "vote_average")

# ids des films exclus (langue/genre bloqués, ex. cinéma indien) — voir recommend.py
_BLOCKED_IDS = {_movies[i]["id"] for i in range(len(_movies)) if _blocked[i]}


def _compact(m):
    return {f: m.get(f) for f in _CATALOG_FIELDS}


@app.get("/")
def root():
    return {
        "service": "MORDU API",
        "docs": "/docs",
        "endpoints": ["/api/health", "/api/movies?search=…", "POST /api/recommend"],
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "films": len(_movies)}


@app.get("/api/movies")
def get_movies(limit: int = 60, search: str | None = None):
    """Catalogue. `search` filtre par titre ; sinon on renvoie les plus populaires."""
    items = [m for m in _movies if m["id"] not in _BLOCKED_IDS]
    if search:
        s = search.lower()
        items = [m for m in items if s in (m.get("title") or "").lower()]
    items = sorted(items, key=lambda m: m.get("popularity") or 0, reverse=True)[:limit]
    return [_compact(m) for m in items]


@app.get("/api/onboarding_pairs")
def onboarding_pairs(n: int = 7, min_votes: int = 2000):
    """Paires « tu préfères A ou B ? » pour l'onboarding.

    On choisit des films BIEN CONNUS (min_votes élevé, pour que l'user les reconnaisse),
    puis on prend un sous-ensemble DIVERS via farthest-point sampling dans l'espace
    d'embedding : deux films éloignés = un choix informatif (pas deux thrillers quasi
    identiques). Chaque choix sert de signal +/- au moteur.
    """
    cand = np.where((_votes >= min_votes) & ~_blocked)[0]
    if len(cand) < 2 * n:
        cand = np.argsort(-_votes)[: max(2 * n, 40)]
        cand = [int(c) for c in cand if not _blocked[c]]
    cand = [int(c) for c in cand]

    sel = [random.choice(cand)]
    while len(sel) < 2 * n and len(sel) < len(cand):
        selE = _E[sel]
        best, best_sim = None, 2.0
        for c in cand:
            if c in sel:
                continue
            nearest = float((_E[c] @ selE.T).max())  # proximité au plus proche déjà pris
            if nearest < best_sim:                    # on veut le plus ÉLOIGNÉ
                best_sim, best = nearest, c
        sel.append(best)

    random.shuffle(sel)
    pairs = []
    for i in range(0, len(sel) - 1, 2):
        pairs.append({"a": _compact(_movies[sel[i]]), "b": _compact(_movies[sel[i + 1]])})
    return pairs


@app.get("/api/img")
def proxy_img(path: str, w: int = 342):
    """Proxy d'affiche TMDB : re-sert l'image AVEC les en-têtes CORS (ajoutés par le
    CORSMiddleware), pour que le front puisse la charger en crossOrigin et la tramer
    au canvas (le CDN TMDB, lui, n'envoie pas de CORS → canvas 'tainted')."""
    if not path.startswith("/"):
        return Response(status_code=400, content=b"bad path")
    url = f"https://image.tmdb.org/t/p/w{w}{path}"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            data = r.read()
    except Exception:
        return Response(status_code=502, content=b"upstream error")
    return Response(content=data, media_type="image/jpeg",
                   headers={"Cache-Control": "public, max-age=86400"})


# --- Domaines (acteurs / réals / studios) pour la dé-pixelisation par maîtrise ---
_DOMAINES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "recommender", "data", "domaines.json")


def _load_domaines():
    if os.path.exists(_DOMAINES_PATH):
        return json.load(open(_DOMAINES_PATH, encoding="utf-8"))
    return []


_domaines = _load_domaines()
_DOM_BY_KEY = {(d["type"], d["id"]): d for d in _domaines}


@app.get("/api/domaines")
def get_domaines(min_catalogue: int = 2):
    """Liste compacte (sans le canon complet). `catalogue_ids` = films du canon présents
    dans MORDU → sert à calculer la maîtrise côté front (vus ∩ catalogue / |catalogue|)."""
    items = [d for d in _domaines if len(d["catalogue_ids"]) >= min_catalogue]
    items.sort(key=lambda d: -len(d["catalogue_ids"]))
    return [{"type": d["type"], "id": d["id"], "name": d["name"],
             "image_path": d["image_path"], "canon_size": d["canon_size"],
             "catalogue_ids": d["catalogue_ids"]} for d in items]


@app.get("/api/domaine/{dtype}/{did}")
def get_domaine(dtype: str, did: int):
    """Le canon complet d'un domaine (pour lister ses films et cocher 'vu')."""
    d = _DOM_BY_KEY.get((dtype, did))
    if not d:
        return Response(status_code=404, content=b"not found")
    return d


class RecoRequest(BaseModel):
    liked_ids: list[int]
    disliked_ids: list[int] = []
    k: int = 10


@app.post("/api/recommend")
def api_recommend(req: RecoRequest):
    """Reco qui apprend de tes choix : films proches de tes aimés, loin de tes rejetés."""
    return recommend(req.liked_ids, req.disliked_ids, req.k)
