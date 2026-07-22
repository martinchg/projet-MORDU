# MORDU — audit technique externe

> **Mode d'emploi.** Copie-colle ce document entier dans Gemini. Il est autoportant :
> l'auditeur n'a accès ni au code, ni aux écrans, ni aux données. Les questions sont au
> §8, et elles sont volontairement dures.
>
> Il existe un autre brief, `AUDIT-EXTERNE.md`, orienté **produit** (le concept, la DA,
> les interdits). Celui-ci est orienté **méthode et statistique** : est-ce que ce que
> cette app affiche est *vrai* ?
>
> Le document contient deux avis de films écrits par l'auteur — c'est la seule donnée
> réelle du projet, et elle est nécessaire pour juger les mesures.

---

## 1. Le produit en dix lignes

MORDU tend **trois films, jamais plus**, aux axes obligatoirement orthogonaux (jamais
trois thrillers). Chaque carte annonce son **registre** — *terrain connu*, *pas de côté*,
*le pari* — et porte un argument de la forme « ce qui relie **mais** ce qui diffère ».
Le choix se fait **à l'aveugle** : les affiches sont tramées, seuls les arguments sont
lisibles. On choisit une **direction**, pas un film.

Après le visionnage, une **serrure** : il faut écrire ce qu'il en reste, en texte libre,
sinon le tirage suivant est bloqué. Ce texte devient une **arête** — un triplet
`(film, texte, date)` — stockée en append-only. Il n'y a **ni note, ni étoile, ni
watchlist** : c'est un rejet explicite, pas un oubli.

Aucun filtrage collaboratif : content-based pur, embeddings MiniLM 384D sur les synopsis
(6000 films), similarité cosinus. **Un seul utilisateur** (l'auteur), **2 arêtes**.
Projet solo, side project, à valeur de portfolio data/ML.

---

## 2. Le modèle de données, et pourquoi il compte pour l'audit

Le profil n'est **jamais stocké**. C'est une **vue recalculée** à la demande :

```python
profil(graines, aretes) = unit( Σ  1·v_i           # films déclarés au départ (« graines »)
                              + Σ  1,5·valence_j·v_j )   # films racontés (« arêtes »)
```

`valence` ∈ [-1, 1] est dérivée du texte par un **lexique de mots positifs/négatifs**
avec fenêtre de négation. Elle aussi est recalculée à la lecture.

Conséquence directe, et c'est le nœud de l'audit : **ce profil est une moyenne
pondérée. Il converge par construction, et il est invariant à l'ordre des arêtes.**

---

## 3. Ce que l'app affiche aujourd'hui

| écran | ce qu'il montre |
|---|---|
| **L'oracle** | les 3 cartes, l'argument, un fait vérifié tiré de Wikipédia, un « pari » sur ce que tu vas retenir |
| **Mon profil** | genres, motifs pondérés par rareté (IDF), vocabulaire, films voisins, un **portrait en une phrase**, une **empreinte** |
| **La carte du goût** | les 6000 films projetés en 2D (PaCMAP), territoires nommés par *lift* de mots-clés (HDBSCAN), ta position |
| **Ma dérive** | l'empreinte rejouée sur l'histoire réelle + ce qui a changé |

**L'empreinte** : le vecteur 384D replié en grille 24×16 — une cellule par dimension —
quantifié sur 11 couleurs. Les 384 dimensions sont **réordonnées** par regroupement
hiérarchique avec ordonnancement optimal des feuilles, pour que les corrélées soient
voisines (corrélation entre voisins : 0,079 → 0,242).

**Le portrait** : les textes projetés sur 10 axes nommés (atmosphère, image, rythme,
intrigue, personnages, ambiguïté morale, émotion, son, construction, mise en scène), par
lexique. Rend une phrase du type *« Tu regardes d'abord X et Y. Tu ne parles jamais de
Z — c'est ce silence qui te distingue le plus. »*

---

## 4. L'épisode central — à juger, c'est le cœur du brief

L'auteur a dit aimer l'empreinte **parce qu'elle évolue** (« si tu t'es adouci, grandi »).
Une page « ta dérive » a donc été construite, avec quatre mesures et un verdict en
français :

- **cap** : angle entre le vecteur d'alors et celui d'aujourd'hui ;
- **ouverture** : écart angulaire moyen entre le centre et les films ;
- **audace** : la bande (connu/écart/pari) où l'oracle avait rangé la carte choisie,
  première moitié contre seconde ;
- **attention** : les mots bruts, première moitié contre seconde.

Puis elle a été passée sur **40 historiques 100 % aléatoires** (films tirés au sort,
textes tirés au sort dans 5 phrases neutres, registres tirés au sort) :

```
verdict non nul                          40/40    à n = 4, 8, 12 et 20
« tu t'es élargi »                       60/60
« tu parlais de X, tu parles de Y »      52/60
« tu oses davantage »                    35/60

exemple produit sur du bruit pur :
  « Tu t'es élargi et tu oses davantage. Tu parlais du rythme, tu parles
    maintenant des personnages. »
```

Et un témoin, sur les vraies données : **ajouter un film AU HASARD** au profil de départ
le fait tourner de **20,9° en médiane** (p5–p95 : 18,0–23,6°). Le premier vrai ressenti de
l'auteur l'a fait tourner de **19,9°** — le **30ᵉ percentile du pur bruit**.

Diagnostic retenu : le profil cumulé étant une moyenne invariante à l'ordre, **aucune
mesure construite dessus ne peut porter d'information temporelle**. Les quatre mesures
étaient des constantes déguisées. Elles ont été **supprimées, pas réglées**.

### Ce qui les remplace

| mesure | définition | argument de validité |
|---|---|---|
| **la braise** | deux profils : celui de *toujours*, et un profil *récent* pondéré par 0,5^(âge/30 j). Rouge posé sur les cellules où ils tombent sur des paliers différents | le profil récent ne converge jamais ; l'écart naît nul et croît avec l'amplitude temporelle |
| **le silence rompu** | un axe nommé dont l'utilisateur n'avait **jamais** parlé et dont il vient de parler | c'est un **événement daté**, pas une tendance : pas d'hypothèse nulle, donc pas de faux positif. Cite son mot |
| **le témoin du pas** | chaque film comparé à 400 films tirés au hasard **depuis le même état** | « ce film t'a moins déplacé que 93 % des autres » est falsifiable ; « tu as tourné de 14° » ne l'est pas |

Un test verrouille désormais : *40 historiques aléatoires → zéro phrase produite.*

### Et un artefact du même ordre, dans le rendu

L'empreinte agrégeait par blocs (3→2→1) et gagnait des paliers (4→11) selon le **nombre**
d'arêtes. En figeant le vecteur et en ne faisant varier que le compteur : **jusqu'à 82,6 %
de la grille changeait de couleur à goût strictement identique**, sur 7 transitions sur 12.
Un vrai pas de goût en déplace ~50 %. L'artefact était donc plus gros que le signal. La
rampe a été supprimée ; un test verrouille que le compteur ne peint plus rien.

---

## 5. Deux bugs de lexique trouvés en production

**a) Homographes.** Le portrait affiché disait *« Tu regardes d'abord l'image et le son »*
— l'axe *image* étant allumé deux fois sur trois par le mot **« belles »**, venu de
*« de très belles femmes qui donnent envie de rester »*. Autres pièges mesurés :

```
« le héros perd SON sang froid »       -> axe « le son »        (possessif)
« TON film est sorti trop tard »       -> axe « l'atmosphère »  (possessif)
« une HISTOIRE d'amour sans intérêt »  -> axe « l'intrigue »    (trop générique)
« le PLAN du braquage »                -> axe « l'image »
```

Corrigé : purge des mots vides hors contexte, purge des mots de **valence**
(« beau », « belle », « sublime » — sinon l'axe le plus stable n'est qu'un compliment),
et passage en **expressions** de ce qui a besoin de contexte (« bande son », « mise en
scène », « le jeu »).

**b) Accents.** La liste de mots vides était écrite sans accents et la tokenisation ne
pliait pas : **« très »** et **« même »** remontaient en tête du nuage « les mots qui te
reviennent ».

---

## 6. Les données réelles, en entier

Trois **graines** (films déclarés, sans description) : *Se7en*, *12 Angry Men*,
*Castle in the Sky*.

Deux **arêtes** :

> **Your Name.** (21/07, 14 h 22) — « film d'amour visionné au moins deux fois, le
> changement de temporalité est très bien abordé et l'on s'y perd dans le sens noble du
> terme ce qui en fait quelque chose de poétique. Les couleurs sont belles, la bande son
> est réussie. Le défaut que je lui donnerais est d'être un peu trop enfantin et de croire
> en une histoire d'amour idyllique. »

> **Casino** (21/07, 15 h 32) — « Un film dans la continuité des films de De Niro, proche
> des Affranchis dans le principe des gangsters, de très belles femmes qui donnent envie
> de rester et une tension constante, je ne pourrais pas dire que c'était vraiment un
> chef-d'œuvre mais je m'attendais à ça et je ne suis pas déçu. Film bien réalisé et
> fidèle à lui-même. »

**Faits mesurés sur ces données** — et plusieurs sont gênants :

- les deux valences recalculées valent **0,721 et 0,721**, à l'identique. Le lexique
  n'atteint qu'environ **36 valeurs distinctes** : deux textes très différents tombent sur
  la même ;
- la valence est **recalculée à la lecture**. Le fichier stocke `-0,19` pour *Casino*
  (avant le correctif de négation). Donc **le passé se réécrit** à chaque édition du
  lexique : « tu t'es adouci » peut devenir « tu t'es durci » parce qu'un mot a été
  ajouté ;
- décrire ses graines **ne déplace pas l'empreinte d'un pixel** : une arête sur un film
  déjà graine laisse le vecteur colinéaire — `unit((1 + 1,5·v)·Σvᵢ) = unit(Σvᵢ)`. Toute la
  valeur de l'onboarding est donc dans les **mots**, pas dans la géométrie ;
- la carte : **43 territoires** pour 6000 films, dont **2030 films en bruit HDBSCAN
  (33,8 %)**. À 10 arêtes, ~7 seulement tomberaient dans un territoire nommé ;
- PaCMAP conserve **10,6 %** du voisinage à k=10, contre **1,6 %** pour l'ACP ;
- seules **0,4 %** des paires de dimensions de l'embedding dépassent |r| = 0,3 — le
  réordonnancement du glyphe a donc un plafond bas par construction ;
- les faits « croustillants » : **~45 %** accrochent vraiment (mesuré sur échantillon
  aléatoire, pas sur les films connus — la première mesure, faite sur des classiques,
  donnait 14/15 et était trompeuse).

---

## 7. Ce qui est déjà connu — ne pas le redécouvrir

1. La boucle avance à la vitesse d'une vraie vie de spectateur ; rien ne pousse à revenir.
2. Écrire un texte après chaque film est la friction centrale, et c'est assumé.
3. La valence par lexique est un plancher (voir §6, résolution ~36 valeurs).
4. Aucun effet de réseau : mono-utilisateur, cold-start permanent.
5. Le corpus d'embedding est le **synopsis**, pas le film : deux films au pitch proche
   mais au geste opposé sont voisins.

---

## 8. Ce qu'on te demande

Sois **exigeant, chiffré, et tranché**. Une réponse vague ne sert à rien. Quand tu
affirmes qu'une mesure est mauvaise, dis **quelle expérience** la démolirait.

**A. La validité statistique — le cœur.**
1. Le diagnostic du §4 est-il correct ? Une moyenne invariante à l'ordre peut-elle porter
   *une* information temporelle qu'on aurait manquée ?
2. **La braise** : profil récent (demi-vie 30 j) contre profil cumulé. Quel est son biais
   le plus grave ? Note qu'elle partage ses films avec le profil cumulé — les deux
   quantités sont **corrélées par construction**. Est-ce fatal ?
3. Quelle **hypothèse nulle** faut-il pour la braise ? Une permutation des *dates* entre
   les mêmes films est-elle le bon témoin, ou en vois-tu un meilleur ?
4. Le **témoin du pas** (400 films au hasard depuis le même état) : le tirage uniforme
   dans le catalogue est-il le bon nul, sachant que l'oracle ne propose jamais uniformément ?
5. À partir de combien d'arêtes une affirmation d'évolution devient-elle défendable ?
   Donne un nombre et sa justification, pas une fourchette.

**B. Les mesures qui restent, et celles qu'on n'a pas vues.**
6. **Le silence rompu** se prétend « sans faux positif possible ». Où est la faille ?
7. Existe-t-il une mesure d'évolution du goût, calculable sur `(film, texte, date)` +
   embeddings, qui **n'ait pas** le défaut de convergence ? Une seule, précise, avec sa
   formule et son test nul.
8. La valence à ~36 valeurs et réécriture rétroactive du passé (§6) : le correctif
   minimal, c'est de **versionner le lexique** et de geler la valence historique. Est-ce
   suffisant, ou faut-il changer de méthode — et laquelle, à coût de projet solo ?

**C. Ce qui est peut-être faux ailleurs.**
9. Avec 33,8 % du catalogue en bruit HDBSCAN, la « carte du goût » est-elle honnête ?
   Que devrait-elle montrer ou taire ?
10. Un glyphe de 384 dimensions largement décorrélées, réordonné puis quantifié : est-ce
    une visualisation légitime ou une jolie image sans contenu lisible ? Tranche.
11. Le corpus d'embedding est le **synopsis**. Nomme le mode de défaillance le plus grave
    que ça induit sur des recommandations « orthogonales », et comment le détecter sans
    étiquettes.
12. Quelle est la faille la plus grave de tout ce document, qui n'est ni au §6 ni au §7 ?

**Format attendu.** Réponses numérotées. Une position tranchée par point. Pour toute
mesure que tu proposes : sa formule, son hypothèse nulle, et le nombre d'observations à
partir duquel elle a de la puissance. Si tu penses qu'une partie du produit devrait être
**supprimée**, dis-le franchement.
