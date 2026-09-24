# Essai de dépôt sur couche inclinée

La seule question que le calcul ne tranchera pas. Elle décide de
l'architecture, pas d'un réglage.

## Ce qui en dépend

| | si le cordon tient à 35-45° | si le cordon ne tient pas |
|---|---|---|
| Architecture (D23) | **tête inclinable** redevient meilleure — 3,5× le volume, cadre plus bas | plateau basculant confirmé |
| Deux mécanismes (D22) | inutiles | il faut plafonner la tête et laisser le plateau finir |
| Course des vis (D24) | 61 mm sur une platine de tête au lieu de 210 | 210 mm, bâti d'un mètre |
| Variante parallèle (D27) | devient le meilleur candidat | reste une note |

Trois décisions attendent ce résultat. Il ne coûte que quelques heures.

## Le montage : incliner l'imprimante, pas la pièce

**Aucune machine 5 axes n'est nécessaire.** Poser une imprimante 3 axes
entière sur une cale reproduit exactement la posture d'une tête
inclinable : la buse reste perpendiculaire à la couche, le plateau reste
sous elle, **seule la direction de la gravité change par rapport au plan
de dépôt.** C'est la même physique, pour le prix d'une cale.

Quatre cales : **0°, 15°, 30°, 45°**. La série de 0° est le témoin.

Précautions, dans l'ordre d'importance :

1. **Brider la machine sur la cale.** À 45° elle glisse, et une machine
   qui bouge pendant l'essai invalide tout.
2. **Séparer l'adhérence du fluage.** Le socle décollé et le cordon qui
   flue sont deux défauts différents, et l'inclinaison les provoque tous
   les deux. Colle ou bâton, jupe large, et on ne juge **que la paroi**.
3. **Bobine à part, alimentation libre.** Une bobine inclinée freine, et
   la sous-extrusion imiterait le fluage.
4. **Même profil, même bobine, même buse** aux quatre angles. Une seule
   variable.
5. Si la machine a un capteur de niveau, **le refaire à chaque angle** :
   son palpage n'est plus vertical par rapport à la gravité, et un
   premier couche mal réglé fausserait la lecture.

## La pièce : un cylindre à une paroi

`tools/piece_essai_incline.py` — cylindre Ø40 × 60 mm, paroi d'un seul
cordon, socle carré de 52 mm, quatre ergots repères. Environ 23 min
l'exemplaire, **1 h 30 pour les quatre angles**.

Un seul cordon par couche, et chaque couche parcourt **toutes les
directions par rapport à la pente**. Le défaut ne se cherche pas, il se
lit : le cordon flue vers l'aval, la paroi s'épaissit en bas de pente et
s'amincit en haut, et le cylindre devient excentré.

Une pièce donne donc la courbe complète en fonction de l'azimut, au lieu
d'un point. Les quatre ergots, de longueurs croissantes, repèrent les
azimuts 0, 90, 180 et 270° — sans eux, impossible de savoir où était
l'amont une fois la pièce détachée.

## Ce qu'on mesure

Au pied à coulisse, à trois hauteurs (15, 30, 45 mm) :

| mesure | ce qu'elle dit |
|---|---|
| épaisseur de paroi en amont et en aval | **le fluage** — c'est la mesure principale |
| excentrement du cylindre par rapport au socle | le cumul du fluage sur toute la hauteur |
| diamètre selon l'axe de pente et en travers | l'ovalisation |
| état de surface amont / aval, à l'œil | l'apparition de cordons non soudés |

Critère, à fixer **avant** de mesurer pour ne pas l'ajuster après :

- **écart de paroi amont/aval sous 15 %** → le dépôt tient, la tête
  inclinable est viable à cet angle ;
- **15 à 30 %** → utilisable avec précautions, c'est la zone où plafonner
  la tête et laisser le plateau finir (D22) prend son sens ;
- **au-delà de 30 %, ou paroi rompue** → le plateau basculant est
  confirmé, D23 tient.

## Ce que l'essai ne dira pas

- **Le comportement à une autre vitesse ou un autre matériau.** Le PLA à
  50 mm/s n'est pas l'ABS à 150. Le résultat borne l'architecture, pas la
  fenêtre de réglage.
- **L'effet du refroidissement dirigé.** Un ventilateur qui souffle d'un
  seul côté introduit sa propre asymétrie, et brouillerait la lecture
  d'azimut. **À couper, ou à rendre annulaire**, et à noter dans le
  compte rendu.
- **La tenue mécanique de la pièce finie.** Autre question, autre essai
  (D12, D14).

## Compte rendu attendu

Un tableau de seize lignes — quatre angles × quatre azimuts — les
épaisseurs mesurées, les photos des quatre pièces côte à côte, et la
réponse au critère ci-dessus. Il se range ici même, et il ferme D21, D22
et D27 d'un coup.
