# Identité HYDRA

Ces fichiers sont une version web du pack de marque. **L'original est sur
le NAS**, `11_HYDRA/01_IMAGES/HYDRA_brand_pack_v3_exact/` — il contient en
plus les cartes de visite, les icônes carrées, les aplats 1024 et les
sources.

| Fichier | Usage |
|---|---|
| `hydra-logo.jpg` | logo principal, encre et aquarelle |
| `hydra-croquis.jpg` | variante croquis technique |
| `icon-32/64/128/256.png` | icônes rondes, tirées du pack |
| `hydra.ico` | icône Windows du pack, illustration complète |
| `favicon.svg` | marque réduite, lisible en petit |
| `favicon-16/32.png`, `favicon.ico` | déclinaisons du favicon |
| `apple-touch-icon.png` | 180 px, écrans d'accueil iOS |

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
petites tailles. `hydra.ico` et les `icon-*.png` du pack héritent de ce
défaut — les garder pour les grands formats, pas pour un onglet.

## Le favicon

`favicon.svg` est dérivé du logo, pas inventé à côté : c'est le **museau
de la tête droite**, extrait au seuil 100 et vectorisé.

- cadrage source `(545, 245) → (665, 365)`, suréchantillonné ×8 avant seuillage
- **une seule forme claire** sur disque d'encre, plus l'œil
- œil `#1f6fb2` en `cx=225 cy=212`, position mesurée par détection de teinte

Deux choses apprises en le faisant, utiles si quelqu'un refait le travail :

- **Sélectionner « les plus grandes formes » ne marche pas.** Les deux
  plus grandes zones claires sont le papier autour de la tête, pas la
  tête. Il faut identifier les masses par leur contenu.
- **Ajouter une deuxième forme dessert.** Le croc devient un îlot détaché
  qui se lit comme une tache. Une masse claire creusée par l'encre — la
  gueule ouverte est un vide, pas un objet — reste plus net à 16 px.

2,4 Ko et une seule courbe, contre 13 Ko et quatorze pour la tête entière.

## Points à trancher

- Le logo porte **HYDRA**, le dépôt s'appelle **hydra5x**. La baseline dit
  « CNC 5 AXIS | FDM | OPEN SOURCE », donc le 5 axes est présent — mais les
  deux noms coexistent sans être accordés.
- La variante croquis contient une coquille : **« Peeple »** au lieu de
  « People ».
