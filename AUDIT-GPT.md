# MORDU — audit produit & expérience

> **Mode d'emploi.** Copie-colle ce document entier dans ChatGPT. Il est autoportant :
> l'auditeur n'a accès ni au code, ni aux écrans. Les questions sont au §7.
>
> Deux autres briefs existent et couvrent autre chose — inutile de les redemander :
> `AUDIT-GEMINI.md` (validité statistique des mesures) et une première passe produit déjà
> faite par un autre modèle, dont les conclusions sont **résumées et arbitrées au §6**.
> **Ne répète pas le §6.** Ce qui est attendu ici, c'est ce que cette passe a manqué.

---

## 1. La thèse

> **MORDU ne montre pas un catalogue. Il tend trois films — trois directions, trois
> arguments. Tu ne choisis pas un film parmi des milliers : tu déclares ton envie du
> soir.**

Trois cartes, jamais plus. Pas de liste, pas de recherche, pas de re-tirage, pas de
quatrième carte. Les axes sont **orthogonaux obligatoires** : jamais trois thrillers.

Chaque carte porte :
- un **registre annoncé** — *terrain connu*, *pas de côté*, *le pari* ;
- un **argument** de la forme « ce qui relie **mais** ce qui diffère » (« l'univers de
  Fincher, comme dans *Se7en*, mais avec un rythme plus sec ») — jamais un « parce que
  vous avez regardé… » ;
- un **fait vérifié** tiré de Wikipédia ;
- un **pari** de la machine sur ce que tu vas retenir (« je parie que la traque va te
  tenir plus que le dénouement »).

**Le choix se fait à l'aveugle** : les affiches restent tramées, illisibles. Seuls les
arguments sont lisibles. On révèle le film **après** l'engagement.

**La boucle :**

```
3 cartes → tu choisis une DIRECTION → le film se révèle → tu le regardes
→ SERRURE : tu écris ce qu'il t'en reste (texte libre, OBLIGATOIRE)
→ une « arête » (film, texte, date) est stockée → ton profil se raffine
→ 3 cartes suivantes
```

**Sans ce texte écrit, le tirage suivant est bloqué.** C'est la mécanique centrale.

---

## 2. Les interdits — décisions prises, avec leur raison

Ce ne sont pas des oublis. Proposer de les rétablir sans argument neuf ne sert à rien.

| écarté | pourquoi |
|---|---|
| **le versus « tu préfères A ou B ? »** | il est impossible de trancher entre *Se7en* et *Princesse Mononoké* ; le choix forcé fabrique un **faux rejet** d'un film adoré |
| **les notes / étoiles** | une note est une *évaluation* (à quel point c'est bon), pas une *envie* (qu'est-ce que je lance ce soir). Mettre 4 et 4,5 ne dit pas lequel on lancera. Netflix a tué ses étoiles en 2017 pour ça |
| **la watchlist** | une liste qu'on consulte pour choisir s'allonge, nous regarde, et devient une **dette** |
| **jauges, badges, séries de jours** | produisent le « cinéma-devoir ». Anti-Duolingo, assumé |
| **un canon imposé** | un classique n'est proposé que s'il part d'un film déjà aimé. **Invitation, jamais dette** |
| **le filtrage collaboratif** | aucune donnée d'usage, et le démarrage à froid est rédhibitoire |

---

## 3. Ce qui existe vraiment, écran par écran

| écran | contenu |
|---|---|
| **L'oracle** | les 3 cartes aveugles, la serrure, et la **boîte aux lettres** (voir §4) |
| **Mon profil** | genres, motifs pondérés par rareté, vocabulaire, films voisins, un **portrait en une phrase**, une **empreinte** |
| **La carte du goût** | 6000 films projetés en 2D, territoires auto-nommés, ta position |
| **Ma dérive** | ce qui a bougé dans ton goût au fil du temps |
| **Domaines** | portraits de réalisateurs/acteurs qui se dé-pixelisent à mesure que tu vois leurs films essentiels |

**L'empreinte** : ton vecteur de goût (384 dimensions) replié en grille 24×16 et quantifié
sur 11 couleurs. C'est une **signature** — unique, déterministe, et **muette**. Elle
t'identifie sans rien raconter, comme une empreinte digitale. Ce qui se *lit* est ailleurs.

**Le portrait** : une phrase du type *« Tu regardes d'abord l'atmosphère et l'image. Tu ne
parles jamais du rythme, de l'intrigue, des personnages — c'est ce silence qui te distingue
le plus. »* Le signal le plus fort n'est pas ce dont tu parles le plus, **c'est ce dont tu
ne parles jamais**.

**La direction artistique** : tramage « dither » (vraies images de films réduites à des
pixels), palette de nuit indexée + un rouge d'impact, typo Impact et monospace. **Règle
dure** : *tramé = ce qui t'est encore caché ; net = ce que tu connais déjà.* Le dither a
donc été **retiré** de la recherche, de la boîte et des fiches, où il était décoratif.

---

## 4. La boîte aux lettres — le point le plus contesté

Quelqu'un te conseille un film. Tu le déposes dans la boîte. **Tu ne peux pas le choisir**
et tu ne peux pas le lancer : c'est l'oracle qui y puise, avec une probabilité de 30 %, et
seulement quand il tombe naturellement dans l'une des trois bandes.

L'intention : capter les conseils d'amis (le vrai canal de découverte de films) sans créer
de liste-dette.

**Le problème, admis** : aujourd'hui la boîte est **affichée** sur l'écran de l'oracle —
les affiches, les titres, un bouton pour supprimer. Donc elle s'allonge et elle te regarde.
C'est exactement le mécanisme de la watchlist rejetée au §2, avec une contrainte en plus :
tu n'as même pas la main sur le déclenchement.

---

## 5. Les contraintes réelles

- **Projet solo, side project.** Pas d'équipe, pas de budget, pas de deadline.
- **Un seul utilisateur : son auteur.** Aucune audience, aucun objectif de croissance.
- Sa valeur assumée : un projet de portfolio data/ML **fini**, plus le plaisir de
  découvrir des technos récentes.
- Web multi-pages sans framework (HTML/CSS/JS natif), API Python (FastAPI). Langue :
  français.
- **Le rythme du produit est celui d'une vraie vie de spectateur** (2-3 films/semaine).
  Rien ne pousse à revenir entre deux visionnages, et c'est délibéré.

---

## 6. La passe produit déjà faite — ne pas la refaire

Résumé fidèle, avec l'arbitrage retenu. **Ce sont des sujets clos ; ne les recycle pas.**

| critique reçue | arbitrage |
|---|---|
| **L'aveuglement au ton.** L'embedding porte sur le *synopsis*, donc sur l'intrigue, pas sur la forme. *Scream* et *Scary Movie* se ressemblent mathématiquement | **Fondé, mais rare.** Mesuré : sur 1891 films connus (~1,8 M de paires), **12 paires** seulement dépassent 0,72 avec des tons opposés — dont *Scream ↔ Scary Movie* (0,736), *Beetlejuice ↔ Insidious* (0,735). Risque de queue, pas taux de base. Un garde-fou par genre est prévu |
| **La serrure bloque au mauvais moment.** On ouvre l'app pour *choisir* (3 jours après), pas après le film. Être bloqué là = fuite vers Netflix | **Vrai pour un produit à utilisateurs, non contraignant ici** (un seul utilisateur, qui est l'auteur, et qui veut une thèse forte). Sujet rouvert seulement si l'app est diffusée |
| **Le choix aveugle tue l'appel viscéral de l'affiche** | **Assumé** : l'affiche est une machine à préjugés (personne ne clique un noir et blanc de 1957). C'est un troc conscient |
| **La boîte aux lettres est une watchlist déguisée** | **Fondé** (voir §4). La réponse retenue n'est PAS de la supprimer mais de la rendre **aveugle** : n'afficher qu'un compte, jamais les titres |
| **La DA ressemble à un terminal de hacking des années 2000** (Impact + monospace + noir/rouge + tramage) | **Encaissé.** À traiter |
| **Idée : une carte « contre-pied »**, le point mathématiquement le plus éloigné | **Rejetée** : elle violerait la règle « toute carte doit avoir une ancre réelle » (invitation, jamais dette). Sans ancre, c'est un jet de dé |
| **Idée : un « purgatoire »**, un film non choisi 3 fois disparaît 6 mois | **Rejetée telle quelle** : ne pas choisir n'est PAS rejeter — c'est toute la thèse contre le versus. Retenu seulement comme *anti-répétition d'affichage*, sans aucun effet sur le goût |
| **Idée : glisser une carte sur l'autre pour générer leur différence** | **Rejetée** : c'est le versus par la porte de derrière |

---

## 7. Ce qu'on te demande

Sois **exigeant et concret**. Une réponse complaisante ne sert à rien. Ne propose rien qui
viole le §2 sans le dire explicitement et l'assumer.

**A. L'expérience, minute par minute.**
1. Déroule la **deuxième semaine** d'un utilisateur : il a vu 2 films, écrit 2 textes. Où
   exactement décroche-t-il, et pourquoi ?
2. Le produit demande d'**écrire**. Écrire est difficile, et un texte bâclé pollue le
   moteur autant qu'il l'informe. Comment obtenir un texte *court mais dense* sans
   formulaire, sans champs guidés, sans le transformer en questionnaire ?
3. Quel est le moment où l'utilisateur ressent, pour la première fois, que **la machine l'a
   compris** ? Si ce moment n'existe pas encore dans ce qui est décrit, invente-le.
4. Qu'est-ce qui, dans cette boucle, produit de la **honte** ou de la **culpabilité** —
   les deux émotions que le produit prétend supprimer ?

**B. La thèse elle-même.**
5. « Trois directions argumentées » plutôt qu'un catalogue : quel est le **contre-exemple**
   le plus embarrassant ? Le soir où cette promesse s'effondre.
6. Le produit refuse notes, listes, jauges et séries. **Que reste-t-il pour donner envie de
   revenir**, à part la qualité de la reco ? Réponds sans réintroduire ce qui est au §2.
7. L'utilisateur écrit sur ses films. Six mois plus tard, il a un journal intime
   cinéphile. **Est-ce ça, le vrai produit ?** Si oui, qu'est-ce qui devrait changer ?

**C. Le neuf.**
8. **Trois fonctionnalités** compatibles avec le §2, qu'aucun des audits précédents n'a
   proposées. Pour chacune : la mécanique précise, le coût, et ce qu'elle casse.
9. Une seule idée pour rendre la **boîte aux lettres** aveugle sans qu'elle devienne
   frustrante — ou l'argument pour la supprimer, qui n'a pas encore été donné.
10. Le produit est **mono-utilisateur** et le restera. Quelle mécanique **sociale** est
    compatible avec ça, c'est-à-dire sans compte, sans flux, sans profils publics ?
11. Si tu ne devais garder **qu'un seul écran** parmi les cinq du §3 et jeter les quatre
    autres, lequel — et qu'est-ce que ça révèle du produit ?
12. Quelle est la faille la plus grave de tout ce document, qui n'est **ni au §5 ni au
    §6** ?

**Format attendu.** Réponses numérotées, une position tranchée par point. Pour chaque
proposition : la mécanique exacte, pas l'intention. Si tu penses qu'une partie du produit
devrait être **supprimée**, dis-le franchement — c'est ce qui est le plus utile.
