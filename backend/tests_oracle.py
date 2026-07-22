"""Tests de l'oracle — les invariants du MANIFESTE, pas du détail d'implémentation.

Chaque test verrouille une décision produit gravée dans MANIFESTE.md. Si un test casse,
c'est soit une régression, soit une décision qu'on a changée — auquel cas on rouvre le
manifeste AVANT de toucher au test.

    python tests_oracle.py        (aucune dépendance, pas besoin de pytest)
"""
import os
import sys
import tempfile

# Les tests écrivent dans un état ISOLÉ : sans ça, ils touchaient les vraies arêtes de
# l'utilisateur. On le pose AVANT d'importer aretes, qui lit la variable au chargement.
os.environ.setdefault("MORDU_ETAT_DIR", tempfile.mkdtemp(prefix="mordu-test-"))

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
        # En autonome on continue pour voir TOUS les échecs d'un coup. Sous pytest il faut
        # lever, sinon la suite passe au vert en imprimant ses propres échecs.
        if "PYTEST_CURRENT_TEST" in os.environ:
            raise AssertionError(f"{nom}  {detail}")


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
        # NÉGATION — trouvé sur un vrai ressenti : « je ne suis pas déçu » est POSITIF,
        # et le comptage naïf le classait négatif. C'est l'échec classique du lexique.
        ("Je ne suis pas déçu.", 0.3, 1.0),
        ("Ce n'est pas génial.", -1.0, 0.1),
        ("Jamais ennuyeux.", 0.2, 1.0),
        # ACCORDS : « belles » doit compter comme « belle », sinon on rate la moitié
        # des adjectifs d'un texte français réel.
        ("Les couleurs sont belles.", 0.3, 1.0),
    ]
    for texte, lo, hi in cas:
        v = aretes.valence(texte)
        check(f"valence {v:+.2f} ∈ [{lo};{hi}] — « {texte[:34]}… »", lo <= v <= hi)


def test_valence_recalculee_a_la_lecture():
    """MANIFESTE §4 : le texte est la donnée brute, la valence est une VUE. Elle doit
    donc être recalculée à la lecture — sinon un ressenti mal noté le reste à jamais et
    continue de fausser le profil, même après correction du lexique."""
    import json
    import os
    chemin = aretes.ARETES_PATH
    sauve = open(chemin, encoding="utf-8").read() if os.path.exists(chemin) else None
    try:
        with open(chemin, "w", encoding="utf-8") as f:
            # on écrit une valence VOLONTAIREMENT fausse dans le fichier
            f.write(json.dumps({"film_id": 1, "titre": "T", "valence": -0.99,
                                "texte": "Magnifique, sublime, bouleversé."}) + "\n")
        lu = aretes.toutes()[0]
        check(f"la valence est recalculée ({lu['valence']:+.2f}, pas -0.99)",
              lu["valence"] > 0.3, str(lu["valence"]))
    finally:
        if sauve is not None:
            open(chemin, "w", encoding="utf-8").write(sauve)
        elif os.path.exists(chemin):
            os.remove(chemin)


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


def test_relecture_ne_vole_pas_la_voix():
    """LE point critique du module : la page profil affiche « les mots que tu emploies ».
    Si la correction d'un LLM remplaçait le brut, ce nuage montrerait le vocabulaire du
    MODÈLE. Le brut doit donc rester la source du vocabulaire, et la correction ne
    servir qu'à la valence et à la lecture."""
    from recommender.profil_vue import construire
    from recommender import relecture
    seeds = ids_from_titles(["Se7en"])
    brut = "chef doeuvre absolu, la mise en scene est hypnotique"
    corr = "Chef-d'œuvre absolu, la mise en scène est hypnotique."
    p = construire(seeds, [{"film_id": seeds[0], "texte": brut, "corrige": corr,
                            "valence": 0.8}])
    mots = {v["mot"] for v in p["vocabulaire"]}
    check("le vocabulaire vient du texte BRUT", "doeuvre" in mots or "mise" in mots,
          str(sorted(mots)[:6]))
    # sans clé, tout dégrade proprement au lieu de casser
    if not relecture.disponible():
        check("sans clé API, relire() renvoie None sans lever",
              relecture.relire("un texte") is None)
    check("texte vide -> None", relecture.relire("") is None)


def test_onboarding_exige_des_descriptions():
    """MANIFESTE §9 : l'onboarding devait être « N films adorés ET une ligne sur
    pourquoi ». Seule la première moitié était implémentée — des graines sans texte ne
    portent ni vocabulaire ni axe d'attention, et le premier ressenti écrit tirait alors
    tout le profil vers lui (constaté à l'usage : dérive vers l'anime)."""
    from recommender.profil_vue import construire
    seeds = ids_from_titles(["Se7en", "Zodiac", "Prisoners", "Fight Club", "12 Angry Men"])
    if len(seeds) < 5:
        return
    muet = construire(seeds, [])
    parle = construire(seeds, [
        {"film_id": seeds[0], "valence": .8,
         "texte": "lambiance poisseuse et la fin qui laisse KO"},
        {"film_id": seeds[1], "valence": .8,
         "texte": "lobsession de lenquete qui devore les personnages"},
        {"film_id": seeds[2], "valence": .8,
         "texte": "la tension morale insoutenable du pere"},
        {"film_id": seeds[3], "valence": .8,
         "texte": "la satire du consumerisme et le retournement"},
        {"film_id": seeds[4], "valence": .8,
         "texte": "un huis clos ou tout se joue sur la parole"},
    ])
    check("sans description : aucun vocabulaire", len(muet["vocabulaire"]) == 0)
    check(f"avec descriptions : du vocabulaire ({len(parle['vocabulaire'])} mots)",
          len(parle["vocabulaire"]) >= 8)
    check("5 descriptions rendent le portrait fiable d'emblée", parle["fiable"] is True)
    check("l'empreinte est plus fine avec les descriptions",
          parle["empreinte"]["finesse"] > muet["empreinte"]["finesse"])


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


def test_portrait_lisible():
    """L'empreinte est unique mais MUETTE — Martin : « elle ne dit rien de moi ».
    Le MANIFESTE §4 promettait pourtant un portrait tiré de ce qu'on ÉCRIT :
    « ce que tu MENTIONNES est ton axe d'attention ». Ce test verrouille la moitié
    qui parle, et surtout le signal du SILENCE (ce dont on ne parle jamais)."""
    from recommender.axes import _de, portrait

    vide = portrait([])
    check("sans ressenti, pas de phrase inventée", vide["phrase"] is None)
    check("sans ressenti, aucun axe cité", not vide["cites"])

    p = portrait([
        {"texte": "les couleurs sont magnifiques et la lumiere sublime"},
        {"texte": "une photo splendide, des decors magnifiques"},
    ])
    check("l'axe dominant est détecté", p["cites"][0] == "image", str(p["cites"][:2]))
    check("la phrase nomme l'axe dominant", "l'image" in (p["phrase"] or ""))
    check("le SILENCE est nommé (le signal le plus distinctif)",
          "jamais" in (p["phrase"] or ""))
    check("les axes muets sont listés", "rythme" in p["jamais"])

    # deux personnes peuvent aimer les mêmes films en n'y regardant pas la même chose
    q = portrait([{"texte": "le rythme est nerveux, un montage sec et rapide"}])
    check("un autre vocabulaire donne un autre portrait",
          q["cites"][0] != p["cites"][0], f"{q['cites'][:1]} vs {p['cites'][:1]}")

    # français : les libellés portent leur article, il faut contracter après « de »
    check("« le rythme » -> « du rythme »", _de("le rythme") == "du rythme")
    check("« les personnages » -> « des personnages »",
          _de("les personnages") == "des personnages")
    check("« l'image » -> « de l'image »", _de("l'image") == "de l'image")

    # le portrait lit le BRUT, jamais le corrigé (même règle que le vocabulaire)
    r = portrait([{"texte": "les couleurs", "corrige": "le rythme nerveux"}])
    check("le portrait lit le texte brut", "image" in r["cites"])


def test_empreinte():
    """L'empreinte est le vecteur profil rendu en glyphe : elle doit être DÉTERMINISTE
    (même goût, même image), SENSIBLE (elle change quand le goût change) et se RÉSOUDRE
    à mesure qu'on écrit — comme les affiches. C'est le Wrapped, dès la 1re arête."""
    from recommender.profil_vue import empreinte
    seeds = ids_from_titles(["Se7en", "Zodiac", "Prisoners"])
    a = empreinte(seeds, [])
    check("l'empreinte se calcule", a is not None and len(a["cellules"]) > 0)
    check("déterministe", a["cellules"] == empreinte(seeds, [])["cellules"])
    autre = ids_from_titles(["Toy Story", "Spirited Away"])
    if autre:
        check("un autre goût donne une autre empreinte",
              a["cellules"] != empreinte(autre, [])["cellules"])
    # la finesse suit le nombre d'arêtes : le glyphe se résout avec toi
    faux = [{"film_id": i, "valence": 0.7} for i in seeds] * 4
    fin = empreinte(seeds, faux)
    check(f"la finesse monte avec les arêtes ({a['finesse']} -> {fin['finesse']})",
          fin["finesse"] > a["finesse"])
    check("plus d'arêtes = plus de paliers", fin["niveaux"] > a["niveaux"])
    check("les cellules restent dans les paliers",
          all(0 <= c < a["niveaux"] for c in a["cellules"]))
    # Les dimensions sont ORDONNÉES pour que les corrélées soient voisines : sans ça
    # le glyphe est du poivre et sel par construction (l'ordre d'un embedding est
    # arbitraire, donc deux cellules voisines n'ont aucun lien).
    import numpy as np
    from recommender.profil_vue import _ordre_dimensions
    from recommender.recommend import _E
    o = _ordre_dimensions()
    check("l'ordre couvre toutes les dimensions, sans doublon",
          len(o) == _E.shape[1] and len(set(int(x) for x in o)) == _E.shape[1])
    C = np.abs(np.corrcoef(_E.T))
    nat = np.mean([C[i, i + 1] for i in range(_E.shape[1] - 1)])
    ord_ = np.mean([C[o[i], o[i + 1]] for i in range(_E.shape[1] - 1)])
    check(f"voisinage plus corrélé qu'en ordre naturel ({ord_:.3f} > {nat:.3f})",
          ord_ > nat * 1.5)


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


def _histoire(mots, registres, jours):
    """Fabrique une histoire d'arêtes datée. Les films sont fixes : ce qu'on teste ici est
    la MESURE de la dérive, pas le catalogue."""
    ids = [(372058, "Your Name."), (524, "Casino"), (949, "Heat"),
           (244786, "Whiplash"), (496243, "Parasite"), (680, "Pulp Fiction")]
    return [{"film_id": ids[i % len(ids)][0], "titre": ids[i % len(ids)][1],
             "texte": mots[i], "valence": 0.7, "registre": registres[i],
             "date": f"2026-07-{jours[i]:02d}T10:00:00+00:00"}
            for i in range(len(mots))]


def test_derive_ne_raconte_pas_de_salades():
    """L'évolution est le cœur de l'empreinte — donc c'est là qu'inventer coûte le plus.

    Trois refus verrouillés : sous 3 arêtes on ne conclut pas, une salve écrite d'un bloc
    est signalée comme telle, et une dérive lexicale sous le seuil de bruit reste muette.
    """
    from recommender.derive import derive
    seeds = ids_from_titles(GRAINES)

    d = derive(seeds, _histoire(["beau", "long"], ["connu", "pari"], [1, 2]),
               avec_empreintes=False)
    check("2 arêtes : pas de verdict", d["verdict"] is None and not d["assez"])
    check("2 arêtes : on dit ce qui manque", d["manque"] == 1, str(d["manque"]))

    meme_jour = _histoire(["beau", "long", "lent", "sombre"],
                          ["connu"] * 4, [1, 1, 1, 1])
    for i, a in enumerate(meme_jour):
        a["date"] = f"2026-07-01T1{i}:00:00+00:00"
    ds = derive(seeds, meme_jour, avec_empreintes=False)
    check("écrit d'un bloc = salve", ds["salve"] is True)
    check("la salve est dite dans le verdict",
          ds["verdict"] and "salve" in ds["verdict"], str(ds["verdict"]))

    # dérive lexicale FRANCHE : image -> personnages
    img = "les couleurs et la lumiere sont magnifiques, un cadrage sublime"
    per = "le jeu des acteurs, l'interpretation et le casting portent le role"
    dl = derive(seeds, _histoire([img, img, per, per], ["connu", "connu", "ecart", "pari"],
                                 [1, 5, 12, 20]), avec_empreintes=False)
    check("dérive d'attention détectée",
          dl["attention"] and dl["attention"]["gagne"]
          and dl["attention"]["gagne"]["cle"] == "personnages",
          str(dl["attention"] and dl["attention"]["gagne"]))
    check("l'axe abandonné est nommé",
          dl["attention"]["perdu"] and dl["attention"]["perdu"]["cle"] == "image",
          str(dl["attention"]["perdu"]))
    check("audace en hausse mesurée", dl["audace"] and dl["audace"]["delta"] > 0,
          str(dl["audace"]))
    check("le verdict contracte l'article",
          "parlais de l'image" in (dl["verdict"] or ""), str(dl["verdict"]))
    check("étalé sur 20 jours : pas une salve", dl["salve"] is False)

    # Inégalité triangulaire sur la sphère : la somme des pas ne peut pas être plus courte
    # que le vol d'oiseau. C'est ce qui rend la sinuosité interprétable — et NON, le cap
    # n'est pas monotone : revenir sur ses pas le fait redescendre, c'est même tout
    # l'intérêt de la mesure.
    caps = [e["cap"] for e in dl["etapes"]]
    check("le cap part de zéro", caps[0] == 0.0, str(caps))
    check("chemin >= distance à vol d'oiseau", dl["chemin"] >= dl["net"] - 1e-6,
          f"{dl['chemin']} < {dl['net']}")
    check("sinuosité >= 1", dl["sinuosite"] >= 1.0 - 1e-6, str(dl["sinuosite"]))


if __name__ == "__main__":
    for f in (test_trois_axes_orthogonaux, test_argument_toujours_ancre,
              test_argument_en_francais, test_suites_ecartees,
              test_jamais_les_graines_ni_les_racontes, test_valence,
              test_valence_recalculee_a_la_lecture,
              test_profil_pondere_par_valence, test_canon_invitation_jamais_dette,
              test_boite_aux_lettres, test_pari_de_l_oracle, test_onboarding_exige_des_descriptions, test_profil_visible,
              test_relecture_ne_vole_pas_la_voix,
              test_portrait_lisible, test_empreinte, test_carte_du_gout,
              test_derive_ne_raconte_pas_de_salades,
              test_serrure_preserve_les_graines):
        print(f"\n{f.__name__}")
        f()
    print(f"\n{'='*46}\n  {_ok} ok · {_ko} échecs")
    sys.exit(1 if _ko else 0)
