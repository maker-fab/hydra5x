# Emprunts — ce qu'on prend ailleurs

`decisions.md` tranche. Ce fichier-ci **accumule**. Une limitation n'est pas
un échec, c'est un paramètre à contourner — et la plupart des contournements
existent déjà, ailleurs, chez des gens qui ont buté sur la même chose.

Une machine se construit avec beaucoup de petites idées venues de partout.
On n'invente que ce qui n'existe nulle part.

**Statuts** : `à évaluer` · `retenu` · `écarté` avec la raison · `bloqué`
avec ce qui manque.

---

## Cinématique et trajectoires

| Emprunt | Source | Résout | Statut |
|---|---|---|---|
| Tranchage courbe aligné sur les contraintes | [S³-Slicer](https://dl.acm.org/doi/10.1145/3550454.3555516), BSD-3 · [code](https://github.com/zhangty019/S3_DeformFDM) | +176 % à la rupture, là où le multidirectionnel planaire donne 0 | **à évaluer** — l'argument mécanique du projet en dépend |
| Tranchage neuronal multi-axes | [NeuralSlicer](https://github.com/RyanTaoLiu/NeuralSlicer), **GPL-3.0** | idem, licence directement combinable | **à évaluer** |
| Découpe conforme | [Open5x](https://ar5iv.labs.arxiv.org/html/2202.11426) | référence du domaine | écarté — dépend de Rhino/Grasshopper, payant |
| Non-planaire sur 3 axes | mods Slic3r / PrusaSlicer | état de surface, sans axe supplémentaire | à évaluer — utile même sans la machine |
| Répartition table + tête | ce projet, `envelope_hybride.py` | les deux limites sont indépendantes et se cumulent | **retenu** |

## Tête et thermique

| Emprunt | Source | Résout | Statut |
|---|---|---|---|
| Chauffage annulaire céramique | E3D Revo, Phaetus Rapido | permet un bloc étroit : la cartouche Ø6 posée à côté du canal interdisait de descendre sous ~Ø16 | **retenu en principe** — cotes à relever |
| Bloc cylindrique | Rapido | supprime la direction défavorable ; sur une tête qui tourne, un bloc carré présente tôt ou tard sa diagonale | **retenu en principe** |
| Refroidissement annulaire | conduits intégrés haut débit | 51,8° au lieu de 23,2°, **et** supprime la dépendance à la direction | **retenu en principe** |
| Chaussette silicone | — | à retirer ou redessiner : 18,4°, elle borne la machine pour quelques euros | à évaluer |
| Extrudeur compact | LGX Lite, Sherpa Mini, Orbiter | masse sur tête mobile | **sans effet sur l'inclinaison** — mesuré à 56-58°, jamais limitant |

## Mécanique

| Emprunt | Source | Résout | Statut |
|---|---|---|---|
| Base TRT complète | [Fractal 5 Pro](https://github.com/fractalrobotics/Fractal-5-Pro), GPL-3.0 | CAO + BOM + Klipper, la seule pile complète | **retenu** — mais D2 rouverte |
| Configurations HH | Rep5x, Open5x | la pièce ne bascule pas ; adhérence et enveloppe préservées | à évaluer — voir D15 |
| Tête inclinable bridée | ce projet, piste v2 | soulage la garde plateau-buse | **retenu en principe** |
| Embase sacrificielle 9 mm | ce projet | supprime la contrainte des premiers millimètres | **retenu** |

## Logiciel

| Emprunt | Source | Résout | Statut |
|---|---|---|---|
| Fork Cortex maintenu | [hydra5x-slicer](https://github.com/maker-fab/hydra5x-slicer) | l'amont est inactif depuis juillet 2025 | **retenu** |
| Tranchage délégué à un slicer mature | PrusaSlicer en CLI | −82 % de rétractions, −58 % de trajet à vide | **retenu** |
| CLI OrcaSlicer | — | meilleure planification que Prusa | **bloqué** — bug de compatibilité en 2.4.2, correctif sur `main` non publié |

---

## Ce qui n'existe nulle part et qu'il faut écrire

- **Le test de collision buse-pièce.** Ni Cortex, ni aucun slicer 3 axes. Écrit ici : `check_collision.py`.
- **Le critère de faisabilité d'une pièce** sur cette classe de machine, avant achat.
- **La couture inter-chunks** avec neutralisation de la première couche.

C'est le périmètre où ce projet apporte quelque chose. Partout ailleurs, il
vaut mieux emprunter.
