"""LE JOURNAL — ce qui s'est passé, dans l'ordre, et qu'on n'écrivait nulle part.

MORDU confond quatre événements différents : choisir une direction, révéler un film, le
regarder vraiment, écrire ce qu'il en reste. Les arêtes ne gardent que le quatrième — donc
tout ce qui n'a pas abouti à un texte n'a jamais existé.

Trois pertes constatées dans le code, pas déduites :

  - `poser_choix()` écrase `en_attente`. Un second choix efface le premier : film,
    registre, pari, date ET les deux cartes écartées disparaissent. Or la docstring de
    cette même fonction dit que ces deux ids sont « IMPOSSIBLES À RECONSTRUIRE APRÈS
    COUP ». Le code s'auto-accusait.
  - `/api/renoncer` appelait `liberer()` et rien d'autre. Zéro ligne écrite. Le taux de
    « révélé mais jamais regardé » — le chiffre dont dépend toute la question de savoir
    s'il faut une machine d'état du visionnage — était NON MESURABLE PAR CONSTRUCTION.
  - `/api/ressenti` n'exigeait ni serrure armée, ni correspondance du film. Un double
    envoi écrivait deux arêtes, et le film pesait deux fois dans le profil. Dans un
    journal append-only, ça ne se dépollue pas.

Ce module ne change RIEN au profil : il n'ajoute aucun poids, aucune pondération, aucune
inférence. C'est un registre. Il rend simplement décidables des questions qui, aujourd'hui,
ne peuvent même pas être posées.

MANIFESTE §3 : ne pas choisir n'est PAS rejeter, et renoncer non plus. Rien de ce qui est
écrit ici n'entre dans `profil()` ni dans `repulsion()`.
"""
import json
import os
from datetime import datetime, timezone

from .aretes import DATA_DIR

JOURNAL_PATH = os.path.join(DATA_DIR, "journal.jsonl")

# Les seuls types admis. Une liste fermée : un journal où l'on peut écrire n'importe quoi
# n'est plus une source de vérité.
TYPES = ("choix", "renonce", "vu", "choix_refuse")


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ecrire(type_, **champs):
    """Ajoute une ligne. Append-only, jamais de réécriture, jamais de suppression."""
    if type_ not in TYPES:
        raise ValueError(f"type d'événement inconnu : {type_}")
    e = {"type": type_, "date": _now(), **champs}
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(JOURNAL_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")
    return e


def tous():
    if not os.path.exists(JOURNAL_PATH):
        return []
    out = []
    with open(JOURNAL_PATH, encoding="utf-8") as f:
        for ligne in f:
            ligne = ligne.strip()
            if not ligne:
                continue
            try:
                out.append(json.loads(ligne))
            except json.JSONDecodeError:
                continue          # une ligne corrompue ne doit pas tuer la lecture
    return out


def compteurs():
    """Ce que le journal permet enfin de savoir.

    `taux_non_vu` reste None sous 5 choix : avec deux ou trois soirées, un ratio n'est
    qu'une anecdote déguisée en pourcentage — et c'est exactement la faute que ce projet
    a passé la journée à retirer de ses écrans.
    """
    evts = tous()
    n = {t: sum(1 for e in evts if e.get("type") == t) for t in TYPES}
    total = n["choix"]
    return {
        "choix": total,
        "vus": n["vu"],
        "renoncements": n["renonce"],
        "choix_refuses": n["choix_refuse"],
        "taux_non_vu": round(n["renonce"] / total, 3) if total >= 5 else None,
        "assez_pour_un_taux": total >= 5,
    }
