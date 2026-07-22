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
    # CE QUE LES DESCRIPTIONS N'APPORTENT PAS, et il vaut mieux l'avoir écrit : elles ne
    # déplacent PAS la géométrie d'un iota. Décrire une graine ajoute une arête sur le
    # MÊME film, donc le vecteur reste colinéaire — unit((1 + 1,5·v)·Σvᵢ) = unit(Σvᵢ).
    # Toute la valeur de l'onboarding est donc dans les MOTS (portrait, vocabulaire,
    # silences rompus), pas dans la géométrie. Promettre l'inverse serait un mensonge.
    from recommender.oracle import profil as _p
    check("décrire ses graines ne bouge pas la géométrie (colinéaire)",
          float(_p(seeds, []) @ _p(seeds, [{"film_id": i, "valence": .8} for i in seeds]))
          > 1 - 1e-9)
    check("… mais donne un portrait là où il n'y en avait aucun",
          parle["portrait"]["phrase"] and not muet["portrait"]["phrase"])


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


def test_elision_sans_rouvrir_les_homographes():
    """« l'intrigue » doit compter comme « intrigue » — sans réveiller les pièges purgés.

    _norm sort « l'intrigue » en UN jeton : le mot n'était donc jamais reconnu, alors que
    « une intrigue » l'était. Le portrait pouvait écrire « tu ne parles jamais de
    l'intrigue » à quelqu'un qui venait d'écrire « l'intrigue est faible ».

    Le correctif NAÏF (dé-éliser le flux de jetons) rouvre la famille d'homographes que
    l'en-tête d'axes.py déclare avoir purgée : « d'un » devient « un », tout se décale, et
    « il parle d'un ton sec » rallume l'atmosphère. D'où la séparation : on enrichit
    l'ensemble des mots vus, les EXPRESSIONS gardent les jetons originaux.
    """
    from recommender.axes import _touches
    for texte, attendu in [("l'intrigue est faible", "intrigue"),
                           ("une intrigue faible", "intrigue"),
                           ("l'image est sublime", "image"),
                           ("d'une mise en scene virtuose", "mise en scène")]:
        check(f"élision reconnue — « {texte} »", attendu in _touches(texte),
              str(sorted(_touches(texte))))

    # les pièges mesurés qui ne doivent JAMAIS revenir
    for texte in ("il parle d'un ton sec", "d'un plan à l'autre", "qu'un plan suffise",
                  "ton film est sorti trop tard"):
        check(f"piège toujours muet — « {texte} »", not _touches(texte),
              str(sorted(_touches(texte))))


def test_le_journal_ne_perd_rien():
    """Le produit détruisait de la donnée tous les soirs, et c'était irrécupérable.

    Trois pertes constatées dans le code : un second choix écrasait `en_attente` (film,
    registre, pari et les DEUX cartes témoins, effacés sans trace) ; `/api/renoncer`
    n'écrivait rien, donc le taux de « révélé mais jamais regardé » était non mesurable
    par construction ; `/api/ressenti` n'exigeait ni serrure ni correspondance de film,
    donc un double envoi doublait le poids d'un film dans le profil.

    Rien de ce qui est écrit ici n'entre dans le profil : renoncer n'est pas rejeter (§3).
    """
    from recommender import journal
    from fastapi.testclient import TestClient
    import main
    seeds = ids_from_titles(GRAINES)
    sauve = aretes.lire_etat()
    n0 = len(journal.tous())
    try:
        c = TestClient(main.app)
        aretes.ecrire_etat({"graines": seeds})

        r = c.post("/api/choix", json={"film_id": seeds[0], "titre": "A",
                                       "registre": "connu", "pari": "p",
                                       "ecartes": [seeds[1], seeds[2]]})
        check("un choix est accepté", r.status_code == 200, str(r.status_code))

        # un second choix sur un AUTRE film doit être refusé — mais tracé
        r2 = c.post("/api/choix", json={"film_id": seeds[1], "titre": "B",
                                        "registre": "pari", "ecartes": [seeds[0]]})
        check("un second choix n'écrase plus le premier", r2.status_code == 409,
              str(r2.status_code))
        check("la serrure d'origine est intacte",
              aretes.en_attente()["film_id"] == seeds[0])
        refus = [e for e in journal.tous() if e["type"] == "choix_refuse"]
        check("même refusé, le choix laisse une trace", len(refus) >= 1)
        check("… avec ses cartes écartées", refus[-1].get("ecartes") == [seeds[0]],
              str(refus[-1].get("ecartes")))

        # un ressenti sur le mauvais film est refusé
        r3 = c.post("/api/ressenti", json={"film_id": seeds[1], "texte": "un texte"})
        check("un ressenti sur le mauvais film est refusé", r3.status_code == 409,
              str(r3.status_code))

        # renoncer LAISSE UNE LIGNE — c'était le trou principal
        r4 = c.post("/api/renoncer")
        check("renoncer est accepté", r4.status_code == 200)
        ren = [e for e in journal.tous() if e["type"] == "renonce"]
        check("renoncer écrit enfin un événement", len(ren) >= 1)
        check("… en gardant le film et ses écartées",
              ren[-1]["film_id"] == seeds[0] and ren[-1].get("ecartes") == [seeds[1], seeds[2]],
              str(ren[-1]))

        # et sans serrure, un ressenti ne peut plus créer d'arête fantôme
        r5 = c.post("/api/ressenti", json={"film_id": seeds[0], "texte": "un texte"})
        check("sans serrure armée, pas d'arête", r5.status_code == 409, str(r5.status_code))

        cpt = journal.compteurs()
        check(f"les compteurs comptent ({cpt['choix']} choix, {cpt['renoncements']} renoncé)",
              cpt["choix"] >= 1 and cpt["renoncements"] >= 1, str(cpt))
        check("sous 5 choix, aucun taux n'est publié", cpt["taux_non_vu"] is None,
              str(cpt["taux_non_vu"]))
        check("le journal ne perd jamais de ligne", len(journal.tous()) > n0)
    finally:
        aretes.ecrire_etat(sauve)


def test_les_cartes_ecartees_sont_gardees_sans_etre_des_rejets():
    """Les deux cartes non prises sont le seul VRAI témoin — et elles étaient jetées.

    Mesurer « de combien ce film t'a déplacé » se compare aujourd'hui à des films tirés
    uniformément dans le catalogue. Or l'oracle ne propose jamais uniformément : le match
    est truqué. Le bon contrefactuel est « et si tu avais pris l'une des deux autres, ce
    soir-là » — et il est IRRÉCUPÉRABLE après coup.

    Mais attention au contresens que ce test verrouille aussi : ne pas choisir n'est pas
    rejeter (MANIFESTE §3). Elles ne doivent toucher ni le profil ni la répulsion.
    """
    from recommender.oracle import profil, repulsion
    seeds = ids_from_titles(GRAINES)
    sauve = aretes.lire_etat()
    try:
        aretes.poser_choix(seeds[0], "X", "connu", "un pari", ecartes=[seeds[1], seeds[2]])
        att = aretes.en_attente()
        check("les deux cartes écartées sont écrites",
              att.get("ecartes") == [seeds[1], seeds[2]], str(att.get("ecartes")))
        aretes.poser_choix(seeds[0], "X", "connu", None, ecartes=[seeds[0], seeds[1]])
        check("le film choisi ne peut pas figurer parmi les écartés",
              aretes.en_attente()["ecartes"] == [seeds[1]],
              str(aretes.en_attente()["ecartes"]))
    finally:
        aretes.ecrire_etat(sauve)

    # et surtout : une carte écartée ne compte NI comme aimée NI comme détestée
    ars = [{"film_id": seeds[1], "valence": 0.8, "ecartes": [seeds[2], seeds[3]]}]
    check("une carte écartée ne crée aucune répulsion", repulsion(ars) is None)
    check("le profil ignore les écartées",
          list(profil(seeds, ars)) == list(profil(seeds, [
              {"film_id": seeds[1], "valence": 0.8}])))


def test_les_rejets_ne_sortent_pas_du_cone():
    """Détester des films ne doit pas envoyer le profil dans le vide.

    La v1 entrait les rejets avec un poids NÉGATIF dans le barycentre. Les embeddings de
    phrases sont anisotropes (cosinus moyen 0,293 entre deux films au hasard, centroïde
    global de norme 0,540) : l'opposé d'un vecteur n'y est pas « le contraire du film »,
    c'est une zone morte. Mesuré, avec 5 rejets, la meilleure similarité du catalogue
    tombait de 0,769 à 0,090 — plus rien ne ressemblait à personne, et l'oracle servait
    quand même trois cartes avec des arguments assurés.
    """
    import numpy as np
    from recommender.oracle import GAMMA_REPULSION, profil, repulsion
    from recommender.recommend import _E, _unit
    seeds = ids_from_titles(GRAINES)
    mu = _unit(_E.mean(axis=0))

    p0 = profil(seeds, [])
    base = float(p0 @ mu)
    detestes = [{"film_id": i, "valence": -1.0} for i in ids_from_titles(
        ["Toy Story", "Shrek", "Frozen", "Cars", "The Smurfs"])]
    if not detestes:
        return
    p = profil(seeds, detestes)
    check(f"le pôle d'attraction ne bouge pas d'un iota ({base:.3f})",
          abs(float(p @ mu) - base) < 1e-9, f"{float(p @ mu):.3f} != {base:.3f}")

    s = _E @ p
    r = repulsion(detestes)
    check("les rejets forment bien un pôle séparé", r is not None)
    s = s - GAMMA_REPULSION * np.clip(_E @ r, 0, None)
    check(f"le catalogue ressemble encore à quelqu'un (simMax {s.max():.3f})",
          s.max() > 0.5, f"simMax={s.max():.3f} — profil hors du cône")

    # et la répulsion doit VRAIMENT servir : les films proches des rejets reculent
    sans = _E @ p
    rang_sans = list(np.argsort(-sans))
    rang_avec = list(np.argsort(-s))
    proche_rejet = int(np.argmax(_E @ r))
    check("un film proche de ce que tu détestes recule au classement",
          rang_avec.index(proche_rejet) > rang_sans.index(proche_rejet),
          f"{rang_sans.index(proche_rejet)} -> {rang_avec.index(proche_rejet)}")


def test_derive_se_tait_sur_du_bruit():
    """LE test de la dérive : sur du hasard pur, elle ne doit rien raconter.

    La v1 produisait une phrase sur 40 historiques aléatoires sur 40 (« tu t'es élargi »
    60/60), et elle se serait armée à la 3e arête. Les mesures étaient des constantes
    déguisées : l'ouverture monte mécaniquement avec le nombre de films, le cap mesure la
    dilution d'un barycentre, la sinuosité décroît en k^-0,5 pour tout le monde.

    Ici on refait exactement l'expérience qui l'avait démasquée.
    """
    import random
    from recommender.derive import derive
    from recommender.recommend import _movies
    seeds = ids_from_titles(GRAINES)
    phrases = ["un film correct", "bof, je ne sais pas trop", "pas mal du tout",
               "je m'attendais a autre chose", "sympa sans plus"]
    rng = random.Random(2026)
    bavard = 0
    for essai in range(40):
        nb = rng.choice((4, 8, 12, 20))
        hist = []
        for j in range(nb):
            m = rng.choice(_movies)
            hist.append({"film_id": m["id"], "titre": m["title"],
                         "texte": rng.choice(phrases), "valence": rng.uniform(-1, 1),
                         "registre": rng.choice(("connu", "ecart", "pari")),
                         "date": f"2026-{1 + j // 28:02d}-{1 + j % 28:02d}T10:00:00+00:00"})
        if derive(seeds, hist).get("verdict"):
            bavard += 1
    check(f"40 historiques aléatoires, {bavard} phrase(s) produite(s)", bavard == 0,
          f"{bavard}/40 — la dérive raconte des salades")

    # et la braise doit être STRICTEMENT nulle quand tout est écrit d'un bloc : sans écart
    # de temps, profil récent == profil de toujours, il n'y a rien à montrer
    salve = [{"film_id": i, "titre": "x", "texte": "un film", "valence": 0.7,
              "date": f"2026-07-01T1{k}:00:00+00:00"} for k, i in enumerate(seeds[:3])]
    d = derive(seeds, salve)
    check("une salve n'écarte rien du tout", d["braise"]["ecart"] < 0.05,
          str(d["braise"]["ecart"]))
    check("une salve est reconnue comme telle", d["salve"] is True)


def test_derive_ce_qui_reste():
    """Ce que la dérive a le droit de dire — et qu'elle mesure vraiment.

    LA BRAISE : deux profils, celui de toujours et celui de maintenant (demi-vie 30 j).
    Le profil cumulé est une moyenne, donc il converge ET il est invariant à l'ordre : il
    ne peut contenir aucune information temporelle. Le profil récent, lui, ne converge
    jamais — c'est le seul mouvement réel disponible.

    LE SILENCE ROMPU : un axe dont tu n'avais jamais parlé et dont tu parles. C'est un
    fait daté, pas une tendance : il n'y a pas d'hypothèse nulle, donc pas de faux
    positif possible.
    """
    from recommender.derive import derive
    seeds = ids_from_titles(GRAINES)

    img = "les couleurs et la lumiere, un cadrage soigne"
    son = "la bande son est magnifique, le silence aussi"
    per = "le jeu des acteurs porte tout le film"

    d = derive(seeds, _histoire([img, img, son, per], ["connu"] * 4, [1, 5, 12, 20]))
    check("aucun verdict, jamais", d["verdict"] is None)
    check("étalé sur 20 jours : pas une salve", d["salve"] is False)
    check(f"amplitude en jours mesurée ({d['jours']})", d["jours"] >= 19)

    axes_rompus = [s["axe"] for s in d["silences"]]
    check("le silence sur le son est rompu, et daté",
          "son" in axes_rompus, str(axes_rompus))
    check("le silence sur les personnages est rompu",
          "personnages" in axes_rompus, str(axes_rompus))
    check("la 1re arête ne compte pas comme une rupture",
          all(s["n"] > 1 for s in d["silences"]), str([s["n"] for s in d["silences"]]))
    check("chaque rupture cite le mot qui l'a déclenchée",
          all(s["mot"] for s in d["silences"]))

    # la braise doit EXISTER dès qu'il y a du temps, et grandir avec l'écart des dates
    check("du temps passe -> un écart apparaît", d["braise"]["ecart"] > 0,
          str(d["braise"]))

    # le témoin : un pas ne vaut que comparé à ce qu'aurait fait n'importe quel film
    pcts = [e.get("pas_pct") for e in d["etapes"] if e["n"] > 0]
    check("chaque pas est situé dans son témoin", all(p is not None for p in pcts),
          str(pcts))
    check("les percentiles sont bien des percentiles",
          all(0.0 <= p <= 1.0 for p in pcts), str(pcts))

    check("un état par ressenti, plus le départ", len(d["etapes"]) == 5,
          str(len(d["etapes"])))


if __name__ == "__main__":
    for f in (test_trois_axes_orthogonaux, test_argument_toujours_ancre,
              test_argument_en_francais, test_suites_ecartees,
              test_jamais_les_graines_ni_les_racontes, test_valence,
              test_valence_recalculee_a_la_lecture,
              test_profil_pondere_par_valence, test_canon_invitation_jamais_dette,
              test_boite_aux_lettres, test_pari_de_l_oracle, test_onboarding_exige_des_descriptions, test_profil_visible,
              test_relecture_ne_vole_pas_la_voix,
              test_portrait_lisible, test_carte_du_gout,
              test_elision_sans_rouvrir_les_homographes,
              test_le_journal_ne_perd_rien,
              test_les_cartes_ecartees_sont_gardees_sans_etre_des_rejets,
              test_les_rejets_ne_sortent_pas_du_cone,
              test_derive_se_tait_sur_du_bruit, test_derive_ce_qui_reste,
              test_serrure_preserve_les_graines):
        print(f"\n{f.__name__}")
        f()
    print(f"\n{'='*46}\n  {_ok} ok · {_ko} échecs")
    sys.exit(1 if _ko else 0)
