# MORDU

Plateforme de recommandation de films par IA. MORDU suggère des films selon ton humeur, le temps que tu as, et ton profil cinématographique — avec pour chaque film l'accroche la plus marquante possible.

## Vision

- Recommandations contextuelles (humeur + temps disponible)
- "La meilleure phrase" sur chaque film : record, anecdote, classement, controverse
- Profil utilisateur construit via onboarding (5 films préférés + personnalité)
- Perles cachées personnalisées
- Mode groupe
- Application mobile (migration vers Expo en cours)

## Structure

```
backend/         FastAPI (Python) — API + moteur de reco (voir ROADMAP-cerveau.md)
mobile/          App Expo / React Native (cible réelle)
design/dither/   Maquette de direction artistique « dither »
```

## Stack

**App mobile (cible)** — Expo / React Native (`mobile/`)
**Backend** — FastAPI (Python) + Uvicorn (`backend/`)
**Moteur de reco** — content-based : embeddings de synopsis (`all-MiniLM-L6-v2`) + similarité cosinus

## Installation

### Backend

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload      # http://127.0.0.1:8000
```

Le moteur de reco a besoin d'une clé TMDB dans `backend/.env` (`TMDB_API_KEY=...`).

### App mobile (Expo)

```bash
cd mobile
npm install
npx expo start
```

## État du projet

Prototype. Direction artistique figée (`design/dither/`). Moteur de reco en construction
selon `ROADMAP-cerveau.md` (jalons J0 → J5).
