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

## D9 — Test de collision buse-piece

**Pourquoi** : c'est le seul trou fonctionnel sans solution sur etagere.
Cortex ne teste que la garde plateau-buse ; aucun slicer 3 axes ne peut
aider, puisqu'il ignore que le plateau s'incline.

**Ce qui rend le probleme tractable** : pendant l'impression d'un chunk le
plateau ne bouge pas. Dans le repere de ce chunk, tout ce qui est deja
imprime est un solide fixe -- le test redevient statique et purement
geometrique.

**Modele de buse** : une hauteur de garde requise en fonction de la
distance horizontale, `h(r) = r / tan(alpha)`. La matiere a distance `r`
doit rester sous `z_pointe + h(r)`. La garde de 12 mm codee en dur dans
Cortex devient une consequence du modele au lieu d'une constante magique.
`alpha` et le rayon utile ne sont pas independants : un alpha proche de
90 deg avec un grand rayon decrit un disque plat a hauteur de pointe,
physiquement absurde.

**Deux etages** : une carte de hauteurs depiste vite sur tous les points,
puis un lancer de rayons sur le maillage reel confirme le pire point.
La carte approxime -- sa dilatation d'une cellule deplace une valeur haute
et fausse la distance rapportee ; le lancer de rayons n'approxime rien.

**Resultat sur la piece en Y a 30 deg** : les deux bras entrent en
collision. Chunk 1, buse a Z=0,20 mm avec de la matiere haute de 5,11 mm
a 1,50 mm de distance -- penetration confirmee **3,41 mm**. Chunk 2, buse
a Z=1,40 mm, matiere a 5,66 mm a 0,25 mm -- penetration **4,01 mm**.

**Ce que ca veut dire** : la piece de reference de ce projet n'est pas
imprimable telle quelle. Le tronc, une fois le bras redresse a la
verticale, se dresse immediatement a cote de la base du bras. Cortex ne
l'a jamais signale parce qu'il ne teste pas ce cas.

**Trois faux negatifs rencontres en construisant l'outil**, tous du meme
type -- un verdict rassurant obtenu en ne testant rien :

1. **Reperes disjoints.** Le slicer externe centre la piece sur son
   plateau (X100 Y100), les maillages sont centres sur l'origine. Le test
   comparait deux regions sans recouvrement et ne trouvait jamais rien.
2. **Marqueur de chunk absent.** Le format de Cortex (`;Chunk 0`) n'etait
   pas reconnu : le fichier n'etait pas analyse du tout. L'outil leve
   desormais une erreur si aucun chunk n'est trouve.
3. **Recalage pollue.** Les deplacements de degagement (parking a Y-175)
   entraient dans l'emprise et decalaient le centre de 8 mm. Le recalage
   ne se calcule plus que sur les points d'extrusion, toujours sur la
   piece.

**Le repere est desormais publie, pas devine** : `stitch_chunks.py` ecrit
`; HYDRA5X_REPERE chunk=N cx=.. cy=..`. En son absence l'outil previent
que son recalage est une deduction invarifiable et que son verdict
n'engage a rien.

### Aucune decoupe du Y ne passe

`tools/sweep_decomposition.py` balaie inclinaison des bras et hauteur du
plan de coupe, en echantillonnant les sections au lieu de trancher.

| bras \ coupe | 26 | 28 | 29 | 30 | 31 | 32 |
|---|---|---|---|---|---|---|
| 10° | 5,17 | 3,22 | **2,23** | n/a | n/a | n/a |
| 20° | 5,61 | 3,58 | 3,89 | n/a | n/a | n/a |
| 25° | 5,53 | 5,37 | 4,46 | n/a | n/a | n/a |
| 30° | 5,86 | 5,53 | 5,00 | 4,13 | n/a | n/a |
| 40° | 7,79 | 6,26 | 5,49 | 4,72 | 3,40 | 2,65 |

Penetration max en mm ; `n/a` = decoupe degeneree. **Aucune case ne passe.**

**Ce qui commande, ce n'est pas l'angle.** A hauteur fixee, passer de 10° a
40° change la penetration de moins de 2 mm ; passer de z=20 a z=31 la fait
tomber de 10 mm a 1 mm. Logique retrospective : ce qui percute est le
tronc dresse a cote de la base du bras, et sa hauteur au point de jonction
depend de l'altitude de coupe, pas de l'angle de redressement.

**Aucune buse ne corrige.** A 45° comme a 80° de demi-angle, la meme
2,23 mm : la matiere fautive est a moins d'un millimetre de la pointe, la
ou aucun cone n'a d'effet. Le meilleur cas, confirme par lancer de rayons,
laisse **1,47 mm** de penetration -- un muret de 2,42 mm a 0,75 mm de la
buse. C'est une rainure etroite ou la buse ne rentre pas, pas un probleme
de degagement conique.

**Conclusion** : cette geometrie en Y, decoupee par demi-espaces, est
structurellement incompatible avec une buse reelle. La parade n'est pas
dans les parametres mais dans la strategie -- trancher les bras en
plusieurs blocs, ou accepter du support sur la jonction.

**Cinquieme faux negatif**, meme famille que les quatre autres : le premier
balayage annoncait une decoupe sans collision a 25°/34 mm. Le plan de
coupe passait **au-dessus** d'une piece haute de 32,1 mm : les chunks
"reorientes" pesaient 0,1 mm3. Zero collision parce qu'il n'y avait plus
de multidirectionnel. Un garde-fou rejette desormais toute decoupe dont
les chunks reorientes font moins de 2 % du volume.

---

## D10 — Eclats booleens : toutes les mesures de collision etaient faussees

**Ce qui a ete trouve** : chaque chunk produit par `decouper()` traine une
nuee de **composantes de volume nul** -- quelques facettes chacune,
dispersees n'importe ou dans la piece. Artefacts des differences
booleennes de manifold3d. Le chunk 0 du coude : 1 composante reelle de
1 355,7 mm3 et **neuf eclats**, dont certains a 30 mm de distance et 43 mm
de hauteur.

Ils ne changent pas le volume, donc le controle de coherence volumique de
`export_chunks.py` les laissait passer. Mais ils etendent la boite
englobante a toute la piece, ils apparaissent dans la carte de hauteurs,
et les rayons les touchent. **Le detecteur mesurait des artefacts.**

**Correction** : `nettoyer()` ne garde que les composantes dont le volume
depasse 1e-6 du total.

**Effet sur les mesures** :

| | avant nettoyage | apres |
|---|---|---|
| coude 90°, 4 chunks | 24 a 31 mm | **0,53 a 0,58 mm** |
| Y a 30° | 4,63 mm | **4,19 mm** |

Le coude passe -- le residu est du bruit de grille, le lancer de rayons
confirme **zero contact** sur les trois chunks. Le Y collisionne vraiment :
sa mesure bouge a peine, D9 tient.

**Ce qui est retire** : la premiere version de ce D10 annoncait une loi
`penetration ~ 0,9 x H`, H etant la hauteur dont le deja-imprime depasse le
plan de base. Cette hauteur etait celle de la nuee d'eclats, qui couvre
toute la piece -- d'ou la correlation, qui ne mesurait que la taille de la
piece. La loi est retiree. Le critere qualitatif -- apres reorientation,
rien de deja imprime ne doit se dresser a cote du plan de base -- reste
valide, mais il n'est plus quantifie.

**Septieme faux resultat de la session, et le plus couteux** : les six
precedents etaient des faux negatifs -- un verdict rassurant obtenu sans
rien tester. Celui-ci est un faux POSITIF massif, qui a fait conclure a
l'impossibilite de geometries parfaitement imprimables. Le signal qui
aurait du alerter plus tot : une penetration de 31 mm sur une piece haute
de 48 mm, soit la buse enfoncee aux deux tiers de la piece. C'etait
absurde et je l'ai rapporte sans le questionner.

---

## D11 — Ce que le multidirectionnel rapporte vraiment : 17 % de matiere

Premiere demonstration complete de la chaine, sur une piece de la bonne
famille : un coude, tube de 6 mm de rayon, virage a 90°, rayon de courbure
30 mm. `tools/parts.py`.

**Le critere passe.** Decoupe en 4 chunks perpendiculaires a l'axe du
tube : penetration 0,53 a 0,58 mm au depistage, et **zero contact confirme
au lancer de rayons** sur les trois chunks reorientes. C'est la premiere
geometrie du projet qui passe le test de collision.

**Mais le gain matiere est faible.**

| Chunks | Sans support | Avec support | Surcout | Economie vs 3 axes |
|---|---|---|---|---|
| 3 axes | 1 215 mm | 1 961 mm | +61 % | -- |
| 4 | 1 426 mm | 1 672 mm | +17,2 % | 14,8 % |
| **6** | **1 500 mm** | **1 626 mm** | **+8,4 %** | **17,1 %** |
| 8 | 1 570 mm | 1 865 mm | +18,8 % | 4,9 % |
| 12 | 1 700 mm | 1 946 mm | +14,5 % | 0,8 % |

Deux effets s'opposent. Plus de chunks aplatit chaque bloc et reduit le
support interne. Mais **chaque coupe coute** : parois et faces pleines
supplementaires. Sans aucun support, la piece passe de 1 215 mm en 3 axes
a 1 700 mm en 12 chunks -- +40 % de matiere rien qu'en decoupant.

L'optimum est a 6 chunks, pour **17 % d'economie**.

**Ce que ca veut dire pour la decision materielle** : 17 % de filament ne
justifient pas 2 600 $ et deux axes. **L'argument matiere ne tient pas.**

Les arguments qui restent, et qui n'ont pas ete mesures :

- **Le support irretirable.** Un canal interne coude ne se desupporte pas.
  La valeur n'y est pas de 17 %, elle est binaire.
- **L'etat de surface** sous les zones supportees.
- **La tenue mecanique.** C'est probablement le vrai argument : en
  multidirectionnel les couches suivent la courbe du tube, alors qu'en
  3 axes elles sont toutes horizontales et le coude delamine en flexion.
  Non mesure, et non mesurable sans machine.

**Conclusion honnete** : la chaine fonctionne et le critere discrimine, mais
la justification economique du multidirectionnel ne passe pas par la
matiere. Elle passe par les pieces qu'on ne peut pas desupporter et par
l'orientation des couches -- deux choses que ce projet n'a pas encore
chiffrees.

---

## D12 — L'argument de tenue mecanique ne tient pas non plus

D11 laissait l'orientation des couches comme dernier argument : « en
multidirectionnel les couches suivent la courbe, donc le coude delamine
moins ». **C'est faux, et l'inverse est vrai.**

**Methode** : `tools/fea_bending.py`, solveur elements finis ecrit ici pour
pouvoir etre valide. Coude creux (r_int 4, r_ext 6, courbure 30, 90°),
encastre a la base, charge verticale en bout. Champ de contraintes calcule
une fois en elastique isotrope, puis projete sur deux champs d'orientation
de couches via `sigma_n = n . sigma . n` -- une piece imprimee casse entre
les couches, pas dans le plan d'une couche.

**Validation du solveur** : poutre tubulaire encastree contre
Euler-Bernoulli. Convergence monotone par le bas -- 34,8 %, 19,0 %,
10,2 %, **6,2 %** d'ecart en raffinant. Comportement attendu d'un
tetraedre lineaire (verrouillage en cisaillement). La comparaison portant
sur un rapport entre deux champs d'orientation appliques au MEME champ de
contraintes, l'erreur de discretisation s'annule.

**Resultat** :

| zone | 3 axes | multidirectionnel | gain |
|---|---|---|---|
| piece entiere | 2,617 MPa | 2,617 MPa | 0,0 % |
| virage seul | 1,745 MPa | 1,767 MPa | **-1,2 %** |
| partie droite | 2,617 MPa | 2,617 MPa | 0,0 % |

**Pourquoi l'intuition etait fausse** : en multidirectionnel, chaque chunk
est pose sur son plan de coupe, lequel est **perpendiculaire** a l'axe du
tube. Les couches ne suivent pas la courbe, elles s'empilent le long du
tube. Une contrainte axiale de flexion tire droit a travers les interfaces.
En 3 axes les couches sont horizontales : dans la partie couchee du coude
elles sont **paralleles** a l'axe, donc bien orientees contre l'effort.

Le pic global tombe a l'encastrement (station 0), dans la partie droite
verticale, identique dans les deux schemas -- d'ou le 0,0 % sur la piece
entiere.

**Portee du resultat** : un cas de charge, une geometrie. Une piece dont la
direction d'impression multidirectionnelle s'aligne avec l'effort
principal y gagnerait. Mais pour un tube en flexion -- le cas d'ecole du
multidirectionnel -- le gain est nul a legerement negatif.

**Ou en est la justification du multidirectionnel** :

| argument | statut |
|---|---|
| economie de matiere | mesure : **17 %** (D11) |
| tenue mecanique | mesure : **nulle a -1,2 %** |
| support irretirable | non mesure, valeur binaire |
| etat de surface | non mesure |

Il ne reste que le support irretirable -- canaux internes, cavites fermees.
C'est un argument reel mais etroit : il ne concerne pas les pieces qu'on
peut desupporter, donc la plupart.

---

## D13 — Le support irretirable : reel, et hors de portee quand meme

Dernier argument encore debout apres D11 et D12. Mesure sur un bloc massif
traverse d'un canal coude a 90°, diametre 10 mm -- `parts.bloc_a_canal()`,
51 x 24 x 47 mm, maillage etanche.

**L'argument est confirme, et il est bien binaire** :

| | filament |
|---|---|
| sans support | 7 704,58 mm |
| support partout | 8 074,83 mm |
| support **depuis le plateau seulement** | 7 704,58 mm |

La troisieme ligne est identique a la premiere : **aucun support ne part du
plateau**. Les 370 mm generes sont integralement a l'interieur du canal.
En 3 axes cette piece n'est pas plus chere, elle est **irrecevable**.

**Mais le multidirectionnel ne la sauve pas** : collision de 25 a 27 mm sur
tous les chunks, confirmee au lancer de rayons.

**Le mecanisme, et il n'est pas celui qu'on croit.** Le chunk 1 a la meme
direction que le chunk 0 -- une simple coupe horizontale, sans
reorientation -- et collisionne pourtant de 25 mm. Parce que dans le modele
de Cortex, `chunk 0` n'est pas « le bas de la piece » : c'est **tout ce que
les demi-espaces ulterieurs n'ont pas reclame**, coins hauts du bloc
compris. Il domine donc tous les chunks suivants.

**Ce n'est pas une limite de la cinematique TRT, c'est une limite du modele
de decoupe** : un demi-espace par chunk, les ulterieurs cisele's dans les
precedents. Ce modele sait produire une pile de tranches sur une piece
elancee ; il ne sait pas decouper un volume massif en escalier.

**Conclusion** : les pieces a canal interne sont precisement celles qui
sont massives, et la masse est ce que ce modele de decoupe ne sait pas
traiter. L'argument survit en theorie et meurt en pratique.

**Bilan des quatre arguments** :

| argument | verdict |
|---|---|
| economie de matiere | 17 %, insuffisant (D11) |
| tenue mecanique | nulle a -1,2 % (D12) |
| support irretirable | reel, mais la piece collisionne (D13) |
| etat de surface | non mesure |

Aucun ne justifie a lui seul 2 600 $ et deux axes supplementaires. Ce qui
reste du projet est **l'outillage de mesure** : il repond, chiffres a
l'appui, a une question que ni Cortex ni Fractal ne posent -- pour cette
piece, le 5 axes sert-il, et de combien.

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
