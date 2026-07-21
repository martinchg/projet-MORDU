# MORDU — brief pour un audit externe

> **Mode d'emploi** : copie-colle ce document entier dans ChatGPT (ou un autre modèle).
> Il est autoportant : l'auditeur n'a accès ni au code, ni aux écrans.
> Les questions à lui poser sont à la fin (§7).

---

## 1. Ce qu'est le produit

MORDU est une application de recommandation de films. Sa thèse :

> **MORDU ne montre pas un catalogue. Il tend trois films — trois directions, trois
> arguments. L'utilisateur ne choisit pas un film parmi des milliers : il déclare son
> envie du soir.**

Trois cartes, jamais plus, aux axes **orthogonaux obligatoires** (jamais trois thrillers).
Pas de liste, pas de recherche, pas de re-tirage, pas de quatrième carte.

Chaque carte porte :
- un **registre annoncé** — « terrain connu », « pas de côté », « le pari » ;
- un **argument** de la forme *ce qui relie* **mais** *ce qui diffère* (ex. « L'univers de
  David Fincher, comme dans Se7en, mais avec un rythme plus sec ») — jamais un « parce que
  vous avez regardé… » ;
- un **fait croustillant** vérifié, extrait de Wikipédia (ex. sur *Psychose* : « le tournage
  de la mort de Marion Crane se fit en sept jours et 70 prises pour 45 secondes ») ;
- un **pari** de l'oracle sur ce que l'utilisateur va retenir (« je parie que la traque va
  te tenir plus que le dénouement »).

**La boucle du produit :**
```
3 cartes → l'utilisateur choisit une DIRECTION → il regarde le film
→ SERRURE : il raconte ce qu'il en reste (texte libre, obligatoire)
→ une « arête » (utilisateur, film, texte, date) est stockée
→ son profil se raffine → 3 cartes suivantes
```

Sans ce ressenti écrit, **le tirage suivant est bloqué**. C'est la mécanique centrale.

**Le choix se fait à l'aveugle** : les affiches restent tramées (illisibles), seuls les
arguments sont lisibles. Le film ne se révèle qu'après l'engagement. Objectif : tuer le
préjugé d'affiche et d'époque (« je n'aurais jamais cliqué un noir et blanc de 1957 — mais
*huis clos où un seul juré retourne onze convaincus*, si »).

---

## 2. La direction artistique

**« Dither »** : de vraies images de films tramées en temps réel (shader WebGL), sur une
**palette indexée figée de 11 couleurs** — nuit bleutée, sables, et un rouge unique
(#E4130F). Cette contrainte est délibérée : elle unifie un catalogue d'affiches qu'on ne
contrôle pas. Une affiche hollywoodienne et un plan de Miyazaki finissent dans le même monde.

**Le principe unificateur : tout se résout depuis le bruit.**
- l'affiche est illisible, puis se résout quand on choisit ;
- les portraits de réalisateurs se dé-pixelisent à mesure qu'on voit leurs films ;
- les titres se résolvent lettre à lettre depuis des glyphes de bruit ;
- le fond est une nappe de bruit tramé qui dérive lentement ;
- l'« empreinte » de l'utilisateur (voir §3) est grossière puis se résout.

**Typographie** : Impact/condensé pour les titres, monospace pour les métadonnées.
L'ombre rouge sérigraphiée est **réservée** au logo et au film révélé (elle avait été mise
partout, ça devenait un tic).

**Interdits assumés** : pas de flou, pas d'emojis, pas de dégradés génériques, pas de
jauges, pas de badges, pas de séries (« streaks »).

---

## 3. Ce qui est déjà construit

- **Moteur** : content-based. 6000 films (TMDB), embeddings de synopsis (MiniLM, 384
  dimensions), similarité cosinus. Aucun filtrage collaboratif.
- **Le profil** est la moyenne pondérée des vecteurs des films aimés/racontés. Pas de note,
  pas d'étoile : la « valence » est dérivée du **texte** du ressenti.
- **Page « mon profil »** (la préférée de l'utilisateur) :
  - **une carte du goût** : les 6000 films projetés en 2D (PaCMAP), regroupés par densité
    (HDBSCAN) en 43 **territoires auto-nommés** par leurs motifs sur-représentés
    (« slasher · thriller psychologique · psychopathe », « anime », « vampire »). Les
    territoires jamais visités restent dans le brouillard. Cliquable.
  - **une empreinte** : le vecteur de goût (384D) replié en grille et rendu dans la
    palette. Déterministe. Grossier au début (blocs 3×3), plein détail vers douze
    ressentis.
  - motifs, genres, réalisateurs, et **les mots que l'utilisateur emploie** quand il
    raconte un film.
- **Les domaines** : réalisateurs/acteurs/studios pixelisés, qui se révèlent à mesure qu'on
  voit leurs films essentiels (leur « canon »).
- **La boîte aux lettres** : on y dépose un film conseillé par un ami, puis on l'oublie.
  Ni ordre, ni tri, ni bouton « regarder celui-là » : c'est l'oracle qui décide quand le
  servir (~1 tirage sur 5).

---

## 4. Les décisions DÉJÀ TRANCHÉES (ne pas les re-proposer)

Chacune répond à une douleur exprimée par l'utilisateur. Une suggestion qui les ignore sera
écartée — mais une critique argumentée de l'une d'elles est bienvenue.

| Écarté | Pourquoi |
|---|---|
| Le versus « tu préfères A ou B ? » | Impossible de trancher entre *Seven* et *Mononoké* : le choix forcé fabrique un **faux rejet** d'un film qu'on adore. |
| Les notes / étoiles | Une note est une **évaluation** (à quel point c'est bon), pas une **envie** (qu'est-ce que je veux ce soir). Mettre 4 et 4,5 ne dit pas lequel on lancera. Netflix a tué ses étoiles en 2017 pour cette raison. |
| La watchlist | Une liste qu'on consulte pour choisir s'allonge, nous regarde, et devient une **dette**. |
| Les jauges de complétion, badges, streaks | Produisent le « cinéma-devoir » : regarder ce qu'on *doit* regarder. Détesté. |
| Un canon imposé | Un essentiel n'est proposé QUE s'il part d'un film déjà aimé (« tu as aimé *12 hommes en colère* → *Témoin à charge* ») — jamais d'une liste absolue (« il FAUT avoir vu *Citizen Kane* »). **Invitation, jamais dette.** |
| Le filtrage collaboratif | Pas de données d'usage ; et le cold-start est rédhibitoire. |

---

## 5. Contraintes réelles

- **Projet solo**, side project. Pas d'équipe, pas de budget, pas de deadline.
- **Un seul utilisateur** aujourd'hui (son auteur). Aucune audience.
- Sa valeur assumée : un projet de portfolio data/ML **fini**, plus le plaisir de
  découvrir des technos récentes.
- Web multi-pages, sans framework (HTML/CSS/JS natif), API Python (FastAPI).
- Langue : français.

---

## 6. Les faiblesses que l'équipe connaît déjà

Inutile de les redécouvrir ; en revanche, des angles neufs dessus sont utiles.

1. **La boucle avance à la vitesse d'une vraie vie de spectateur** (2-3 films/semaine).
   Rien ne pousse à revenir entre deux visionnages.
2. **Il faut écrire un texte après chaque film.** C'est le pari central du produit et sa
   plus grosse friction.
3. **La valence est dérivée par un lexique de mots** — plancher assumé, à remplacer.
4. **Les faits croustillants** : ~45 % seulement accrochent vraiment ; le filtrage par
   heuristiques plafonne.
5. **Aucun effet de réseau** : tout est mono-utilisateur.

---

## 7. Ce qu'on te demande

Sois **exigeant et concret**. Les réponses vagues ou complaisantes ne servent à rien.

**A. Challenge le concept.**
1. Quelle est la faille la plus grave que tu vois, et qui n'est pas dans la liste §6 ?
2. La serrure (ressenti obligatoire pour débloquer) est-elle un trait de génie ou une
   friction qui tuera l'usage ? Argumente les deux côtés, puis tranche.
3. Le choix à l'aveugle (affiches masquées) : qu'est-ce que ça fait perdre, dont on ne se
   rend pas compte ?
4. Y a-t-il une contradiction interne entre les décisions du §4 ?

**B. Challenge la direction artistique.**
5. Une palette figée de 11 couleurs et un tramage systématique : où est-ce que ça va
   casser (accessibilité, lisibilité, lassitude après 50 sessions) ?
6. Le principe « tout se résout depuis le bruit » est-il assez fort pour porter un produit
   entier, ou est-ce un gimmick qui va s'user ?
7. Qu'est-ce qui, dans cette DA, ressemble malgré tout à quelque chose de déjà vu ?

**C. Apporte du neuf.**
8. Trois idées de fonctionnalités **compatibles** avec les interdits du §4, qu'on n'a pas
   envisagées. Pas de « ajoutez du social » sans mécanique précise.
9. Une idée de visualisation de données qui exploiterait les embeddings ou les textes des
   ressentis, et qu'on n'a pas déjà (voir §3).
10. Si tu devais supprimer **une seule** chose du produit pour le rendre meilleur, laquelle
    et pourquoi ?

**Format attendu** : réponses numérotées, une position tranchée par point, et pour chaque
idée neuve : ce qu'elle apporte, ce qu'elle coûte, et pourquoi elle ne viole pas le §4.
