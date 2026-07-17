"""J2 — data/movies.json -> data/embeddings.npy  (voir ROADMAP-cerveau.md).

Encode chaque synopsis avec all-MiniLM-L6-v2 (local, gratuit, tourne sur CPU).
Les vecteurs sont NORMALISÉS (norme 1) : à J3, la similarité cosinus se réduit à un
simple produit scalaire.

Tourne HORS LIGNE (une fois, ou quand le catalogue change).
Idempotent : ne recalcule pas si embeddings.npy est déjà aligné sur movies.json (sauf --force).

    python embed.py
    python embed.py --force

NB : au 1er lancement, le modèle (~90 Mo) se télécharge depuis HuggingFace (gratuit),
puis reste en cache (~/.cache/huggingface). Aucune API, aucun coût.
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
MOVIES = os.path.join(DATA_DIR, "movies.json")
EMB = os.path.join(DATA_DIR, "embeddings.npy")
MODEL_NAME = "all-MiniLM-L6-v2"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="recalcule même si embeddings.npy est à jour")
    args = ap.parse_args()

    if not os.path.exists(MOVIES):
        sys.exit(f"❌ {MOVIES} absent. Lance d'abord ingest.py (J1).")
    movies = json.load(open(MOVIES, encoding="utf-8"))

    # idempotence : si le .npy existe et a le bon nombre de lignes, on ne refait rien
    if os.path.exists(EMB) and not args.force:
        prev = np.load(EMB)
        if prev.shape[0] == len(movies):
            print(f"✓ {EMB} déjà à jour ({prev.shape}). Rien à faire (--force pour recalculer).")
            return

    # import ici (lourd) pour que --help reste instantané
    from sentence_transformers import SentenceTransformer

    print(f"→ chargement du modèle {MODEL_NAME} (local, CPU)...")
    model = SentenceTransformer(MODEL_NAME)

    # On enrichit le synopsis avec genres + KEYWORDS : les keywords TMDB (ex. "serial
    # killer, nonlinear timeline, twist ending, dystopia") sont bien plus discriminants
    # que les genres seuls -> gros gain de précision sur les voisins.
    def text_of(m):
        parts = []
        if m.get("genres"):
            parts.append(", ".join(m["genres"]))
        if m.get("keywords"):
            parts.append(", ".join(m["keywords"]))
        parts.append(m["overview"])
        return ". ".join(parts)

    texts = [text_of(m) for m in movies]

    print(f"→ encodage de {len(texts)} synopsis...")
    emb = model.encode(
        texts,
        batch_size=64,
        convert_to_numpy=True,
        normalize_embeddings=True,   # vecteurs unitaires -> cosinus = produit scalaire
        show_progress_bar=True,
    ).astype(np.float32)

    # sanity checks (le test de J2)
    assert emb.shape[0] == len(movies), "désalignement films/vecteurs"
    assert not np.isnan(emb).any(), "des NaN dans les embeddings"

    np.save(EMB, emb)
    print(f"\n✓ écrit {EMB}")
    print(f"  shape={emb.shape}  dim={emb.shape[1]}  dtype={emb.dtype}  NaN=non")
    print("  Test J2 OK si shape == (nb_films, 384). Ensuite J3 (recommend.py).")


if __name__ == "__main__":
    main()
