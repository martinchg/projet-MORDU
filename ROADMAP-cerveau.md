# MORDU — Le cerveau (moteur de reco) · Roadmap

> But de ce doc : te démarrer le moteur ML sans écrire le code. Les décisions techniques sont
> **déjà tranchées** (pas d'options à débattre — c'est ce qui tue les projets perso). Tu suis,
> tu implémentes. Règle d'or : **chaque étape doit produire un truc qui TOURNE et se teste avant
> de passer à la suivante.**

## 0. Ce que « fini » veut dire (le seul objectif)
Un endpoint `/api/recommend` qui reçoit une liste de films aimés et renvoie les N films les plus
proches, calculés — pas écrits en dur. Branché au front qui existe déjà. Point.
Tout le reste de la vision (humeur, temps, mode groupe, mobile, « meilleure phrase ») = **plus tard,
on n'y touche pas.**

## 1. Le principe en 30 secondes
**Reco par contenu (content-based), pas collaborative.** Tu n'as pas de données d'usage → le
collaborative filtering est hors-jeu. Content-based = « ce film ressemble à ceux que tu aimes ».

Mécanique :
1. Chaque film → un **vecteur** (embedding) qui capture son « sens » (à partir du synopsis).
2. Ton profil = la **moyenne** des vecteurs de tes films aimés.
3. Reco = les films dont le vecteur est le **plus proche** du tien (similarité cosinus), en
   excluant ceux déjà vus.

C'est tout. Simple, robuste, et ça gère le *cold start* (un nouvel utilisateur suffit de 5 films).

## 2. Stack — décidée, pas à débattre
| Brique | Choix | Pourquoi (court) |
|---|---|---|
| Données | **API TMDB** (gratuite) | Vrais films, synopsis, genres, affiches. L'affiche servira en phase 2 (CLIP). |
| Embeddings texte | **sentence-transformers `all-MiniLM-L6-v2`** | Léger, tourne sur ton CPU, largement suffisant. Ne perds pas 3h à comparer les modèles. |
| Similarité | **cosinus, avec numpy** | Pour < 50k films, pas besoin de FAISS. Over-engineering interdit au début. |
| Stockage | **fichiers locaux** (JSON + un `.npy` pour les vecteurs) | Pas de base de données au début. Tu en mettras une si un jour ça grossit. |
| API | **FastAPI** (ton `main.py` existant, étendu) | Déjà en place. |

Inscription TMDB : themoviedb.org → compte gratuit → API key → dans `backend/.env`.

## 3. Structure des fichiers (dans `backend/`)
```
backend/
├── main.py               # FastAPI — étendre avec l'endpoint /api/recommend
├── .env                  # TMDB_API_KEY=...
├── requirements.txt      # + requests, sentence-transformers, numpy
└── recommender/
    ├── ingest.py         # TMDB -> data/movies.json  (télécharge, met en cache)
    ├── embed.py          # data/movies.json -> data/embeddings.npy
    ├── recommend.py      # la logique : profil -> top-k
    └── data/             # movies.json + embeddings.npy (cache local, git-ignoré)
```
Rôle de chaque fichier, en une ligne :
- **ingest.py** : appelle TMDB, récupère ~1000-2000 films populaires (id, titre, synopsis, genres,
  poster_url), écrit `data/movies.json`. Idempotent : si le fichier existe, on ne re-télécharge pas.
- **embed.py** : charge `movies.json`, encode chaque synopsis en vecteur, sauve la matrice dans
  `data/embeddings.npy` (aligné sur l'ordre des films). À relancer seulement si les films changent.
- **recommend.py** : charge films + embeddings une fois ; fonction `recommend(liked_ids, k)` →
  calcule le vecteur profil (moyenne des aimés), cosinus contre toute la matrice, retire les
  `liked_ids`, renvoie les k meilleurs.
- **main.py** : `POST /api/recommend` avec un body `{ "liked_ids": [...], "k": 10 }` → appelle
  `recommend(...)` → renvoie la liste des films.

## 4. Le pipeline (flux de données)
```
TMDB  --ingest.py-->  movies.json  --embed.py-->  embeddings.npy
                                                        |
liked_ids (front)  ------------------------------>  recommend.py  --> top-k --> front
```
Note : `ingest` et `embed` tournent **hors ligne** (une fois, ou quand tu rafraîchis le catalogue).
`recommend` tourne **à chaque requête**, mais ne recalcule jamais les embeddings — il les lit.

## 5. Roadmap par jalons (chacun testable seul)
- **J0 — Setup** : venv, `pip install` des 3 libs, clé TMDB dans `.env`. Test : un `print` qui
  confirme que la clé marche (un appel TMDB qui renvoie 1 film).
- **J1 — Ingestion** : `ingest.py` écrit `movies.json` avec ~1000 films. Test : ouvrir le JSON,
  vérifier titres + synopsis présents.
- **J2 — Embeddings** : `embed.py` produit `embeddings.npy`. Test : shape = (nb_films, 384), et
  pas de NaN.
- **J3 — Reco en CLI** : `recommend.py` avec un `if __name__ == "__main__"` où tu hardcodes 5
  films que t'aimes → il imprime le top-10. **C'est le moment magique** : tu vois si les recos ont
  du sens. Itère ici tant que ce n'est pas convaincant.
- **J4 — API** : endpoint `/api/recommend` dans `main.py`. Test : appel curl/Postman renvoie le
  top-k en JSON.
- **J5 — Branche le front** : le front existant appelle `/api/recommend` au lieu des 2 films en
  dur. **Fini = ici.** Tu as un moteur de reco end-to-end qui tourne.

Ne saute pas J3. C'est là que tu valides que le cerveau est intelligent avant de l'habiller.

## 6. Les pièges qui TUENT le projet (à fuir)
- Vouloir une vraie base de données, un cache Redis, du Docker, avant que J5 marche. **Non.**
- Passer une soirée à choisir « le meilleur » modèle d'embedding. MiniLM, point, tu changeras après.
- Repartir sur la migration mobile Expo avant que le moteur existe. Le mobile ne prouve rien.
- Ajouter les filtres humeur/temps/genre avant J5. Features accessoires = piège.
- Ne pas finir un jalon (« ça marche à moitié ») avant de passer au suivant.

## 7. Ce que tu apprends au passage (ton moteur : « apprendre des technos »)
- **Embeddings** : transformer du sens en vecteurs — la brique de tout le ML moderne.
- **Similarité cosinus** : mesurer la proximité sémantique.
- **Content-based vs collaborative filtering** : et pourquoi content-based ici (cold start).
- **Séparer offline (embed) et online (serve)** : une vraie règle d'archi ML de prod.

## 8. Phase 2 — PLUS TARD (ne pas y toucher avant que J5 tourne)
- **CLIP sur les affiches** : embeddings visuels → reco par « ce que le film *dégage* » visuellement.
  C'est ton pont vers le génératif/diffusion (même famille que ton DDPM). Fusion texte+image.
- Filtres contextuels (genre, durée, humeur) par-dessus la reco.
- Vraie base de données + plus de films.
- L'app mobile, quand le cerveau est solide.

---
**Rappel de cadre :** MORDU est un *side project*. Il ne passe pas avant ta cible stage (data/ML
quant) ni ta prépa entretien. Mais fini, c'est une ligne de CV qui te vend — y compris pour le
quant (ML end-to-end, livré seul). En coquille, il ne dit rien. **Donc : va jusqu'à J5.**
