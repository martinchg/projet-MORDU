"""Enrichit movies.json avec les notes ET le classement IMDb — datasets publics, gratuits, SANS clé.

Sources (https://datasets.imdbws.com/, usage personnel/non commercial) :
  - title.ratings.tsv.gz : tconst, averageRating, numVotes  (tous les titres notés)
  - title.basics.tsv.gz  : tconst, titleType, ...           (pour ne garder que les FILMS)

On joint par imdb_id, on ajoute la note + le nb de votes, et on calcule un CLASSEMENT
PONDÉRÉ (formule bayésienne du Top 250 IMDb) **restreint aux films** (sinon des épisodes
de séries ultra-notés faussent le rang). But : pouvoir dire « Top X IMDb » avec un vrai chiffre.

    python imdb.py            # télécharge ce qui manque, puis enrichit movies.json
    python imdb.py --force    # re-télécharge les datasets (mis à jour quotidiennement)

Datasets git-ignorés (data/). Réécrit movies.json en place (on n'ajoute que des champs :
imdb_rating, imdb_votes, imdb_rank — l'ordre ne change pas, alignement embeddings préservé).
"""
import argparse
import gzip
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
MOVIES = os.path.join(DATA_DIR, "movies.json")
RATINGS_GZ = os.path.join(DATA_DIR, "title.ratings.tsv.gz")
BASICS_GZ = os.path.join(DATA_DIR, "title.basics.tsv.gz")
RATINGS_URL = "https://datasets.imdbws.com/title.ratings.tsv.gz"
BASICS_URL = "https://datasets.imdbws.com/title.basics.tsv.gz"
MIN_VOTES = 25000                       # seuil du Top 250 IMDb
MOVIE_TYPES = {"movie", "tvMovie"}      # on exclut tvEpisode / short / tvSeries / ...


def fetch(url, dst, label):
    print(f"→ téléchargement {label} : {url}")
    urllib.request.urlretrieve(url, dst)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="re-télécharge les datasets IMDb")
    args = ap.parse_args()

    if not os.path.exists(MOVIES):
        sys.exit("❌ movies.json absent. Lance d'abord ingest.py.")

    if args.force or not os.path.exists(RATINGS_GZ):
        fetch(RATINGS_URL, RATINGS_GZ, "notes (~25 Mo)")
    if args.force or not os.path.exists(BASICS_GZ):
        fetch(BASICS_URL, BASICS_GZ, "types de titres (~214 Mo, une seule fois)")

    # 1) ensemble des tconst qui sont des FILMS
    print("→ lecture des types (pour ne garder que les films)...")
    movie_ids = set()
    with gzip.open(BASICS_GZ, "rt", encoding="utf-8") as f:
        next(f)  # en-tête
        for line in f:
            tconst, ttype, _ = line.split("\t", 2)
            if ttype in MOVIE_TYPES:
                movie_ids.add(tconst)
    print(f"  {len(movie_ids):,} films identifiés")

    # 2) notes
    ratings = {}
    with gzip.open(RATINGS_GZ, "rt", encoding="utf-8") as f:
        next(f)
        for line in f:
            tconst, avg, votes = line.rstrip("\n").split("\t")
            try:
                ratings[tconst] = (float(avg), int(votes))
            except ValueError:
                continue
    print(f"  {len(ratings):,} titres notés chargés")

    # 3) classement pondéré bayésien, restreint aux FILMS assez votés
    eligible = [(t, r, v) for t, (r, v) in ratings.items()
                if v >= MIN_VOTES and t in movie_ids]
    C = sum(r for _, r, _ in eligible) / len(eligible)  # moyenne globale des films éligibles

    def weighted(r, v):
        return (v / (v + MIN_VOTES)) * r + (MIN_VOTES / (v + MIN_VOTES)) * C

    ranked = sorted(((t, weighted(r, v)) for t, r, v in eligible), key=lambda x: -x[1])
    rank_of = {t: i + 1 for i, (t, _) in enumerate(ranked)}
    print(f"  {len(ranked):,} films classés (>= {MIN_VOTES:,} votes)  |  moyenne C={C:.2f}")

    # 4) join
    movies = json.load(open(MOVIES, encoding="utf-8"))
    n_rated = 0
    for m in movies:
        tid = m.get("imdb_id")
        if tid and tid in ratings:
            r, v = ratings[tid]
            m["imdb_rating"] = r
            m["imdb_votes"] = v
            m["imdb_rank"] = rank_of.get(tid)   # None si pas un film assez voté
            n_rated += 1
        else:
            m["imdb_rating"] = m["imdb_votes"] = m["imdb_rank"] = None

    json.dump(movies, open(MOVIES, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    n_ranked = sum(1 for m in movies if m.get("imdb_rank"))
    print(f"\n✓ {n_rated}/{len(movies)} films enrichis d'une note IMDb")
    print(f"  {n_ranked} classés parmi les films IMDb")
    print("  (movies.json réécrit — redémarre uvicorn pour recharger)")


if __name__ == "__main__":
    main()
