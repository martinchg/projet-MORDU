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

## RÈGLE ABSOLUE POUR TOUT AGENT — n'écris JAMAIS dans les données de Martin

`backend/recommender/data/etat.json`, `aretes.jsonl` et `journal.jsonl` sont ses vraies
données de spectateur. Elles ne sont ni régénérables, ni reconstituables : deux ans de
ressentis écrits à la main n'existent nulle part ailleurs.

**Interdits, sans exception :**
- tout `POST`/`DELETE` vers l'API qui tourne (`:8000`) — y compris « juste pour tester »
- tout appel à `aretes.ajouter / poser_choix / liberer / deposer / poser_graines /
  ecrire_etat`, ou à `journal.ecrire`, sans isolation
- toute écriture directe dans `backend/recommender/data/`

**Le seul mode autorisé pour tester un état :**
```bash
MORDU_ETAT_DIR=$(mktemp -d) python3 -c "…"
```
et vérifie que l'isolation a bien pris : `assert aretes.DATA_DIR == os.environ["MORDU_ETAT_DIR"]`.

**Pourquoi cette règle existe.** Le 22/07, un sous-agent d'audit a déposé un film dans la
boîte aux lettres et libéré la serrure de Martin sur *Nightmare Alley*. Il a fallu
reconstituer l'état à la main depuis une trace de conversation. Les tests, eux, étaient
isolés depuis des semaines — la règle existait pour `tests_oracle.py` et pour personne
d'autre. C'est le seul incident de la journée qui ait touché des données irremplaçables.
