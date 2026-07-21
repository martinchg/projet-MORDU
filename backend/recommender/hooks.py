"""Faits croustillants — pré-génération OFFLINE de data/hooks.json.

Pour chaque film de data/movies.json, on va chercher sur Wikipédia (FR d'abord, EN en
repli) les sections de fabrication (Production / Tournage / Genèse / Casting / Accueil…),
on les découpe en phrases et on scelle les 3 phrases les plus « croustillantes » selon des
heuristiques 100 % locales (aucun LLM, aucune clé API).

    python hooks.py --limit 15        # les 15 films les plus connus (test rapide)
    python hooks.py                   # tout le catalogue
    python hooks.py --force           # re-télécharge tout (sinon on complète l'existant)
    python hooks.py --limit 15 --show # affiche les hooks obtenus à la fin

Appariement film <-> page Wikipédia
-----------------------------------
On ne fait PAS de recherche floue par titre en premier : on passe par Wikidata en
interrogeant la propriété P345 (identifiant IMDb). L'imdb_id de movies.json est une clé
exacte, donc le rattachement est exact (un mauvais match donnerait une anecdote sur le
mauvais film, c'est le pire échec possible pour ce produit). Le repli par titre n'est
utilisé que si le film n'a pas d'imdb_id ou n'est pas dans Wikidata, et il est alors
VÉRIFIÉ (année + réalisateur doivent apparaître dans l'article).

Raffinement LLM ultérieur
-------------------------
Toute la « qualité éditoriale » est concentrée dans `_score_interet(phrase, ctx)`.
C'est le seul point à remplacer pour brancher un LLM : mêmes entrées (une phrase, un
contexte), même sortie (un float). Le reste du pipeline (résolution de page, extraction,
découpage, cache, reprise) est inchangé. Voir la docstring de la fonction.
"""
import argparse
import gzip
import hashlib
import json
import os
import re
import sys
import time
import unicodedata

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
MOVIES = os.path.join(DATA_DIR, "movies.json")
OUT = os.path.join(DATA_DIR, "hooks.json")
# Cache disque des articles bruts : permet de re-scorer (--rescore) sans retaper
# Wikipédia, et de reprendre proprement après une coupure.
CACHE_DIR = os.path.join(DATA_DIR, "wiki_cache")

UA = "MorduBot/0.1 (projet perso de reco de films; contact: martinchassaing01@gmail.com)"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
WIKI_API = "https://{lang}.wikipedia.org/w/api.php"
WIKI_URL = "https://{lang}.wikipedia.org/wiki/{title}"

DELAI = 0.25          # politesse réseau entre requêtes (s)
TIMEOUT = 25
SAVE_EVERY = 10       # sauvegarde incrémentale (reprise si ça coupe)
SEUIL_REPLI_EN = 8.0  # sous ce score, l'article FR est jugé trop pauvre -> on tente l'EN

# --------------------------------------------------------------------------------------
# Sections d'article qui contiennent des anecdotes, et leur poids.
# Le poids multiplie le score des phrases de la section : une phrase de « Tournage » vaut
# structurellement plus qu'une phrase de « Box-office ».
# --------------------------------------------------------------------------------------
SECTIONS_POIDS = [
    # (motif de titre de section, poids)
    (r"anecdote|autour du film|trivia|le saviez", 1.35),
    (r"tournage|filming|shooting|production design", 1.30),
    (r"choix des interpr|casting|distribution des r|attribution des r", 1.30),
    (r"gen[eè]se|développement|developp|development|écriture|ecriture|scénario|screenplay|writing", 1.25),
    (r"pré-?production|pre-?production", 1.20),
    (r"^production", 1.20),
    (r"effets spéciaux|effets visuels|special effects|visual effects|maquillage|cascades", 1.15),
    (r"post-?production|montage|editing", 1.10),
    (r"musique|bande originale|soundtrack|score", 1.00),
    (r"postérité|posterit|legacy|héritage|influence", 1.05),
    (r"accueil|reception|critique|controverse|polémique|censure|controversy", 0.95),
    (r"distinction|récompense|awards|accolades", 0.85),
    # le box-office et la sortie sont presque toujours du remplissage chiffré : très bas,
    # sinon les phrases « a rapporté X millions le premier jour » remontent (itération 3).
    (r"box-?office|recettes|sortie|release|marketing|promotion", 0.45),
]

# Sections à ignorer complètement (résumé de l'intrigue, listes, appareil critique).
SECTIONS_EXCLUES = re.compile(
    r"^(synopsis|résumé|resume|intrigue|plot|fiche technique|distribution$|cast$|"
    r"personnages|notes et références|références|notes|annexes|bibliographie|"
    r"articles connexes|liens externes|voir aussi|see also|references|external links|"
    r"further reading|sources|éditions|adaptations?$|suite|suites|série|remake)",
    re.I,
)

# Sections hors sujet où qu'apparaisse le motif dans le chemin : ce sont des sections
# d'analyse ou de comparaison à l'œuvre source, pas des sections de fabrication. Elles
# produisent des phrases qui parlent de l'INTRIGUE et non du tournage — donc des faux
# « faits croustillants » (repéré à l'itération 1 : Le Seigneur des anneaux, The Dark Knight).
SECTIONS_HORS_SUJET = re.compile(
    r"differences? avec|variations? par rapport|par rapport (?:au|a la|aux) (?:livre|roman|comics|bd)|"
    r"comparaison|fidelite|themes?|analyse|interpretation|symbol|lecture|"
    r"produits? derives?|jeu video|merchandis|novellis|bande dessinee|"
    r"suites?$|prequel|spin-?off|univers|franchise|"
    r"edition|blu-?ray|dvd|diffusion|television|streaming|"
    r"liste|palmares$|selections?$|nominations?$",
    re.I,
)

# --------------------------------------------------------------------------------------
# Marqueurs de scoring. (motif, poids). Motifs appliqués sur la phrase en minuscules
# désaccentuée pour être robuste aux variations d'accent.
# --------------------------------------------------------------------------------------
# Chaque marqueur porte une FAMILLE. Les poids d'une même famille ne s'additionnent pas
# franchement (max + 35 % du reste) : une seule anecdote qui répète « pressenti / refusa /
# remplacée » ne doit pas écraser une anecdote d'une autre nature (rendements décroissants
# introduits à l'itération 2, sinon les phrases de casting monopolisent tout le classement).
BONUS = [
    # --- refus, quasi-castings, « ça a failli être quelqu'un d'autre » : le meilleur filon
    ("casting_alt", r"\brefus(?:e|a|ent|ait|er|ee?s?)\b|\bdecline\b|\bturned down\b|\brejet", 3.2),
    ("casting_alt", r"\ba failli\b|\bfaillit\b|\bavait failli\b|\bnearly\b|\balmost\b", 3.2),
    ("casting_alt", r"\bpremier choix\b|\bpressenti|\benvisage(?:e|ait|ent)?\b|\bconsidered for\b|\bapproached\b", 2.8),
    ("casting_alt", r"\binitialement\b|\bau depart\b|\ba l'origine\b|\borigin(?:al|ellement|ally)\b|\bdevait etre\b|\baurait du\b", 2.4),
    ("casting_alt", r"\bremplac|\bquitte le projet\b|\babandonne le projet\b|\brenvoy|\blicenci|\bfired\b|\breplaced\b|\bdropped out\b", 2.8),
    ("pression", r"\bse porte volontaire\b|\bsupplie\b|\binsiste pour\b|\bexige\b|\bimpose\b|\bmenace\b|\bse bat pour\b", 2.2),
    ("audition", r"\bauditionn|\baudition\b|\bbout d'essai", 1.6),
    # --- improvisation / hors scénario : anecdote reine
    ("impro", r"\bimprovis", 3.6),
    ("impro", r"n'?etait pas (?:prevu|dans le scenario|ecrit)|pas prevue? (?:dans|au) scenario|\bnot in the script\b|\bad-?lib", 3.6),
    ("impro", r"\breplique culte\b|\bphrase culte\b|\bscene culte\b|\bcelebre replique\b", 2.4),
    # --- incidents, accidents, extrêmes physiques
    ("incident", r"\baccident|\bblesse|\bblessure|\bhospitalis|\bfracture|\bse casse\b|\bs'est casse|\bs'est coupe", 3.4),
    ("incident", r"\bincendie\b|\bexplos|\bnoy(?:e|ade)|\bfailli mourir\b|\bcoma\b|\bevacu|\bpanique", 2.6),
    ("incident", r"\bmeurt\b|\bdecede\b|\bmort (?:de|du|pendant|durant|sur le tournage)|\bdied\b", 2.2),
    ("corps", r"\bperd(?:u|it)? \d+ ?(?:kilos?|kg|livres)|\bpris \d+ ?(?:kilos?|kg)|\bmaigri|\bregime\b|\bprise de poids\b", 3.2),
    ("corps", r"\bdepression\b|\bdepressif\b|\bcauchemars?\b|\binsomnie|\bepuis(?:e|ement)\b|\bs'est evanoui", 2.2),
    ("corps", r"\breste (?:dans|en) (?:le|la|son) (?:personnage|role)\b|\bmethod acting\b|\bne quitte jamais son (?:role|personnage)\b", 2.6),
    # --- records, chiffres marquants, prouesses
    ("prises", r"\b\d+ ?prises\b|\b\d+ ?takes\b", 3.4),
    ("record", r"\brecord\b|\bjamais (?:vu|realise|atteint)\b|\ble plus (?:cher|long|grand|gros)\b|\bpremier film a\b|\bune premiere\b", 2.4),
    ("duree", r"\b\d+ ?(?:mois|semaines|jours) de tournage\b|\btournage (?:a )?dur|\ba dure \d+ ?(?:mois|semaines|jours|heures)", 2.2),
    # chiffres concrets et palpables (figurants, hectares, litres…) : tres « croustillant »
    ("chiffres", r"\b\d{2,}(?:[  ]\d{3})* ?(?:figurants|hectares|acres|tonnes|litres|kilometres|metres|costumes|decors|plans|techniciens|personnes|chevaux|rats|abeilles)\b", 2.6),
    ("argent", r"\b\d[\d  ]{2,}(?:000)? ?(?:dollars|euros)|\b\d+(?:[.,]\d+)? ?millions? de (?:dollars|euros)|\$\d", 1.4),
    ("argent", r"\bdepassement\b|\bsurcout\b|\bexplose le budget\b|\bdepasse le budget\b", 1.8),
    # --- censure, interdiction, scandale
    ("censure", r"\binterdi(?:t|te|ction)\b|\bcensur|\bbanni\b|\bbanned\b|\bboycott|\bscandale\b|\bpolemique\b|\bproces\b|\bplainte\b|\bmenace de mort\b", 2.6),
    # --- réécriture, fins alternatives, coupes
    ("reecriture", r"\breecri|\brewrit|\bfin alternative\b|\bautre fin\b|\bchange(?:r|e)? la fin\b|\bfin (?:originale|initiale)\b", 2.8),
    ("reecriture", r"\bcoupe(?:e|es)? au montage\b|\bsupprime(?:e|es)? au montage\b|\bscene(?:s)? coupee|\bcut from the film\b|\bjamais (?:tournee|utilisee)\b", 2.6),
    # --- vrai / faux : « c'était réel »
    ("reel", r"\bveritable(?:s)?\b|\bpour de vrai\b|\breellement\b|\bsans trucage\b|\ben vrai\b|\bvraie(?:s)? (?:larmes|blessures?|dents)\b", 2.0),
    ("reel", r"\b(?:cogner|frapper|boire|manger|pleurer|crier|conduire|nager) vraiment\b|\bvraiment (?:cogne|frappe|bu|mange|pleure)|\ba ordonne a\b|\ba demande a\b.*\bvraiment\b", 2.2),
    ("reel", r"\bsans (?:le )?(?:savoir|prevenir|avertir)\b|\ba l'insu\b|\bcache aux?\b|\bignorai(?:t|ent)\b|\bne savai(?:t|ent) pas\b|\breaction (?:reelle|authentique)\b", 3.0),
    ("inspiration", r"\bs'inspire de\b|\binspire (?:par|d'un|de la)\b|\bfait(?:s)? reel|\bhistoire vraie\b|\bbase sur (?:l'histoire|un fait)", 1.6),
    # --- récompenses
    ("prix", r"\boscar|\bpalme d'or\b|\bcesar\b|\bgolden globe|\bbafta|\bours d'or\b|\blion d'or\b", 1.4),
    # --- petits détails de fabrication savoureux
    ("artisanat", r"\bmaquette\b|\bfait main\b|\bconstrui(?:t|te|sent) (?:de toutes pieces|specialement)\b|\bdecor(?:s)? (?:reel|construit)|\ba l'echelle\b|\bgrandeur nature\b", 2.0),
    ("artisanat", r"\bvrai(?:e|s)? (?:sang|animaux|chevaux|rats|abeilles|serpents)\b|\bdresseur", 1.6),
    ("cascade", r"\bcascade(?:s|ur|urs)?\b|\bdoublure\b|\bsans doublure\b|\blui-meme ses cascades\b", 2.2),
    ("apprentissage", r"\bappri(?:s|t) a\b|\bs'entraine\b|\bentrainement\b|\bapprendre le\b|\bpris des cours\b|\bformation de \d+", 2.0),
    ("cameo", r"\bcameo\b|\bapparait brievement\b|\bfait une apparition\b", 1.8),
]

MALUS = [
    # --- purement factuel : dates, distribution, chiffres administratifs
    (r"\b(?:sort|est sorti|sortie) (?:en salles?|le|nationale|au cinema|en france)\b", -3.0),
    (r"\bdistribue par\b|\bdistribution assuree\b|\bproduit par la societe\b|\bcoproduction\b", -2.0),
    (r"\bpresente (?:en (?:avant-premiere|competition)|au festival)\b", -1.5),
    (r"\bnumero un du box-?office\b|\bengrange\b|\bcumule\b|\brecettes? (?:de|mondiales)", -1.2),
    # équivalents anglais (l'article EN sert de repli : il lui faut ses propres filtres)
    (r"\bgrossed\b|\bearned \$|\bopening (?:day|weekend|wednesday)\b|\bbox office\b|"
     r"\bdebuted at\b|\bhighest-?grossing\b|\bdomestic(?:ally)?\b|\btheaters?\b|"
     r"\bwas released (?:in|on)\b|\bdistributed by\b|\bsecond weekend\b|"
     r"\bpassed \$|\bmillion from\b|\bscreens\b|\b4dx\b|\bimax screens\b|"
     r"\bworldwide opening\b|\ball-?time record\b|\bper-?theater\b", -4.5),
    (r"\bof (?:entertainment weekly|the new york times|rolling stone|variety|"
     r"the guardian|empire|time|the hollywood reporter|usa today)\b|"
     r"\bsaid:|\bwrote:|\bgave the film\b|\breviewer|\bcritics? (?:praised|noted|said)\b|"
     r"\breview aggregat|\bapproval rating\b|\baverage rating\b", -3.5),
    # promo / marketing : ce n'est pas de la fabrication
    (r"\bpromotion\b|\bavant-?premiere\b|\bconference de presse\b|\bbande-?annonce\b|"
     r"\bcampagne (?:de |marketing|publicitaire)|\baffiche(?:s)? du film\b", -2.2),
    (r"\bsite agregateur\b|\bmetacritic\b|\brotten tomatoes\b|\ballocine\b|\bmoyenne de \d|\bnote de \d|\bsur la base de \d+ (?:critiques|avis)", -4.0),
    (r"\bobtient un score\b|\brecueille \d+ ?%|\b\d+ ?% (?:de critiques|d'avis)|\b\d+(?:[.,]\d+)? ?/ ?10\b", -4.0),
    # --- phrases de liste / énumération de noms ou de rôles
    (r"\b(?:role|roles?) (?:de|du|des)\b.*\b(?:role|roles?) (?:de|du|des)\b", -1.5),
    (r"\bdans le role de\b.*,.*,", -1.5),
    # --- méta-encyclopédique
    (r"\bvoir (?:aussi|la section)\b|\bcet article\b|\bce paragraphe\b|\bcf\.", -3.0),
    (r"\bselon (?:le|la|les) (?:sites?|magazines?|journaux)\b", -0.8),
    # --- spéculation journalistique (« devrait », « pourrait ») : ce n'est PAS un fait
    #     (repéré à l'itération 1 sur The Dark Knight Rises)
    (r"\b(?:devrait|devraient|pourrait|pourraient|serait|seraient|"
     r"envisagerait|souhaiterait)\b", -3.6),
    (r"\brumeur|\bselon des sources\b|\bn'a pas ete confirme\b|\bpeut-etre\b", -2.0),
    # --- avis de critique : c'est une opinion, pas un fait de fabrication
    #     (itération 2 : The Dark Knight remontait une citation de journaliste)
    (r"\ble (?:journaliste|critique|magazine|quotidien|site|chroniqueur)\b|"
     r"\bla (?:critique|revue|journaliste)\b|\bpour le new york times\b|\bvariety\b|"
     r"\bempire\b|\btelerama\b|\bles inrock", -3.0),
    (r"\b(?:declare|estime|juge|ecrit|salue|deplore|regrette) que\b|"
     r"\bselon (?:lui|elle|le critique)\b|\bs'interroge", -1.6),
    # déclaration d'intention du réalisateur en interview : c'est du discours, pas un fait
    (r"\ba declare (?:a|au|dans|lors|en)\b|\bexplique (?:a|au|dans|avoir|que)\b|"
     r"\baffirme (?:a|au|dans|avoir|que)\b|\bconfie (?:a|au|dans)\b|\bdans un entretien\b|"
     r"\blors d'une interview\b|\bvoulait (?:que|montrer|faire|eviter)\b|\bsouhaitait\b", -2.6),
    (r"\bchef-?d'oeuvre\b|\bunanime|\bencense|\bplebiscit|\bdithyrambique", -2.0),
    # --- drames réels : ce produit sert des anecdotes plaisantes, pas des faits divers.
    #     Filtrage éditorial volontaire (itération 3, repéré sur The Dark Knight Rises).
    (r"\battentat|\bfusillade|\btuerie|\bmassacre\b|\bvictimes\b|\bhommage aux victimes\b|"
     r"\bsuicide|\boverdose|\bviol\b|\bagression sexuelle|\bharcelement|\bpedophil|"
     r"\bproces pour\b|\bcondamne a de la prison\b", -6.0),
    # --- généralisations vagues, sans anecdote nommée
    (r"^(?:la plupart|plusieurs|certains|certaines|de nombreux|de nombreuses|"
     r"beaucoup|d'autres|quelques)\b", -2.0),
    # --- amorces / anaphores : la phrase doit se comprendre SEULE sur une carte
    (r"^(?:il|elle|ils|elles|celui-ci|celle-ci|ceux-ci|ce dernier|cette derniere|"
     r"ces derniers|cependant|toutefois|neanmoins|en effet|par ailleurs|de plus|"
     r"ensuite|puis|enfin|egalement|c'est|cela|ceci|he|she|they|it|however|"
     r"a l'inverse|en revanche|d'ailleurs|pour autant|de son cote|quant a)\b", -4.0),
    # anaphore non résolue dans l'amorce (« Après avoir refusé, ce dernier a déclaré… »)
    (r"^.{0,70}?\b(?:ce dernier|cette derniere|ces derniers|celui-ci|celle-ci|"
     r"le remplacer|la remplacer|lui succeder|ce projet|ce role|cette scene|"
     r"ce personnage|cette version|ce choix|cette idee|ce refus|cette premiere|"
     r"cette improvisation|cette sequence|ce moment|ce passage|cet episode|"
     r"cet incident|cet accident|cette decision|ce changement|cette technique|"
     r"this scene|this sequence|this decision)\b", -4.0),
    # amorce sans sujet nommé : acceptable mais moins bon qu'un nom propre
    (r"^(?:le film|the film|le tournage|le realisateur|l'acteur|l'actrice)\b", -1.0),
]

BONUS = [(fam, re.compile(p, re.I), w) for fam, p, w in BONUS]
MALUS = [(re.compile(p, re.I), w) for p, w in MALUS]


# Abréviations à protéger du découpage en phrases.
ABREV = [
    "M.", "Mme.", "Mlle.", "Dr.", "Pr.", "St.", "Ste.", "Mr.", "Mrs.", "Ms.", "Jr.", "Sr.",
    "etc.", "cf.", "env.", "ex.", "réf.", "vol.", "No.", "n°.", "av. J.-C.", "apr. J.-C.",
    "U.S.", "U.K.", "A.I.", "J.-C.",
]

_RE_REF = re.compile(r"\[\s*\d+\s*\]|\[\s*(?:note|n|réf\.?)[^\]]{0,12}\]", re.I)
_RE_ESPACES = re.compile(r"[ \t   ]+")
_RE_PAREN_VIDE = re.compile(r"\(\s*\)|\[\s*\]")
# marqueurs de lien interlangue laissés par le rendu texte de fr.wikipedia : « … (en) »
_RE_INTERWIKI = re.compile(r"\s*\((?:en|de|es|it|pt|nl|ru|ja|zh|pl|sv)\)")
_RE_MODELE = re.compile(r"\{\{[^}]*\}\}")
_RE_BALISE = re.compile(r"<[^>]+>")


# ======================================================================================
# Nettoyage / découpage
# ======================================================================================
def _desaccentue(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def chemin_cache(lang, titre):
    h = hashlib.sha1(f"{lang}:{titre}".encode("utf-8")).hexdigest()[:16]
    return os.path.join(CACHE_DIR, f"{lang}_{h}.txt.gz")


def nettoie(texte):
    """Enlève balises, modèles wiki, appels de note, espaces insécables parasites."""
    t = _RE_BALISE.sub(" ", texte)
    t = _RE_MODELE.sub(" ", t)
    t = _RE_REF.sub("", t)
    t = t.replace(" ", " ").replace(" ", " ").replace(" ", " ")
    t = t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&quot;", '"')
    t = _RE_INTERWIKI.sub("", t)   # « … Anna Christie (en), jouée à Broadway »
    t = _RE_PAREN_VIDE.sub("", t)
    t = _RE_ESPACES.sub(" ", t)
    t = re.sub(r"\s+([,;:.!?])", r"\1", t)
    return t.strip()


def decoupe_phrases(texte):
    """Découpe en phrases, en protégeant abréviations, initiales et nombres décimaux."""
    t = texte
    for i, a in enumerate(ABREV):
        t = t.replace(a, f"\x00{i}\x00")
    # initiales isolées : « J. J. Abrams », « George A. Romero »
    t = re.sub(r"\b([A-ZÀ-Ý])\.(?=\s*[A-ZÀ-Ý])", "\\1\x01", t)
    # nombres décimaux anglais / numérotation « 1.5 »
    t = re.sub(r"(\d)\.(\d)", "\\1\x02\\2", t)

    morceaux = re.split(r"(?<=[.!?…])[ \n]+(?=[«\"'(A-ZÀ-Ý0-9])", t)

    phrases = []
    for p in morceaux:
        p = p.replace("\x01", ".").replace("\x02", ".")
        for i, a in enumerate(ABREV):
            p = p.replace(f"\x00{i}\x00", a)
        p = p.strip()
        if p:
            phrases.append(p)
    return phrases


def parse_sections(extrait):
    """`prop=extracts&explaintext` rend un texte avec des titres « == Section == ».

    Retourne [(titre_complet, poids, corps)] pour les seules sections retenues. Le titre
    complet inclut la section parente (« Production > Tournage ») pour le débogage.
    """
    lignes = extrait.split("\n")
    sections = []
    pile = {}          # niveau -> titre
    courant = None
    buf = []

    def ferme():
        if courant is not None and buf:
            sections.append((courant[0], courant[1], "\n".join(buf)))

    for ligne in lignes:
        m = re.match(r"^(={2,6})\s*(.+?)\s*\1\s*$", ligne)
        if m:
            ferme()
            buf = []
            niveau = len(m.group(1))
            titre = m.group(2).strip()
            pile = {k: v for k, v in pile.items() if k < niveau}
            pile[niveau] = titre
            chemin = " > ".join(pile[k] for k in sorted(pile))
            poids = poids_section(chemin, titre)
            courant = (chemin, poids) if poids else None
        else:
            if courant is not None:
                buf.append(ligne)
    ferme()
    return sections


def poids_section(chemin, titre):
    """Poids d'une section, 0 si on l'ignore. Une sous-section hérite du parent."""
    if SECTIONS_EXCLUES.match(_desaccentue(titre).lower().strip()):
        return 0.0
    chemin_n = _desaccentue(chemin).lower()
    titre_n = _desaccentue(titre).lower()
    # hors sujet : le motif peut être n'importe où dans le chemin (une sous-section
    # « Différences avec le roman » sous « Production » reste hors sujet).
    if SECTIONS_HORS_SUJET.search(chemin_n):
        return 0.0
    meilleur = 0.0
    for motif, poids in SECTIONS_POIDS:
        motif_n = _desaccentue(motif)
        if re.search(motif_n, titre_n) or re.search(motif_n, chemin_n):
            meilleur = max(meilleur, poids)
    return meilleur


# ======================================================================================
# SCORING — le seul endroit à remplacer pour un raffinement LLM
# ======================================================================================
def _score_interet(phrase, ctx=None):
    """Note le potentiel « croustillant » d'une phrase. Plus haut = meilleur hook.

    C'EST LE POINT D'EXTENSION LLM. Contrat à respecter si on le remplace :
        entrée  : `phrase` (str, déjà nettoyée) ; `ctx` (dict optionnel) avec au moins
                  {"title", "year", "director": [..], "cast": [..], "section", "poids"}
        sortie  : float. Négatif ou ~0 = à jeter, > 4 = bon candidat.
    Rien d'autre dans le pipeline ne dépend de l'implémentation. Une version LLM peut
    donc être branchée en changeant uniquement cette fonction (idéalement en la rendant
    batchée, cf. `meilleurs_candidats` qui l'appelle phrase par phrase).

    Heuristiques actuelles, dans l'ordre d'importance :
      1. auto-suffisance (une anecdote doit se comprendre seule, hors contexte) ;
      2. marqueurs narratifs (refus, improvisation, accident, secret, record…) ;
      3. présence de noms propres / de personnes du film ;
      4. malus sur le factuel administratif, les scores d'agrégateurs, les listes ;
      5. longueur : la phrase doit tenir dans une carte de l'app.
    """
    ctx = ctx or {}
    n = len(phrase)
    if n < 55 or n > 340:
        return -10.0
    # fragment : une phrase qui ne commence pas par une majuscule (ou un chiffre / une
    # ouverture de citation) est un morceau mal découpé, inutilisable tel quel.
    if not (phrase[0].isupper() or phrase[0].isdigit() or phrase[0] in "«\"'"):
        return -10.0

    p = _desaccentue(phrase).lower()
    score = 0.0

    # --- 1. marqueurs, par famille avec rendements décroissants -------------------------
    par_famille = {}
    for famille, motif, poids in BONUS:
        if motif.search(p):
            par_famille.setdefault(famille, []).append(poids)
    for poids in par_famille.values():
        poids.sort(reverse=True)
        score += poids[0] + 0.35 * sum(poids[1:])
    for motif, poids in MALUS:
        if motif.search(p):
            score += poids
    # une famille isolée = souvent un faux positif ; deux familles = vraie histoire
    touches = len(par_famille)
    if touches >= 2:
        score += 1.4
    if touches == 0:
        score -= 2.5

    # --- 2. auto-suffisance ------------------------------------------------------------
    # noms propres en milieu de phrase (hors début) => la phrase nomme ses acteurs
    propres = re.findall(r"(?<![.!?]\s)(?<!^)\b[A-ZÀ-Ý][a-zà-ÿ]{2,}\b", phrase)
    if propres:
        score += min(len(set(propres)), 3) * 0.55
    else:
        score -= 1.5

    # pronom sans antécédent : un « il / elle » qui arrive AVANT le premier nom propre
    # de la phrase renvoie à quelque chose qui n'est pas dans le hook. Règle générale,
    # plus fiable que d'énumérer les amorces fautives une par une.
    # On ignore le tout premier mot (souvent « Lorsque », « Après »… — une majuscule de
    # début de phrase n'est pas un nom propre) et on accepte les capitales internes
    # (« DiCaprio », « McAdams »), sinon on pénalise à tort les meilleures phrases.
    apres_1er_mot = phrase.partition(" ")[2]
    decalage = len(phrase) - len(apres_1er_mot)
    m_pron = re.search(r"\b(?:il|elle|ils|elles|he|she|they)\b", p)
    m_propre = re.search(r"\b[A-ZÀ-Ý][\wà-ÿ'’-]*[a-zà-ÿ]{2}", apres_1er_mot)
    if m_pron and (not m_propre or m_pron.start() < m_propre.start() + decalage):
        score -= 2.6

    # noms du film (réalisateur / casting) : ancre la phrase sur CE film et signale que
    # l'anecdote concerne une tête d'affiche, pas un second rôle oublié.
    noms = []
    for cle in ("director", "cast"):
        for nom in (ctx.get(cle) or [])[:6]:
            noms.extend(part for part in nom.split() if len(part) > 3)
    if noms:
        vus = sum(1 for part in set(noms) if _desaccentue(part).lower() in p)
        score += min(vus, 2) * 1.3

    # --- 3. propreté -------------------------------------------------------------------
    parentheses = phrase.count("(")
    score -= max(0, parentheses - 1) * 1.2
    virgules = phrase.count(",")
    if virgules >= 5:
        score -= (virgules - 4) * 0.7          # énumération
    if phrase.count(";") >= 2:
        score -= 1.5
    if re.search(r"\b(?:et|and)\b.*\b(?:et|and)\b.*\b(?:et|and)\b", p):
        score -= 1.0
    if not phrase.rstrip().endswith((".", "!", "?", "…", "»", '"')):
        score -= 2.5                            # phrase tronquée
    # guillemets déséquilibrés = citation coupée en plein milieu, illisible sur une carte.
    # On vérifie aussi l'ORDRE : un « » » qui précède son « « » signale un morceau de
    # citation arraché au paragraphe voisin.
    ouvre, ferme = phrase.find("«"), phrase.find("»")
    if (phrase.count('"') % 2 or phrase.count("«") != phrase.count("»")
            or (ferme != -1 and (ouvre == -1 or ferme < ouvre))):
        score -= 3.0

    # --- 4. longueur (cloche douce autour de 150 signes) --------------------------------
    if 90 <= n <= 230:
        score += 1.0
    elif n > 290:
        score -= 1.0

    # --- 5. poids de la section --------------------------------------------------------
    score *= ctx.get("poids", 1.0)
    return round(score, 2)


# ======================================================================================
# Réseau
# ======================================================================================
class Wiki:
    def __init__(self, delai=DELAI):
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": UA, "Accept-Encoding": "gzip"})
        self.delai = delai
        self.appels = 0

    def get(self, url, **params):
        params.setdefault("format", "json")
        params.setdefault("formatversion", 2)
        for essai in range(3):
            try:
                time.sleep(self.delai)
                self.appels += 1
                r = self.s.get(url, params=params, timeout=TIMEOUT)
                if r.status_code in (429, 503):
                    time.sleep(2 + 3 * essai)
                    continue
                r.raise_for_status()
                return r.json()
            except Exception as e:
                if essai == 2:
                    print(f"    ⚠ réseau : {type(e).__name__} {e}")
                    return None
                time.sleep(1.5 * (essai + 1))
        return None

    # --- Wikidata : imdb_id -> Q-id ----------------------------------------------------
    def qid_par_imdb(self, imdb_id):
        d = self.get(WIKIDATA_API, action="query", list="search",
                     srsearch=f'haswbstatement:"P345={imdb_id}"', srlimit=1)
        if not d:
            return None
        res = d.get("query", {}).get("search", [])
        return res[0]["title"] if res else None

    # --- Wikidata : Q-ids -> titres de pages fr/en (par lots de 50) ---------------------
    def sitelinks(self, qids):
        out = {}
        for i in range(0, len(qids), 50):
            lot = qids[i:i + 50]
            d = self.get(WIKIDATA_API, action="wbgetentities", ids="|".join(lot),
                         props="sitelinks", sitefilter="frwiki|enwiki")
            if not d:
                continue
            for qid, ent in (d.get("entities") or {}).items():
                liens = ent.get("sitelinks") or {}
                out[qid] = {
                    "fr": (liens.get("frwiki") or {}).get("title"),
                    "en": (liens.get("enwiki") or {}).get("title"),
                }
        return out

    # --- Wikipédia : texte brut d'un article (mis en cache sur disque) -------------------
    def extrait(self, lang, titre):
        chemin = chemin_cache(lang, titre)
        if os.path.exists(chemin):
            try:
                with gzip.open(chemin, "rt", encoding="utf-8") as f:
                    return f.read() or None
            except Exception:
                pass
        d = self.get(WIKI_API.format(lang=lang), action="query", prop="extracts",
                     explaintext=1, redirects=1, titles=titre)
        if not d:
            return None
        pages = d.get("query", {}).get("pages") or []
        if not pages or pages[0].get("missing"):
            return None
        txt = pages[0].get("extract") or None
        if txt:
            os.makedirs(CACHE_DIR, exist_ok=True)
            with gzip.open(chemin, "wt", encoding="utf-8") as f:
                f.write(txt)
        return txt

    # --- Repli : recherche par titre ----------------------------------------------------
    def cherche(self, lang, requete, limite=5):
        d = self.get(WIKI_API.format(lang=lang), action="query", list="search",
                     srsearch=requete, srlimit=limite)
        if not d:
            return []
        return [r["title"] for r in d.get("query", {}).get("search", [])]


# ======================================================================================
# Résolution de la page + extraction
# ======================================================================================
def verifie_page(extrait, film):
    """Repli titre uniquement : l'article parle-t-il bien de CE film ?

    Exige l'année (± 1 an, les articles citent parfois l'année de production) ET au moins
    un nom du réalisateur, sinon on refuse — un faux positif vaut moins que rien.
    """
    if not extrait:
        return False
    txt = _desaccentue(extrait[:6000]).lower()
    annee = film.get("year")
    ok_annee = False
    if annee and str(annee).isdigit():
        a = int(annee)
        ok_annee = any(str(a + d) in txt for d in (-1, 0, 1))
    realisateurs = film.get("director") or []
    ok_real = any(_desaccentue(nom).lower() in txt for nom in realisateurs if len(nom) > 4)
    if realisateurs:
        return ok_annee and ok_real
    return ok_annee and _desaccentue(film["title"]).lower() in txt


def sources(w, film, cache_qid, avec_en=True):
    """Articles utilisables pour ce film, FR d'abord : [(lang, titre, extrait, methode)].

    L'article EN n'est chargé que si on le demande (`avec_en`) : l'appelant ne descend
    sur l'anglais que quand le meilleur candidat français est trop faible, ce qui évite
    une requête inutile sur les ~80 % de films correctement documentés en français.
    """
    trouves = []
    qid = cache_qid.get(film.get("imdb_id"))
    if qid:
        for lang in ("fr", "en"):
            if lang == "en" and not avec_en:
                continue
            titre = qid.get(lang)
            if not titre:
                continue
            ext = w.extrait(lang, titre)
            if ext:
                trouves.append((lang, titre, ext, "wikidata"))
        return trouves

    # --- repli par titre, avec vérification -------------------------------------------
    annee = film.get("year") or ""
    langues = ("fr", "en") if avec_en else ("fr",)
    for lang in langues:
        gabarits = [f'intitle:"{film["title"]}" film {annee}',
                    f'{film["title"]} film {annee}']
        trouve = False
        for req in gabarits:
            if trouve:
                break
            for titre in w.cherche(lang, req, 4):
                ext = w.extrait(lang, titre)
                if verifie_page(ext, film):
                    trouves.append((lang, titre, ext, "titre+vérif"))
                    trouve = True
                    break
    return trouves


def a_des_sections(extrait):
    return bool(parse_sections(extrait))


def meilleurs_candidats(extrait, film, n=3):
    """Phrases les mieux notées de l'article, dédoublonnées."""
    ctx_base = {
        "title": film.get("title"),
        "year": film.get("year"),
        "director": film.get("director") or [],
        "cast": film.get("cast") or [],
    }
    notes = []
    for chemin, poids, corps in parse_sections(extrait):
        for para in corps.split("\n"):
            para = nettoie(para)
            if len(para) < 60:
                continue
            phrases = [nettoie(p) for p in decoupe_phrases(para)]
            ctx = dict(ctx_base, section=chemin, poids=poids)
            # On teste des FENÊTRES de 1 à 3 phrases consécutives : sur Wikipédia,
            # l'anecdote est souvent étalée (« … le scénario ne prévoyait pas ce moment.
            # Heath Ledger a improvisé. »). Une fenêtre résout aussi les anaphores, la
            # phrase de tête fournissant l'antécédent. Chaque phrase en plus coûte un
            # malus fixe pour ne pas favoriser mécaniquement les fenêtres longues.
            for i in range(len(phrases)):
                for taille in (1, 2, 3):
                    if i + taille > len(phrases):
                        break
                    fenetre = " ".join(phrases[i:i + taille]).strip()
                    if len(fenetre) > 340:
                        break
                    s = _score_interet(fenetre, ctx) - 1.1 * (taille - 1)
                    if s > 0:
                        notes.append({"hook": fenetre, "score": round(s, 2),
                                      "section": chemin})

    notes.sort(key=lambda x: -x["score"])
    # Dédoublonnage par recouvrement de vocabulaire : les fenêtres glissantes produisent
    # des candidats qui se contiennent les uns les autres, il faut 3 anecdotes DIFFÉRENTES.
    retenus, sacs = [], []
    for c in notes:
        mots = set(re.findall(r"\w{4,}", _desaccentue(c["hook"]).lower()))
        if not mots:
            continue
        if any(len(mots & s) / min(len(mots), len(s)) > 0.45 for s in sacs):
            continue
        sacs.append(mots)
        retenus.append(c)
        if len(retenus) >= n:
            break
    return retenus


# ======================================================================================
# Pilotage
# ======================================================================================
def charge_films(limite=None):
    with open(MOVIES, encoding="utf-8") as f:
        films = json.load(f)
    # « les plus populaires » = les plus connus : on prend la notoriété la plus fiable
    # disponible (votes IMDb, sinon votes TMDB), pas la popularité TMDB du jour qui est
    # biaisée vers les sorties de la semaine.
    films.sort(key=lambda m: -(m.get("imdb_votes") or (m.get("vote_count") or 0)))
    return films[:limite] if limite else films


def sauve(res):
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    os.replace(tmp, OUT)


def main():
    ap = argparse.ArgumentParser(description="Génère data/hooks.json (faits croustillants).")
    ap.add_argument("--limit", type=int, default=None,
                    help="ne traiter que les N films les plus connus")
    ap.add_argument("--force", action="store_true",
                    help="re-télécharger même les films déjà présents dans hooks.json")
    ap.add_argument("--delai", type=float, default=DELAI, help="délai entre requêtes (s)")
    ap.add_argument("--show", action="store_true", help="afficher les hooks obtenus")
    args = ap.parse_args()

    if not os.path.exists(MOVIES):
        sys.exit(f"❌ {MOVIES} introuvable — lance d'abord ingest.py.")
    os.makedirs(DATA_DIR, exist_ok=True)

    res = {}
    if os.path.exists(OUT) and not args.force:
        try:
            res = json.load(open(OUT, encoding="utf-8"))
        except Exception:
            res = {}

    films = charge_films(args.limit)
    todo = [m for m in films if args.force or str(m["id"]) not in res]
    print(f"→ {len(films)} films visés, {len(todo)} à traiter "
          f"({len(films) - len(todo)} déjà en cache).")
    if not todo:
        print(f"✓ rien à faire. {OUT}")
        return

    w = Wiki(delai=args.delai)

    # Phase 1 — Wikidata : imdb_id -> Q-id -> titres de page (appariement exact) --------
    # Le résultat est persisté : c'est une correspondance stable, inutile de la repayer
    # à chaque --force (ce qui rend le re-scoring quasi gratuit en réseau).
    print("→ appariement Wikidata via l'identifiant IMDb...")
    os.makedirs(CACHE_DIR, exist_ok=True)
    map_path = os.path.join(CACHE_DIR, "_wikidata.json")
    cache_qid = {}
    if os.path.exists(map_path):
        try:
            cache_qid = json.load(open(map_path, encoding="utf-8"))
        except Exception:
            cache_qid = {}

    imdb_ids = [m["imdb_id"] for m in todo
                if m.get("imdb_id") and m["imdb_id"] not in cache_qid]
    qid_par_film = {}
    for i, iid in enumerate(imdb_ids, 1):
        q = w.qid_par_imdb(iid)
        if q:
            qid_par_film[iid] = q
        else:
            cache_qid[iid] = {}          # mémorise l'absence pour ne pas la re-chercher
        if i % 25 == 0:
            print(f"   {i}/{len(imdb_ids)} — {len(qid_par_film)} trouvés")
    liens = w.sitelinks(sorted(set(qid_par_film.values())))
    for iid, q in qid_par_film.items():
        cache_qid[iid] = liens.get(q, {})
    with open(map_path, "w", encoding="utf-8") as f:
        json.dump(cache_qid, f, ensure_ascii=False)
    print(f"   {sum(1 for v in cache_qid.values() if v.get('fr'))} pages FR, "
          f"{sum(1 for v in cache_qid.values() if not v.get('fr') and v.get('en'))} EN seules.")

    # Phase 2 — extraction + scoring ----------------------------------------------------
    ok = vide = perdu = 0
    for i, film in enumerate(todo, 1):
        mid = str(film["id"])
        # On tente le français seul ; si sa meilleure phrase est trop faible (article
        # court, section Production absente), on paie une requête de plus pour l'anglais
        # et on garde le meilleur des deux. Le français reste privilégié à score égal.
        lang = titre = methode = None
        cands = []
        for tour, avec_en in ((1, False), (2, True)):
            for lg, ttl, ext, meth in sources(w, film, cache_qid, avec_en=avec_en):
                if tour == 2 and lg == "fr":
                    continue                       # déjà évalué au tour 1
                c = meilleurs_candidats(ext, film)
                mieux = c and (not cands or c[0]["score"] > cands[0]["score"] + 1.0)
                if mieux:
                    cands, lang, titre, methode = c, lg, ttl, meth
                elif lang is None and (ttl or c):
                    lang, titre, methode = lg, ttl, meth
            if cands and cands[0]["score"] >= SEUIL_REPLI_EN:
                break

        if not titre:
            perdu += 1
            res[mid] = {"hook": None, "source_url": None, "score": 0.0,
                        "candidates": [], "title": film["title"],
                        "erreur": "aucune page Wikipédia vérifiée"}
        else:
            url = WIKI_URL.format(lang=lang, title=titre.replace(" ", "_"))
            if cands:
                ok += 1
            else:
                vide += 1
            res[mid] = {
                "hook": cands[0]["hook"] if cands else None,
                "source_url": url,
                "score": cands[0]["score"] if cands else 0.0,
                "candidates": cands,
                "title": film["title"],
                "year": film.get("year"),
                "lang": lang,
                "wiki_title": titre,
                "match": methode,
            }
        if i % SAVE_EVERY == 0 or i == len(todo):
            sauve(res)
            print(f"  {i}/{len(todo)} — {ok} avec hook, {vide} sans phrase retenue, "
                  f"{perdu} sans page  ({w.appels} requêtes)")

    sauve(res)
    print(f"\n✓ écrit {OUT} — {len(res)} films, {ok}/{len(todo)} avec hook.")

    if args.show:
        for film in films:
            e = res.get(str(film["id"]))
            if not e:
                continue
            print(f"\n── {e.get('title')} ({e.get('year')})  [{e.get('match')}, "
                  f"{e.get('lang')}]  score {e.get('score')}")
            for c in e.get("candidates", []):
                print(f"   • [{c['score']:.1f}] {c['section']}\n     {c['hook']}")
            if not e.get("candidates"):
                print(f"   (rien — {e.get('erreur', 'aucune phrase au-dessus du seuil')})")


if __name__ == "__main__":
    main()
