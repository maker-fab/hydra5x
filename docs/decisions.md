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

## D7 — Reprendre Cortex en fork maintenu

**Pourquoi** : toute la chaîne repose sur un slicer inactif depuis le
22 juillet 2025 — dernier commit sur le README seul, deux issues ouvertes
en octobre 2025 sans réponse, PR #4 sans réaction. Dépendre d'un projet
mort sans en assurer la maintenance, c'est reporter la panne, pas l'éviter.

Le fork est [maker-fab/hydra5x-slicer](https://github.com/maker-fab/hydra5x-slicer),
GPL-3.0 conservée, filiation GitHub conservée, crédit à Fractal Robotics
explicite dans le README et modifications déclarées comme la licence
l'exige. La PR amont reste ouverte : si Fractal Robotics revient, les
correctifs les attendent.

**Ce que la décision débloque, et qui n'était pas évident** :

- **D4 s'inverse.** Le vrai correctif du figeage GUI — créer le pool de
  processus une seule fois à l'import, avant que pyglet ne lance ses
  threads — avait été jugé hors proportion : il fallait refondre 8 sites
  d'appel dans le code d'un tiers, à re-patcher indéfiniment. En possédant
  le code, l'objection tombe.
- **Le verrou `numpy<2` devient attaquable.** `trimesh 4.3.1` utilise
  `ndarray.ptp()`, supprimé dans NumPy 2, d'où les deux environnements
  séparés. Monter trimesh est risqué — mais `test_limits.py` et les G-code
  de référence octet pour octet existent déjà. Le harnais n'avait pas été
  construit pour ça ; c'est pourtant lui qui rend la tentative raisonnable.

**Chantiers, par rapport valeur/risque** : garde plateau-buse
configurable, puis sortie du verrou `numpy<2`, puis figeage du GUI, puis
collision buse-pièce — le seul vrai trou fonctionnel, et le plus dur.

**Ce que ça coûte** : un engagement de maintenance. Un fork non maintenu
est pire que pas de fork, il divise l'attention sans rien réparer.

---

## D8 — Deleguer le tranchage des chunks a un slicer mature

**Pourquoi la question se pose** : le coeur de Cortex fait 1 878 lignes.
OrcaSlicer represente 49 Mo de C++, 880 contributeurs et quinze ans de
lignee depuis Slic3r. Viser la parite fonctionnelle est une illusion.

Mais un chunk pose a plat **est** une piece 3 axes ordinaire. D'ou le
partage : Cortex garde la decomposition, la garde plateau-buse et la
couture du G-code avec les reorientations — ce que personne d'autre ne
fait. Un slicer mature tranche chaque chunk, avec ses perimetres, ses
supports et ses profils.

**Mesure sur le chunk principal du Y**, tranche par Cortex seul :

| | |
|---|---|
| couches | 141 |
| filament | 15 728 mm |
| trajet extrude | 30 170 mm |
| trajet a vide | 16 009 mm (53 % du trajet extrude) |
| retractions | **2 946**, soit ~21 par couche |
| infill | 83 s de calcul |

2 946 retractions sur une piece quasi cylindrique et un deplacement a vide
valant la moitie du trajet utile : marqueurs d'un ordonnancement faible.
Un slicer mature fait du *combing* — il contourne en restant dans la piece
plutot que de retracter.

**Mesure comparative, meme chunk, meme hauteur de couche** :

| | Cortex | PrusaSlicer 2.7.2 | ecart |
|---|---|---|---|
| couches | 141 | 140 | -0,7 % |
| filament | 1 003 mm | 1 328 mm | **+32 %** |
| trajet extrude | 30 170 mm | 39 229 mm | +30 % |
| trajet a vide | 16 009 mm | 5 478 mm | **-66 %** |
| retractions | 2 946 | 499 | **-83 %** |
| lignes de G-code | 85 268 | 34 130 | -60 % |

Rapporte a la couche : **20,9 retractions chez Cortex contre 3,6**. Et le
trajet a vide passe de 53 % du trajet extrude a 14 %. C'est le *combing* :
Prusa contourne en restant dans la piece la ou Cortex leve et retracte.

**Le contre-sens a ne pas commettre** : Prusa depose **plus** de matiere,
pas moins -- 3 194 mm3 contre 2 412, soit 55 % du volume plein contre
41 %. A 20 % de remplissage annonce des deux cotes, Cortex **sous-extrude**.
Ce n'est pas un gain d'efficacite de sa part, c'est un defaut : parois
trop maigres. L'ecart de +32 % de filament est donc a son desavantage,
pas au notre.

**Erreur commise en mesurant** : la premiere version de `compare_slicers.py`
comptait les reprises apres retraction comme de l'extrusion, ce qui
gonflait le filament de 2 495 mm chez Prusa et 14 727 mm chez Cortex --
et donnait un faux « -76 % de filament », exactement l'inverse de la
realite. Un mouvement d'extrudeur sans deplacement XYZ n'est pas une
extrusion. Le correctif fait retomber la mesure sur les chiffres que les
deux slicers annoncent eux-memes : 1 328,0 contre 1 328,02 annonce par
Prusa, 1 002,9 contre un dernier E a 1 002,89 chez Cortex.

**Chaine complete, piece en Y entiere** (`tools/stitch_chunks.py`) :

| | Cortex | chunks Prusa cousus | ecart |
|---|---|---|---|
| couches | 173 | 144 | -17 % |
| filament | 1 166 mm | 1 577 mm | +35 % |
| trajet extrude | 35 076 mm | 46 440 mm | +32 % |
| trajet a vide | 18 352 mm | 7 715 mm | **-58 %** |
| retractions | 3 542 | 622 | **-82 %** |
| lignes de G-code | 100 499 | 37 728 | -63 % |

20,5 retractions par couche contre 4,3. Matiere deposee : 43 % du volume
plein contre 59 % -- la sous-extrusion de Cortex se confirme a l'echelle
de la piece.

Le contrat machine est inchange : angles et vitesses decomposees
identiques au chiffre pres a la reference Cortex, retour a l'origine
compris.

**Les quatre pieges de la couture**, dans l'ordre ou ils mordent :

1. **La "premiere couche" du chunk 1 se pose sur du plastique.** Vitesse
   reduite, surepaisseur, compensation de pied d'elephant et surchauffe
   d'accroche deviennent des defauts. Neutralises par chunk.
2. **Les prologues s'empilent.** Sans filtrage la machine se re-origine et
   rechauffe a chaque frontiere.
3. **L'axe E repart de zero** a chaque chunk : G92 E0 a chaque frontiere.
4. **Le labourage.** Le corps du chunk descend a la hauteur de couche a la
   position de degagement, puis traverse le plateau a 0,2 mm -- la buse
   racle ce qui est deja imprime. Trouve en relisant la sortie, pas
   prevu. Corrige : positionnement XY a altitude de garde, descente
   ensuite.

**Ce qui n'est pas resolu** : aucune validation physique, et la collision
buse-piece reste non testee -- ni par Cortex, ni par Prusa qui ignore le
plateau incline, ni par la couture.

**Conclusion** : l'ecart est structurel, pas cosmetique. La delegation du
tranchage a un slicer mature est justifiee.

**Ce qui bloque la voie OrcaSlicer** : la CLI d'OrcaSlicer est
inutilisable en 2.4.2. Son controle de compatibilite process/machine
compare des noms litteraux la ou l'interface evalue
`compatible_printers_condition` ; toute paire de prereglages passee par
`--load-settings` sort en `CLI_PROCESS_NOT_COMPATIBLE` (-17) avant meme
la moindre action, `--export-3mf` compris. Le defaut est decrit dans leur
propre code sur `main`, symptome et code de sortie compris ; le correctif
n'est dans aucune version publiee — ni la 2.4.2 du 7 juillet 2026, ni la
nightly, qui date de 2024.

Quatre configurations tentees : prereglages aplatis, heritage conserve,
compatibilite recablee explicitement, `--datadir` dedie. Meme code a
chaque fois. Sans prereglage du tout, Orca echoue plus tot encore (-51) :
son profil par defaut combine E relatif et `layer_gcode` vide,
combinaison qu'il refuse lui-meme.

**Ce que ca change pour l'architecture** : les options necessaires existent
bien (`--rotate_x`, `--cut`, `--ground_face_normal`), mais la CLI d'Orca
est une surface mal maintenue. Y adosser la chaine, c'est en heriter la
fragilite. La mesure passe donc par **PrusaSlicer**, meme lignee, CLI
stable depuis quinze ans, disponible en paquet distribution.

**Ce que la delegation ne resoudra pas** : aucun slicer 3 axes ne connait
le plateau incline. La collision entre la buse et la matiere deja deposee
reste entierement a la charge de ce projet.

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
