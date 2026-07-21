"""Tests de l'oracle — les invariants du MANIFESTE, pas du détail d'implémentation.

Chaque test verrouille une décision produit gravée dans MANIFESTE.md. Si un test casse,
c'est soit une régression, soit une décision qu'on a changée — auquel cas on rouvre le
manifeste AVANT de toucher au test.

    python tests_oracle.py        (aucune dépendance, pas besoin de pytest)
"""
import sys

from recommender import aretes
from recommender.oracle import BANDES, _est_suite, profil, tirage
from recommender.recommend import _movies, ids_from_titles

GRAINES = ["Se7en", "Zodiac", "Prisoners", "Fight Club", "Shutter Island"]
_ok, _ko = 0, 0


def check(nom, cond, detail=""):
    global _ok, _ko
    if cond:
        _ok += 1
        print(f"  ok   {nom}")
    else:
        _ko += 1
        print(f"  ÉCHEC {nom}  {detail}")


def test_trois_axes_orthogonaux():
    """MANIFESTE §1 : trois cartes, jamais trois thrillers."""
    seeds = ids_from_titles(GRAINES)
    for s in (1, 7, 42, 99, 404, 2026):
        cs = tirage(seed_ids=seeds, seed=s)
        check(f"3 cartes (seed {s})", len(cs) == 3, f"-> {len(cs)}")
        if len(cs) != 3:
            continue
        regs = [c["registre"] for c in cs]
        check(f"3 registres distincts (seed {s})", len(set(regs)) == 3, str(regs))
        ids = [c["id"] for c in cs]
        check(f"pas de doublon (seed {s})", len(set(ids)) == 3, str(ids))
        # décroissance d'affinité : connu > écart > pari
        affs = [c["affinite"] for c in cs]
        check(f"affinités décroissantes (seed {s})",
              affs[0] >= affs[1] >= affs[2], str(affs))


def test_argument_toujours_ancre():
    """MANIFESTE §3 : invitation, pas dette — jamais de carte sans lien réel."""
    seeds = ids_from_titles(GRAINES)
    generiques = ("Droit dans ton axe.", "Voisin de ce que tu aimes, par un autre chemin.",
                  "Rien à voir avec tes habitudes — c'est le pari.")
    total, nus = 0, []
    for s in range(1, 26):
        for c in tirage(seed_ids=seeds, seed=s):
            total += 1
            if c["argument"] in generiques:
                nus.append(c["title"])
    check("aucun argument générique", not nus, f"{len(nus)}/{total} nus : {nus[:3]}")


def test_argument_en_francais():
    """Le projet est en français : pas de mot-clé TMDB brut dans la phrase."""
    seeds = ids_from_titles(GRAINES)
    fuites = []
    anglais = ("serial killer", "psychological", "world war", "concentration camp",
               "neo-noir film", "crime scene", "based on", "whodunit et investigation")
    for s in range(1, 26):
        for c in tirage(seed_ids=seeds, seed=s):
            for a in anglais:
                if a in c["argument"].lower():
                    fuites.append((c["title"], a))
    check("pas d'anglais brut dans l'argument", not fuites, str(fuites[:3]))


def test_suites_ecartees():
    """Proposer « Scream VI » sans les précédents est une faute produit — MAIS la règle
    est CONDITIONNELLE : si tu as vu la base, la suite redevient recommandable."""
    cas = [("Scream VI", True), ("Kill Bill: Vol. 2", True), ("The Godfather Part II", True),
           ("Glass Onion: A Knives Out Mystery", True),   # base APRÈS les deux-points
           ("Blade Runner 2049", True),                   # c'est bien une suite
           ("Se7en", False), ("12 Angry Men", False),
           ("X-Men", False), ("1917", False), ("Ocean's Eleven", False)]
    for titre, attendu in cas:
        check(f"écartée sans la base ? {titre} = {attendu}",
              _est_suite({"title": titre}) == attendu)

    # ...et redeviennent valides quand la base a été vue
    vus = {"blade runner", "knives out"}
    for titre in ("Blade Runner 2049", "Glass Onion: A Knives Out Mystery"):
        check(f"base vue -> {titre} redevient proposable",
              _est_suite({"title": titre}, vus) is False)
    check("base non vue -> Scream VI reste écarté",
          _est_suite({"title": "Scream VI"}, vus) is True)

    seeds = ids_from_titles(GRAINES)
    vus_t = {(m["title"] or "").lower() for m in _movies if m["id"] in seeds}
    trouvees = [c["title"] for s in range(1, 21)
                for c in tirage(seed_ids=seeds, seed=s) if _est_suite(c, vus_t)]
    check("aucune suite orpheline tirée", not trouvees, str(trouvees[:3]))


def test_jamais_les_graines_ni_les_racontes():
    """On ne propose pas ce que tu as déjà vu ou déjà raconté."""
    seeds = ids_from_titles(GRAINES)
    exclus = [_movies[10]["id"], _movies[20]["id"]]
    for s in (3, 33, 333):
        ids = [c["id"] for c in tirage(seed_ids=seeds, exclure=exclus, seed=s)]
        check(f"graines exclues (seed {s})", not (set(ids) & set(seeds)))
        check(f"exclusions respectées (seed {s})", not (set(ids) & set(exclus)))


def test_valence():
    """La valence pilote le profil : un signe faux éloigne d'un film aimé."""
    cas = [
        ("Le retournement m'a cueilli, l'ambiguïté m'a happé. Rythme un peu mou.", 0.0, 1.0),
        ("Magnifique, sublime, bouleversé par la fin.", 0.6, 1.0),
        ("Ennuyeux, prétentieux, creux.", -1.0, -0.4),
        ("J'ai abandonné au bout de 40 minutes.", -1.0, -0.3),
        ("Sympa sans plus.", 0.2, 0.5),
        # pièges de sous-chaîne : beaucoup/mouvement/effort ne sont PAS des jugements
        ("Beaucoup de mouvement, un effort de mise en scène.", 0.2, 0.5),
    ]
    for texte, lo, hi in cas:
        v = aretes.valence(texte)
        check(f"valence {v:+.2f} ∈ [{lo};{hi}] — « {texte[:34]}… »", lo <= v <= hi)


def test_profil_pondere_par_valence():
    """Un film détesté ne doit pas tirer le profil vers lui."""
    seeds = ids_from_titles(["Se7en", "Zodiac"])
    aime = profil(seeds, [{"film_id": seeds[0], "valence": 1.0}])
    deteste = profil(seeds, [{"film_id": seeds[0], "valence": -1.0}])
    check("valence change le profil", float((aime * deteste).sum()) < 0.999)


def test_canon_invitation_jamais_dette():
    """MANIFESTE §3 : un essentiel ne se cite que si la personne est DÉJÀ dans tes
    arêtes. « Un essentiel de Fincher » invite ; « il FAUT Citizen Kane » endette."""
    from recommender.oracle import _essentiel_de
    refs = [m for m in _movies if m["title"] in ("Se7en", "Zodiac")]
    check("références trouvées", len(refs) == 2)
    gone = [m for m in _movies if m["title"] == "Gone Girl"]
    if gone:
        e = _essentiel_de(gone[0], refs)
        check("Gone Girl = essentiel de Fincher (via Se7en)",
              e is not None and e[0] == "David Fincher", str(e))
    toy = [m for m in _movies if m["title"] == "Toy Story"]
    if toy:
        check("Toy Story n'est PAS une invitation pour un profil Fincher",
              _essentiel_de(toy[0], refs) is None)
    # sans références, aucune invitation possible (pas de canon absolu)
    if gone:
        check("aucun canon sans arête préalable", _essentiel_de(gone[0], []) is None)


def test_boite_aux_lettres():
    """MANIFESTE §6 : la boîte est une SOURCE que l'oracle pondère, pas une file où
    l'on pioche. Elle doit pouvoir remonter un film TRÈS éloigné du goût — c'est
    souvent la raison même du conseil — sans jamais s'imposer."""
    seeds = ids_from_titles(["Se7en", "Zodiac", "Prisoners"])
    cible = ids_from_titles(["The Big Lebowski"])
    if not cible:
        return
    cible = cible[0]
    sorties = sum(1 for s in range(1, 41)
                  if cible in [c["id"] for c in tirage(seed_ids=seeds, seed=s, boite=[cible])])
    sans = sum(1 for s in range(1, 41)
               if cible in [c["id"] for c in tirage(seed_ids=seeds, seed=s)])
    check(f"la boîte fait remonter le film ({sorties}/40 contre {sans}/40 sans)",
          sorties > sans)
    check("elle ne l'impose jamais (pas 40/40)", sorties < 40, str(sorties))
    # et elle ne casse pas la structure
    for s in (2, 8):
        cs = tirage(seed_ids=seeds, seed=s, boite=[cible])
        check(f"toujours 3 cartes avec la boîte (seed {s})", len(cs) == 3)
        check(f"registres distincts avec la boîte (seed {s})",
              len({c["registre"] for c in cs}) == 3)


def test_pari_de_l_oracle():
    """MANIFESTE §9 : l'oracle PRÉDIT ce que tu vas retenir, et c'est LUI qu'on note.
    Le point de design : la série appartient à la machine — l'utilisateur ne peut
    jamais échouer, donc jamais culpabiliser (l'inverse d'un streak)."""
    seeds = ids_from_titles(GRAINES)
    for s in (1, 5, 12, 30):
        cs = tirage(seed_ids=seeds, seed=s)
        for c in cs:
            check(f"chaque carte porte un pari (seed {s})",
                  bool(c.get("pari")) and len(c["pari"]) > 12, str(c.get("pari")))
    # le palmarès note l'ORACLE, pas l'utilisateur
    p = aretes.palmares()
    check("le palmarès existe et est neutre au départ",
          set(p) >= {"paris", "juges", "bons", "score"}, str(p))


def test_profil_visible():
    """Un moteur qui apprend sans rien restituer est une boîte noire — et la confiance
    est TOUT le produit. Le profil doit être calculable, et HONNÊTE sur sa minceur."""
    from recommender.profil_vue import construire, _sans_article
    seeds = ids_from_titles(["Se7en", "Zodiac", "Prisoners"])
    p = construire(seeds, [])
    check("le profil se calcule", p["films"] == 3, str(p["films"]))
    check("il avoue son manque de fiabilité sans arêtes", p["fiable"] is False)
    check("des genres sortent", len(p["genres"]) > 0)
    check("des voisins sortent", len(p["voisins"]) > 0)
    check("les voisins excluent tes propres films",
          not ({v["id"] for v in p["voisins"]} & set(seeds)))
    # régression : lstrip() retirait des CARACTÈRES, « l'animation » -> « nimation »
    check("« l'animation » -> « animation »", _sans_article("l'animation") == "animation")
    check("« le thriller » -> « thriller »", _sans_article("le thriller") == "thriller")
    # avec des arêtes, le vocabulaire de l'utilisateur apparaît
    p2 = construire(seeds, [{"film_id": seeds[0], "valence": 0.8,
                             "texte": "ambiguïté morale fascinante, atmosphère poisseuse"}])
    check("le vocabulaire de tes ressentis remonte",
          any(v["mot"].startswith("ambig") for v in p2["vocabulaire"]),
          str([v["mot"] for v in p2["vocabulaire"][:5]]))


def test_carte_du_gout():
    """La carte doit être HONNÊTE : si la projection déforme trop, elle ment sur ce que
    le moteur fait. On vérifie qu'elle conserve mieux le voisinage qu'une ACP."""
    import numpy as np
    from recommender.carte import carte, _N
    from recommender.recommend import _E

    seeds = ids_from_titles(["Se7en", "Zodiac", "Prisoners"])
    c = carte(seeds, [])
    check("tous les films sont sur la carte", c["films"] == len(_movies))
    check("des territoires sont nommés", c["clusters"] >= 5, str(c["clusters"]))
    check("les noms ne sont pas vides",
          all(t["nom"] and t["nom"] != "—" for t in c["territoires"]))
    check("un centre de gravité existe", c["centre"] is not None)
    tiens = [p for p in c["points"] if p["k"] == 2]
    check("tes films sont marqués", len(tiens) == 3, str(len(tiens)))
    check("les coordonnées sont bornées [0,1]",
          all(0 <= p["x"] <= 1 and 0 <= p["y"] <= 1 for p in c["points"]))

    # la raison d'être du changement : PaCMAP doit battre l'ACP sur le voisinage
    from sklearn.neighbors import NearestNeighbors
    k = 10
    ihi = NearestNeighbors(n_neighbors=k + 1).fit(_E).kneighbors(_E)[1]
    ilo = NearestNeighbors(n_neighbors=k + 1).fit(_N).kneighbors(_N)[1]
    garde = np.mean([len(set(ihi[i, 1:]) & set(ilo[i, 1:])) / k for i in range(len(_E))])
    Xc = _E - _E.mean(0)
    Pacp = Xc @ np.linalg.svd(Xc, full_matrices=False)[2][:2].T
    iacp = NearestNeighbors(n_neighbors=k + 1).fit(Pacp).kneighbors(Pacp)[1]
    gacp = np.mean([len(set(ihi[i, 1:]) & set(iacp[i, 1:])) / k for i in range(len(_E))])
    check(f"PaCMAP ({garde:.1%}) conserve mieux le voisinage que l'ACP ({gacp:.1%})",
          garde > gacp * 1.5)


def test_serrure_preserve_les_graines():
    """Régression : poser un choix effaçait les graines (donc tout le profil)."""
    import os
    sauve = aretes.lire_etat()
    try:
        aretes.poser_graines([807, 1949])
        aretes.poser_choix(1592, "Primal Fear", "connu")
        check("graines survivent au choix", aretes.graines() == [807, 1949],
              str(aretes.graines()))
        check("serrure armée", aretes.en_attente() is not None)
        aretes.liberer()
        check("serrure libérée", aretes.en_attente() is None)
        check("graines survivent à la libération", aretes.graines() == [807, 1949])
    finally:
        aretes.ecrire_etat(sauve)


if __name__ == "__main__":
    for f in (test_trois_axes_orthogonaux, test_argument_toujours_ancre,
              test_argument_en_francais, test_suites_ecartees,
              test_jamais_les_graines_ni_les_racontes, test_valence,
              test_profil_pondere_par_valence, test_canon_invitation_jamais_dette,
              test_boite_aux_lettres, test_pari_de_l_oracle, test_profil_visible,
              test_carte_du_gout, test_serrure_preserve_les_graines):
        print(f"\n{f.__name__}")
        f()
    print(f"\n{'='*46}\n  {_ok} ok · {_ko} échecs")
    sys.exit(1 if _ko else 0)
