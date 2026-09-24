# Emprunts — ce qu'on prend ailleurs

`decisions.md` tranche. Ce fichier-ci **accumule**. Une limitation n'est pas
un échec, c'est un paramètre à contourner — et la plupart des contournements
existent déjà, ailleurs, chez des gens qui ont buté sur la même chose.

Une machine se construit avec beaucoup de petites idées venues de partout.
On n'invente que ce qui n'existe nulle part.

**Statuts** : `à évaluer` · `retenu` · `écarté` avec la raison · `bloqué`
avec ce qui manque.

**Critère transverse** : un composant fermé prive d'un levier de réglage.
C'est une contrainte d'ingénierie, pas une position sur le libre — mais ce
n'est un problème que si le levier est nécessaire. **Mesurer d'abord,
écarter ensuite.** La ligne Revo a été corrigée pour cette raison : elle
disait « écarté » avant toute mesure.

---

## Cinématique et trajectoires

| Emprunt | Source | Résout | Statut |
|---|---|---|---|
| **Tranchage non-planaire générique** | **[S4 Slicer](https://github.com/jyjblrd/S4_Slicer), GPL-3.0**, 951 ★, maj 2025-04 | couches courbes continues, sans support. **Un seul notebook Python** : numpy, scipy, networkx, open3d, pyvista, tetgen, pygcode. Aucun CUDA, Qt ni MKL | **retenu pour évaluation** — le seul utilisable des trois |
| Tranchage courbe aligné sur les contraintes | [S³-Slicer](https://dl.acm.org/doi/10.1145/3550454.3555516), BSD-3 · [code](https://github.com/zhangty019/S3_DeformFDM) | +176 % à la rupture | **écarté en pratique** — Windows + Visual Studio + Qt + Intel oneMKL, piloté par une séquence de boutons dans une interface. Non scriptable |
| Tranchage neuronal multi-axes | [NeuralSlicer](https://github.com/RyanTaoLiu/NeuralSlicer), GPL-3.0 | idem | **écarté en pratique** — exige de compiler S³ d'abord ET d'y **greffer un bouton à la main** dans `MainWindow.ui`, plus PyTorch 1.11 / CUDA 11.3 |
| Découpe conforme | [Open5x](https://ar5iv.labs.arxiv.org/html/2202.11426) | référence du domaine | écarté — dépend de Rhino/Grasshopper, payant |
| Non-planaire sur 3 axes | mods Slic3r / PrusaSlicer | état de surface, sans axe supplémentaire | à évaluer — utile même sans la machine |
| Répartition table + tête | ce projet, `envelope_hybride.py` | les deux limites sont indépendantes et se cumulent | **retenu** |

## Tête et thermique

| Emprunt | Source | Résout | Statut |
|---|---|---|---|
| Chauffage annulaire céramique | Phaetus Rapido | supprime la cartouche Ø6 posée à côté du canal, qui interdisait de descendre sous ~Ø16 | **retenu en principe** — cotes à relever |
| E3D Revo | — | changement de buse à froid en moins d'une minute | **à mesurer** — écarté trop vite sur un principe. Le système est fermé, donc la protrusion n'est pas réglable ; mais si le profil de série est déjà bon, le levier est inutile. `mesurer_tete.py` tranchera. La variante **Voron** est la plus élancée du catalogue, à prendre en premier. |
| Bloc cylindrique | Rapido | supprime la direction défavorable ; sur une tête qui tourne, un bloc carré présente tôt ou tard sa diagonale | **retenu en principe** |
| Refroidissement annulaire | conduits intégrés haut débit | 51,8° au lieu de 23,2°, **et** supprime la dépendance à la direction | **retenu en principe** |
| Chaussette silicone | — | à retirer ou redessiner : 18,4°, elle borne la machine pour quelques euros | à évaluer |
| Extrudeur compact | LGX Lite, Sherpa Mini, Orbiter | masse sur tête mobile | **sans effet sur l'inclinaison** — mesuré à 56-58°, jamais limitant |

**Sortie de S4 Slicer** : axes `X, Z, C, B`, pas de Y — cinématique Core
R-Theta, la machine 4 axes de son auteur. `B` varie **en continu pendant le
dépôt**, donc du non-planaire vrai, pas du multidirectionnel par blocs.

Correspondance plausible vers la TRT de Fractal : `C→A`, `B→B`, `X→X`,
`Z→Z`, `Y=0`. Une TRT est une R-Theta avec un axe de plus, donc elle
devrait exécuter cette sortie telle quelle. **Non vérifié** — reste à
confirmer ce que `B` incline sur sa machine, plateau ou tête.

## Mécanique

| Emprunt | Source | Résout | Statut |
|---|---|---|---|
| Base TRT complète | [Fractal 5 Pro](https://github.com/fractalrobotics/Fractal-5-Pro), GPL-3.0 | CAO + BOM + Klipper, la seule pile complète | **retenu** — mais D2 rouverte |
| Configurations HH | Rep5x, Open5x | la pièce ne bascule pas ; adhérence et enveloppe préservées | à évaluer — voir D15 |
| **Configuration mixte 4 axes** | **[Core R-Theta](https://github.com/jyjblrd/Core-R-Theta-4-Axis-Printer)**, 915 ★, CAO STEP + PCB KiCad + config RepRapFirmware | plateau qui tourne sans basculer, **buse inclinable sur 270°** (B de −180° à +90°). Supprime le balancement de la pièce ET donne l'accès en biais | **à évaluer sérieusement** — voir D18 |
| Tête inclinable bridée | ce projet, piste v2 | soulage la garde plateau-buse | **retenu en principe** |
| **Montage « Core » X + B** | [Core R-Theta](https://github.com/jyjblrd/Core-R-Theta-4-Axis-Printer) | deux moteurs couplés par courroie pilotent translation ET rotation de tête, **les deux restent sur le chariot** — supprime la masse sur la buse | **retenu en principe** |
| **Bague tournante** | Fractal 5 Pro, Rep5x | rotation **sans limite** ; Fractal y passe l'alimentation du plateau chauffant | **retenu** — le problème d'enroulement est résolu, pas à contourner |
| Table 3 points parallèle | proposition | Z + basculement tout azimut sur trois actionneurs ; supprime le berceau | **à évaluer** — voir architecture-v2.md |
| Changeur multi-hotends | Archer, multipoleguy — [multipoledynamics.com](https://multipoledynamics.com/hardware) | quatre outils sur connecteurs rapides, électriques ET filament ; RepRapFirmware détecte le nombre d'outils et reconfigure l'interface | **écarté pour l'instant** — hors périmètre tant que la cinématique n'est pas figée, mais l'idée du connecteur rapide filament est à garder |
| **Plateau « Multipole »** | Archer, [Hardware](https://multipoledynamics.com/hardware) | plateau dont l'orientation change **en continu**, sur un CoreXY ordinaire, volume 300×300×350. Pas de berceau basculant visible | **à évaluer** — confirme que la voie « plateau orientable sans berceau » est tenue par quelqu'un d'autre ; **cinématique non publiée**, aucune CAO, rien à copier |
| **Changeur d'outil DAKSH V2** | [ankurv2k6/daksh-toolchanger-v2](https://github.com/ankurv2k6/daksh-toolchanger-v2), 337 ★ | changeur **entierement imprime**, aucune piece usinee, verrouillage mecanique sans servo inspire de la Prusa XL. Moins de 4 s par changement, calibration XYZ automatique entre outils, config et macros Klipper fournies. **Compatible Voron Trident** -- exactement la base retenue en D23 | **a evaluer serieusement** — mais licence contradictoire, voir ci-dessous |
| Embase sacrificielle 9 mm | ce projet | supprime la contrainte des premiers millimètres | **retenu** |

## Logiciel

| Emprunt | Source | Résout | Statut |
|---|---|---|---|
| Fork Cortex maintenu | [hydra5x-slicer](https://github.com/maker-fab/hydra5x-slicer) | l'amont est inactif depuis juillet 2025 | **retenu** |
| Tranchage délégué à un slicer mature | PrusaSlicer en CLI | −82 % de rétractions, −58 % de trajet à vide | **retenu** |
| MaxiSlicer | Archer — [Software](https://multipoledynamics.com/software) | slicer 5 axes non-planaire « pour tout le monde », multi-cinématiques, aussi utilisable en 3 axes | **écarté faute d'existence** — en développement, aucune version publiée, aucune licence annoncée, aucun dépôt. À re-regarder, pas à attendre |
| CLI OrcaSlicer | — | meilleure planification que Prusa | **bloqué** — bug de compatibilité en 2.4.2, correctif sur `main` non publié |

**Ce que dit Multipole Dynamics, et qui recoupe ce projet** : la 5 axes bute
sur un œuf et une poule — pas de machines parce qu'il n'y a pas de logiciel,
pas de logiciel parce qu'il n'y a pas de machines. Ils tranchent que **le
logiciel est le gros morceau**, et construisent une machine surtout pour
avoir de quoi le démontrer.

C'est la même conclusion qu'ici, obtenue autrement : la mécanique existe
déjà (Fractal, Core R-Theta, Rep5x, tous publiés), c'est le tranchage qui
manque. Différence de méthode : eux écrivent un slicer neuf et fermé, on
part d'un existant libre.

**Reserve de licence sur DAKSH V2** : le depot declare **CC0-1.0** (domaine
public, aucune restriction) alors que son README ecrit « can be used freely
for **non commercial** purposes ». Les deux ne peuvent pas etre vrais. Tant
que ce n'est pas leve par l'auteur, **on ne peut pas integrer ces fichiers**
dans un projet publie sous GPL-3.0 / CERN-OHL-S : une clause non commerciale
est incompatible avec les deux. L'idee reste libre a reprendre, les fichiers
non.

**Reserve technique** : DAKSH V2 s'appuie sur un **Z quadri-courroie**,
donc un plateau sur QUATRE points. Notre table basculante en demande
exactement trois. Le changeur lui-meme est cote TETE et se moque de ce que
fait le plateau (D20) -- c'est la partie a reprendre. Le systeme Z, non.

---

## Ce qui n'existe nulle part et qu'il faut écrire

- **Le test de collision buse-pièce.** Ni Cortex, ni aucun slicer 3 axes. Écrit ici : `check_collision.py`.
- **Le critère de faisabilité d'une pièce** sur cette classe de machine, avant achat.
- **La couture inter-chunks** avec neutralisation de la première couche.

C'est le périmètre où ce projet apporte quelque chose. Partout ailleurs, il
vaut mieux emprunter.
