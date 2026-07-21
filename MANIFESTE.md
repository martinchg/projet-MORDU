# MORDU — Manifeste de l'oracle

> Ce doc grave la philosophie du produit, issue de la session de cadrage du 20/07/2026.
> Usage : (1) relire pour trier ce qu'on garde/retire, (2) s'armer contre toute objection.
> Règle : une décision inscrite ici ne se re-débat pas en passant — on rouvre le manifeste,
> on tranche, on le met à jour. Sinon c'est du drift.

## 1. La phrase

**MORDU ne te montre pas un catalogue. Il te tend trois films — trois directions, trois
arguments. Tu ne choisis pas un film parmi des milliers : tu déclares ton envie du soir.**

k=3, axes orthogonaux OBLIGATOIRES (jamais trois thrillers — sinon c'est un mini-menu).
Pas de liste, pas de recherche, pas de re-tirage, pas de 4ᵉ carte. Chaque carte est un
mini-pitch sur un axe distinct (« l'univers Fincher mais un rythme plus sec, porté par X
primé à Cannes ») — jamais un « parce que vous avez regardé… ».

> Historique : la v1 de cette phrase était k=1 (« LE prochain, un seul »). Tuée le jour
> même par l'objection du re-tirage (« pas ce soir » répété = un menu ralenti) — réponse
> de Martin : 3 directions orthogonales. Le choix entre trois axes n'est pas un classement
> de films : c'est une déclaration d'humeur, l'information que l'oracle ne peut pas
> deviner. Et un raté est co-signé (tu as choisi ta direction) → la confiance survit,
> là où chaque raté k=1 était 100 % la faute de l'oracle.

## 2. D'où ça vient (les douleurs fondatrices — les tiennes)

Chaque décision du produit répond à un rejet que TU as formulé. C'est ta légitimité :

- **« Impossible de trancher entre Seven et Mononoké. »** Le versus (« ça ou ça ») fabrique
  de faux négatifs : rejeter un chef-d'œuvre qu'on adore parce qu'on a été forcé de choisir.
  Le ranking par préférence est le mauvais cadre : tu ne *classes* pas le cinéma, tu le *tiens*.
- **« Mettre 4 et 4,5 ne dit pas lequel j'ai envie de regarder. »** Une note est une
  *évaluation* (à quel point c'est bon), pas une *envie* (qu'est-ce que je veux ce soir).
  Netflix a tué ses étoiles en 2017 pour cette raison exacte.
- **« Ma liste "à regarder" ne fait que s'allonger. »** La watchlist est une dette qui
  culpabilise. Elle réintroduit le choix ET la charge mentale. C'est la maladie, pas le remède.
- **« Aimer ce qu'on "doit" aimer, regarder ce qu'on "doit" regarder. »** La cinéphilie-
  checklist est détestable. Pas-vu ≠ ignorant. Un canon peut inviter, jamais endetter.
- **« J'écrirais pour moi, pas pour les autres. »** Les critiques publiques sont un acte
  social. Le ressenti MORDU est un acte égoïste : il paie en meilleure reco suivante.

## 3. La boucle (le rituel)

```
ORACLE (3 cartes, axes orthogonaux : arguments + [terrain connu | pari annoncé])
   → tu choisis ta DIRECTION (≠ choisir un film ; non-choisi ≠ rejeté,
     JAMAIS en disliked_ids — piège hérité de l'onboarding versus, interdit ici)
   → tu regardes
   → SERRURE : tu racontes ton ressenti (condition du tirage suivant)
   → l'arête (toi, film, texte, date) est stockée, brute, à jamais
   → ton profil se raffine
   → ORACLE suivant
```

- La **serrure** accepte tout état honnête : « détesté », « abandonné à 40 min », « pas eu
  le temps » sont des clés valides — et des signaux précieux. L'oracle ne punit jamais
  l'honnêteté, seulement le silence. Minimum : une phrase. La profondeur est récompensée
  (meilleure reco), jamais exigée.
- L'**accroche** est l'organe de confiance : un oracle sans liste de repli doit argumenter
  son choix. Fait croustillant (tournage, réal, anecdote) extrait de Wikipédia par LLM,
  pré-généré offline (`hooks.json`).
- L'**exploration est annoncée** : l'oracle a mandat pour te sortir de ta zone (tempéré ou
  total), mais il le DIT. Un pari étiqueté qui rate coûte peu ; le même pari muet tue la
  confiance. Explore/exploit rendu honnête par l'UI — c'est un trait de caractère.
- **La ligne invitation/dette** (réponse de Martin, à graver) : l'invitation part de TES
  arêtes vers l'extérieur (« tu as aimé 12 hommes en colère → Témoin à charge ») ; la
  dette descend d'une liste absolue vers toi (« il FAUT avoir vu Citizen Kane »). MORDU
  ne fait QUE des invitations : toute exploration est ancrée dans une arête existante,
  jamais dans un canon abstrait.

## 4. Le modèle de données (l'idée théorique centrale)

Un ressenti n'est une propriété **ni de la personne, ni du film** : c'est une propriété de
la **paire** — une arête d'un graphe biparti personnes—films, avec du texte dessus.

- Une seule critique confond la personne et le film (« humour noir » : c'est toi ou c'est
  Fight Club ?). On démêle par **triangulation** : la personne = ce qui est invariant à
  travers SES arêtes ; le film = ce qui est invariant à travers les arêtes de TOUS.
- C'est la structure de la factorisation matricielle, avec du texte (riche) à la place
  d'un scalaire (pauvre). Champ de recherche existant : McAuley et al., texte → facteurs.
- **Ce que tu mentionnes** compte autant que la valence : parler d'ambiguïté morale sur
  Seven et de satire sur Fight Club, jamais du rythme — c'est TON axe d'attention. Ton
  goût, c'est ce que tu regardes *dans* les films.
- Stockage : arêtes brutes en append-only, JAMAIS fusionnées à l'écriture. Les profils
  (personne, film) sont des agrégats recalculables. Pas de DB avant que ça le mérite.

## 5. Le dither est le langage entier de l'app

Un seul geste esthétique — la révélation — décliné en trois moments de jeu :

1. **Le choix à l'aveugle** : les trois cartes montrent leurs ARGUMENTS ; les films
   restent tramés. Tu choisis une direction → le film se révèle. Tue le préjugé d'affiche
   et d'époque (tu n'aurais jamais cliqué un noir-et-blanc de 1957 — mais « huis clos où
   un seul juré retourne onze convaincus », si). Le reveal suit un engagement : il reste
   signifiant soir après soir. (Défaut ou option : §9.)
2. **Les portraits du canon** : réals/acteurs se dé-pixelisent à mesure que tu vois leurs
   films essentiels. Conséquence visible de ta vie de spectateur — pas un objectif chiffré.
3. **Ton portrait (le « Wrapped »)** : tous les N films, MORDU te rend qui tu es — tiré de
   ce que tu as ÉCRIT, pas de ce que tu as compté. Qualitatif là où Letterboxd (Year in
   Review) est quantitatif. Sa seule raison d'exister est le portrait par le texte :
   personne d'autre n'a cette donnée.

Pas de jauges, pas de badges, pas de streaks. Le rythme de l'app est indexé sur ta vraie
vie de spectateur — l'anti-Duolingo, assumé.

## 6. La boîte aux lettres (PAS une watchlist)

Un pote te conseille un film, tu vois une bande-annonce, le film du soir est trop long →
tu le **donnes à l'oracle** et tu l'oublies. Différence structurelle : une watchlist est
une file que TU consultes pour choisir (retour du choix, retour de la dette) ; la boîte
est une **source que l'oracle pondère** (candidats bonus — c'est LUI qui décide quand leur
heure est venue). Règle d'airain : **on ne choisit jamais dedans.** Affichage : affiches
tramées, sans ordre, sans bouton.

## 7. Catéchisme — réponse à toute objection

**« La boucle avance trop lentement, personne ne reviendra mardi. »**
L'app n'est pas un feed où revenir : c'est un compagnon du moment où tu veux un film.
Sa cadence naturelle = ta cadence de visionnage (2-3×/semaine pour un cinéphile). C'est
une récurrence réelle et honnête — l'engagement indexé sur la vie, pas sur la dopamine.

**« La jauge de maîtrise fabrique du cinéma-checklist. »**
Il n'y a pas de jauge dans la boucle. Le canon est un ingrédient invisible de l'arbitrage,
pas un tableau de scores. L'app peut te servir un classique « parce qu'il te manque et que
t'es prêt » sans jamais te montrer une barre de complétion.

**« Une carte de ce que je connais, on s'y regarde une fois. »**
La carte n'est pas le produit ; la décision rendue l'est. Le miroir est un sous-produit
(les portraits), le service est le verdict du soir.

**« Le côté croisé (profils films par la foule) exige des users que tu n'as pas. »**
Assumé. Le produit vaut en single-player : mes arêtes suffisent à mon oracle. Le croisé est
une couche future, pas une condition. (Et les axes « foule » existent déjà : Tag Genome.)

**« Personne n'écrira de ressenti. »**
Personne n'écrit pour les autres, c'est vrai. Ici on écrit pour soi : le ressenti est le
ticket du prochain film, avec un payoff immédiat et égoïste. Et le minimum est une phrase.

**« Pourquoi pas juste demander à ChatGPT "quel film ce soir" ? »**
Un LLM nu n'a ni mémoire structurée de tes arêtes, ni catalogue discipliné, ni rituel, ni
enjeu de confiance — il te donne le film-consensus de ton prompt. MORDU accumule un actif
que le chat ne construit jamais : ton graphe de ressentis, qui rend chaque verdict meilleur
que le précédent. Le moat n'est pas le modèle, c'est la donnée d'arêtes + le rituel.

**« Netflix fait déjà ça. »**
Netflix optimise la rétention DANS son catalogue, avec un conflit d'intérêt structurel
(te faire rester, pas te faire grandir). MORDU est agnostique à la plateforme et optimise
ta relation au cinéma — y compris en te sortant de ta zone, en le disant.

**« Un film = 2h. Un verdict raté coûte trop cher pour déléguer le choix. »**
Les gens paient DÉJÀ le coût : 30-40 min de scroll pour souvent ne rien choisir (paradoxe
du choix). Et le raté est couvert : trois directions argumentées (l'erreur d'un soir est
co-signée — tu as choisi ton axe, la confiance survit), le pari annoncé quand l'oracle
explore, l'accroche qui argumente chaque carte.

**« Trois cartes, c'est déjà un menu — ton zéro-choix est mort. »**
Trois options orthogonales et argumentées ≠ un catalogue. Le paradoxe du choix naît de
l'abondance comparable (40 thrillers interchangeables) ; trois directions incomparables
sont une question (« t'as envie de quoi ? »), pas un rayonnage. Le choix porte sur TOI
(ton humeur), pas sur un classement de films — et le non-choisi n'est jamais un rejet.

**« Dès que le texte pilote la reco, on écrit pour diriger, pas pour dire (Goodhart). »**
Goodhart exige une divergence entre l'optimiseur et le bénéficiaire. En single-player,
c'est la même personne : « mentir » pour avoir des films rapides = déclarer qu'on veut
des films rapides. Diriger l'oracle, c'est l'utiliser. Seule vraie limite : se mentir à
soi (écrire le goût qu'on aimerait avoir) — et l'usage le corrige.

**« C'est une app de niche. »**
Oui. Side project, single-player d'abord, et la niche (cinéphiles fatigués du choix) est
la taille de Letterboxd. Une niche qui suffit largement à un produit solo — et à une ligne
de CV : recsys hybride + NLP + produit fini.

**« Écrire un ressenti à 23h45 après le film ? Jamais. »**
La serrure est asynchrone : le prochain verdict attend ton ressenti, pas l'inverse. Tu
écris le lendemain dans ton lit, dans le métro. Une phrase débloque ; la suite enrichit.

**« Le Wrapped existe déjà (Letterboxd Year in Review). »**
Le leur : des stats de comportement (combien, quoi, quand). Le nôtre : un portrait tiré du
texte (comment tu regardes). S'il dégénère en « stats de l'année en joli », il est mort —
d'où : la serrure ressenti est le cœur, c'est elle qui fabrique la donnée unique.

## 8. Le cimetière (écarté, et pourquoi — ne pas ressusciter en douce)

- **Le versus « ça ou ça »** : fabrique de faux négatifs entre chefs-d'œuvre orthogonaux.
- **Les étoiles/notes** : évaluation ≠ envie. Le texte porte les deux, et le pourquoi.
- **La watchlist classique** : dette + retour du choix. Remplacée par la boîte aux lettres.
- **Financement participatif de films** : marketplace two-sided + produit financier régulé
  (PSFP) — une boîte avec juriste, pas un side project data/ML. L'instinct derrière
  (« donner du poids aux vrais connaisseurs ») est gardé pour une couche future non
  financière, ou un autre projet.
- **« Devenir une énorme base de données »** : une DB est un moyen, pas un but. Les films
  utiles ~ dizaines de milliers → JSON + npy tiennent en RAM. Seuls des USERS justifieront
  une vraie DB.
- **NN d'embeddings users (NCF) sur MovieLens** : les embeddings users ne se transfèrent
  pas à un nouvel utilisateur (cold start réintroduit). Ce qu'on garde : les embeddings
  FILMS collaboratifs (transférables par moyenne), MF/ALS avant tout NN.
- **Scraper Letterboxd/IMDB/RT** : ToS, fragile. Les données propres existent : MovieLens
  (+ Tag Genome), Amazon Movies & TV, TMDB reviews, Wikipédia, export CSV Letterboxd (celui
  de l'user, consenti).
- **Jauges, badges, streaks** : le cinéma-devoir. Le seul « progrès » visible est visuel
  (la révélation) et indexé sur le réel.

## 9. Ouvert — à trancher À L'USAGE, pas en débat

- Choix à l'aveugle (arguments seuls, films tramés) : par défaut ou optionnel ? (Il faut
  bien savoir quoi taper dans la barre du streaming — révélation après le choix règle ça.)
- Si l'utilisateur choisit toujours le même axe : l'oracle fait-il tourner les deux
  autres ? (bandit léger — idée de Martin)
- Aucune des trois cartes ne tente : que se passe-t-il ? (nouvelle donne complète ? signal
  de profil ? — c'est le successeur de la question du re-tirage)
- Degré d'exploration : réglé par l'user (« ce soir, surprends-moi ») ou décidé par
  l'oracle ? Les deux ?
- N du Wrapped (tous les combien de films ?).
- Le ressenti vocal (dicter au lieu d'écrire) — baisse la friction de la serrure.
- **Le pari de l'oracle** (proposé, JAMAIS validé — à trancher). L'oracle ne se contente
  pas d'argumenter : il PRÉDIT ton ressenti (« je parie que la tension te tiendra plus que
  le dénouement »). Ton ressenti le note, et il affiche son track record (« il te connaît
  à 7/10 »). Intérêt : la série appartient à l'ORACLE, pas à toi — tu ne peux jamais être
  en retard ni échouer, c'est lui qui joue sa crédibilité. Ça donnerait l'anticipation
  d'un jeu sans la culpabilité d'un streak, et ça transformerait la serrure (corriger sa
  copie) en moment savoureux plutôt qu'en péage. Risque : une prédiction ratée trop
  souvent abîme le personnage.
- Cold start (le trou reconnu) : l'onboarding-arêtes (« cite 3 films adorés + une ligne
  sur pourquoi » = 3 arêtes riches jour 1) suffit-il ? L'import CSV Letterboxd est jugé
  non viable par Martin (friction). À valider en vrai.

## 10. La v0 — CONSTRUITE (21/07/2026)

Fait, testé de bout en bout dans le navigateur (57 tests dans `backend/tests_oracle.py`) :

1. **`GET /api/oracle`** — 3 cartes aux axes orthogonaux (`recommender/oracle.py`).
   Bandes en PERCENTILES (adaptatif à n'importe quel profil, pas de seuil en dur),
   orthogonalité garantie entre cartes, suites orphelines écartées, qualité en départage.
   Les cartes non choisies ne vont JAMAIS en `disliked_ids`.
2. **Arguments générés** — `<ce qui relie> mais <ce qui diffère>`, en français, moules
   variés. Ancre par réal / acteur / motif rare (pondéré IDF) avec repli de genre.
   Leçon apprise : la sémantique décide, l'ancre ne fait qu'argumenter — l'inverse
   sortait Transformers à un amateur de Miyazaki.
3. **Serrure** — `POST /api/choix` puis `POST /api/ressenti` → arêtes en JSONL
   append-only (`recommender/aretes.py`), valence dérivée du texte. Pas de tirage tant
   que le précédent n'est pas raconté.
4. **Écran du rituel** — `design/webclient/oracle.html` : choix à l'aveugle (affiches
   tramées, arguments lisibles) puis révélation animée du film choisi.
5. **Faits croustillants** — `recommender/hooks.py`, extraits de Wikipédia, film résolu
   via Wikidata P345 (identifiant IMDb) et non par titre. Les faits ternes (box-office)
   sont écartés au profit d'un candidat de repli.
6. **Canon en ingrédient invisible** — un essentiel n'est cité que si la personne est
   déjà dans tes arêtes (invitation), jamais depuis une liste absolue (dette).

7. **La boîte aux lettres** (§6) — on y dépose avec la provenance, on n'y choisit
   jamais ; l'oracle y puise délibérément (~30 %). Un simple bonus de score ne
   suffisait pas : un film conseillé peut être à 0.14 d'affinité sous sa bande.
8. **Les portraits reliés aux arêtes** — `/api/vus` (graines + arêtes) alimente les
   domaines. Les deux moitiés du produit se parlent enfin.
9. **Le pari de l'oracle** (§9) — il prédit ce que tu vas retenir, tu le notes, il
   tient son palmarès. La série appartient à la MACHINE : tu ne peux jamais échouer.
10. **Le moteur visuel** (`mordu.js`) — tramage en shader WebGL (un seul contexte),
    grain vivant, température par genre, révélation à 60 fps, fond de bruit qui dérive,
    titres qui se résolvent depuis des glyphes. Tout se résout depuis le bruit.

Reste à faire : le **Wrapped** (le portrait tiré de ce que tu écris — il lui faut des
dizaines d'arêtes, donc du temps, pas du code), la **projection Tag Genome** (qui
remplacera la valence lexicale), le **raffinement LLM des faits croustillants**
(~45 % accrochent, plafond des heuristiques atteint), et le **mobile Expo**, resté
sur ses films en dur.

**Juge de paix (objection 8, la seule sans réponse verbale possible) : v0 + trois semaines
d'usage réel par Martin. On compte les arêtes. C'est le test de l'homme qui existe.**

**Juge de paix (objection 8, la seule sans réponse verbale possible) : v0 + trois semaines
d'usage réel par Martin. On compte les arêtes. C'est le test de l'homme qui existe.**
