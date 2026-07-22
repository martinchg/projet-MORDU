"""J4 — API MORDU (FastAPI).

Expose le moteur de reco :
  GET  /api/movies      -> catalogue (compact), avec ?search= et ?limit=
  POST /api/recommend   -> body {liked_ids: [...], k: 10} -> top-k films proches

Lancer (depuis backend/, venv activé) :
    uvicorn main:app --reload      # http://127.0.0.1:8000  (docs : /docs)
"""
import difflib
import json
import os
import random
import re
import unicodedata
import urllib.request

import numpy as np
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from recommender.recommend import recommend, _movies, _E, _votes, _blocked, _ID2IDX
from recommender.oracle import tirage
from recommender import aretes
from recommender import relecture
from recommender.profil_vue import construire as construire_profil
from recommender.derive import derive as construire_derive
from recommender.carte import carte as construire_carte

app = FastAPI(title="MORDU API")

# CORS ouvert pour le dev (le front — mobile Expo — parle à FastAPI:8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# champs compacts renvoyés pour le catalogue (le front n'a pas besoin de tout)
_CATALOG_FIELDS = ("id", "title", "year", "genres", "poster_url", "poster_path",
                   "vote_average")

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


def _norm(s):
    """Titre comparable : sans accents, sans ponctuation, en minuscules."""
    s = unicodedata.normalize("NFD", (s or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", s)


@app.get("/api/movies")
def get_movies(limit: int = 60, search: str | None = None):
    """Catalogue. `search` filtre par titre ; sinon on renvoie les plus populaires.

    Le filtre par sous-chaîne seul rate les titres stylisés : chercher « seven » ne
    trouvait pas « Se7en ». On complète donc par un repli FLOU (difflib) — sinon un
    film que l'utilisateur a en tête reste introuvable, ce qui est rédhibitoire pour
    l'onboarding.
    """
    items = [m for m in _movies if m["id"] not in _BLOCKED_IDS]
    if search:
        s = _norm(search)
        exacts = [m for m in items if s in _norm(m.get("title"))]
        if len(exacts) < limit:
            vus = {m["id"] for m in exacts}
            scores = []
            for m in items:
                if m["id"] in vus:
                    continue
                r = difflib.SequenceMatcher(None, s, _norm(m.get("title"))).ratio()
                if r >= 0.72:
                    scores.append((r, m))
            scores.sort(key=lambda x: -x[0])
            exacts += [m for _, m in scores[: limit - len(exacts)]]
        items = exacts
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


# =====================================================================================
# L'ORACLE — cf. MANIFESTE.md. Trois cartes, trois axes, une serrure.
# =====================================================================================

class ChoixRequest(BaseModel):
    film_id: int
    titre: str | None = None
    registre: str | None = None
    pari: str | None = None


class RessentiRequest(BaseModel):
    film_id: int
    texte: str
    titre: str | None = None
    registre: str | None = None
    pari: str | None = None
    pari_juste: bool | None = None
    corrige: str | None = None


class GraineRequest(BaseModel):
    film_id: int
    titre: str | None = None
    texte: str = ""            # « pourquoi celui-là ? » — obligatoire côté API


class GrainesRequest(BaseModel):
    ids: list[int] = []                    # ancienne forme, conservée
    films: list[GraineRequest] = []        # nouvelle : film + description


@app.get("/api/oracle")
def api_oracle(seed: int | None = None):
    """Les trois cartes du soir.

    SERRURE : si un film a été choisi mais pas encore raconté, on ne tire pas. Le
    ressenti est le ticket du tirage suivant (MANIFESTE §3). On ne punit que le silence.
    """
    attente = aretes.en_attente()
    if attente:
        return {"bloque": True, "en_attente": attente,
                "message": "Raconte-moi le précédent, et je te ressers."}

    ars = aretes.toutes()
    seeds = aretes.graines()
    if not seeds and not ars:
        return {"bloque": False, "cartes": [], "besoin_onboarding": True,
                "message": "Donne-moi trois films que tu as adorés."}

    ids_boite = [b["film_id"] for b in aretes.boite()]
    cartes = tirage(seed_ids=seeds, aretes=ars,
                    exclure=list(aretes.films_racontes()), seed=seed,
                    boite=ids_boite)
    # on signale la provenance : « c'est Théo qui te l'avait soufflé » est un moment
    # de plaisir gratuit, et ça justifie la carte sans la transformer en dette
    src = {b["film_id"]: b.get("source") for b in aretes.boite()}
    for c in cartes:
        if c["id"] in src:
            c["de_la_boite"] = src[c["id"]] or True
    return {"bloque": False, "cartes": cartes, "arêtes": len(ars)}


@app.post("/api/choix")
def api_choix(req: ChoixRequest):
    """« Ce soir, c'est celui-là. » Arme la serrure — les non-choisis ne sont PAS
    des rejets (MANIFESTE §3 : jamais en disliked_ids)."""
    aretes.poser_choix(req.film_id, req.titre, req.registre, req.pari)
    return {"ok": True, "en_attente": aretes.en_attente()}


@app.post("/api/ressenti")
def api_ressenti(req: RessentiRequest):
    """La serrure : une arête (toi, film, texte, date). Libère le tirage suivant."""
    texte = (req.texte or "").strip()
    if len(texte) < 3:
        return Response(status_code=400, content=b"ressenti vide")
    extra = {"pari": req.pari, "pari_juste": req.pari_juste}
    if req.corrige and req.corrige.strip() and req.corrige.strip() != texte:
        extra["corrige"] = req.corrige.strip()   # vue, à côté du brut — jamais à la place
    a = aretes.ajouter(req.film_id, texte, req.titre, req.registre, extra=extra)
    aretes.liberer()
    return {"ok": True, "arete": a, "total": len(aretes.toutes()),
            "palmares": aretes.palmares()}


@app.post("/api/relire")
def api_relire(req: RessentiRequest):
    """Relecture d'un ressenti : orthographe et phrases cassées, RIEN d'autre.

    Le texte brut n'est jamais remplacé — la correction est une vue stockée à côté
    (MANIFESTE §4). Le vocabulaire du profil continue de lire le brut, sinon on
    afficherait le vocabulaire du modèle à la place de celui de l'utilisateur.
    """
    if not relecture.disponible():
        return {"ok": False, "raison": "pas de clé ANTHROPIC_API_KEY configurée"}
    r = relecture.relire(req.texte)
    if not r:
        return {"ok": False, "raison": "aucune correction proposée"}
    return {"ok": True, **r}


@app.get("/api/relecture_dispo")
def api_relecture_dispo():
    return {"disponible": relecture.disponible(), "modele": relecture.MODELE}


@app.get("/api/profil")
def api_profil():
    """Ce que l'oracle a compris de toi. Tout est recalculé à la volée depuis les
    arêtes brutes — rien n'est stocké (MANIFESTE §4 : les profils sont des vues)."""
    return construire_profil(aretes.graines(), aretes.toutes(), aretes.palmares())


@app.get("/api/evolution")
def api_evolution():
    """TA dérive : l'empreinte rejouée à chaque état historique réel, plus les quatre
    mesures de ce qui a changé (cap, ouverture, audace, attention). Pas de simulation,
    et un refus explicite de conclure sous 3 arêtes ou sur une seule séance."""
    return construire_derive(aretes.graines(), aretes.toutes())


@app.get("/api/carte")
def api_carte():
    """La carte du goût : PaCMAP 2D du catalogue + territoires nommés + ta position."""
    return construire_carte(aretes.graines(), aretes.toutes())


@app.post("/api/renoncer")
def api_renoncer():
    """« Finalement je ne l'ai pas regardé. »

    La serrure bloquait TOUT tant que le film choisi n'était pas raconté : ouvrir
    l'app après avoir choisi un film de 2h25 sans l'avoir vu menait à un cul-de-sac.
    Or le manifeste dit qu'on ne punit que le SILENCE, pas l'attente. Renoncer est un
    état honnête : on libère la serrure sans écrire d'arête (rien à raconter), et le
    film redevient tirable plus tard.
    """
    a = aretes.en_attente()
    aretes.liberer()
    return {"ok": True, "libere": a}


@app.get("/api/aretes")
def api_aretes():
    """Toutes tes arêtes — la matière première, brute, jamais agrégée à l'écriture."""
    return aretes.toutes()


MIN_GRAINES = 5
MIN_TEXTE_GRAINE = 15


@app.post("/api/graines")
def api_graines(req: GrainesRequest):
    """Onboarding : des ARÊTES, pas des identifiants nus (MANIFESTE §9).

    Le manifeste demandait « N films adorés ET une ligne sur pourquoi » ; seule la
    première moitié était implémentée. Des graines sans texte ne portent ni le
    vocabulaire ni les axes d'attention de la personne — le profil reposait alors
    presque entièrement sur le premier ressenti écrit, qui le tirait tout entier vers
    lui. On exige donc une description par film, et on écrit de vraies arêtes.
    """
    if req.films:
        if len(req.films) < MIN_GRAINES:
            return Response(status_code=400,
                            content=f"il faut {MIN_GRAINES} films".encode())
        courts = [f.titre or f.film_id for f in req.films
                  if len((f.texte or "").strip()) < MIN_TEXTE_GRAINE]
        if courts:
            return Response(status_code=400,
                            content=f"description trop courte : {courts}".encode())
        for f in req.films:
            aretes.ajouter(f.film_id, f.texte.strip(), f.titre,
                           registre="onboarding", extra={"source": "onboarding"})
        aretes.poser_graines([f.film_id for f in req.films])
        return {"ok": True, "graines": aretes.graines(),
                "aretes": len(aretes.toutes())}

    aretes.poser_graines(req.ids)          # ancienne forme (compatibilité)
    return {"ok": True, "graines": aretes.graines()}


@app.get("/api/etat")
def api_etat():
    ars = aretes.toutes()
    return {"graines": aretes.graines(), "aretes": len(ars),
            "en_attente": aretes.en_attente(),
            "boite": len(aretes.boite()),
            "palmares": aretes.palmares()}


@app.get("/api/graines_muettes")
def api_graines_muettes():
    """Films de départ qui n'ont PAS de description.

    Ceux-là ne portent ni vocabulaire ni axe d'attention : ils ne pèsent que par leur
    vecteur. Les compléter enrichit le profil sans rien effacer — on ajoute une arête,
    on ne réécrit aucune donnée existante.
    """
    racontes = aretes.films_racontes()
    out = []
    for i in aretes.graines():
        if i in racontes or i not in _ID2IDX:
            continue
        m = _movies[_ID2IDX[i]]
        out.append({"film_id": i, "titre": m.get("title"), "year": m.get("year"),
                    "poster_path": m.get("poster_path"), "genres": m.get("genres")})
    return out


@app.get("/api/vus")
def api_vus():
    """Les films que tu as réellement vus : graines + arêtes.

    C'est ce qui relie enfin les deux features : jusqu'ici les domaines se
    nourrissaient d'un localStorage séparé, donc raconter un film ne révélait
    aucun portrait. Une seule source de vérité — tes arêtes.
    """
    return sorted(set(aretes.graines()) | aretes.films_racontes())


# --- La boîte aux lettres (MANIFESTE §6) : PAS une watchlist ------------------------
class BoiteRequest(BaseModel):
    film_id: int
    titre: str | None = None
    source: str | None = None       # « un pote », « bande-annonce »…


@app.get("/api/boite")
def api_boite():
    """On peut la VOIR, on n'y choisit jamais : c'est l'oracle qui décide quand
    l'heure d'un film est venue (sinon on recrée la watchlist-dette)."""
    vus = set(aretes.graines()) | aretes.films_racontes()
    items = [b for b in aretes.boite() if b["film_id"] not in vus]
    for b in items:
        m = _movies[_ID2IDX[b["film_id"]]] if b["film_id"] in _ID2IDX else None
        if m:
            b["poster_path"] = m.get("poster_path")
            b["genres"] = m.get("genres")
            b["year"] = m.get("year")
    return items


@app.post("/api/boite")
def api_boite_ajouter(req: BoiteRequest):
    return {"ok": True, "item": aretes.deposer(req.film_id, req.titre, req.source),
            "total": len(aretes.boite())}


@app.delete("/api/boite/{film_id}")
def api_boite_retirer(film_id: int):
    aretes.retirer_boite(film_id)
    return {"ok": True, "total": len(aretes.boite())}
