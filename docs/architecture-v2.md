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
  Mesuré en D-encombrement : le moteur n'est pas limitant géométriquement
  (56-58°), mais il l'est dynamiquement.
- **Filament à travers une articulation.** Chiffré dans `envelope.md` :
  70 à 85 mm de mou suffisent, une boucle de service.
- **Dépôt désaligné de la gravité** quand B est grand. Le TRT gardait le
  cordon toujours pressé sur la couche ; ici non. C'est le vrai coût, et il
  n'est pas mesuré.
- **Rien n'existe côté firmware.** Klipper ne connaît pas cette
  cinématique ; RepRapFirmware la fait sur 4 axes chez Bird.

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
