# Enveloppe angulaire — ce que la machine peut réellement incliner

Établi par calcul et par exécution du slicer. Aucune mesure sur matériel.

## Le maximum utile est 45°, pas 90°

En slicing multidirectionnel, **on imprime toujours à plat** : le plan de
coupe du chunk est horizontal pendant le dépôt. L'inclinaison ne sert qu'à
réorienter *entre* les chunks. La physique de l'extrusion ne voit jamais
l'angle — pas de filet qui pend, pas de bain de fusion qui coule.

La question est donc purement géométrique :

- une 3 axes gère les surplombs jusqu'à ~45°
- pour un surplomb d'angle α, il faut basculer de (α − 45)
- le surplomb maximal concevable est 90°, un plafond horizontal

**45° couvrent tout.** Au-delà, aucun gain pour l'impression sans support.
Combinés aux 360° de l'axe A, ils donnent accès à n'importe quelle
orientation utile.

## Le modèle de garde de Cortex

`slicing_functions.py` et `widget_functions.py`, constante en dur :

```python
minAcceptableBedToNozzleClearance = 12.0
```

Pour chaque point de chaque couche d'un chunk incliné :

```python
garde = abs(z) / sin(theta)
```

Si la garde tombe sous 12 mm, le slicing est refusé. Deux comportements en
découlent :

- à θ→0 la garde tend vers l'infini — sans inclinaison, le plateau ne peut
  pas monter vers la buse
- **à z=0 la garde vaut 0 quelle que soit l'inclinaison** — tout point au
  contact du plateau interdit de basculer

```
  z\theta     5°      10°     20°     30°     45°     90°
    0,0 mm    0,0     0,0     0,0     0,0     0,0     0,0
    2,0 mm   22,9    11,5     5,8     4,0     2,8     2,0
    8,0 mm   91,8    46,1    23,4    16,0    11,3     8,0
   12,0 mm  137,7    69,1    35,1    24,0    17,0    12,0
```

**Réserve** : le raisonnement physique derrière `z/sin(θ)` n'est pas
reconstituable depuis le code, et n'a pas été vérifié contre une vraie
distance géométrique. Ça ressemble à une simplification de l'auteur.
À confronter au matériel avant de s'y fier.

## Angle maximal selon la hauteur du point le plus bas

`θ_max = arcsin(z / garde)`

```
  z =  1 mm  ->   4,8°
  z =  2 mm  ->   9,6°
  z =  4 mm  ->  19,5°
  z =  6 mm  ->  30,0°
  z =  8,5 mm -> 45,1°   <- plafond utile atteint
  z = 12 mm  ->  90,0°
```

Conforme aux mesures : roue à aubes refusée dès 7°, cube à 30°, Y en
cylindres à 45°.

## La contrainte tient dans une bande de 8,5 mm

Hauteur minimale pour atteindre 45° :

| garde | z minimal |
|---|---|
| 12 mm (Cortex par défaut) | 8,49 mm |
| 8 mm (hotend court) | 5,66 mm |
| 20,5 mm (hypothèse Volcano) | 14,50 mm |

**Au-dessus de 8,5 mm, le plateau seul fait déjà 45°.** Tête inclinable,
hotend court, refroidissement déporté ne servent qu'à élargir cette bande.

## La parade : embase sacrificielle de 9 mm

Concevoir les pièces avec une embase d'au moins 9 mm, imprimée à plat en
3 axes, avant toute réorientation. Au-delà, les 45° sont disponibles sans
contrainte.

Elle résout **trois** problèmes :

1. **enveloppe angulaire** — les 45° disponibles
2. **surface d'adhérence** — proportionnelle à la résistance au cisaillement
3. **éloignement de l'amorce de pelage** — sans embase, le levier s'applique
   sur les premières couches de la pièce réelle, souvent les plus délicates

| Solution | Gain | Coût |
|---|---|---|
| **Embase sacrificielle 9 mm** | bande → 0 | conception pièce |
| Hotend court (garde 8 mm) | bande → 5,7 mm | choix de composant |
| Tête inclinable 20° | bande → 5,1 mm | 3e axe + IK + slicer |

Limite : inopérante quand la géométrie basse est elle-même ce qu'il faut
réorienter. Une roue radiale ouverte en est l'exemple — la matière
contrainte *est* la pièce.

**Pas de contournement par montage réutilisable** : `align_mesh_base_to_xy`
remet systématiquement la base de chaque chunk à z=0. Une plaque épaisse
sous le lit ne change rien. Les 9 mm doivent être imprimés.

## Efforts pendant et après réorientation

Vitesses lues dans `printer.cfg` (`rotation_distance` 90 et 24) : **A
tourne à 24,4 °/s, B à 5,4 °/s**, mouvements de ~3,7 s synchronisés.

**Inertie de rotation : négligeable.** ω = 0,426 rad/s → 0,28 % de g à
150 mm de l'axe.

**La gravité une fois incliné est la vraie contrainte**, et elle est
permanente pendant toute l'impression du chunk suivant :

| θ | cisaillement (pièce 200 g) | part du poids |
|---|---|---|
| 20° | 0,67 N | 34,2 % |
| 45° | 1,39 N | 70,7 % |

**Le pelage est le mode de rupture, pas le glissement.** Moment
m·g·sin(θ)·h : 83,2 N·mm à 45° pour une pièce de 200 g dont le centre de
gravité est à 60 mm. Contraintes au bord faibles — une adhérence correcte
tient largement. Relation utile :

> Doubler la largeur d'embase divise la contrainte au bord par 4.

## Piste v2 — tête inclinable

Ajouter une inclinaison de tête bornée, en gardant la TRT : machine à
6 axes pour 5 degrés de liberté, donc **redondante**. Le degré excédentaire
donne un espace nul exploitable pour maximiser la garde.

| z du point le plus bas | plateau seul | + tête 20° |
|---|---|---|
| **0,0 mm** | **0,0°** | **20,0°** |
| 1,0 mm | 4,8° | 24,8° |
| 4,0 mm | 19,5° | 39,5° |
| 8,0 mm | 41,8° | 61,8° |

Le gain est maximal là où la machine actuelle refuse tout.

Prix : masse en rotation sur le portique, passage du filament à travers une
articulation, calcul de garde devenu vraiment 3D, aucun firmware ni slicer
existant.

**Variante bien moins chère** : inclinaison **fixe** de la tête, sans
actionneur. L'axe A du plateau existe déjà pour orienter la pièce face à
elle. Zéro moteur, zéro cinématique nouvelle. Défaut : tête inclinée en
permanence, ce qui complique la première couche.

### Contrainte filament — pivot autour de la pointe

Entrée du filament à h mm au-dessus de la pointe, basculement θ :

- déport latéral = h·sin(θ)
- descente = h·(1 − cos θ)

À h=60 mm et θ=20° : 20,5 mm de déport, 3,6 mm de descente.

Longueur de gaine libre nécessaire pour rester au-dessus de R=40 mm
(seuil sûr pour du PLA 1,75) :

```
  tête 15° -> déport 15,5 mm -> gaine >= 61 mm
  tête 20° -> déport 20,5 mm -> gaine >= 70 mm
  tête 30° -> déport 30,0 mm -> gaine >= 85 mm
```

**70 à 85 mm de mou : une boucle de service, pas une contrainte
d'architecture.** Le danger réel n'est pas le rayon instantané mais la
fatigue au même point, le PLA chaud immobile dans un coude, et les chargés
fibre.

**Un hotend court aide deux fois** : moins d'encombrement face au plateau
*et* moins de débattement du filament. Le Volcano, avec ses 8,5 mm de
chambre en plus que le V6, pénalise les deux.
