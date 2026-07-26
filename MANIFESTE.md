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

**LE VERDICT — la valence DITE, pas devinée (26/07). Et pourquoi ce n'est PAS une note.**
La valence a toujours piloté le vecteur profil ; jusqu'ici elle était *devinée* du texte
par un lexique. Or ce lexique est un plancher assumé — mesuré à l'audit, il n'atteint
qu'une trentaine de valeurs distinctes, et deux ressentis très différents tombent souvent
sur la même. Martin a donc demandé « un endroit pour juger les films », et il a raison :

> Laisser la personne **déclarer** son verdict est strictement plus fiable que le déduire
> de ses mots.

Ce n'est pas ressusciter la note du §2, et la distinction est nette :
- une **note** est une *évaluation fine* (4 contre 4,5) qui produit un classement et ne
  dit pas quoi lancer ce soir — c'est ça qui est au cimetière ;
- le **verdict** est une *valence grossière* — cinq crans sémantiques, `adoré / aimé /
  bof / pas aimé / détesté` (+ `abandonné`), **jamais un chiffre affiché**. C'est
  exactement la quantité que le moteur calculait déjà, rendue explicite.

Deux garde-fous pour que ça ne dérive pas vers la note :
- **le texte reste primordial.** Le verdict ne remplace QUE la devinette de valence ; il
  ne remplace pas le texte, qui seul porte *ce que tu regardes* (tes axes). Un verdict
  sans texte est plus pauvre qu'un texte sans verdict.
- **aucun agrégat, aucun classement, aucune moyenne affichée.** Le verdict vit sur
  l'arête, comme une propriété de la paire. On ne calcule jamais « ta note moyenne ».

Détail d'implémentation : `aretes.VERDICTS` mappe les crans sur `[-1, 1]`, `valence_de()`
prend le verdict quand il existe et retombe sur le lexique sinon — donc les arêtes
anciennes, sans verdict, gardent exactement leur comportement.

## 5. Le dither est le langage entier de l'app

Un seul geste esthétique — la révélation — décliné en trois moments de jeu :

1. **Le choix à l'aveugle** : les trois cartes montrent leurs ARGUMENTS ; les films
   restent tramés. Tu choisis une direction → le film se révèle. Tue le préjugé d'affiche
   et d'époque (tu n'aurais jamais cliqué un noir-et-blanc de 1957 — mais « huis clos où
   un seul juré retourne onze convaincus », si). Le reveal suit un engagement : il reste
   signifiant soir après soir. (Défaut ou option : §9.)
2. **Les portraits du canon** : réals/acteurs se dé-pixelisent à mesure que tu vois leurs
   films essentiels. Conséquence visible de ta vie de spectateur — pas un objectif chiffré.
3. **Ton portrait** : MORDU te rend qui tu es — tiré de ce que tu as ÉCRIT, pas de ce
   que tu as compté. Qualitatif là où Letterboxd (Year in Review) est quantitatif.

   **Deux objets distincts, et il a fallu la remarque de Martin pour le voir (21/07 :
   « l'empreinte ne dit rien de moi ») :**
   - ~~**L'EMPREINTE**~~ — **MORTE LE 22/07, et c'est la leçon la plus dure du projet.**
     Un audit externe a porté un argument testable : *une rotation orthogonale de
     l'espace conserve tous les cosinus, donc toutes les recommandations, et produit un
     glyphe totalement différent.* Mesuré :

     ```
     écart max sur les 6000 similarités : 3,3e-16   le modèle est LE MÊME
     ordre complet des 6000 films       : identique
     cellules du glyphe qui changent    : 90,4 %
     ```

     Le repli « c'est une signature, pas un portrait » ne tenait pas non plus : en
     ajoutant 20 films PRIS DANS SON PROPRE GOÛT, le glyphe s'éloignait de lui-même de
     0,663 — contre 0,794 pour un inconnu. **83 % du chemin vers quelqu'un d'autre.**
     Une signature doit être stable pour la même personne.

     **Elle n'a PAS été remplacée, et c'est la bonne réponse.** L'atlas construit pour
     prendre sa place a été enterré le jour même (§8) : il était honnête et inutile.
     Ce qui reste sur « Mon profil » est ce qui se LIT — le portrait en une phrase, tes
     mots, tes arêtes brutes — plus **la carte du goût**, qui, elle, n'a jamais rien
     prétendu de plus que ce qu'elle est.

     Le désir derrière l'empreinte — *voir comment j'ai évolué* — reste donc SANS RÉPONSE,
     et on l'assume. Mieux vaut un manque nommé qu'un objet qui le comble en trompant.
     À rouvrir vers trente ressentis, quand il y aura vraiment quelque chose à voir.

     > **La règle qui en sort, et qui vaut pour tout le produit :** toute représentation
     > du goût doit pouvoir être reliée à un film, une scène ou une phrase — jamais
     > seulement à une disposition arbitraire de nombres.
   - **LE PORTRAIT** est ce qui se *lit* : la projection des ressentis sur des axes
     NOMMÉS (atmosphère, image, rythme, intrigue, personnages, ambiguïté morale,
     émotion, son, construction, mise en scène). C'est le §4 appliqué — « ce que tu
     MENTIONNES est ton axe d'attention ».

   Le signal le plus fort n'est pas ce dont on parle le plus, **c'est ce dont on ne
   parle JAMAIS** : deux personnes peuvent adorer les mêmes films sans y regarder du
   tout la même chose. La phrase le dit explicitement.

   **LA DÉRIVE — le troisième objet, et le seul qui vaille vraiment (22/07).** Martin :
   « j'aime bien le principe de l'empreinte parce que ça dit qui tu es et comment tu as
   ÉVOLUÉ dans le temps, si tu t'es adouci, grandi — c'est pour ça que j'aime le truc
   dessin, parce que ça évolue ; alors que le portrait c'est un peu nul, pas original ».
   Il a raison, et le diagnostic est net : **la signature et le portrait décrivent tous
   les deux un INSTANTANÉ.** N'importe qui peut se voir écrire « tu regardes l'image ».
   Personne ne peut se voir écrire SA trajectoire.

   La dérive ne coûte aucun stockage : les arêtes sont horodatées et append-only (§4),
   donc l'histoire est déjà là.

   **PREMIÈRE VERSION JETÉE LE JOUR MÊME, et c'est la leçon la plus chère du projet.**
   Elle mesurait quatre choses (cap en degrés, ouverture, audace, attention) et rendait
   un verdict en français. Passée sur 40 historiques **tirés au hasard** — films au
   hasard, textes au hasard, registres au hasard :

   ```
   verdict non nul                       40/40   à n = 4, 8, 12 et 20
   « tu t'es élargi »                    60/60
   « tu parlais de X, tu parles de Y »   52/60
   « tu oses davantage »                 35/60
   ```

   Elle ne se taisait que parce qu'il n'y avait que 2 arêtes ; elle se serait armée à la
   3ᵉ. Les causes sont structurelles :

   > **Le profil cumulé est une moyenne. Il converge par construction, et il est
   > INVARIANT À L'ORDRE — il ne peut donc contenir aucune information temporelle.**

   Tout le reste en découle. L'ouverture monte mécaniquement dès qu'on ajoute un film ; un
   cap en degrés mesure la dilution d'un barycentre (témoin : un film **au hasard** fait
   tourner le profil de 20,9° en médiane, le premier vrai ressenti l'a fait tourner de
   19,9° — le 30ᵉ percentile du bruit) ; la sinuosité décroît en k^-0,5 pour l'humanité
   entière. C'étaient des constantes déguisées en mesures.

   **Ce qui reste, et qui tient :**

   | mesure | l'idée | pourquoi elle est vraie |
   |---|---|---|
   | **la braise** | deux profils au lieu d'un — celui de TOUJOURS, et celui de MAINTENANT (demi-vie 30 j). Le rouge est posé là où ils tombent sur des paliers différents | le profil récent, lui, ne converge jamais. Il naît vide, il grandit avec la vie |
   | **le silence rompu** | un axe dont tu n'avais JAMAIS parlé et dont tu viens de parler | c'est un ÉVÉNEMENT daté, pas une tendance : pas d'hypothèse nulle, donc pas de faux positif. Et ce sont TES mots |
   | **le témoin du pas** | chaque film comparé à 400 films au hasard depuis le même état | « ce film t'a moins déplacé que 93 % des autres » est vérifiable ; « tu as tourné de 14° » ne veut rien dire |

   **Et la rampe de finesse de l'empreinte est morte avec.** Le glyphe agrégeait par blocs
   et gagnait des paliers selon le NOMBRE d'arêtes : à goût strictement identique, jusqu'à
   **82,6 %** de la grille changeait de couleur. L'artefact était plus gros que le signal —
   c'était une jauge de complétion dessinée en pixels, soit le §8 en douce. Un test
   verrouille désormais l'inverse : ajouter des arêtes qui ne déplacent pas le vecteur ne
   doit changer **aucune** cellule.

   **La règle qui sort de tout ça, et qui vaut pour toute mesure future :**

   > Aucune phrase dont l'hypothèse nulle n'a pas été testée sur ces données-là.
   > Une évolution inventée serait la pire trahison possible du produit.

Pas de jauges, pas de badges, pas de streaks. Le rythme de l'app est indexé sur ta vraie
vie de spectateur — l'anti-Duolingo, assumé.

**LA RÈGLE DU TRAMAGE (21/07, après remarque de Martin : « c'est trop homogène »).**
Le dither ne s'applique QUE lorsqu'une image doit être CACHÉE :

> **Tramé = ce qui t'est encore caché. Net = ce que tu connais déjà.**

Il reste donc sur les 3 cartes aveugles et sur les portraits de domaines — là il porte
une mécanique. Il est retiré de la recherche, de la boîte aux lettres, des voisins du
profil et des fiches : là il était décoratif, et dans la recherche carrément nuisible
(on cherche un film qu'on connaît, le tramer ne cachait rien et gênait). Mettre du
dither partout contredisait la force même de cette DA — être porteuse, pas décorative —
et écrasait le contraste qui lui donne son sens.

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

- **L'ATLAS (22/07, mort le jour de sa naissance)** — et c'est la meilleure entrée de ce
  cimetière, parce que la cause est nommée par Martin lui-même :

  > « Trop abstrait. Ça ne fait que mettre des points, ça ne bouge pas. Faire un truc
  > original et bizarre juste pour le dire, parce qu'en vrai ça ne sert à rien. »

  Construit pour remplacer l'empreinte, qu'une rotation orthogonale avait démasquée. Il
  était, lui, rigoureusement honnête : contenu invariant par rotation, aucun pixel sans
  cause, aucune légende qui ne passe son hypothèse nulle. Il a été mesuré sous toutes les
  coutures — et il ne servait à rien.

  **La leçon, et elle vaut pour tout le reste :** vérifier qu'une chose est VRAIE ne dit
  rien sur son droit d'exister. Une journée entière à rendre une image honnête, sans
  jamais demander à quoi elle sert. Le test qu'elle échouait est simple et il aurait dû
  venir en premier :

  > **Est-ce que ça aide à choisir un film ce soir, ou est-ce que ça change ce que
  > l'oracle tire ? Si non, ça n'a pas sa place.**

  Aggravant : le produit dit « tu ne choisis pas parmi des milliers, tu déclares une
  envie ». L'atlas étalait les 6000 films sous les yeux. C'était le catalogue rentré par
  la porte de derrière, en plus joli.

  Ce qui SURVIT et qu'on ne touche pas : la **carte du goût** du profil. Elle ne prétend
  rien de plus que ce qu'elle est, et son abstraction est le plancher du problème — on ne
  peut pas faire mieux en projetant 384 dimensions sur un plan.
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
- ~~Cold start~~ **RÉSOLU (21/07)** : l'onboarding demande désormais **5 films ET une
  description par film** (min. 15 caractères), et écrit de vraies arêtes. La v1 ne
  gardait que les titres — Martin l'a constaté à l'usage : ses 3 graines muettes ne
  pesaient rien et son unique ressenti écrit tirait tout le profil vers l'anime.
  Mesuré : 5 films décrits donnent 5 arêtes, un portrait « fiable » dès le jour 1,
  une empreinte à 42 % de finesse (contre 17 %) et des motifs cohérents au lieu de
  dispersés. Les graines muettes existantes peuvent être complétées depuis le profil,
  sans rien effacer. L'import CSV Letterboxd reste jugé non viable (friction).

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
