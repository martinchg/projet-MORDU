# MORDU — guide projet

App mobile de **recommandation de films par IA**. Reco par humeur + temps dispo, avec pour
chaque film « la meilleure accroche » (fait marquant). Projet solo, side project (cf. mission :
data/ML). Détail produit dans `README.md` ; moteur de reco dans `ROADMAP-cerveau.md`.

## Structure

```
backend/              FastAPI (Python). API + moteur de reco (voir ROADMAP-cerveau.md).
backend/recommender/  Moteur de reco : ingest.py -> embed.py -> recommend.py (data/ git-ignoré).
mobile/               App Expo / React Native (cible réelle).
design/dither/        Maquette de direction artistique « dither » (voir son README).
ROADMAP-cerveau.md    Plan du moteur de reco (content-based, embeddings + cosinus), jalons J0→J5.
```

## Direction artistique (figée)

Pâte « dither » : vraies images de films tramées (pixels réels, palette de nuit + un rouge),
typo sérigraphie 3D **variée par film**, mood-drift (froid↔chaud), grain au survol.
Déterministe, pas de ML. Réf : `design/dither/`.

## Conventions / à savoir

- **Ne pas éditer les fichiers générés/lourds** : `design/dither/posters.js` (images base64),
  tout `posters/`, `dist/`, `node_modules/`, `venv/`, `.npy`, `movies.json`. Ils sont
  git-ignorés et régénérables.
- **Secrets** : la clé TMDB va dans `backend/.env` (git-ignoré — ne jamais committer).
- Images de films : CDN public `image.tmdb.org` (sans clé pour les images ; clé requise pour
  la recherche/catalogue).
- Langue du projet : **français** (UI, commentaires, docs).
