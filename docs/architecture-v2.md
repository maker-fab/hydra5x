# Architecture v2 — inspirée du Core R-Theta

Proposition, pas décision. Elle s'appuie sur tout ce qui a été mesuré dans
`decisions.md` et sur une machine qui existe, tourne, et publie sa CAO.

## Ce qu'on prend, et à qui

| Idée | Source | Pourquoi |
|---|---|---|
| **Plateau qui tourne sans jamais basculer** | [Core R-Theta](https://github.com/jyjblrd/Core-R-Theta-4-Axis-Printer) | supprime le décollement, et **supprime le mode de collision mesuré en D9 et D13** — c'est le basculement de la pièce qui dressait les murs |
| **Buse inclinable à grande course** | idem, B de −180° à +90° | accès en biais dans les rainures, que le TRT ne peut pas |
| **Plateau chauffant en PCB** | idem, KiCad publié | plan, léger, bon marché |
| Tranchage non-planaire | [S4 Slicer](https://github.com/jyjblrd/S4_Slicer), GPL-3.0 | tourne ici, `tools/s4_headless.py` |
| Délégation à un slicer mature | ce projet, D8 et D11 | −82 % de rétractions ; S4 fait pareil |
| Bloc cylindrique, refroidissement annulaire | Rapido, CHC | mesuré : 22,3° contre 17,7° |
| Cinématique de référence validée | ce projet, `kinematics/` | PENTA_AXIS corrigé, deux bugs signalés en amont |

## La différence avec Fractal

| | Fractal 5 Pro (TRT) | v2 proposée |
|---|---|---|
| Tête | XYZ, fixe en orientation | XYZ **+ inclinaison B** |
| Plateau | rotation A **+ basculement B** | rotation A **seule** |
| Berceau basculant | oui, lourd et encombrant | **supprimé** |
| Garde plateau-buse 12 mm | contrainte structurante | **sans objet** — le plateau reste plat |
| Pièce qui se décolle | risque à fort angle | **impossible** |

Cinq axes : X, Y, Z, A (plateau), B (buse). La rotation A et l'inclinaison
B donnent les deux degrés d'orientation, X/Y/Z la position — sans le
couplage du Core R-Theta, qui utilise C à la fois pour l'azimut de position
et pour celui d'orientation, faute d'axe Y.

## Le point que j'avais mal lu

Les **22,3° mesurés sur le CHC Pro ne sont pas une limite d'orientation
globale.**

- En multidirectionnel planaire, la couche est horizontale dans le repère
  machine, la buse verticale. L'inclinaison sert *entre* les chunks, et la
  gêne vient de la matière déjà déposée, de travers.
- En non-planaire, la buse est **perpendiculaire à la surface locale**.
  L'angle buse-surface est nul par construction.

Les 22,3° bornent donc la **géométrie locale** — combien une concavité peut
être serrée, à quelle distance un mur voisin peut se dresser — pas la
course de B. C'est pourquoi le Core R-Theta va à −180° sans difficulté.

## Ce que ça coûte, honnêtement

- **Masse et encombrement sur la tête.** Le moteur B s'ajoute au hotend.
  Mesuré : le moteur n'est pas limitant géométriquement (56-58°), mais il
  l'est dynamiquement. **Levée par le montage Core de Bird** — voir la
  variante ci-dessus, les moteurs restent sur le chariot.
- **Filament à travers une articulation.** Chiffré dans `envelope.md` :
  70 à 85 mm de mou suffisent, une boucle de service.
- **Dépôt désaligné de la gravité** quand B est grand. Le TRT gardait le
  cordon toujours pressé sur la couche ; ici non. C'est le vrai coût, et il
  n'est pas mesuré.
- **Rien n'existe côté firmware.** Klipper ne connaît pas cette
  cinématique ; RepRapFirmware la fait sur 4 axes chez Bird.

## Variante — table 3 points, tête rotative déportée

Deux idées qui se combinent bien.

### Table sur trois points indépendants

Trois actionneurs verticaux sous le plateau donnent `Z` **plus le
basculement dans n'importe quel azimut** — pas un axe B unique. Cinématique
parallèle, type tripode.

**Ce que ça supprime** : l'axe A. La pièce n'a jamais à tourner sur
elle-même, donc ni collecteur tournant, ni enroulement de câbles. Et le
berceau basculant disparaît, avec la garde de 12 mm.

Débattement, calculé :

| entraxe | course | inclinaison | utile (80 %) |
|---|---|---|---|
| 200 mm | 100 mm | 26,6° | 21,3° |
| 160 mm | 80 mm | 26,6° | 21,3° |
| 120 mm | 120 mm | 45,0° | 36,0° |

Avec 21,3° de table et une tête améliorée à ~26°, on atteint **47°** — la
cible de 45° établie dans ce fichier.

### Le montage « Core » de Bird : les moteurs quittent la tête

Le [Core R-Theta](https://www.3dnatives.com/imprimante-3d-polaire-4-axes-core-r%CE%B8-joshua-bird-23122024/)
utilise **deux moteurs reliés par une courroie qui pilotent à la fois la
translation X et la rotation de la tête** — un CoreXY appliqué à X et B.

Les deux moteurs restent fixes sur le chariot Z. **Rien de lourd ne bouge
avec la buse.** C'est la réponse directe à l'objection « masse sur la tête »
listée plus bas : elle tombe.

Coût annoncé de leur machine : **300 à 400 $**, contre 2 600 à 2 900 pour
la Fractal.

### Ce que cette variante coûte

- **La pièce bascule quand même.** Le mode de collision de D9 et D13
  revient, réduit proportionnellement — 21° au lieu de 45° — mais pas
  supprimé. C'est l'avantage que la configuration mixte pure avait.
- **Aucun firmware.** Ni Klipper ni RepRapFirmware n'ont de cinématique
  pour une table 3 points basculante. À écrire.
- **Couplage Z/inclinaison** : basculer déplace la hauteur du centre, à
  compenser.
- **Redondance** : tête (2 DOF) + table (3 DOF) + X/Y = sept axes pour six
  degrés de liberté. Ce n'est pas un défaut — `envelope.md` le notait pour
  la piste v2 : **le degré excédentaire donne un espace nul exploitable**.
  La machine peut choisir, parmi les postures qui placent correctement la
  buse, celle qui maximise la garde. C'est ce qui pourrait annuler le
  retour du problème de collision, et ça se calcule avec
  `check_collision.py`.

## Ce qu'il faudrait mesurer avant de décider

1. **Le dépôt à B élevé** — le cordon tient-il sur une couche inclinée de
   45° par rapport à la gravité ? Non simulable honnêtement, demande une
   machine ou des essais.
2. **La chaîne S4 de bout en bout** sur une de nos pièces, pour comparer
   au régime discret déjà mesuré.
3. **Le profil de silhouette d'une tête à B intégré** — la nôtre n'existe
   pas, il faudrait la dessiner avant de la mesurer.

## Ce qui reste valide du travail existant

Toute la chaîne logicielle : détection de collision, mesure dans le
G-code, délégation au slicer, cinématique de référence. D17 l'a établi —
le multidirectionnel est la discrétisation grossière du non-planaire, donc
les outils opèrent au même endroit, juste à une autre résolution.

Ce qui tombe : la garde plateau-buse comme contrainte structurante, et
l'enveloppe angulaire bâtie dessus.
