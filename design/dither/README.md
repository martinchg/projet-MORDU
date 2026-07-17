# MORDU — maquette « dither »

Maquette de **direction artistique** (pas l'app finale). Montre la pâte visuelle retenue :
vraies images de films passées dans un **dithering** (pixels réels, palette de nuit + rouge),
typo sérigraphie 3D variée par film, **mood-drift** (la pâte glisse froid ↔ chaud selon l'humeur),
grain animé au survol, taille de pixels réglable.

## Fichiers

| Fichier | Rôle | Suivi git |
|---|---|---|
| `index.html` | Page (markup + liens css/js) | oui |
| `styles.css` | Tout le style | oui |
| `app.js` | Logique : dithering canvas, mood-drift, rendu | oui |
| `build_posters.py` | Récupère les images TMDB → `posters.js` | oui |
| `posters.js` | **Généré** : images en base64 | **non** (git-ignoré) |

## Lancer

```bash
python3 build_posters.py          # génère posters.js (images TMDB, CDN public, sans clé)
python3 -m http.server 8000       # puis ouvre http://localhost:8000/design/dither/
```

(Un serveur local est nécessaire pour que le navigateur charge `posters.js`.)

## Notes

- `posters.js` est git-ignoré : ce sont des images TMDB (copyright), chacun les régénère.
- Les polices s'appuient sur des fonts système macOS (Impact, Didot, American Typewriter,
  Futura, Baskerville…). Sur l'app réelle (Expo), il faudra embarquer les fonts.
- Zéro dépendance, zéro build : du HTML/CSS/JS + un script Python pour les images.
- Le dithering est **déterministe** (Bayer 4×4) — pas de ML. Voir le débat diffusion/ML
  tranché dans la mémoire projet.
