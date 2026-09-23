# Chiffrage — BOM, usinage, prérequis

Source : `fractalrobotics/Fractal-5-Pro`, `BOM/BOM.xlsx` (204 lignes) et
`CAD/Fractal_5_Pro_Assembly.zip`.

## Matière : 2 456 $

Prix d'achat réel, packs minimum. Le README de Fractal annonce ~1 900 $ —
l'écart vient du surplus de visserie acheté par boîte entière.

| Catégorie | Coût | Réfs |
|---|---|---|
| Additional Hardware | 634 $ | 29 |
| Electronics | 576 $ | 20 |
| McMaster Hardware | 410 $ | 43 |
| Extrusions (Misumi) | 326 $ | 10 |
| Machined Parts — matière brute | 288 $ | 7 |
| Enclosure Panels | 182 $ | 6 |
| ABS pour pièces imprimées | 40 $ | — |

## Usinage : 150-370 € — absent du BOM

Les 288 $ ne couvrent que la matière brute. **Le coût de découpe n'est
chiffré nulle part.**

Mesuré sur la CAO (STEP chargé via OpenCascade, longueur de coupe calculée
exactement : pour un solide d'épaisseur *e*,
`(surface_totale − 2 × aire_projetée) / e` = longueur de chant) :

**17 pièces en alu 1/8" (3,175 mm), 10,08 m de découpe, 0,233 m² de
pièces.** Tôle achetée 0,581 m² → utilisation 40 %, nesting normal.

| Pièce (L × l) | Aire | Coupe |
|---|---|---|
| 480,0 × 50,8 | 242 cm² | 1,18 m |
| 380,0 × 100,0 | 330 cm² | 1,38 m |
| **324,0 × 324,0** — plateau | 822 cm² | 1,20 m |
| 301,6 × 263,7 — base gimbal | 448 cm² | 1,72 m |
| 190,0 × 124,5 ×2 — flasques | 127 cm² | 0,93 m ch. |
| 387,4 × 12,7 — règle de lit | 49 cm² | 0,80 m |
| + 10 plus petites | | 1,95 m |

| Filière | €/m | Découpe |
|---|---|---|
| Service en ligne EU | 8-14 | **80-140 €** |
| Prestataire local | 15-25 | 150-250 € |
| Fablab | 3-6 | 30-60 € |

Hors laser : **25-40 €** tournage arbre Ø30 (coupe à 75 mm), **40-80 €**
fraisage des barres 3/8"×1" et 3/4"×3/4".

**Budget réel : 2 600-2 900 $.**

## Les 21 pièces usinées — le point dur

Quasiment toutes en aluminium 1/8" découpé CNC, plus du tournage. Le
**gimbal** en concentre 13 : plaques latérales gauche/droite/base, plateau
d'entraînement et plateau de fabrication Ø324 mm, goussets d'angle, brides
d'arbre, arbre Ø30 tourné.

Composants clés du gimbal, à commander tôt :

- **bague tournante (slip ring) 22 mm OD**, 36 $ — achemine puissance et
  signal vers le plateau chauffant en rotation, pièce critique
- **chauffant Kapton Ø300 mm 24 V**, 21 $
- arbre Ø30 sur roulements, précontrainte par rondelle ondulée empilée
- courroie fermée + poulie GT2 20T pour l'axe A
- seulement 2 pièces imprimées fonctionnelles : B-Gear et A-Shaft Pulley

## Électronique

Octopus Pro + **8 × TMC2209** + Raspberry Pi (hôte Klipper). **7 moteurs** :
CoreXY (2), 3 vis-mères Z, extrudeur, axe B — plus un A-Stepper séparé.
Extrudeur Bondtech LGX Lite V2, hotend E3D Volcano, palpeur inductif Omron.

Le choix du Volcano mérite réexamen : chambre de fusion allongée (+8,5 mm
vs V6), optimisée pour le débit, à l'inverse de ce que réclame l'enveloppe
d'inclinaison. Voir `envelope.md`.

## CAO

**Un seul fichier STEP** (19 Mo compressé, 103 Mo déplié, 985 solides).
Universel à ouvrir, mais **géométrie morte** : pas d'historique
paramétrique, pas d'esquisses. Suffisant pour usiner et mesurer, pénible
pour modifier.

## DXF pour devis

Extraits par `tools/export_dxf.py`, dans `fabrication/` :

- **11 profils alu** 3,175 mm, 0,233 m² — `dxf-alu/`
- **16 panneaux caisson** 3,0 mm, 2,301 m² — `dxf-caisson/`

Planches de contrôle : `dxf_planche.png`, `dxf_caisson_planche.png`.
Géométrie vérifiée avec `ezdxf` — lignes, arcs, cercles cohérents.

## Prérequis non évidents

1. **Accès CNC** (ou prestataire) pour la tôle alu 1/8", plus un **tour**
   pour l'arbre Ø30.
2. **Une imprimante capable d'ABS** — les pièces imprimées sont en ABS,
   donc caisson fermé. Il faut une bonne 3 axes avant de construire la
   5 axes.
