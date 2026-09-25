# Tête inclinable — quatre concepts, mesurés

`cad/tetes.py` construit quatre mécanismes et mesure les deux critères qui
comptent. Il ne tranche pas tout seul : il donne les chiffres.

## Les deux critères, et pourquoi il en faut deux

| | ce qu'il dit | contre quoi |
|---|---|---|
| **demi-encombrement** | ce que la tête retire aux courses du bâti | collision tête ↔ **bâti** |
| **silhouette** | jusqu'où elle plonge dans une concavité | collision tête ↔ **pièce** |

Ils sont indépendants et souvent opposés : une tête compacte gagne le
premier en resserrant de la matière autour de la buse, et perd le second
pour exactement la même raison.

La silhouette reprend la méthode de `mesurer_tete.py` — profil de hauteur
minimale à chaque rayon, puis `θ_max = min_r arctan(h(r)/r)`.

## Les chiffres, à 35° sur un bâti de 400

| concept | demi-enc. | course utile | silhouette |
|---|---|---|---|
| colonnes | 139,3 mm | **121,4 mm** | 40,9° |
| **biellettes** | 112,7 mm | **174,7 mm** | **40,9°** |
| cardan série | **82,7 mm** | **234,5 mm** | **33,7°** ✗ |
| **pivot central** | 112,7 mm | **174,7 mm** | **40,9°** |

Course des actionneurs, identique partout : `√3·R·tan θ` = **54,6 mm** à
R45. Résolution exigée pour tenir 0,1° à la platine : **136 µm**.

## Ce que chaque concept est

**1. Colonnes** — trois vérins verticaux montés sur la platine. Le plus
direct, celui qui était dessiné. **Le pire** : les colonnes dépassent vers
le haut et se couchent en s'inclinant, ce qui coûte 53 mm de course de
plus que la variante suivante, pour aucun gain.

**2. Biellettes** — les actionneurs restent sur le chariot, trois
biellettes courtes tirent la platine. Rien de haut ne bouge avec elle.
Réponse directe au défaut du concept 1, et rien n'est perdu en
silhouette.

**3. Cardan série** — deux axes rotatifs A et B, une chape autour du
hotend. **Le meilleur sur l'encombrement, le seul à rater la cible sur la
silhouette** : 33,7° contre 35° visés. Sa chape descend près de la buse,
c'est-à-dire exactement là où se trouve la matière déjà déposée. C'est
l'objection que D27 et D30 formulaient sans la chiffrer ; elle est
chiffrée.

**4. Pivot central** — un joint de cardan au centre prend les efforts
latéraux, trois biellettes ne font que pousser. Mêmes chiffres que le
concept 2, plus trois avantages qui ne se mesurent pas en millimètres :

- le **pivot est choisi**, pas subi. Il est défini par un joint réel, pas
  par l'intersection de trois contraintes.
- il **résout le blocage** laissé ouvert depuis D25 : trois rotules
  rigides sur trois verticales se bloqueraient, un plateau rigide gardant
  ses distances entre points. Avec un pivot central porteur, les trois
  biellettes ne contraignent plus que la hauteur — le degré latéral est
  libéré par construction.
- il **encaisse l'effort de dépôt et le verrouillage d'outil** dans une
  pièce, au lieu de les répartir sur trois liaisons.

## Recommandation

**Le pivot central.** Il ne coûte rien face aux biellettes seules — mêmes
174,7 mm de course, même silhouette — et il ferme la question mécanique
qui restait ouverte.

Le cardan série n'est pas écarté pour son principe : il est écarté parce
que sa chape mord 1,3° sous la cible. Une chape redessinée plus haute ou
plus étroite le ramènerait dans le jeu, et il rendrait alors 60 mm de
course de plus. **À reprendre si l'encombrement devient le point dur.**

## Ce qui reste à décider

- **Le type d'actionneur** : vis, courroie, ou biellette poussée. La
  résolution de 136 µm pour 0,1° est atteignable par les trois ; le jeu,
  non — une vis trapézoïdale sans rattrapage ne tiendra pas.
- **La forme du joint central** : cardan, rotule, ou lame flexible. Le
  flexible est **écarté à 35°**, voir ci-dessous.
- **Le passage du filament** à travers le joint central, qui occupe l'axe.

## Le joint central : pourquoi pas une articulation flexible

Une lame ou un col flexible supprime le jeu par construction — pas de
contact glissant, donc rien à rattraper. C'est exactement ce que
demandent les 0,1° admissibles. `tools/pivot_flexible.py` chiffre ce que
ça coûte.

La borne vient de la déformation de la matière, pas de la géométrie :

    theta_max = epsilon_admissible x L / c

`c` = rayon du col. Tout est dans le rapport longueur sur épaisseur, et
le seul levier est la longueur.

**Longueur libre nécessaire pour atteindre 35°**, en fatigue illimitée :

| matériau | Ø1 mm | Ø2 mm | Ø3 mm |
|---|---|---|---|
| acier ressort | 102 mm | 204 mm | 305 mm |
| béryllium-cuivre | 76 mm | 153 mm | 229 mm |
| titane Gr5 | **51 mm** | 102 mm | 153 mm |

**Le pivot doit tenir dans les 80 mm qui séparent la platine de la
pointe.** Un col de 102 à 305 mm n'y entre pas. Seul le titane en Ø1
passerait, à 51 mm — et il flambe à 138 N, soit 46 N utiles avec un
coefficient 3. C'est le pivot qui encaisse l'effort de dépôt *et* le
verrouillage d'outil.

Ce qu'un col **qui tient dans 40 mm** donne réellement :

| matériau | Ø1 | Ø1,5 | Ø2 |
|---|---|---|---|
| acier ressort | 13,8° | 9,2° | 6,9° |
| titane Gr5 | **27,5°** | 18,3° | 13,8° |

**Environ 14° pour un col robuste, 28° pour un col fragile.** Pas 35°.

Le polypropylène atteint 35° en 12 mm — et flue sous charge permanente.
Une charnière vivante n'est pas un pivot de précision.

**Conséquence** : le joint central est un **cardan à roulements
préchargés** ou une **rotule**, pas un flexible. Le flexible redeviendrait
le bon choix si la cible d'inclinaison descendait vers 15° : un col titane
Ø2 de 44 mm y suffit, sans jeu et sans entretien.

Dernier point à ne pas oublier : **un pivot flexible rappelle toujours
vers sa position neutre**. À 35° sur un col titane Ø2, il faut 535 N.mm
en permanence, soit 12 N par actionneur à R45. Un entraînement
irréversible — vis sans fin, vis trapézoïdale — encaisse ça sans
consommer de courant. Une courroie, non.

---

## Filament des pièces imprimées

`tools/filaments.py`. Le critère n'est pas la rigidité, c'est la **dérive
thermique** : un changeur d'outil vit sur sa répétabilité, et les offsets
sont étalonnés à une température donnée.

### Ce que le calcul apprend d'abord

Pièce de 100 mm, caisson variant de 40 K :

| filament | dérive | choc | élec. | couleurs | aspect |
|---|---|---|---|---|---|
| ASA | 0,360 mm | 1,00 | isolant | toutes | semi-mat |
| ASA-GF | 0,200 mm | 0,55 | **isolant** | **claires** | mat |
| ASA-CF | 0,140 mm | 0,35 | **conduit** | noir | mat |
| PC-CF | 0,100 mm | 0,40 | conduit | noir | mat |
| *alu 6061* | *0,092 mm* | — | — | — | — |

**Aucun plastique imprimé ne tient 0,10 mm sur 100 mm avec 40 K d'écart.
L'aluminium lui-même y est à peine.** Le matériau ne peut donc pas porter
seul la tolérance — c'est l'étalonnage automatique des offsets qui la
porte, et DAKSH le fait à chaque changement.

Ce qui compte n'est donc pas la dérive absolue mais **la dérive entre deux
étalonnages**, soit ±10 K en régime établi :

| filament | dérive à ±10 K |
|---|---|
| ASA | 0,090 mm |
| **ASA-GF** | **0,050 mm** |
| ASA-CF | 0,035 mm |
| *alu 6061* | *0,023 mm* |

À ce régime, **l'ASA-GF suffit largement**, et la question du CF ne se
pose plus en ces termes.

### GF plutôt que CF, et pour trois raisons

1. **Le CF conduit l'électricité.** La tête porte une carte, des nappes,
   un capteur et des LED. Les fibres affleurantes et la poussière de
   ponçage créent des chemins de fuite. **La fibre de verre est
   isolante.**
2. **Le CF casse net.** Ténacité 0,35 contre 0,55 pour le GF et 1,00 pour
   l'ASA nu. Le `ToolLock` encaisse 2000 chocs et porte 9 inserts M3 sous
   charge : c'est de la ténacité qu'il lui faut.
3. **Le CF n'existe qu'en noir.** Le GF se colore.

### Par poste

| dossier | filament | pourquoi |
|---|---|---|
| **Gantry**, **Dock** | **ASA-GF** | portent les offsets ; 0,05 mm à ±10 K, isolant, coloré, mat |
| **ToolLock** | **ASA nu** ou ASA mat | ténacité et tenue des inserts priment |
| **Toolhead** | **ASA-GF** | isolant obligatoire, proche du bloc |

Le **PA6-GF** est la montée en gamme cohérente si le caisson dépasse
90 °C : 120 °C de service, isolant, ténacité 0,70. Il exige un séchage
sérieux — il reprend l'humidité en quelques heures.

### Le mat

Un filament « mat » est un filament **chargé** — microbilles minérales ou
craie. Les mêmes charges réduisent le retrait, donc le gauchissement, et
abrasent la buse. **Mat ou fibré, c'est la même contrainte : buse
durcie.**

L'ASA-GF est mat par construction. L'ASA nu est semi-mat. Il n'y a rien à
chercher de plus.

**Le piège** : les produits vendus « Matte » sont presque toujours du
**PLA**. Service 50 °C, contre 50-60 °C en caisson et 80-100 °C contre le
bloc. Disqualifié ici, quelle que soit sa finition.
