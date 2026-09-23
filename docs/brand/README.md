# Identité HYDRA

Ces fichiers sont une version web du pack de marque. **L'original est sur
le NAS**, `11_HYDRA/01_IMAGES/HYDRA_brand_pack_v3_exact/` — il contient en
plus les cartes de visite, les icônes carrées, les aplats 1024 et les
sources.

| Fichier | Usage |
|---|---|
| `hydra-logo.jpg` | logo principal, encre et aquarelle |
| `hydra-croquis.jpg` | variante croquis technique |
| `icon-32/64/128/256.png` | icônes rondes |
| `hydra.ico` | icône Windows multi-résolution |

## Limites à connaître avant d'imprimer

**La source maximale est 884 × 778 px.** Les icônes 1024 du pack sont des
agrandissements, pas une définition supérieure. À 300 dpi cela fait
**75 mm de large** : suffisant pour une carte de visite, insuffisant pour
une plaque de machine, une sérigraphie ou tout format au-delà de l'A6.
Le croquis technique est encore plus limité — 499 × 489.

**Il n'existe pas de version vectorielle.** Les fichiers `.svg` du pack
sont des conteneurs qui embarquent le PNG en base64 ; ils pèsent 1,8 Mo et
n'apportent rien de plus qu'un PNG. Le pack le dit lui-même. Une vraie
vectorisation demanderait un redessin.

**Le logo ne réduit pas.** À 64 px on devine la créature, à 32 px c'est une
tache bleu-gris. C'est une illustration, pas une marque conçue pour les
petites tailles — choix légitime, mais un favicon lisible reste à dessiner.

## Points à trancher

- Le logo porte **HYDRA**, le dépôt s'appelle **hydra5x**. La baseline dit
  « CNC 5 AXIS | FDM | OPEN SOURCE », donc le 5 axes est présent — mais les
  deux noms coexistent sans être accordés.
- La variante croquis contient une coquille : **« Peeple »** au lieu de
  « People ».
