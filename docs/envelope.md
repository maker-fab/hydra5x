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

> **Cette limite angulaire n'est pas la seule, ni la plus mordante.**
> La collision entre la buse et la matière déjà déposée est une contrainte
> **indépendante**, qui peut interdire une découpe bien avant que l'angle
> ne pose problème. La pièce de démonstration de ce dépôt tient largement
> dans les 45° et reste pourtant impossible à imprimer : le tronc se dresse
> à moins d'un millimètre de la base du bras. Voir
> [`decisions.md`](decisions.md) D9.

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

## Bases géométriques : table et tête se partagent l'inclinaison

Le dépôt raisonnait en « table **ou** tête ». C'est un faux choix. Les deux
contraintes sont de **nature différente**, donc indépendantes, et
l'inclinaison demandée se répartit :

```
θ_table + θ_tête  ≥  θ_demandé

  θ_table ≤ marge · arcsin( z / G )      ← dépend de z, NULLE à z = 0
  θ_tête  ≤ marge · min( α, bridage )    ← constante
```

`z` = hauteur du point le plus bas du chunk, `G` = garde plateau-buse
(12 mm chez Cortex), `α` = demi-angle du cône de buse. Le bridage vient du
bloc chauffant, de la ventilation et du passage du filament — c'est la
valeur à relever sur la CAO réelle.

**Pourquoi le cumul rapporte** : la limite de la table s'effondre quand la
pièce descend et vaut zéro au contact du plateau. Celle de la tête est
constante. **La tête couvre exactement là où la table est impuissante.**

`tools/envelope_hybride.py`. Hauteur minimale pour atteindre 45°, marge de
sécurité 80 % sur chaque axe :

| configuration | z minimal |
|---|---|
| table seule | **9,98 mm** |
| table + tête à 45° | **2,34 mm** |
| table + tête bridée à 20° | **7,10 mm** |

La bande contrainte passe de 10 mm à 2,3 mm — facteur 4. Toute la valeur
tient dans le bridage réel de la tête, qui est une question de CAO.

**Ordre de répartition** : charger la **tête en priorité**. Contre-intuitif,
mais la limite de la tête est constante alors que celle de la table se
raréfie quand la pièce descend. Avec une tête à 36° utiles, la table n'a
plus que 9° à fournir pour atteindre 45° — la garde plateau-buse cesse
d'être le facteur limitant.

**Réserve héritée** : tout repose sur `garde = z / sin(θ)`, modèle de
Cortex non reconstituable depuis son code et jamais confronté à une
distance géométrique réelle. À vérifier sur le matériel.

## Encombrement de la tête : ce qui borne vraiment

`tools/encombrement_tete.py`. Pivot au bout de la buse, chaque obstacle
réduit à son débord latéral `w` et sa hauteur `d` au-dessus de la pointe :

```
θ_max = arctan( d / w )
```

| obstacle | w | d | limite |
|---|---|---|---|
| **chaussette silicone** | 12 mm | 4 mm | **18,4°** |
| buse de ventilation pièce | 14 mm | 6 mm | 23,2° |
| coin bas du bloc Volcano | 10 mm | 4,5 mm | 24,2° |
| dissipateur | 15 mm | 16 mm | 46,8° |
| moteur direct drive | 30 mm | 45 mm | 56,3° |
| moteur LGX Lite compact | 25 mm | 40 mm | 58,0° |

**Le direct drive et l'électronique ne bornent rien.** Les déporter achète
de la masse et du câblage, pas un degré. `arctan(d/w)` est très favorable
dès qu'un obstacle est haut.

**Ce qui borne la machine tient dans un cylindre de 14 mm de rayon et 6 mm
de haut autour de la pointe.** Et les trois obstacles qui s'y trouvent sont
bon marché à traiter :

| | gain | coût |
|---|---|---|
| retirer la chaussette silicone | 18,4° → 23,2° | quelques euros |
| déporter la ventilation par conduit | 23,2° → 24,2° | une pièce imprimée |
| chanfreiner le coin du bloc | 24,2° → **32,7°** | une lime |

Les trois traités, l'outil donne **32,7° bruts / 26,2° utiles** — le coin
du bloc chanfreiné borne toujours. Atteindre le dissipateur à 46,8°
demanderait un bloc de 8,4 mm de large, irréaliste sur un Volcano.

**Correction** : une première rédaction annonçait 46,8° ici. C'était la
conclusion écrite avant lecture du chiffre — la même erreur que sur
l'orientation des couches (D12). 26,2° utiles restent un gain net contre
14,7°, mais la tête ne fournit pas les 45° seule.

**Réserve** : la protrusion de buse sous le bloc n'est pas publiée par E3D.
Les valeurs de `d` sont estimées. Le bloc Volcano 20×20×11,5 mm est
confirmé. Le tableau de sensibilité de l'outil vaut mieux que les valeurs
absolues — à relever au pied à coulisse.

### Mesure réelle : CHC Pro, depuis sa CAO

`tools/mesurer_tete.py` sur le STEP du CHC Pro, récupéré depuis
[Printables](https://www.printables.com/model/595187-triangle-labs-chc-pro-hotend).
**Le fichier n'est pas redistribué ici** — CAO tierce, licence non vérifiée,
même raison qui écarte de vendoriser Cortex. À télécharger pour reproduire :

```bash
.venv-dxf/bin/python3 tools/mesurer_tete.py "CHC Pro Hotend.stp"
```

Profil de silhouette `h(r)` = hauteur minimale de matière à la distance `r`
de l'axe, puis `θ_max = min_r arctan(h(r)/r)`.

| rayon | hauteur | angle | quoi |
|---|---|---|---|
| ≤ 1,25 mm | 0 | — | méplat de pointe, c'est le pivot |
| **1,50 mm** | 0,62 mm | **22,3°** | **cône de la buse** |
| 2,25–4,25 mm | 2,00 mm | 26–38° | épaulement |
| **6,00 mm** | 2,60 mm | **23,4°** | **face basse du bloc** |
| 8,25 mm | 4,24 mm | 27,9° | bord du bloc, Ø16,5 |
| ≥ 8,50 mm | 20,8 mm | 67° | au-dessus, sans effet |

**22,3° bruts, 17,8° utiles** — contre 17,7° / 14,2° estimés pour le
Volcano. Le CHC Pro gagne 26 %, mesuré et non supposé.

**Le résultat qui compte** : le cône de la buse et la face basse du bloc
bornent **à égalité**, 22,3° contre 23,4°. Corriger un seul ne rapporte
rien — chanfreiner le bloc plafonne à 22,3°, allonger la buse plafonne à
23,4°. Il faut les deux.

`encombrement_tete.py`, qui réduit chaque pièce à un point et garde le
pire, aurait manqué cette égalité. Seul le profil la montre.

### Longueur de buse et forme du bloc

`d = w · tan(θ)`. La question se pose naturellement sur `d`, mais **le
paramètre sensible est `w`**.

Et `w` n'est pas la demi-largeur : c'est la **demi-diagonale**, car un bloc
rectangulaire a une direction défavorable, et sur une tête qui tourne
autour de C cette direction finit toujours par se présenter.

À protrusion standard de 4,5 mm :

| bloc | w pire | limite | directionnel ? |
|---|---|---|---|
| Dragon / V6 23×16 | 11,5 mm | 21,4° | oui, axe long |
| Volcano 20×20 | **14,1 mm** | **17,7°** | oui, diagonale |
| cylindrique Ø14 | 7,0 mm | 32,7° | **non** |
| cylindrique Ø12 | 6,0 mm | **36,9°** | **non** |
| cylindrique Ø10 | 5,0 mm | 42,0° | **non** |

Un bloc cylindrique Ø12 double la limite **sans toucher à la buse**.

Protrusion nécessaire, sur ce bloc cylindrique Ø12 :

| cible utile | protrusion |
|---|---|
| 26° (budget partagé avec la table) | 3,8 mm — le standard suffit |
| 36° | **6,0 mm** — +1,5 mm, thermiquement négligeable |
| 45° (tête seule) | 9,0 mm — commence à poser problème |

**Réponse : 6 mm.** Le gain est maximal pour un coût thermique encore nul.
Au-delà, la protrusion n'est pas chauffée — la zone de fusion est dans le
bloc — et la pointe dérive en température.

**Ordre des travaux** : le bloc cylindrique d'abord, la buse ensuite.
Allonger la buse sur un bloc carré, c'est payer en thermique ce qu'on
obtient gratuitement en changeant la forme.

Le Rapido valide la faisabilité : chauffe cylindrique, bloc plus léger,
*« its cylindrical form allows even heating of the melting zone »*. La
symétrie de révolution chauffe mieux, elle ne coûte rien.

**Correction** : une première version de cette page prenait w = 10 mm pour
le Volcano, sa demi-largeur. C'est la demi-diagonale qui compte, 14,1 mm,
soit 17,7° et non 24,2°.

### Refroidissement annulaire : pas une optimisation, une nécessité

| solution | w | d | limite |
|---|---|---|---|
| buse latérale classique | 14 mm | 6 mm | 23,2° |
| conduit déporté, sortie à 10 mm | 12 mm | 10 mm | 39,8° |
| **canaux annulaires type turbine** | 11 mm | 14 mm | **51,8°** |
| canaux intégrés au dissipateur | 15 mm | 16 mm | 46,8° |

Le gain d'encombrement est réel — 51,8° sort le refroidissement de la liste
des contraintes. **Mais ce n'est pas l'argument principal.**

Une buse latérale souffle d'un seul côté. Sur une tête qui bascule et
tourne, la direction du refroidissement varie par rapport au cordon déposé
selon l'orientation, et à 30° d'inclinaison une partie du flux passe à
côté. Des canaux annulaires sont symétriques de révolution : indépendants
de l'inclinaison comme de la rotation.

Le refroidissement directionnel est déjà un défaut connu en 3 axes — d'où
les conduits doubles. Il devient **structurel** dès que la tête s'oriente.

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
