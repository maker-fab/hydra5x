# Mouvements — qui bouge, comment, et à quelle vitesse

Avant le volume, la cinématique. Ce fichier répartit les six mouvements
entre le plateau et la tête, et traite les problèmes que chaque choix crée.

Il faut **trois translations et deux rotations**. La sixième — tourner
autour de l'axe de la buse — n'a pas de sens pour une buse ronde.

## La répartition retenue

| mouvement | porté par | pourquoi |
|---|---|---|
| X, Y | chariot CoreXY | éprouvé, deux moteurs fixes au bâti, rien de lourd qui bouge |
| Z | plateau | le plateau descend, le portique reste bas et rigide |
| **C — rotation à plat** | plateau | la pièce reste posée, jamais penchée |
| **B — inclinaison** | tête | seul axe embarqué |

Empilement : **Z porte C**, pas l'inverse. L'ascenseur soulève le
tourne-disque. Le contraire ferait tourner le mécanisme de levage.

## Les quatre problèmes de mouvement, dans l'ordre d'importance

### 1. Le point piloté doit rester la pointe de la buse

Quand B tourne, si le pivot n'est pas à la pointe, la pointe décrit un arc
et sort de sa trajectoire. Deux parades :

**a) Pivot mécanique à la pointe.** La tête tourne autour d'un centre situé
au bout de la buse. Géométriquement propre, mais la chape doit enjamber
toute la hauteur de la tête : un arc de 70 mm de rayon autour de la buse,
encombrant et exactement là où la matière déjà déposée se trouve.

**b) Pivot où c'est commode, compensation logicielle.** X, Y et Z bougent
pendant que B tourne, pour maintenir la pointe en place. C'est la pratique
standard en CN 5 axes. Coût réel : **toute rotation de B entraîne les trois
translations**, donc la vitesse de B est bornée par la dynamique de XYZ, et
le balayage de compensation mord sur l'enveloppe.

Choix : **(b)**, parce que (a) place de la mécanique précisément là où il
n'y a pas de place. Mais (b) impose que la compensation existe dans le
firmware avant le premier essai — ce n'est pas une option de confort.

### 2. Les rotations sont-elles indexées ou continues ?

C'est **la** question, celle qui décide du firmware et de la classe de
machine.

| | quand B et C bougent | la machine pendant le dépôt | existe ? |
|---|---|---|---|
| **indexé** (multidirectionnel) | **entre** les blocs | une 3 axes ordinaire | **oui, ici même** |
| **continu** (non-planaire) | **pendant** le cordon | 5 axes coordonnés, RTCP, look-ahead | non sous Klipper |

En indexé, rien de difficile : on s'arrête, on tourne, on repart. Les
`MANUAL_STEPPER` de Cortex suffisent, et c'est déjà ce que fait
`stitch_chunks.py`.

En continu, B et C doivent être interpolés avec X, Y, Z sur chaque segment.
**C'est le vrai mur**, et il est logiciel.

D17 a établi que le multidirectionnel est la discrétisation grossière du
non-planaire. Conséquence pour la mécanique : **construire une machine
capable du continu, la piloter d'abord en indexé.** Le matériel ne change
pas, seul le firmware monte en gamme.

### 3. Ce qui doit être rapide, et ce qui peut être lent

| axe | régime indexé | régime continu |
|---|---|---|
| X, Y | rapide — vitesse de dépôt | rapide |
| Z | lent | moyen |
| **B, C** | **lents** — quelques secondes par bloc | rapides |

En indexé, B et C peuvent être **très démultipliés**. Ça change tout :

- **vis sans fin** sur B et C — rapport 40:1 à 100:1, irréversible, pas
  cher, pas de jeu sous charge, et l'axe tient sa position moteur coupé ;
- moteurs minuscules, donc pas de masse ajoutée sur la tête ;
- rigidité élevée sans effort de conception.

C'est un cadeau du régime indexé qu'il serait dommage de ne pas prendre. À
noter : passer au continu plus tard demandera de revoir ces réducteurs —
une vis sans fin ne suit pas un profil de vitesse. **À décider avant
d'usiner**, pas après.

### 4. Jeu et raideur sur B

B porte la buse au bout d'un bras de 70 mm. **0,1° de jeu = 0,12 mm à la
pointe** — soit plus que la précision recherchée. Même exigence que pour un
axe linéaire, sur un axe rotatif, ce qui est plus difficile.

La même arithmétique vaut pour le changement d'outil : la répétabilité de
la référence de B entre directement dans l'offset de l'outil (D20).

## Ce que le mouvement du plateau impose

**La pièce orbite si elle n'est pas centrée.** Rotation de C d'un angle
quelconque : une pièce décalée de `d` du centre décrit un cercle de rayon
`d`. XY doit couvrir cette orbite, donc le cercle circonscrit de la pièce.
D'où l'enveloppe naturellement **cylindrique** d'une machine à plateau
tournant, et l'intérêt de centrer la pièce.

**Le défaut classique des machines polaires ne mord pas ici.** Sur une
polaire, C dessine : la vitesse linéaire s'annule au centre et explose au
bord, et une petite erreur XY devient une grosse erreur angulaire près de
l'axe. Ici **C ne dessine pas**, il indexe l'azimut entre deux blocs. Le
problème disparaît avec l'usage.

**Le passage tournant est un problème résolu.** Fractal fait passer
l'alimentation du plateau chauffant par une bague ; Rep5x tourne sans
limite. Quelques euros, pas une contrainte d'architecture.

## Ce que le mouvement de la tête impose

**Le filament traverse une articulation.** Chiffré dans `envelope.md` : 70
à 85 mm de mou suffisent, une boucle de service. Ce n'est pas bloquant.

**Les moteurs peuvent rester à terre.** Le montage « Core » de Joshua Bird
couple deux moteurs par courroie pour piloter à la fois la translation X et
la rotation B, **les deux moteurs restant sur le chariot Z**. Rien de lourd
ne bouge avec la buse. C'est la réponse directe à l'objection « masse sur
la tête ».

**Le refroidissement doit être annulaire.** Une tête qui s'incline dans
toutes les directions ne peut pas avoir un ventilateur d'un seul côté :
selon l'azimut il gêne ou il ne souffle pas au bon endroit. Mesuré : 51,8°
contre 23,2° (`envelope.md`).

## Ce qu'il reste à trancher

1. **Indexé d'abord, continu ensuite — ou continu tout de suite ?** Décide
   des réducteurs de B et C, donc de la mécanique.
2. **Compensation du point piloté : dans le firmware, ou dans le
   post-traitement du G-code ?** Le post-traitement est plus simple et
   suffit en indexé ; il ne suffira pas en continu.
3. **Le cordon tient-il sur une couche inclinée ?** Le seul point que le
   calcul ne tranchera pas (D21).
