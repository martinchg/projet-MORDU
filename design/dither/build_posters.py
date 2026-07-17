#!/usr/bin/env python3
"""Récupère des images de films (TMDB, CDN public) et génère `posters.js` (base64 inline).

Pourquoi base64 : la maquette doit tourner comme fichier autonome (canvas + getImageData
sans souci de CORS/CSP). `posters.js` est git-ignoré car ce sont des images TMDB (copyright)
— chaque personne régénère localement.

Usage :
    python3 build_posters.py

Aucune clé API requise : le CDN image.tmdb.org est public. Les hash viennent de mobile/App.js.
"""
import base64
import json
import os
import sys
import urllib.request

# id interne -> hash d'image TMDB (paysage, w342)
STILLS = {
    "fightclub": "hZkgoQYus5vegHoetLkCJzb17zJ",
    "shining":   "mmd1HnuvAzFc4iuVJcnBrhDNEKr",
    "parasite":  "hiKmpZMGZsrkA3cdce8a7Dpos1j",
    "angry":     "w4bTBXcqXc2TUyS5Fc4h67uWbPn",
    "eternal":   "W1ffLQGHoxfAOq0ZYdPtJlvAdb",
    "lost":      "6ITVHoipvxAS8luzKtHTbPaHLtT",
    "lebowski":  "hXsy4XCCHrUk81XoRhcooyWejao",
}
CDN = "https://image.tmdb.org/t/p/w342/{}.jpg"


def main():
    out = {}
    for key, h in STILLS.items():
        url = CDN.format(h)
        print(f"→ {key:10s} {url}", file=sys.stderr)
        with urllib.request.urlopen(url, timeout=20) as resp:
            out[key] = "data:image/jpeg;base64," + base64.b64encode(resp.read()).decode()
    dst = os.path.join(os.path.dirname(os.path.abspath(__file__)), "posters.js")
    with open(dst, "w", encoding="utf-8") as f:
        f.write("// GÉNÉRÉ par build_posters.py — ne pas éditer. Git-ignoré (images TMDB, copyright).\n")
        f.write("var POSTERS = " + json.dumps(out) + ";\n")
    print(f"✓ écrit {dst}  ({len(out)} images)", file=sys.stderr)


if __name__ == "__main__":
    main()
