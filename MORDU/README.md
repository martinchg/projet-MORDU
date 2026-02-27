# MORDU Project

## Prérequis

- Python 3.8+
- Node.js

## Installation et Lancement

### 1. Backend (Python/FastAPI)

1. Ouvrir un terminal dans `backend/`.
2. Installer les dépendances :
   ```bash
   pip install -r requirements.txt
   ```
3. Lancer le serveur :
   ```bash
   uvicorn main:app --reload
   ```
   Le serveur sera accessible sur [http://127.0.0.1:8000](http://127.0.0.1:8000).

### 2. Frontend (React/Vite)

1. Ouvrir un nouveau terminal dans `frontend/`.
2. Installer les dépendances :
   ```bash
   npm install
   ```
3. Lancer l'application :
   ```bash
   npm run dev
   ```
   L'application sera accessible sur [http://localhost:5173](http://localhost:5173).

## Corrections Apportées

- **index.html** manquant a été créé correctement pour Vite.
- **Config Vite & Tailwind** ajoutée pour le style et le build.
- **BentoCard** corrigé pour être cliquable.
- **requirements.txt** ajouté pour le backend.
