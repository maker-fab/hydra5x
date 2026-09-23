# Décisions d'architecture

Chaque entrée : ce qui a été décidé, pourquoi, et ce qui la remettrait en
cause. **Ne pas rouvrir sans élément neuf.**

---

## D1 — Le projet est un démonstrateur, assumé

La machine est l'objectif. La pièce visée (roue radiale ouverte) est un
prétexte, pas une justification.

**Pourquoi** : mesuré que la roue ne justifie pas les 5 axes — tilt
utilisable ≤ 5°, et le 3 axes la produit correctement (littérature :
fonctionnelle à 1500 tr/min, moyeu en bas + lissage chimique).

**Ce que ça implique** : critère de succès = la machine imprime en
multidirectionnel et est comprise de bout en bout. Pas « une pièce sortie
mieux qu'en 3 axes ». Les pièces de test servent à *montrer* la capacité,
pas à l'exiger.

**Ne pas rouvrir** « à quoi ça sert » / « quelle pièce le justifie ». Posé,
mesuré, tranché. Si une pièce pertinente apparaît — haute, étroite,
surplombs multidirectionnels, section modeste aux plans de coupe — tant
mieux, ce sera un bonus.

---

## D2 — Cinématique TRT, base Fractal 5 Pro

Plateau assurant rotation (A) et basculement (B), tête fixe en XYZ.

**Pourquoi** : tête légère et simple — bonne dynamique, hotend standard,
pas de filament traversant une articulation. Et Fractal fournit CAD + BOM +
Klipper + slicer, la seule pile complète existante.

**Alternatives écartées** : Rep5x et Open5x sont tête-tête (HH), avec les
problèmes inverses. Open5x exige en plus Rhino/Grasshopper, payant.

**Conséquence non évidente** : la tête étant immobile, elle ne peut jamais
s'écarter. Son encombrement est une contrainte fixe que rien ne compense —
d'où le poids de chaque millimètre sous la buse. Sur une machine tête-tête
le raisonnement serait inverse.

---

## D3 — Chemin 1 : Fractal tel que conçu, Klipper, Cortex

**Pas** de Marlin `PENTA_AXIS_TRT` avec TCP firmware.

**Pourquoi** : le chemin 2 (Marlin + TCP) achèterait du mouvement 5 axes
coordonné, dont aucun slicer conformal ne permet l'usage aujourd'hui. Et
changer de firmware casse la sortie de Cortex — `MANUAL_STEPPER
STEPPER=stepper_a` est du Klipper, Marlin ne le comprend pas — obligeant à
réécrire `write_5_axis_gcode`.

**Ce qui la remettrait en cause** : l'apparition d'un slicer conformal
utilisable. La mécanique étant identique, le passage à Marlin reste
possible plus tard — seules l'électronique et la config changent.

---

## D4 — Slicing en headless, GUI pour préparer et visualiser

**Pourquoi** : le slicing depuis le GUI de Cortex se fige. Mesuré : 33 min
sans progression, CPU 282 %, **0 processus enfant**, RSS figé,
`utime=363 962 / stime=266 471` — 42 % du temps CPU en temps système, donc
contention de verrous, pas du travail.

Cause : `fork()` depuis un processus multi-threadé (boucle pyglet + thread
de slicing), ce que Python signale par un `DeprecationWarning` à chaque
étape parallèle. En headless le processus est mono-thread.

**Trois correctifs tentés, aucun ne tient** :

- `ThreadPoolExecutor` — l'optimisation des chemins est du Python pur, donc
  tenue par le GIL : les threads se piétinent
- `mp_context='forkserver'` — `_fixup_main_from_path` ré-exécute le module
  principal dans le worker
- `mp_context='spawn'` — même problème de ré-import

**Le correctif qui marcherait** : créer le pool une seule fois à l'import
de `slicing_functions`, avant que pyglet ne lance ses threads. Demande de
refondre les 8 sites d'appel et leurs blocs `with`. Hors proportion, la
voie headless étant validée.

---

## D5 — Voie multidirectionnelle, pas non-planaire continu

**Pourquoi** : le non-planaire continu n'a aucun outil utilisable —
S3-Slicer et Neural Slicer sont du code d'article ACM.

**Découverte structurante** : les deux voies n'ont pas les mêmes besoins
matériels. Le multidirectionnel n'exige **ni mouvement 5 axes coordonné ni
cinématique TCP** — c'est de l'impression 3 axes entrecoupée de
réorientations discrètes. Vérifié dans le code de Cortex : entre chunks il
lève Z, parque la tête, tourne le plateau, reprend. La buse n'imprime
jamais inclinée.

C'est pourquoi tout le travail sur `PENTA_AXIS_HH` ne sert que pour la voie
continue.

---

## D6 — Licence : GPL-3.0, CERN-OHL-S pour le matériel

**Pourquoi** : largement contraint. Cortex et Fractal 5 Pro sont GPL-3.0,
la cinématique de référence dérive de Marlin, GPL-3.0 également. Reste
`export_dxf.py`, original — GPL-3.0 par cohérence.

La GPL étant une licence logicielle mal ajustée à la mécanique, toute pièce
publiée le sera sous **CERN-OHL-S**, la variante fortement réciproque.

**Conséquence** : le double licensing est fermé — il exige de détenir tout
le copyright, impossible en dérivant de Cortex. Les modèles compatibles
restent la vente de matériel, de kits, de service et d'intégration.

---

## Erreurs commises — pour ne pas les refaire

Le schéma est constant : **le raisonnement géométrique et logique a tenu,
les estimations de grandeurs physiques ont été fausses**. Toutes ont été
corrigées par la mesure.

| Affirmation | Réalité |
|---|---|
| « G43/G49 pas compilés en mono-extrudeur » | faux — les deux fonctionnent |
| « le builder web produit une cinématique morte » | faux — `G43.4` active bien le TCP |
| « des couches perdent de la matière » | faux — polygones dégénérés d'aire nulle, rien n'était perdu |
| plaques gimbal ~350 × 250 mm | 301,6 × 263,7 et 190 × 124,5 — surestimé de 50 % |
| « l'inertie de rotation va arracher la pièce » | 0,28 % de g — c'est la gravité qui compte |
| envelopper 985 solides avant de filtrer | >17 h sans aboutir ; filtrage OCP d'abord → 15 min |
| `transformShape(plane.rG)` pour aplatir | mauvais sens — 5 DXF sur 11 avec une dimension nulle |

**Règle qui en découle** : ne jamais publier une estimation de grandeur
physique sans l'avoir mesurée. Le calcul de vérification coûte toujours
moins cher que la correction.
