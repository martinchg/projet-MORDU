"""J1 (enrichi) — Ingestion TMDB -> data/movies.json  (voir ROADMAP-cerveau.md).

Deux phases :
  1) on collecte des ids de films populaires (bulk, filtré par votes + sortis) + les favoris ;
  2) pour chaque id, UN appel détaillé (append_to_response) qui ramène tout : runtime,
     réalisateur, cast, keywords, tagline, trailer, certification, studio, streaming FR,
     imdb_id, en plus du synopsis/genres/poster.

C'est ~1000 appels détaillés (quelques minutes, gratuit, dans les limites), payés une fois.

    python ingest.py            # crée data/movies.json s'il n'existe pas
    python ingest.py --force    # force le re-téléchargement
    python ingest.py --target 1200

Clé TMDB lue dans ../.env (TMDB_API_KEY=...). v3 (api_key) ou v4 (Bearer) auto.
"""
import argparse
import datetime
import json
import os
import sys
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
OUT = os.path.join(DATA_DIR, "movies.json")
ENV = os.path.join(HERE, "..", ".env")

BASE = "https://api.themoviedb.org/3"
IMG_BASE = "https://image.tmdb.org/t/p/w342"
LANG = "en-US"          # synopsis EN : langue interne d'embedding, n'affecte pas l'UI
MIN_VOTES = 100         # filtre qualité (obscur/junk en dessous)
TODAY = datetime.date.today().isoformat()
APPEND = "credits,keywords,videos,release_dates,watch/providers"

# Tes favoris — recherchés explicitement pour garantir leur présence (gardés sans filtre).
FAVORITES = [
    ("Se7en", 1995), ("The Game", 1997), ("Fight Club", 1999), ("In Time", 2011),
    ("Ready Player One", 2018), ("Shutter Island", 2010), ("Inception", 2010),
    ("The Dark Knight Rises", 2012), ("Joker", 2019), ("The Prestige", 2006),
    ("Interstellar", 2014), ("Limitless", 2011), ("Prisoners", 2013),
    ("The Batman", 2022), ("Avatar", 2009), ("The Truman Show", 1998),
    ("Inglourious Basterds", 2009), ("I Am Legend", 2007),
    ("The Pursuit of Happyness", 2006), ("Django Unchained", 2012),
    ("La La Land", 2016), ("The Matrix", 1999), ("Requiem for a Dream", 2000),
    ("Get Out", 2017), ("Her", 2013), ("The Shining", 1980), ("Whiplash", 2014),
    ("Blade Runner", 1982), ("The Departed", 2006), ("Arrival", 2016),
    ("The Founder", 2016), ("Dark Waters", 2019), ("8 Mile", 2002),
    ("The Social Network", 2010), ("Moneyball", 2011), ("Catch Me If You Can", 2002),
    ("The Imitation Game", 2014), ("Erin Brockovich", 2000), ("Gran Torino", 2008),
    ("Million Dollar Baby", 2004), ("Gone Girl", 2014), ("The Martian", 2015),
    ("Blade Runner 2049", 2017), ("Zodiac", 2007),
    ("Once Upon a Time in Hollywood", 2019), ("12 Angry Men", 1957),
    ("Primal Fear", 1996), ("Goodfellas", 1990), ("Pulp Fiction", 1994),
    ("Taxi Driver", 1976), ("Scarface", 1983), ("The Godfather", 1972),
    ("Full Metal Jacket", 1987), ("Dead Poets Society", 1989),
    ("Oppenheimer", 2023), ("Drive", 2011), ("Parasite", 2019),
    ("Good Will Hunting", 1997), ("Snatch", 2000), ("Forrest Gump", 1994),
    ("Eternal Sunshine of the Spotless Mind", 2004), ("Lost in Translation", 2003),
    ("The Great Gatsby", 2013), ("The Big Lebowski", 1998), ("21 Jump Street", 2012),
    ("The Hangover", 2009), ("Men in Black", 1997), ("World War Z", 2013),
    ("Focus", 2015), ("Ocean's Eleven", 2001), ("Mr. & Mrs. Smith", 2005),
    ("Hitch", 2005), ("Crazy, Stupid, Love.", 2011), ("War Dogs", 2016),
    ("The Words", 2012),
]


class TMDB:
    """Client TMDB : détecte tout seul si la clé est v3 (api_key) ou v4 (Bearer)."""

    def __init__(self, key):
        self.key = key
        self.s = requests.Session()
        self.mode = self._detect()

    def _detect(self):
        r = self.s.get(f"{BASE}/configuration", params={"api_key": self.key}, timeout=20)
        if r.status_code == 200:
            return "v3"
        r = self.s.get(f"{BASE}/configuration",
                       headers={"Authorization": f"Bearer {self.key}"}, timeout=20)
        if r.status_code == 200:
            return "v4"
        sys.exit("❌ Clé TMDB invalide (ni v3 ni v4). Vérifie TMDB_API_KEY dans .env.")

    def get(self, path, **params):
        params.setdefault("language", LANG)
        for attempt in range(4):
            if self.mode == "v3":
                r = self.s.get(f"{BASE}{path}", params={**params, "api_key": self.key}, timeout=20)
            else:
                r = self.s.get(f"{BASE}{path}", params=params,
                               headers={"Authorization": f"Bearer {self.key}"}, timeout=20)
            if r.status_code == 429:
                time.sleep(1 + attempt)
                continue
            r.raise_for_status()
            return r.json()
        r.raise_for_status()


def load_key():
    if not os.path.exists(ENV):
        sys.exit(f"❌ .env introuvable : {ENV}")
    for line in open(ENV, encoding="utf-8"):
        if line.strip().startswith("TMDB_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("❌ TMDB_API_KEY= absent de .env")


def bulk_ok(m):
    """Filtre qualité sur les données bulk (avant de payer l'appel détaillé)."""
    if (m.get("vote_count") or 0) < MIN_VOTES:
        return False
    rd = m.get("release_date") or ""
    return bool(rd) and rd <= TODAY


def enrich(detail):
    """Construit notre fiche riche depuis un /movie/{id}?append_to_response=... ."""
    overview = (detail.get("overview") or "").strip()
    if not overview:
        return None

    crew = detail.get("credits", {}).get("crew", [])
    cast = detail.get("credits", {}).get("cast", [])
    directors = [c["name"] for c in crew if c.get("job") == "Director"]
    kws = [k["name"] for k in detail.get("keywords", {}).get("keywords", [])]

    trailer = next(
        (v["key"] for v in detail.get("videos", {}).get("results", [])
         if v.get("type") == "Trailer" and v.get("site") == "YouTube"),
        None,
    )

    cert = ""
    for rd in detail.get("release_dates", {}).get("results", []):
        if rd.get("iso_3166_1") == "US":
            cert = next((d["certification"] for d in rd.get("release_dates", [])
                         if d.get("certification")), "")
            break

    providers = (detail.get("watch/providers", {}).get("results", {})
                 .get("FR", {}).get("flatrate", []))

    poster = detail.get("poster_path")
    return {
        "id": detail["id"],
        "title": detail.get("title") or detail.get("original_title"),
        "year": (detail.get("release_date") or "")[:4] or None,
        "overview": overview,
        "tagline": (detail.get("tagline") or "").strip() or None,
        "genres": [g["name"] for g in detail.get("genres", [])],
        "keywords": kws[:25],
        "director": directors,
        "cast": [c["name"] for c in cast[:6]],
        "runtime": detail.get("runtime"),
        "certification": cert or None,
        "studios": [c["name"] for c in detail.get("production_companies", [])[:3]],
        "providers_fr": [p["provider_name"] for p in providers],
        "trailer_key": trailer,
        "imdb_id": detail.get("imdb_id"),
        "original_language": detail.get("original_language"),
        "poster_path": poster,
        "poster_url": (IMG_BASE + poster) if poster else None,
        "popularity": detail.get("popularity"),
        "vote_average": detail.get("vote_average"),
        "vote_count": detail.get("vote_count"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=1000)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(OUT) and not args.force:
        n = len(json.load(open(OUT, encoding="utf-8")))
        print(f"✓ {OUT} existe déjà ({n} films). --force pour re-télécharger.")
        return

    tmdb = TMDB(load_key())
    print(f"→ clé OK (mode {tmdb.mode})")

    # Phase 1 : collecter les ids candidats (bulk, filtrés) + favoris ---------------
    ids = []           # ordre = populaires d'abord
    seen = set()
    page = 1
    while len(ids) < args.target and page <= 500:
        data = tmdb.get("/movie/popular", page=page)
        for m in data.get("results", []):
            if m["id"] not in seen and bulk_ok(m):
                seen.add(m["id"]); ids.append(m["id"])
        if page % 10 == 0 or page == 1:
            print(f"  ids populaires — page {page:>3} — {len(ids)} candidats")
        if page >= data.get("total_pages", page):
            break
        page += 1
        time.sleep(0.05)
    ids = ids[:args.target]

    print(f"→ résolution des {len(FAVORITES)} favoris...")
    for title, year in FAVORITES:
        params = {"query": title}
        if year:
            params["primary_release_year"] = year
        res = tmdb.get("/search/movie", **params).get("results", [])
        if not res:
            print(f"  ⚠ favori introuvable : {title} ({year})")
            continue
        fid = res[0]["id"]
        if fid not in seen:
            seen.add(fid); ids.append(fid)
        time.sleep(0.02)

    # Phase 2 : appel détaillé par film ---------------------------------------------
    print(f"→ {len(ids)} films à détailler (1 appel chacun)...")
    movies = []
    for i, mid in enumerate(ids, 1):
        try:
            detail = tmdb.get(f"/movie/{mid}", append_to_response=APPEND)
            rec = enrich(detail)
            if rec:
                movies.append(rec)
        except Exception as e:
            print(f"  ⚠ échec sur id {mid}: {e}")
        if i % 100 == 0:
            print(f"  détaillés {i}/{len(ids)} — {len(movies)} retenus")
        time.sleep(0.03)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(movies, f, ensure_ascii=False, indent=2)

    with_kw = sum(1 for m in movies if m["keywords"])
    with_dir = sum(1 for m in movies if m["director"])
    with_rt = sum(1 for m in movies if m["runtime"])
    print(f"\n✓ écrit {OUT}")
    print(f"  {len(movies)} films  |  {with_kw} avec keywords  |  {with_dir} avec réalisateur  |  {with_rt} avec runtime")
    print("  Puis J2 : python embed.py --force  (ré-embed avec keywords).")


if __name__ == "__main__":
    main()
