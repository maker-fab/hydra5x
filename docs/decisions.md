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

## D2 — Cinématique TRT, base Fractal 5 Pro  ⟨REFERMÉE par D23 : table basculante retenue, mécanisme rouvert⟩

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

## D14 — L'etat de l'art dit l'inverse : 2 a 3x plus solide, et le code existe

Tout ce qui precede -- D11, D12, D13 -- mesure **une seule technique** : le
multidirectionnel PLANAIRE, des chunks plats reorientes entre eux. C'est ce
que fait Cortex, et c'est ce que ce depot a explore toute la journee.

La litterature mesure autre chose.

**Le tranchage courbe aligne sur les contraintes** ne suit pas la
geometrie, il suit le champ de contraintes principales calcule par
elements finis. Resultats publies :

| | gain |
|---|---|
| Reinforced FDM, SIGGRAPH Asia 2020 | **+176 %** de force a la rupture en traction, +27 % en compression |
| S³-Slicer, SIGGRAPH Asia 2022 | jusqu'a **203 %** de charge contre du planaire a direction optimisee |

Soit **2 a 3 fois plus solide**. Contre les 0 % a -1,2 % mesures en D12.

**D12 n'est pas faux, il est hors sujet.** Il mesure des couches planes
perpendiculaires a l'axe du tube -- normal qu'elles n'apportent rien. Les
couches courbes, elles, suivent reellement l'effort. La conclusion « la
tenue mecanique ne justifie pas le 5 axes » ne vaut que pour le
multidirectionnel planaire.

**Le code est disponible et sous licence compatible** :

| depot | etoiles | derniere maj | licence |
|---|---|---|---|
| `zhangty019/S3_DeformFDM` | 175 | 2025-04-24 | BSD-3-Clause |
| `RyanTaoLiu/NeuralSlicer` | 101 | 2024-10-15 | **GPL-3.0** |

**Ce que ca invalide dans ce depot** : D5 a ecarte le non-planaire continu
au motif qu'il « n'a que du code d'article ». Cette premisse est fausse.
Deux implementations maintenues existent, dont une en GPL-3.0, donc
directement combinable avec ce projet.

**Ce que ca revalorise** : `tools/fea_bending.py`, ecrit pour demolir
l'argument mecanique, calcule precisement le champ de contraintes dont ces
methodes ont besoin en entree. La premiere moitie du chemin est deja la,
construite sans le savoir.

**Reserve** : ce sont des codes de recherche. Disponible n'est pas
utilisable, et les chiffres publies sont ceux de leurs auteurs. A evaluer,
pas a croire -- c'est exactement l'erreur commise en D12, ou l'argument
mecanique a ete affirme deux fois avant d'etre calcule.

**Ce qui a fait trouver ca** : une remarque de l'utilisateur -- « si tu
restes bloque dans cette approche, tu risques de passer a cote ». Une
journee entiere passee a mesurer une technique sans verifier qu'elle etait
la bonne.

---

## D15 — D2 rouverte : la collision dépend de la configuration cinématique

Les quatre configurations canoniques de la 5 axes :

| | rotations | la pièce bouge ? |
|---|---|---|
| tête-tête (HH) | A+C ou B+C dans la broche | **non** |
| table-table (TRT) | C sur le plateau, A sur le berceau | **oui, elle bascule** |
| mixte tête-table | une de chaque | partiellement |

**Tout ce que ce dépôt a mesuré en collision — D9, D13 — porte sur le
TRT.** En TRT la pièce bascule : le déjà-imprimé pivote et vient se dresser
à côté de la buse. C'est le mode de défaillance mesuré sur le Y (2,35 mm
confirmés) et sur le bloc à canal (25 à 27 mm).

**En tête-tête, ce mode n'existe pas.** La pièce ne bouge jamais, le
déjà-imprimé reste où il est. La collision devient « corps de buse incliné
contre pièce » : locale, bornée par l'encombrement du bloc chauffant, et
c'est le problème classique de la CNC 5 axes — traité depuis des décennies.

**Le lien avec D14** : le tranchage courbe, celui qui donne 2 à 3× la
résistance, exige que l'axe de la buse varie par rapport à la surface. Le
tête-tête le fait nativement. Le TRT ne peut le faire qu'en tournant la
pièce entière, ce qui *cause* le balancement.

**Ce qui rend la réouverture légitime** : D2 a été tranché sur la dynamique
(tête légère, hotend standard, pas de filament dans une articulation) et
sur la disponibilité d'une pile complète chez Fractal. **La collision
n'était pas mesurée à l'époque.** Elle l'est maintenant et elle pointe dans
l'autre sens. D2 contenait déjà l'avertissement -- « sur une machine
tête-tête le raisonnement serait inverse » -- jamais appliqué aux mesures.

**Ironie du dépôt** : la cinématique extraite, corrigée et validée en
`kinematics/` -- `rep5x_ik.cpp`, `PENTA_AXIS_HH` -- **est du tête-tête**.
Le projet a validé HH puis retenu TRT pour le matériel.

**Ce qui n'est pas dit** : que TRT soit un mauvais choix. Ses raisons
tiennent. Le tête-tête paie en masse mobile, en filament traversant un
joint, et l'encombrement du bloc chauffant y limite l'inclinaison
utilisable. Aucune des deux n'a été chiffrée sur ce critère.

**Ce qu'il faut mesurer pour trancher** :

1. Rejouer `check_collision.py` en configuration HH -- pièce fixe, buse
   inclinée. Le test existe, seul le repère change.
2. Chiffrer l'inclinaison maximale d'un tête-tête réel, limitée par
   l'encombrement du hotend, comme la garde de 12 mm l'a été pour le TRT.
3. Comparer les deux sur la même pièce et le même critère.

Tant que ce n'est pas fait, D2 reste ouverte et le choix TRT n'est pas
justifié par la mesure -- seulement par la disponibilité.

---

## D16 — La plage d'inclinaison EST la specification de la machine

Question posee : a quoi sert de s'incliner au-dela de 90°, et pour quelle
piece ? La reponse relie plusieurs fils laisses separes.

**Le raisonnement des 45° est juste mais incomplet.** « 45° couvrent
tout » (envelope.md) vaut pour l'angle entre la normale d'une surface et la
direction de construction. Ce que la machine execute, c'est l'angle entre
les directions de deux chunks SUCCESSIFS. Ces deux-la peuvent etre
opposees.

**La piece qui exige plus de 90° est le re-entrant.** Un crochet : la tige
monte, la courbe revient vers le bas, sa face interne regarde vers le
bas-dedans. Pour l'imprimer a plat il faut tourner de plus de 90° par
rapport a la tige. Meme chose pour un C, une barbelure, une levre
interieure.

**Et c'est exactement le cas du support irretirable de D13.** Un re-entrant
est precisement ce qui piege le support. Le seul argument binaire du projet
et l'exigence des 90° sont **la meme chose**, formulee deux fois.

**Ce que ca coute.** Au-dela de 90° la piece est retournee : l'adherence au
plateau ne la tient plus, il faut du bridage mecanique. Ce n'est plus un
reglage, c'est une autre classe de machine. Cortex borne d'ailleurs son
champ d'angle a 0-90° (`widget_functions.py`, `S_theta`) : au-dela n'est
pas exprimable dans l'outil.

**L'asymetrie gravitaire, non formulee jusqu'ici, y compris dans D2** :

- **TRT** : la buse reste verticale, le plan de coupe devient horizontal.
  La gravite presse le cordon sur la couche precedente **a toute
  inclinaison**.
- **tete-tete** : la piece reste a plat, la couche deposee est inclinee de
  B. La gravite a une composante **dans le plan de la couche**, le cordon
  fondu glisse. A 90° il faudrait adherer sur un mur vertical.

C'est un argument fort pour le TRT que D2 n'avait pas identifie -- il avait
choisi sur la dynamique et la disponibilite. Et ca nuance D15, qui ne
regardait que la collision.

**La specification qui decoule** :

| plage de B | ce que ca couvre | ce que ca exige |
|---|---|---|
| **0 a ~50°** | tous les surplombs, sans exception | adherence au plateau suffit ; mecanisme simple et rigide |
| 50 a 90° | rien de plus en surplomb | inutile |
| **au-dela de 90°** | les re-entrants, donc le support irretirable | bridage mecanique, slicer a ecrire, autre classe de machine |

**La plage d'inclinaison est donc la decision structurante**, pas la
configuration cinematique. Elle determine le bridage, la rigidite, le cout,
et si le seul argument binaire du projet est dans le perimetre ou non.

**Ce qu'il faut trancher** : le re-entrant est-il dans le perimetre ?

- **Non** : borner a ~50°, et la machine se simplifie considerablement.
  Mais D11 a D13 ont montre que les autres arguments -- matiere, mecanique
  -- ne la justifient pas. Une machine simple pour un gain de 17 %.
- **Oui** : c'est le seul argument qui tienne, et il impose une machine que
  personne ne fabrique et un slicer que personne n'a ecrit.

---

## D17 — Le multidirectionnel est l'approximation discrete du non-planaire

En ouvrant le notebook de S4 Slicer, son architecture apparait -- et c'est
celle que ce projet a reinventee cet apres-midi sans le savoir.

**Ce que fait S4** :

1. maillage tetraedrique, champ de rotation pilote par les surplombs
2. **deformation du modele** pour rendre les surplombs imprimables a plat
3. export du STL deforme
4. « **Now, go and slice the stl file in Cura!** » -- un slicer 3 axes
   ordinaire fait perimetres, remplissage et supports
5. le G-code est relu, la **deformation inverse** lui est appliquee : les
   couches planes deviennent courbes et les axes rotatifs apparaissent

**S4 ne tranche pas.** Il deforme, delegue, puis de-deforme. C'est
exactement le principe de `stitch_chunks.py` -- delegation a PrusaSlicer,
recouture -- trouve independamment le meme jour (D8, D11).

**Et la relation entre les deux approches est une relation d'ordre** :

| | champ de rotation |
|---|---|
| multidirectionnel (Cortex, ce depot) | **constant par morceaux** -- un angle par chunk |
| non-planaire (S4, S³) | **continu** -- un angle par point |

Le multidirectionnel n'est pas une technique concurrente du non-planaire :
c'en est la discretisation la plus grossiere possible. Ce qui explique
retrospectivement tous les resultats de la journee :

- D12, tenue mecanique nulle : des couches planes perpendiculaires a l'axe
  du tube ne suivent rien. Un champ continu suit la courbe.
- D9 et D13, collisions : les sauts d'angle entre chunks creent les murs
  qui percutent. Un champ continu n'a pas de saut.
- D11, 17 % de matiere seulement : chaque coupe coute des parois et des
  faces pleines. Un champ continu n'a pas de coupe.

**Les trois limites mesurees sont des artefacts de la discretisation**, pas
des proprietes du 5 axes. C'est la conclusion que D14 annoncait sans la
demontrer ; l'architecture de S4 la rend evidente.

**Consequence pour le projet** : la chaine construite aujourd'hui --
decoupe, delegation, couture, detection de collision, mesure -- reste
valide. Elle opere juste au mauvais point du spectre. Passer au continu ne
demande pas de la jeter mais de remplacer le champ constant par morceaux
par un champ continu, et la recouture par une deformation inverse.

---

## D18 — La configuration mixte existe, marche, et est documentee

En cherchant d'ou venait le `MIN_ROTATION = -130°` de S4 Slicer, on tombe
sur la machine de son auteur :
[Core-R-Theta-4-Axis-Printer](https://github.com/jyjblrd/Core-R-Theta-4-Axis-Printer),
915 etoiles, maj juin 2025, avec CAO STEP complete, PCB du plateau en
KiCad, et config RepRapFirmware.

**Limites d'axes reelles**, relevees dans `to4axis.g` :

```
M208 C-20000000 X-37.5 Z-50 B-180 S1    ; minima
M208 C 20000000 X115.5 Z200  B  90 S0   ; maxima
```

| axe | course | ou |
|---|---|---|
| C | **continu**, sans butee | plateau |
| X | -37,5 a 115,5 mm, passe le centre | tete, radial |
| Z | -50 a 200 mm | tete |
| **B** | **-180° a +90°, soit 270°** | **la buse** |

Le README le dit : « leverages the printer's **rotating nozzle** ». C'est
la **quatrieme configuration canonique**, mixte tete-table -- une rotation
sur le plateau, une sur la tete.

**Ce que ce point de compromis apporte** :

| | plateau bascule ? | buse s'incline ? | depot aligne sur la gravite ? |
|---|---|---|---|
| TRT | oui | non | **oui, a tout angle** |
| tete-tete | non | oui | non |
| **mixte** | **non** | **oui** | non |

La mixte prend l'avantage du TRT -- la piece ne bascule jamais, donc ni
decollement ni balancement, donc pas le mode de collision mesure en D9 et
D13 -- **et** celui du tete-tete, la buse entre en biais. Elle paie le
desalignement gravitaire au depot, le point souleve en D16.

**Et elle repond a la question des 90°** : un B de -180° a +90° ne coute
rien quand c'est la buse qui tourne. La contrainte de bridage identifiee
en D16 ne s'applique qu'aux configurations ou la PIECE se retourne.

**Ce que ca change pour D2, rouverte en D15** : le choix n'etait pas binaire
TRT/HH. Il y a un troisieme point, realise, documente, avec sa CAO et son
firmware publics, et un slicer non-planaire ecrit pour lui.

**Reserve** : c'est une machine 4 axes, pas 5 -- pas de second axe de
rotation de la tete. Son enveloppe d'orientations est donc plus etroite
qu'une 5 axes complete, ce qui suffit pour du non-planaire de revolution
mais pas pour toute orientation.

---

## D19 — La base de construction, reprise a zero sur quatre points

Base demandee : **plateau inclinable, tete rotative, multi-tete, evaluation
de volume**. Les trois premiers se comptent en degres de liberte, le
quatrieme se calcule. `tools/volume_utile.py` fait le calcul.

### 1. Plateau inclinable — trois points, et la borne est dure

Trois actionneurs verticaux sous le plateau donnent **Z plus le basculement
dans n'importe quel azimut**. Pas de berceau, pas d'arbre Ø30, pas de bague
tournante, pas de garde plateau-buse de 12 mm.

La borne ne depend ni de la tete ni du slicer, seulement de l'empattement
et de la course des vis -- levier = 1,5 x rayon des points :

| rayon des points | course differentielle | brut | utile (80 %) |
|---|---|---|---|
| 100 mm | 100 mm | 33,7° | 27,0° |
| 100 mm | 150 mm | **45,0°** | **36,0°** |
| 150 mm | 100 mm | 24,0° | 19,2° |
| 150 mm | 200 mm | 41,6° | 33,3° |

**Un grand plateau s'incline mal.** Pour atteindre les 45° de D16 il faut
un plateau d'environ Ø200 et 150 mm de course differentielle. C'est le
premier arbitrage reel de la machine, et il pousse vers le petit.

Le materiel existe deja : **Voron Trident** est un CoreXY a trois moteurs Z
independants sous le plateau. Manquent seulement des rotules aux trois
appuis -- les siennes sont rigides -- la course differentielle, et la
cinematique firmware.

### 2. Tete rotative — lever l'ambiguite avant de chiffrer

Trois choses differentes portent ce nom :

| | degres de liberte d'orientation | ce que ca achete |
|---|---|---|
| rotation autour de son PROPRE axe (C) | **zero** | presenter la face etroite du bloc dans le sens de bascule |
| rotation autour d'un axe HORIZONTAL (bascule B) | **un** | l'acces en biais, mais la gravite tire le cordon (D16) |
| tete au bout d'un bras qui pivote | un, plus une translation couplee | idem, avec un porte-a-faux en plus |

Le premier cas est le seul gratuit, et il est **deja obtenu autrement** :
un bloc chauffant carre 20x20 limite a arctan(4,5/14,1) = 17,7° sur sa
diagonale et 24,2° sur sa face. Un bloc CYLINDRIQUE donne les 24,2° dans
toutes les directions, sans moteur. La rotation C ne rattrape que le defaut
d'un bloc carre.

**Consequence** : avec une table a trois points, la tete n'a besoin
d'aucun axe. Le compte tombe juste.

### 3. Le compte d'axes — cinq moteurs, cinq degres, aucune redondance

| | moteurs | apporte |
|---|---|---|
| chariot | X, Y | position horizontale |
| plateau | Z1, Z2, Z3 | hauteur + basculement dans tout azimut |

Cinq moteurs, trois degres de position et deux d'orientation. Le sixieme --
la rotation autour de l'axe de la buse -- **n'a pas de sens pour une buse
ronde**. Rien a supprimer, rien de redondant.

Ce que ca elimine par rapport au TRT de D2 : le berceau (13 des 21 pieces
usinees de la Fractal), la bague tournante, la garde plateau-buse, et le
decollement par rotation de la piece sur elle-meme.

Ce que ca conserve de D16 : la buse reste verticale, le plan de coupe
devient horizontal, **la gravite presse le cordon a toute inclinaison**.
C'est l'argument qui avait sauve le TRT, et il survit ici sans le berceau.

Ce que ca coute : **aucun firmware n'existe**. Ni Klipper ni RepRapFirmware
n'ont de cinematique de plateau basculant a trois points. La
cinematique directe et inverse sont fermees et courtes -- un plan par trois
points -- mais elles sont a ecrire et a homologuer.

### 4. Evaluation de volume — le chiffre que personne n'annonce

Quand le plateau s'incline de theta, la piece bascule avec lui : son point
haut monte, son enveloppe s'elargit, le bord du plateau plonge. Le volume
**garanti** -- celui ou n'importe quelle piece passe a n'importe quelle
inclinaison -- s'effondre.

Sur un cadre de Voron Trident 300 (X300 Y300 Z250) :

| inclinaison | cylindre utile | volume | perte |
|---|---|---|---|
| 0° | Ø300 x 250 | 17,67 L | — |
| 15° | Ø200 x 206 | 6,47 L | 63 % |
| 25° | Ø224 x 114 | 4,49 L | 75 % |
| 35° | Ø240 x 90 | 4,07 L | **77 %** |
| 45° | Ø284 x 70 | 4,43 L | 75 % |

**Une machine 5 axes a plateau inclinable est naturellement plate.** Le
terme dominant est `H.sin(theta)` : la hauteur coute beaucoup plus cher que
la largeur. Passe 20° l'optimum devient un galet large et bas, et le volume
ne bouge presque plus -- la perte est payee d'un coup, tot.

Il faut aussi **106 mm de vide sous un plateau Ø300 a 45°**, et 100 mm de
course Z mangee par la seule bascule.

**Honnetete du chiffre** : c'est le volume GARANTI. Une piece qui ne
demande 45° que sur un detail n'a pas besoin de toute l'enveloppe a 45° --
le volume reel est entre ce chiffre et celui a 0°, et depend de la piece.
Ce que le tableau borne, c'est ce qu'on peut promettre sans connaitre la
piece.

### 5. Multi-tete — le cout est en volume, pas en masse

Quatre docks de 55 x 60 mm le long du fond :

| | volume a 0° | volume a 35° |
|---|---|---|
| une tete | 17,67 L | 4,07 L |
| quatre tetes | 11,31 L | 2,08 L |

**Moitie du volume utile en moins**, a inclinaison egale. Et chaque outil
parque est un obstacle de plus dans le champ de bascule de la piece.

Le changeur d'outil de l'Archer est une belle piece d'ingenierie, mais
c'est une fonctionnalite de machine mature. **Hors perimetre tant que la
cinematique n'est pas figee** -- il se rajoute apres, il ne conditionne
rien.

### Ce que la base devient

**Cadre CoreXY ordinaire, plateau Ø200 sur trois actionneurs a 150 mm de
course differentielle, tete fixe a bloc cylindrique et refroidissement
annulaire, une seule tete.** Cinq moteurs, 36° utiles, environ 1,2 L
garanti.

Ce n'est pas une petite machine par economie : c'est ce que la geometrie
autorise. Le point dur n'est plus mecanique -- il est dans la cinematique
firmware, qui n'existe nulle part.

---

## D20 — Plateau carre, bascule a deux axes, et le chargement des tetes

Suite directe de D19, sur trois precisions demandees. `volume_utile.py` et
`table_3points.py` portent les calculs.

### Une correction a D19

Le tableau d'inclinaison des trois points y prenait un bras de levier de
1,5 x rayon. **C'est l'azimut favorable.** Un triangle equilateral a une
portee qui varie de 1,5 a 1,732 x rayon selon l'azimut de bascule. La
limite d'une machine est son pire azimut :

| rayon des appuis | course differentielle | pire azimut | utile (80 %) |
|---|---|---|---|
| 100 mm | 150 mm | **40,9°** (et non 45,0) | 32,7° |
| 150 mm | 150 mm | 30,0° | 24,0° |
| 150 mm | 200 mm | 37,6° | 30,1° |

### Plateau carre — gagnant a plat, perdant en bascule

Un plateau carre de 300 mm contient une piece de 300x300, la ou un Ø300
n'en contient qu'une de Ø300. A plat, **22,50 L contre 17,67 L**, +27 %.

En bascule, l'avantage s'inverse. La piece carree presente sa **diagonale**
dans les azimuts a 45° : 41 % d'etendue en plus, exactement la ou une table
a trois points equilaterale est deja la plus faible. Les deux anisotropies
se cumulent, elles ne se compensent pas.

Cadre X300 Y300 Z250, plateau carre 300 :

| inclinaison | piece carree | piece ronde |
|---|---|---|
| 0° | **22,50 L** | 17,67 L |
| 15° | 11,01 L | 9,98 L |
| 30° | 5,30 L | 7,45 L |
| 45° | **3,25 L** (−85,5 %) | **5,07 L** (−71,3 %) |

**Le plateau carre est le bon choix ; la piece carree ne l'est pas.** Passe
~25° d'inclinaison, un cylindre bat un cube de plus de 50 %. Le plateau
reste carre parce qu'il est plus simple a fabriquer, a chauffer et a
brider, et parce que le bas de la plage -- ou se fait le gros du travail --
lui donne raison.

Il faut aussi **150 mm de vide sous un plateau carre de 300 mm a 45°**,
contre 106 mm pour un Ø300 : c'est la diagonale du plateau qui plonge.

### Bascule a deux axes — un cardan, pas trois points

Deux rotations orthogonales composent leurs angles :

    cos(theta) = cos(alpha) . cos(beta)

**45° sur chaque axe donnent 60° de bascule reelle.** Le cardan est donc
plus efficace que ses courses ne le laissent croire -- mais seulement en
diagonale : 45,2° garantis dans le pire azimut, 60,0° en diagonale.

**Son anisotropie est l'inverse de celle des trois points** : fort en
diagonale, faible sur ses axes ; le triangle equilateral fait le contraire.
Mauvaise nouvelle pour un plateau carre, dont la diagonale est justement
l'azimut ou la piece deborde le plus. La encore, les defauts se cumulent.

Ce que le cardan coute face aux trois points : le berceau revient, avec ses
paliers, son encombrement et sa masse -- c'est ce que D19 avait supprime.
Ce qu'il apporte : deux axes rotatifs vrais, donc **une course angulaire
non bornee par une course lineaire**, et une cinematique que Fractal a deja
ecrite pour Klipper.

**La hauteur du pivot ne change rien au volume.** Deplacer le centre de
rotation ajoute une translation, et l'encombrement d'un solide est
invariant par translation. Un cardan sous le plateau change ou la piece se
trouve, pas la course qu'il faut pour la promener. Il ne compte que pour la
plongee des bords du plateau. C'est contre-intuitif et ca simplifie la
conception : placer le cardan la ou la mecanique est commode.

### Chargement des tetes — ou couper, exactement

Un changeur d'outil classique suppose la tete **rigidement liee au chariot
dans une orientation fixe** : on amene le chariot au dock, on engage un
accouplement cinematique, on verrouille. Une tete inclinable casse cette
hypothese. Deux facons de la retablir :

**a) L'axe B fait partie de l'outil echange.** Chaque tete porte son
moteur de bascule. L'accouplement doit passer sa puissance et ses signaux,
chaque outil coute un moteur, et la masse echangee explose. Ecarte.

**b) L'axe B reste sur le chariot, seul le hotend s'echange.**
L'accouplement est porte par la chape basculante. **On commande B a son
angle de reference, puis on accoste exactement comme sur une 3 axes.** Le
changeur redevient un probleme resolu -- Prusa XL, E3D, Archer.

La solution est (b), et le probleme qu'elle cree n'est pas mecanique mais
**metrologique** : la repetabilite de l'axe B entre dans la chaine de
tolerance de l'offset d'outil. A 60 mm de la pointe, **0,1° d'erreur font
0,1 mm en XY**. Il faut donc une butee ou un capteur de reference sur B
avec la meme exigence qu'un capteur d'origine, pas un simple pas perdu.

**Le vrai cout d'une tete inclinable est ailleurs : dans l'enveloppe XY.**
Une tete de longueur L au-dessus de la pointe, de demi-largeur w, pivotant
autour de la pointe, deborde lateralement de `L.sin(B) + w.cos(B)` :

| tete | B=0° | B=30° | B=45° | B=60° |
|---|---|---|---|---|
| L=70, w=25 | 25 mm | 57 mm | 67 mm | 73 mm |
| L=90, w=25 | 25 mm | 67 mm | 81 mm | 90 mm |
| L=70, w=18 | 18 mm | 51 mm | 62 mm | 70 mm |

Une tete courte de 70 mm passe de 25 a 67 mm de debord a 45°. **Il faut
84 mm de cadre en plus**, 42 de chaque cote, soit 28 % d'un cadre de 300.
C'est du meme ordre que ce que coute la bascule du plateau, et ca s'y
ajoute.

### Ce qui en decoule

Le compte d'axes de D19 tient toujours : **si le plateau bascule sur deux
axes, la tete n'a besoin d'aucun axe rotatif.** Une tete inclinable ET un
plateau basculant, c'est un degre de liberte de trop (D19 §3), paye deux
fois -- en enveloppe XY et en repetabilite d'outil.

Le changeur d'outil, lui, ne pose alors **aucun probleme nouveau** : tete
fixe, accouplement fixe, changeur de 3 axes standard. C'est un argument de
plus pour mettre toute l'orientation dans le plateau.

---

## D21 — Ce que la tete inclinable achete vraiment

D19 et D20 ont empile les couts de la tete inclinable. Question retournee :
**quel est son avantage ?** Il y en a un, et il est plus gros que tous les
couts listes.

### Le cout de la bascule change de nature

| | ce qui balaie l'enveloppe | le cout croit avec |
|---|---|---|
| plateau basculant | **la piece entiere** | la taille de la PIECE |
| tete inclinable | **le corps de la tete** | la taille de la TETE |

C'est la seule asymetrie structurelle entre les deux architectures, et
elle est decisive : une tete fait 70 mm de long, une piece peut en faire
250. Le cout de la tete est **borne et connu a la conception** ; celui du
plateau croit avec ce qu'on imprime.

### Le chiffre

Meme cadre X300 Y300 Z250, plateau carre 300, piece carree, `volume_utile.py` :

| inclinaison | plateau basculant | tete inclinable (L=70, w=25) |
|---|---|---|
| 0° | 22,50 L | 22,50 L |
| 15° | 11,01 L | **17,42 L** |
| 30° | 5,30 L | **13,92 L** |
| 45° | 3,25 L (−85,5 %) | **11,24 L (−50,1 %)** |
| 60° | hors de portee | 10,00 L |
| 90° | exige un bridage mecanique | **10,82 L** |

**3,5 fois plus de volume a 45°.** Et la hauteur reste entiere : 250 mm a
toute inclinaison, contre 110 mm pour le plateau basculant, qui doit
coucher la piece pour la faire passer sous le portique.

### Les quatre autres avantages, dans l'ordre

1. **La piece ne se decolle jamais.** D16 concluait qu'au-dela de 90° « la
   piece est retournee, l'adherence ne la tient plus, il faut un bridage
   mecanique -- une autre classe de machine ». Avec une tete inclinable,
   **ca disparait** : la piece reste a plat quoi qu'il arrive. Le seul
   argument binaire du projet -- le support irretirable de D13, qui est un
   re-entrant, qui exige plus de 90° -- redevient atteignable sans changer
   de classe de machine.

2. **La masse en mouvement ne croit pas avec l'impression.** Un plateau qui
   bascule porte la piece : ses accelerations admissibles baissent a mesure
   que la piece grossit. Une machine qui ralentit en cours de travail. La
   tete pese ce qu'elle pese, du debut a la fin.

3. **Le plateau reste un plateau.** Pas de cardan, pas de trois rotules,
   pas de bague tournante, et surtout **pas de 300 a 750 W de chauffage ni
   de thermistance a faire passer par une articulation mobile**. C'est la
   liaison la plus penible de la machine ; la supprimer vaut mieux que la
   reussir.

4. **Le firmware existe deja**, partiellement : le Core R-Theta fait
   tourner une tete inclinable de −180° a +90° sous RepRapFirmware.

### Ce que ca n'achete PAS — a ne pas se raconter

**Aucune garde buse-piece.** La collision ne depend que de la pose
*relative* buse/piece. A inclinaison egale, incliner la tete ou incliner le
plateau donne exactement la meme interference. C'est deja etabli et ca vaut
ici aussi -- c'est la meme erreur que la redondance avait failli faire
commettre.

**La gravite reste le vrai prix.** Le plateau basculant garde le plan de
depot horizontal et presse le cordon a toute inclinaison (D16) ; la tete
inclinable depose sur un plan incline, et a 45° la gravite tire le cordon
avec 71 % de son poids dans le plan de la couche. **Ce cout n'est toujours
pas mesure.** Deux choses le nuancent sans le supprimer :

- le cordon est **repasse et plaque par le meplat de la buse**, il n'est pas
  simplement pose ; la gravite n'est pas seule en jeu ;
- en non-planaire continu (D17) la surface locale est de toute facon
  inclinee dans le repere machine, regime que le non-planaire 3 axes
  pratique deja sans drame.

C'est le seul point ou le plateau basculant garde un avantage franc. Il
vaut un essai reel, pas un arbitrage sur le papier.

### Ou ca laisse l'architecture

L'orientation demande deux degres. S'ils viennent tous les deux de la tete
(A+B dans la broche), on est en tete-tete : masse et encombrement
cumules. S'ils viennent tous les deux du plateau (D19), on paie 85 % du
volume.

**La combinaison qui tient debout : plateau qui TOURNE a plat (C), tete qui
S'INCLINE (B).** Le plateau ne bascule jamais -- pas de decollement, pas de
berceau, pas de perte de volume par balayage -- et la bague tournante est
un probleme resolu. La tete ne porte qu'un axe. C'est le Core R-Theta avec
un axe Y en plus, et c'est ce que `architecture-v2.md` proposait avant que
D19 ne parte sur le tout-plateau.

Reste a trancher par l'essai, pas par le calcul : **le cordon tient-il sur
une couche inclinee a 45° ?**

---

## D22 — Marier les deux bascules : oui, mais pas pour economiser

Question : peut-on incliner le plateau ET la tete ? Oui. Mais **les couts
d'encombrement s'additionnent, ils ne se partagent pas.**

### Pourquoi ils s'ajoutent

Le plateau fait balayer la PIECE. La tete fait balayer SON PROPRE CORPS.
Les deux excursions se produisent au meme instant, dans la meme direction,
et se mettent bout a bout. Repartir l'inclinaison entre deux organes ne
repartit pas la place qu'ils consomment.

C'est exactement le piege que la redondance avait deja tendu une fois, sur
la collision. Meme forme d'erreur : croire qu'un degre de liberte de plus
allege un cout, alors qu'il en ajoute un.

### Le chiffre

Cube de 200 mm, tete L=70 w=25, `volume_utile.py` :

**Inclinaison totale 45°**

| plateau | tete | cadre X/Y | cadre Z | enveloppe |
|---|---|---|---|---|
| **0°** | **45°** | 284 | **200** | **16,2 L** |
| 15° | 30° | 309 | 266 | 25,4 L |
| 30° | 15° | 314 | 315 | 30,9 L |
| 45° | 0° | 304 | 341 | 31,6 L |

**Inclinaison totale 90°** — le cas des re-entrants (D16)

| plateau | tete | cadre X/Y | cadre Z | enveloppe |
|---|---|---|---|---|
| **0°** | **90°** | 290 | **200** | **16,8 L** |
| 30° | 60° | 375 | 315 | 44,3 L |
| 45° | 45° | 388 | 341 | **51,5 L** |

**Le partage moitie-moitie est la posture la plus chere**, a chaque angle
total. A 90° elle coute trois fois le tout-tete.

### Ce que le mariage achete quand meme

Il n'achete pas d'encombrement. Il achete trois choses reelles :

1. **De la course.** Une table a trois points plafonne vers 30-40° par sa
   mecanique (D20). Au-dela, seule la tete peut fournir. Si on veut a la
   fois depasser 45° et limiter l'inclinaison de la tete, il faut les deux.

2. **Un reglage entre deux maux.** L'inclinaison de la tete penche la
   couche et laisse la gravite tirer le cordon ; l'inclinaison du plateau
   penche la piece et sollicite son adherence. **Plafonner la tete a
   l'angle ou le cordon tient encore, et laisser le plateau finir** est le
   seul arbitrage honnete -- et il demande une valeur mesuree qu'on n'a
   pas.

3. **Des postures d'evitement.** La collision buse-piece ne depend que de
   la pose relative et ne bouge pas. Mais la collision tete-BATI, elle, en
   depend : avec deux organes on choisit une posture qui degage le bati
   sans changer la pose de depot.

### La regle qui rend le mariage abordable

**Le cadre se dimensionne sur la pire posture qu'on s'autorise, pas sur la
somme des courses.** Si l'on s'interdit d'utiliser les deux bascules en
meme temps a fort angle, le cadre n'a jamais a payer la ligne du milieu :

    cadre = max( cout tout-tete , cout tout-plateau )
    et non  cout tete + cout plateau

Concretement : **une bascule a la fois.** Le plateau pour les petits
angles, ou sa gravite favorable vaut quelque chose et ou son cout en cadre
est encore faible ; la tete pour les grands angles et les re-entrants, ou
elle est seule capable et ou son cout est borne.

C'est le mariage utile : deux mecanismes, un seul actif a la fois, et un
cadre dimensionne sur le plus gros des deux -- **284 x 284 x 341 pour un
cube de 200**, contre 388 x 388 x 341 si l'on s'autorise le 45/45.

### Ce que ca coute a construire

Deux mecanismes au lieu d'un : un plateau orientable **et** une tete
inclinable. Sept axes pour cinq degres. Deux cinematiques a ecrire, deux
references a etalonner, deux sources de jeu. **C'est cher, et ca ne se
justifie que si le point 2 ci-dessus se revele contraignant** -- c'est-a-
dire si le cordon ne tient pas sur une couche fortement inclinee.

**Donc l'essai de depot incline (D21) ne decide pas d'un reglage : il
decide s'il faut construire une machine ou deux mecanismes.** C'est le
prochain jalon, et il est physique, pas logiciel.

---

## D23 — Table inclinable retenue. Reste a choisir le mecanisme  ⟨ROUVERTE PAR D29 : son argument decisif ne tient pas⟩

Decision prise : **c'est le plateau qui s'oriente, pas la tete.** D2 est
refermee sur ce point, apres avoir ete rouverte par D15.

### Ce que ca retient, et ce que ca accepte

Retenu, mesure ou etabli :

- la gravite presse le cordon a toute inclinaison : le plan de depot reste
  horizontal (D16). **C'est le seul cout de la tete inclinable qui n'etait
  pas chiffrable, et il est ecarte d'office ;**
- la tete reste simple, legere, sans articulation traversee par le filament ;
- le changeur d'outil ne pose **aucun probleme nouveau** (D20) ;
- toute la chaine logicielle du depot parle deja cette machine : le fork
  Cortex, `stitch_chunks.py` verifie chiffre par chiffre sur le protocole
  Fractal, `check_collision.py`, la cinematique de reference.

Accepte, chiffre :

- **cadre plus haut** : +70 % de hauteur pour la meme piece (D21) ;
- volume garanti reduit, et la reduction croit avec la taille de la piece ;
- les re-entrants au-dela de 90° restent hors de portee : la piece serait
  retournee, il faudrait un bridage (D16). **L'argument du support
  irretirable de D13 sort du perimetre de la premiere machine.**

Une piece **cylindrique** coute nettement moins cher qu'un cube : a 45°,
283 mm de cadre au lieu de 341 en Z. La diagonale du cube est ce qui se
paie.

### Le choix qui reste : berceau ou trois points

| | berceau a deux axes | table a trois points |
|---|---|---|
| course angulaire | non bornee | **~35-40°**, bornee par la course lineaire |
| pieces usinees | 13 des 21 de la Fractal | aucune, trois vis et trois rotules |
| garde plateau-buse 12 mm | **oui**, contrainte structurante | **sans objet** |
| alimentation du plateau chauffant | bague tournante | cable souple, ne tourne pas |
| moteurs | X, Y, Z, A, B = 5 | X, Y, Z1, Z2, Z3 = 5 |
| firmware | **existe** (Fractal, Klipper, GPL) | **n'existe nulle part** |
| materiel de base | CAO Fractal | Voron Trident, produit en masse |
| cout | 2 600-2 900 $ chiffres | cadre CoreXY ordinaire |

**Le choix revient a decider ou placer l'inconnu.** Le berceau met le
risque dans la mecanique -- 21 pieces usinees, 150 a 370 € de decoupe, un
arbre tourne -- et rien dans le logiciel. Les trois points font l'inverse :
mecanique banale et bon marche, **zero ligne de firmware existante**.

### Recommandation : les trois points

Quatre raisons, dans l'ordre :

1. **35-40° suffisent au perimetre retenu.** D16 a etabli que 0-50°
   couvrent tous les surplombs sans exception, et les re-entrants sortent
   de toute facon du perimetre d'une table basculante. La borne des trois
   points ne mord pas sur ce qu'on a decide de faire.

2. **Ca supprime la garde de 12 mm**, qui a fausse ou complique toutes les
   mesures d'enveloppe de ce depot.

3. **Le risque va la ou le projet est fort.** Ce depot produit du logiciel
   -- une douzaine d'outils, un fork maintenu, une cinematique corrigee en
   amont. Il n'a pas d'atelier. Concentrer l'inconnu dans du code est un
   choix de prudence, pas d'ambition.

4. Le materiel de base **existe, est produit en masse et coute peu** :
   Voron Trident est deja un CoreXY a trois moteurs Z independants sous le
   plateau. Manquent trois rotules, la course, et la cinematique.

Ce que ca coute cote logiciel : la sortie de `stitch_chunks.py` vise
aujourd'hui des angles A/B. Il faudra la faire viser trois hauteurs. C'est
une **transformation de sortie, contenue** -- le decoupage en blocs et la
couture ne changent pas.

### Dimensionnement propose

Pour une piece cible de **Ø200 x 200 mm** a **35°** :

| | valeur |
|---|---|
| plateau | carre 250 mm |
| portee des appuis (pire azimut) | 217 mm |
| **course differentielle des trois vis** | **152 mm** |
| courses X / Y | 279 mm |
| course Z | 279 mm + la course differentielle |
| vide sous le plateau | ~101 mm (diagonale du plateau a 35°) |

Le plateau est plus grand que la piece de 25 mm au pourtour, pour la bride
et la premiere couche.

### Ce qu'il faut faire ensuite, dans l'ordre

1. **Ecrire la cinematique directe et inverse des trois points** -- un plan
   par trois points, quelques lignes, plus les butees et les singularites.
   A valider hors machine, contre `check_collision.py`.
2. **Etendre `stitch_chunks.py`** pour emettre trois hauteurs au lieu de
   A/B, en gardant l'ancien chemin pour la comparaison.
3. **Essai de depot incline** -- il ne conditionne plus l'architecture,
   mais il borne l'angle utile.
4. Seulement apres : la mecanique.

---

## D24 — Plateau 400, hauteur 400 : ce que la marge coute vraiment

Choix : **plateau 400 x 400, hauteur 400.** Prendre de la marge plutot que
de dimensionner au plus juste. Ce que ca donne, et la contrainte que ca
cree.

### Ce qu'on imprime

Cadre X400 Y400 Z400, plateau carre 400, piece cylindrique :

| inclinaison | piece | volume |
|---|---|---|
| 0° | Ø400 x 400 | 50,27 L |
| 15° | Ø328 x 320 | 27,04 L |
| 25° | Ø304 x 294 | 21,34 L |
| **35°** | **Ø320 x 240** | **19,30 L** |
| 40° | Ø332 x 226 | 19,56 L |

Environ **Ø300 x 250 utiles a pleine inclinaison**. C'est une vraie
machine, pas un demonstrateur de table.

### La contrainte que le grand plateau cree

**Plus le plateau est grand, plus l'inclinaison coute cher en course
lineaire.** La portee des appuis croit avec le rayon, et la course
differentielle croit avec la portee :

| rayon des appuis | porte-a-faux du plateau | portee | 30° | **35°** | 40° |
|---|---|---|---|---|---|
| 200 mm (au bord) | 83 mm | 346 mm | 200 mm | **243 mm** | 291 mm |
| 175 mm | 108 mm | 303 mm | 175 mm | 212 mm | 254 mm |
| **150 mm** | **133 mm** | **260 mm** | 150 mm | **182 mm** | 218 mm |
| 125 mm | 158 mm | 217 mm | 125 mm | 152 mm | 182 mm |
| 100 mm | 183 mm | 173 mm | 100 mm | 121 mm | 145 mm |

**C'est le nouvel arbitrage, et il n'existait pas sur un plateau de 250.**
Rapprocher les appuis du centre divise la course differentielle par deux --
mais met le plateau en porte-a-faux. Un plateau de 400 sur des appuis a
R=125 deborde de 158 mm a ses coins ; avec 2 kg de piece dessus, la fleche
n'est plus negligeable a l'echelle d'une couche.

**Corrige apres validation** (`cinematique_3points.py`) : les 182 mm
donnent **exactement 35,0°**, marge nulle. Il faut distinguer l'angle que
le mecanisme atteint en butee de l'angle qu'on s'autorise a commander.

| rayon des appuis | porte-a-faux | 35° en butee | 35° a 90 % | 35° a 80 % |
|---|---|---|---|---|
| 200 mm | 83 mm | 243 mm | 279 mm | 332 mm |
| **150 mm** | **133 mm** | 182 mm | **210 mm** | 249 mm |
| 125 mm | 158 mm | 152 mm | 175 mm | 207 mm |

**Retenu : appuis a R=150 mm, 210 mm de course differentielle**, soit 35°
utilisables a 90 % de la butee (38,9° mecaniques). Sur une course de vis,
90 % est une marge suffisante -- on connait ses butees, contrairement a une
garde geometrique. Le levier contre la fleche du porte-a-faux est
l'**epaisseur et le nervurage du plateau**, pas le rayon des appuis.

### Ce que ca fait a la hauteur de la machine

La course differentielle s'ajoute a la course d'impression sur chaque vis :

    course d'une vis = 400 (impression) + 210 (differentiel) = 610 mm

Plus la plongee du coin du plateau a 35° -- **162 mm** pour un carre de
400 -- qui doit etre libre sous le plateau. Plus le plateau, le portique,
l'embase.

**Le bati approche 1 000 mm de haut.** C'est la consequence directe du
choix 400/400, et il vaut mieux la voir maintenant qu'au moment de
commander les profiles. Ce n'est pas redhibitoire -- une Voron 2.4 350 fait
deja 800 mm -- mais ca change la classe de machine, le transport, et la
rigidite a obtenir.

### Ce qui reste inchange

Tout le raisonnement de D23. Le plateau grandit, la cinematique non.

---

## D25 — Inclinaison du plateau : validee, avec deux corrections

`cinematique_3points.py` valide l'inclinaison avant toute mecanique. Le
plateau est traite comme ce qu'il est, un plan rigide sur trois hauteurs
imposees :

    h_i = z + R . cos(azimut_i - phi) . tan(theta)

Aller-retour verifie exact sur douze azimuts : la pose se relit sans perte
depuis les trois hauteurs.

### Correction 1 — c'est une tangente, pas un sinus

Les verins sont **verticaux**, donc les points d'appui gardent leur
distance HORIZONTALE au centre quand le plateau s'incline. La hauteur d'un
plan de pente theta a la distance d vaut `d.tan(theta)`, pas `d.sin(theta)`.

Sans consequence sur les chiffres de D24, qui utilisaient deja la tangente
-- mais une premiere ecriture de l'outil avait le sinus, et elle annoncait
54° la ou le mecanisme en donne 35.

### Correction 2 — l'ecart entre verins depend de l'azimut

L'outil affirmait d'abord que l'ecart de hauteur etait independant de
l'azimut. **Faux, et la table qu'il imprimait juste au-dessus le
contredisait** : 129 mm dans un azimut, 149 mm dans un autre.

`max - min` de `cos(a - phi)` sur trois azimuts a 120° vaut **1,5** quand
la pente passe entre deux verins et **racine de 3** quand elle passe par un
verin. **15 % d'ecart**, et c'est le pire qui dimensionne.

    course differentielle = V3 . R . tan(theta)

C'est la meme anisotropie que `table_3points.py` mesurait deja par la
portee des appuis. Les deux outils disent maintenant la meme chose.

### Ce que ca donne sur la machine retenue

Plateau 400, appuis a R=150, **210 mm de course differentielle** :

| | valeur |
|---|---|
| inclinaison en butee | 38,9° |
| inclinaison commandee, a 90 % | **35,0°** |
| ecart de hauteur a 35°, pire azimut | 182 mm |
| ecart a 35°, azimut favorable | 158 mm |
| course d'une vis | 400 + 210 = **610 mm** |

### Ce que cet outil ne traite pas, exprès

La liaison mecanique des appuis. Trois rotules rigides sur trois
verticales se bloqueraient -- un plateau rigide garde ses distances entre
points, trois points contraints sur trois verticales non. Il faudra liberer
un degre lateral par jambe.

**Ca ne change aucun angle calcule ici.** C'est de la conception d'appui,
et elle vient apres.

---

## D26 — La chaine 3 verins tourne de bout en bout

`test_3points.py` : **6 controles sur 6**, ecarts au niveau du flottant
(10^-13). Pas de tolerance genereuse -- la cinematique etant exacte en
forme fermee, tout ecart au-dela du bruit machine serait une erreur.

| controle | resultat |
|---|---|
| aller-retour hauteurs <-> pose, grille dense | 6,8.10^-13 |
| normale du chunk ramenee sur +Z | 1,0.10^-13 deg |
| centre du plateau immobile | 8,5.10^-14 mm |
| anisotropie mesuree | 1,5000 a 1,7321 -- exactement 1,5 et racine de 3 |
| budget de course et reciprocite des formules | 2,8.10^-14 |
| garde sur course insuffisante | leve, en nommant le chunk |

L'anisotropie n'est plus un resultat annonce, elle est **mesuree sur 720
azimuts** et retrouve les deux bornes theoriques.

### L'angle de chunk que la machine execute

R=150, 210 mm de course differentielle :

| angle de chunk | ecart pire azimut | reste |
|---|---|---|
| 30° | 150,0 mm | 60,0 |
| 35° | 181,9 mm | 28,1 |
| **38°** | **203,0 mm** | **7,0** |
| 39° | 210,4 mm | **hors course** |

**La butee tombe entre 38 et 39°**, ce qui recoupe les 38,95° calcules par
`angle_max`. Les 35° retenus en D24 laissent 28 mm de reserve.

### De bout en bout

`stitch_chunks.py --machine 3points` produit 37 957 lignes sur la piece en
Y, `check_collision.py` les relit et rend **le meme verdict que sur la
sortie berceau** : 2 chunks en collision, 2,27 mm confirmes au lancer de
rayons.

C'est le controle qui compte : la collision ne depend que de la pose
relative, donc **les deux machines doivent donner le meme resultat**. Un
ecart aurait signale une erreur de conversion. Le diff des deux G-code le
confirme directement -- identiques hors commandes machine, a un mot de
commentaire pres.

### Ce qui reste, et qui n'est plus de la geometrie

1. **La cinematique Klipper.** Les `MANUAL_STEPPER` basculent le plateau a
   l'arret ; ils ne coordonnent rien. Suffisant en indexe (D-mouvements),
   insuffisant des qu'on voudra du continu.
2. **Le couplage Z/inclinaison pendant le depot.** Le centre du plateau
   reste a sa consigne -- verifie -- mais un point a distance `r` du centre
   monte de `r.sin(theta)`. A 35° et r=150, c'est **86 mm**. Deja compte
   dans le cadre de D24, pas encore compense dans le G-code.
3. **L'essai de depot incline.** Toujours le seul point que le calcul ne
   tranchera pas.

---

## D27 — Incliner la TETE par le meme procede : trois verins, pas quatre  ⟨LECTURE CORRIGEE PAR D28 : c'est le PORTIQUE qui bascule⟩

Idee proposee : appliquer a la tete ce qu'on fait au plateau -- une
platine suspendue a plusieurs points dont on pilote les hauteurs, donc une
inclinaison dans tout azimut, **et un changeur d'outil qui reste
possible**.

C'est coherent, et ca a un merite que la version a berceau n'a pas.

### D'abord : trois points, pas quatre

Un plan est defini par **trois** points. Un quatrieme rend le systeme
hyperstatique : quatre verins rigides sur une platine rigide se battent
entre eux, et la repartition des efforts depend des tolerances, pas de la
commande.

La Voron 2.4 s'en accommode parce que ses quatre moteurs Z **nivellent un
portique a l'arret**, avec un peu de souplesse admise, et ne l'inclinent
jamais en marche. Une inclinaison commandee en cours d'impression ne
pardonne pas ca. **Trois.**

### Le merite reel : la course s'effondre avec le rayon

Meme formule que pour le plateau -- `course = V3 . R . tan(theta)` -- mais
appliquee a une platine de tete, donc a un tout petit rayon :

| rayon | ce que c'est | 25° | 35° | 45° |
|---|---|---|---|---|
| 150 mm | plateau 400 (D24) | 121 mm | **182 mm** | 260 mm |
| 60 mm | platine de tete | 49 mm | 73 mm | 104 mm |
| **50 mm** | **platine de tete** | 40 mm | **61 mm** | 87 mm |
| 40 mm | platine compacte | 32 mm | 49 mm | 69 mm |

**61 mm au lieu de 182 pour la meme inclinaison.** Trois fois moins de
course, donc des vis courtes, un bati qui ne monte pas a un metre, et des
verins qui peuvent etre rapides. C'est le vrai argument de cette idee, et
il est fort.

### Le changeur d'outil : compatible, mais il l'etait deja

D20 l'avait etabli : avec l'axe de bascule **sur le chariot** et seul le
hotend echange, on commande la bascule a sa reference et on accoste comme
sur une 3 axes. Le changeur redevient un probleme resolu.

La version parallele ajoute quand meme quelque chose : une bascule serie
demande une **chape autour de la buse**, encombrante et placee exactement
la ou se trouve la matiere deja deposee. Une platine a trois verins est
**plate** : l'accouplement d'outil se pose dessus, sans rien entourer.

### Les trois couts, chiffres

**1. Le point pilote se deplace.** Le pivot d'une platine est au-dessus de
la pointe, pas dedans. La pointe part en arc :

| pivot au-dessus de la pointe | 25° | 35° | 45° |
|---|---|---|---|
| 60 mm | 25 mm | 34 mm | 42 mm |
| 80 mm | 34 mm | **46 mm** | 57 mm |
| 100 mm | 42 mm | 57 mm | 71 mm |

A compenser en X, Y et Z a chaque mouvement de bascule -- la compensation
RTCP de `docs/mouvements.md` §1, qui devient **obligatoire des le premier
essai**, pas une option.

**2. La tete grossit, et l'enveloppe le paie deux fois.** La platine et
ses trois verins elargissent la tete. Debord lateral en bascule :

| | B=0° | B=35° | B=45° |
|---|---|---|---|
| tete nue (L70, w25) | 25 mm | 61 mm | 67 mm |
| tete + platine (L95, w55) | 55 mm | 99 mm | **106 mm** |

Le cout en cadre passe de 84 a **102 mm** de chaque cote. L'avantage
structurel de la tete inclinable -- un cout borne par la taille de la tete
(D21) -- tient toujours, mais la borne monte.

**3. La masse va sur le chariot mobile.** Trois verins, trois moteurs,
une platine. Sauf a les entrainer par courroies depuis des moteurs fixes,
facon Core R-Theta (D18) -- ce qui est possible et deja repertorie.

### Ce que ca ne change pas

**L'argument qui a decide D23 tient entier** : une tete inclinable depose
sur un plan incline, et la gravite tire le cordon dans le plan de la
couche. Un plateau basculant garde le plan de depot horizontal. Cette
idee rend la tete inclinable **moins chere et plus compacte**, elle ne la
rend pas meilleure pour le depot.

**Statut : retenue comme variante serieuse, pas comme revision de D23.**
Elle devient le meilleur candidat si l'essai de depot incline montre que
le cordon tient -- et elle reglerait alors d'un coup les 610 mm de course
de vis et le bati d'un metre de D24.

Elle s'ajoute donc a ce que l'essai doit trancher. Cet essai decide
maintenant de trois choses : l'angle utile, s'il faut deux mecanismes
(D22), et laquelle des deux architectures construire.

---

## D28 — C'est le portique qui bascule, pas la buse

D27 avait mal lu l'idee. Ce n'est pas la tete qui pivote autour de sa
pointe sur une petite platine : **c'est le portique entier qui s'incline**,
porte par ses appuis en Z. La tete continue de se promener en X et Y
dessus, comme sur n'importe quel CoreXY. Le plateau, lui, ne bouge plus.

C'est une Voron 2.4 dont le portique, au lieu de rester horizontal,
prend une pente.

### Ce que ca change par rapport a D27 -- et c'est beaucoup

**Il n'y a plus de compensation a inventer.** D27 chiffrait 46 mm de
derive de pointe a compenser par RTCP. Ici la question ne se pose pas dans
les memes termes : incliner le portique deplace la tete, et **la tete se
rattrape avec ses propres axes X et Y**, qui sont deja la et deja rapides.
Ce n'est plus un mecanisme a ajouter, c'est un changement de repere.

**Le changeur d'outil devient indifferent a l'inclinaison.** Les docks
sont montes sur le portique : ils s'inclinent avec lui. La geometrie
relative tete/dock ne change jamais, donc **on accoste a n'importe quel
angle**, sans revenir a une reference. C'est mieux que la solution (b) de
D20, qui imposait de remettre la bascule a zero avant chaque changement.

**La piece ne bouge toujours pas.** Plateau fixe et plat : pas de
decollement, pas de balayage, pas d'effondrement de volume par la taille
de la piece (D21). L'avantage structurel de la famille « tete inclinable »
est conserve entier.

### Le cout, et il est franc : la course

Meme formule, mais le portique est **plus grand que le plateau**, et la
course suit :

| ce qui bascule | portee des appuis | 25° | 35° | 45° |
|---|---|---|---|---|
| platine de tete (D27) | 87 mm | 40 mm | 61 mm | 87 mm |
| **plateau 400 (D24)** | **260 mm** | 121 mm | **182 mm** | 260 mm |
| portique, appuis a 300 | 260 mm | 121 mm | 182 mm | 260 mm |
| **portique 400, 4 coins** | **566 mm** | 264 mm | **396 mm** | 566 mm |

Avec quatre appuis aux coins d'un portique carre, **la portee passe par la
diagonale** : 566 mm pour un portique de 400. A 35° il faut **396 mm de
course differentielle**, contre 182 pour le plateau. Chaque colonne Z doit
alors offrir 400 + 396 = **796 mm**, et le bati depasse 1,2 m.

Le levier existe : **rapprocher les appuis des centres de cotes plutot que
des coins.** Trois appuis a 300 mm de portee ramenent le differentiel a
182 mm, exactement comme le plateau. Le portique devient porte-a-faux a ses
coins -- meme arbitrage que pour le plateau en D24, resolu par la rigidite
de la poutre et non par l'ecartement des appuis.

### La contrainte de conception a ne pas manquer

**Les moteurs CoreXY doivent etre embarques sur le portique qui bascule.**
Si les moteurs restent sur le bati et que les courroies montent vers un
portique incline, les quatre trajets de courroie ne varient plus de la
meme facon : la boucle CoreXY se desaccorde et produit une derive X/Y a
chaque bascule.

Le portique doit donc etre un **ensemble rigide et autonome** -- moteurs,
courroies, chariot -- que les appuis Z se contentent de porter. C'est
l'architecture de la Voron 2.4 a portique volant, **a confirmer sur sa CAO
avant de s'en reclamer**.

### Surface utile

Un portique incline se raccourcit en projection :

| inclinaison | course X ou Y utile |
|---|---|
| 15° | x 0,966 -- 400 devient 386 mm |
| 35° | x 0,819 -- 400 devient 328 mm |
| 45° | x 0,707 -- 400 devient 283 mm |

Perte reelle mais modeste, et sans commune mesure avec les 75 a 85 % que
coute le balayage d'une piece sur un plateau basculant (D19, D21).

### Ce que ca ne change pas

**L'argument qui a decide D23 tient toujours.** Un portique incline depose
dans un plan incline : la buse est perpendiculaire a la couche, et la
gravite tire le cordon dans le plan de cette couche. Exactement la meme
physique que la tete inclinable. Le plateau basculant reste le seul a
garder le plan de depot horizontal.

### Les trois familles, cote a cote

| | plateau bascule | portique bascule | platine de tete |
|---|---|---|---|
| plan de depot vs gravite | **horizontal** | incline | incline |
| la piece bouge | oui | **non** | **non** |
| volume perdu a 35° | 60 a 77 % | ~18 % | ~18 % |
| course differentielle a 35° | 182 mm | 182 a 396 mm | **61 mm** |
| changeur d'outil | indifferent | **indifferent** | retour a la reference |
| compensation de pointe | aucune | changement de repere | RTCP a ecrire |
| masse basculee | plateau + piece | **portique entier** | platine + tete |
| firmware de base | a ecrire | a ecrire | a ecrire |

**Statut : troisieme candidat serieux, a egalite avec D27.** Il est plus
lourd a basculer et demande plus de course, mais il supprime la
compensation de pointe et rend le changeur d'outil indifferent a l'angle.

Les trois familles attendent le meme resultat : `docs/essai-depot-incline.md`.
Si le cordon tient sur une couche inclinee, **deux des trois** deviennent
meilleures que le plateau basculant retenu en D23. Sinon D23 tient seul.

---

## D29 — L'argument de la gravite ne tient pas. D23 est rouverte

Simulation demandee pour trancher entre les trois familles. Elle tranche,
mais pas ou on l'attendait : **elle detruit l'argument qui avait decide
D23.**

### L'erreur de raisonnement

Toutes les notes precedentes -- D16, D21, D22, D23, D27, D28 -- reposaient
sur : « une tete inclinee depose sur un plan incline, et a 30° la gravite
tire le cordon avec 50 % de son poids ».

C'est exact et **sans portee**. Une composante de force ne dit rien tant
qu'on ne la compare pas a ce qui lui resiste. Je ne l'avais jamais fait.

Ce qui resiste : la **viscosite** du polymere fondu et la **tension
superficielle**. Les deux varient en `h^2`. A 0,2 mm d'epaisseur, elles
sont ecrasantes.

### Les chiffres (`tools/simu_depot_incline.py`)

PLA, couche 0,2 mm, cordon fondu pendant 1 s :

| inclinaison | nombre de Bond | derive du cordon | en part de couche |
|---|---|---|---|
| 15° | 0,0041 | 0,08 µm | 0,04 % |
| 30° | 0,0078 | 0,16 µm | 0,08 % |
| **45°** | **0,0111** | **0,22 µm** | **0,11 %** |
| 90° | 0,0157 | 0,31 µm | 0,16 % |

**Bond = 0,011 a 45°** : la tension superficielle domine la gravite d'un
facteur cent. La derive visqueuse est de **0,2 micron**, mille fois moins
que la hauteur de couche.

La capillarite ne cesserait de dominer (Bond = 1) qu'a une couche de
**1,90 mm** -- neuf fois la notre. L'argument vaudrait pour une coulee de
beton, pas pour un cordon de 0,2 mm.

### Et ce n'est pas un resultat fragile

Balayage de la viscosite sur **quatre decades** et du temps de figeage de
0,1 a 20 s, a 45°. La derive n'atteint une hauteur de couche que pour
`mu = 1 Pa.s` -- de l'eau tiede, pas un polymere fondu, qui se situe entre
100 et 10 000.

Quatre materiaux : PLA 0,11 %, ABS 0,05 %, PETG 0,07 %, TPU 0,03 %.
Couches de 0,2 a 1,2 mm : de 0,2 % a 1,3 %.

Un polymere fondu est de plus **rheofluidifiant** : au repos, a faible
cisaillement, sa viscosite est la PLUS HAUTE. Prendre une viscosite
newtonienne est donc conservateur dans le bon sens.

### Ce que la simulation ne dit pas

- Les **ponts et surplombs sans substrat** : la, le cordon pend
  effectivement. Mais c'est precisement ce que la 5 axes sert a eviter.
- Le **cisaillement de la buse**, qui domine largement la gravite et n'est
  pas directionnel.
- L'**etat de surface** et l'aspect, que seul un essai montrera.

`docs/essai-depot-incline.md` reste a faire -- mais il devient une
**confirmation**, plus un point de decision. L'architecture n'attend plus
apres lui.

### Ce que la comparaison donne alors (`tools/comparer_architectures.py`)

Piece de 200 x 200 x 200 a 35° :

| famille | course diff. | course d'un verin | cadre Z | inertie relative |
|---|---|---|---|---|
| plateau basculant (D23) | 182 mm | 382 mm | **326 mm** | 39 x |
| portique, appuis milieux | 210 mm | 410 mm | 200 mm | 55 x |
| portique, 4 coins (D28) | 396 mm | 596 mm | 200 mm | 198 x |
| **platine de tete (D27)** | **61 mm** | **261 mm** | **200 mm** | **1 x** |

La duree de bascule ne departage rien en indexe : 2 a 5 minutes sur une
impression de six heures, moins de 1,5 %.

**Elle departage tout en continu.** L'inertie croit en `masse x portee^2` :
la platine est **39 a 198 fois** plus favorable. C'est le seul organe
qu'on puisse esperer piloter pendant le depot. Les trois autres sont des
mecanismes d'indexation, et le resteront.

Or D17 a etabli que le multidirectionnel est la discretisation grossiere
du non-planaire, et D14 que les 2 a 3x de resistance viennent du continu.
**Choisir un organe qui ne peut pas aller au continu, c'est se fermer le
seul gain mecanique reel du projet.**

### Decision

**D23 est rouverte.** Le plateau basculant avait ete retenu sur un
argument qui ne tient pas, et il est le plus penalisant sur les criteres
qui restent : 326 mm de cadre en Z contre 200, et une inertie qui
l'enferme dans l'indexe.

**La platine de tete (D27) devient le candidat de tete** : course la plus
courte, bati le plus bas, piece qui ne bouge jamais, et la seule voie
ouverte vers le non-planaire continu.

Ce qu'elle doit encore payer, et qui est du logiciel :

1. **La compensation du point pilote.** Pivot a ~80 mm au-dessus de la
   pointe, donc 46 mm de derive a 35°. A ecrire avant le premier essai.
2. **L'encombrement de la tete**, qui grossit de la platine : 84 a 102 mm
   de cadre de chaque cote.

Ces deux-la sont bornes et connus. L'inertie du plateau ne l'est pas.

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
