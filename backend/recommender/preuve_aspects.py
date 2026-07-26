"""PREUVE — le modèle « aimé/détesté par aspect » sur les vrais films de Martin.

    cd backend && python3 -m recommender.preuve_aspects

Reproduit la mesure du 26/07 qui a fondé aspects.py : on compare, pour ses deux films
détestés (Anatomie, Tenet, mêmes reproches : alambiqué + mou), ce que voient trois
représentations. Seule la dernière rend justice à son modèle.

Les axes signés sont ici ÉTIQUETÉS À LA MAIN à partir de ses critiques — c'est ce que le
LLM de aspects.py automatisera. Le but de ce fichier est de montrer que la CIBLE est la
bonne, avant de dépenser une seule requête.
"""
import numpy as np

from .axes import AXES
from .recommend import _E, _ID2IDX

# Étiquetage manuel des 10 axes, signé, tiré des vraies critiques (verbatim dans le repo).
# +1 aimé cet aspect · -1 détesté · 0 pas évoqué.
_ORDRE = list(AXES.keys())  # atmosphère image rythme intrigue personnages morale émotion son structure "mise en scène"
_FILMS = {
    #                atm img ryt int per mor emo son str mes
    "L'Odyssée (+)": [0,  1, -1,  0,  1,  0,  0, -1,  1,  1],
    "Se7en (+)":     [1,  1,  0,  1,  1,  0,  0,  0,  0,  1],
    "12 hommes (+)": [0,  0,  0,  1,  1,  1,  0,  0,  1,  0],
    "Château (+)":   [0,  1,  0,  0,  1,  1,  1,  0,  0,  0],
    "Anatomie (-)":  [0,  0, -1,  0,  0,  0,  0,  0, -1,  0],
    "Tenet (-)":     [0,  0,  0,  0,  0,  0,  0,  0, -1,  0],
}
_TMDB = {"L'Odyssée (+)": 1368337, "Se7en (+)": 807, "12 hommes (+)": 389,
         "Château (+)": 10515, "Anatomie (-)": 915935, "Tenet (-)": 577922}


def _cos(u, v):
    if not np.any(u) or not np.any(v):
        return 0.0
    return float(u @ v / (np.linalg.norm(u) * np.linalg.norm(v)))


def main():
    V = {k: np.array(v, float) for k, v in _FILMS.items()}
    syn = {k: _E[_ID2IDX[i]] for k, i in _TMDB.items()}

    print("=== Anatomie(-) vs Tenet(-) : tes deux détestés, MÊME reproche (alambiqué+mou)")
    print(f"   synopsis (moteur actuel) : {_cos(syn['Anatomie (-)'], syn['Tenet (-)']):+.3f}")
    print(f"   axes nommés et signés    : {_cos(V['Anatomie (-)'], V['Tenet (-)']):+.3f}  <- ils se relient")
    print()
    ody = "L'Odyssée (+)"
    print("=== Tenet(-) vs L'Odyssée(+) : même sujet Nolan/temps, jugements OPPOSÉS")
    print(f"   synopsis                 : {_cos(syn['Tenet (-)'], syn[ody]):+.3f}")
    print(f"   axes signés              : {_cos(V['Tenet (-)'], V[ody]):+.3f}  <- opposés, comme toi")
    print()
    prof = np.mean(list(V.values()), axis=0)
    print("=== TON GOÛT PAR AXE (moyenne signée)")
    for ax, val in sorted(zip(_ORDRE, prof), key=lambda t: -t[1]):
        barre = ("+" * round(val * 10)) if val > 0 else ("-" * round(-val * 10))
        print(f"   {ax:<14} {val:+.2f}  {barre}")
    print()
    print("Étiquetage manuel. aspects.py automatise cette colonne (LLM) dès qu'une clé")
    print("ANTHROPIC_API_KEY est dans backend/.env — à vérifier contre ces étiquettes avant")
    print("de brancher quoi que ce soit dans le moteur.")


if __name__ == "__main__":
    main()
