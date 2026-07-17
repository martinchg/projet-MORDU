"""Construit les DOMAINES (acteurs, réalisateurs, studios) et leur CANON, pour la mécanique
de dé-pixelisation par maîtrise (voir mémoire mordu-idee-depixel-maitrise).

Un « domaine » = une entité (personne OU studio) qui a un canon de films NOTABLES.
Le canon n'est PAS la filmo complète : on garde les films notables (notoriété = nb de votes,
et pour les acteurs le haut d'affiche = billing), pas l'obscur ni les petits rôles.

- Personnes : réals présents >= DIR_MIN fois dans le catalogue, acteurs >= ACT_MIN fois.
  On résout leur id TMDB (/search/person) puis leur filmo (/person/{id}/movie_credits).
- Studios : whitelist de studios reconnaissables ; canon via /discover?with_companies.

Sortie : data/domaines.json (git-ignoré). ~400-500 appels TMDB, une fois.
    python canon.py
"""
import collections
import json
import os
import time

from ingest import TMDB, load_key, IMG_BASE  # réutilise le client TMDB (retry, v3/v4)

HERE = os.path.dirname(os.path.abspath(__file__))
MOVIES = os.path.join(HERE, "data", "movies.json")
OUT = os.path.join(HERE, "data", "domaines.json")

CANON_MIN_VOTES = 400      # un film "compte" au-dessus de ce nb de votes
ACT_MAX_ORDER = 4          # un acteur "compte" s'il est dans le top-5 de l'affiche
DIR_MIN = 2                # réal gardé s'il a >= 2 films dans le catalogue
ACT_MIN = 3                # acteur gardé s'il a >= 3 films dans le catalogue
MAX_DIR = 90               # bornes (les plus présents d'abord)
MAX_ACT = 90

STUDIOS = [
    # animation (le cas le plus propre)
    "Pixar", "Studio Ghibli", "DreamWorks Animation", "Walt Disney Animation Studios",
    "Illumination", "Laika", "Sony Pictures Animation", "Aardman",
    # live-action signature
    "A24", "Blumhouse Productions", "Marvel Studios", "Legendary Pictures",
    "Plan B Entertainment", "New Line Cinema", "Working Title Films", "Lucasfilm",
]


def poster_url(path):
    return (IMG_BASE + path) if path else None


def canon_from_credits(credits, is_director):
    """Filtre la filmo -> canon (films notables). Renvoie une liste triée par votes."""
    out = {}
    if is_director:
        for c in credits.get("crew", []):
            if c.get("job") == "Director" and (c.get("vote_count") or 0) >= CANON_MIN_VOTES:
                out[c["id"]] = c
    else:
        for c in credits.get("cast", []):
            if c.get("order", 99) <= ACT_MAX_ORDER and (c.get("vote_count") or 0) >= CANON_MIN_VOTES:
                out[c["id"]] = c
    films = sorted(out.values(), key=lambda c: -(c.get("vote_count") or 0))
    return [{
        "id": c["id"],
        "title": c.get("title") or c.get("original_title"),
        "year": (c.get("release_date") or "")[:4] or None,
        "votes": c.get("vote_count"),
        "poster_url": poster_url(c.get("poster_path")),
    } for c in films]


def main():
    movies = json.load(open(MOVIES, encoding="utf-8"))
    catalogue_ids = {m["id"] for m in movies}

    dir_count = collections.Counter()
    act_count = collections.Counter()
    for m in movies:
        for d in (m.get("director") or []):
            dir_count[d] += 1
        for a in (m.get("cast") or []):
            act_count[a] += 1

    directors = [n for n, c in dir_count.most_common() if c >= DIR_MIN][:MAX_DIR]
    actors = [n for n, c in act_count.most_common() if c >= ACT_MIN][:MAX_ACT]
    print(f"→ {len(directors)} réalisateurs + {len(actors)} acteurs + {len(STUDIOS)} studios à traiter")

    tmdb = TMDB(load_key())
    domaines = []

    def add_person(name, is_director):
        res = tmdb.get("/search/person", query=name).get("results", [])
        if not res:
            return
        p = res[0]
        credits = tmdb.get(f"/person/{p['id']}/movie_credits")
        canon = canon_from_credits(credits, is_director)
        if len(canon) < 2:
            return
        domaines.append({
            "type": "director" if is_director else "actor",
            "id": p["id"],
            "name": p.get("name") or name,
            "image_path": p.get("profile_path"),
            "canon": canon,
            "canon_size": len(canon),
            "catalogue_ids": [f["id"] for f in canon if f["id"] in catalogue_ids],
        })
        time.sleep(0.03)

    for i, name in enumerate(directors, 1):
        add_person(name, True)
        if i % 25 == 0:
            print(f"  réalisateurs {i}/{len(directors)}")
    for i, name in enumerate(actors, 1):
        add_person(name, False)
        if i % 25 == 0:
            print(f"  acteurs {i}/{len(actors)}")

    print("→ studios...")
    for name in STUDIOS:
        res = tmdb.get("/search/company", query=name).get("results", [])
        if not res:
            print(f"  ⚠ studio introuvable : {name}")
            continue
        comp = res[0]
        data = tmdb.get("/discover/movie", with_companies=comp["id"], sort_by="vote_count.desc")
        films = [f for f in data.get("results", []) if (f.get("vote_count") or 0) >= CANON_MIN_VOTES]
        canon = [{
            "id": f["id"], "title": f.get("title"),
            "year": (f.get("release_date") or "")[:4] or None,
            "votes": f.get("vote_count"), "poster_url": poster_url(f.get("poster_path")),
        } for f in films]
        if not canon:
            continue
        domaines.append({
            "type": "studio",
            "id": comp["id"],
            "name": comp.get("name") or name,
            "image_path": comp.get("logo_path"),
            "canon": canon,
            "canon_size": len(canon),
            "catalogue_ids": [f["id"] for f in canon if f["id"] in catalogue_ids],
        })
        time.sleep(0.03)

    json.dump(domaines, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    by_type = collections.Counter(d["type"] for d in domaines)
    print(f"\n✓ écrit {OUT}")
    print(f"  {len(domaines)} domaines : {dict(by_type)}")
    print(f"  canon moyen : {sum(d['canon_size'] for d in domaines)//max(1,len(domaines))} films")


if __name__ == "__main__":
    main()
