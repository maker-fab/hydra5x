# Le slicer — ce qu'il faut savoir avant de s'en servir

Amont : [Fractal Cortex](https://github.com/fractalrobotics/Fractal-Cortex)
de Fractal Robotics — GPL-3.0, Python, ~200 étoiles, 37 forks.
**Inactif depuis juillet 2025.**

Ce projet en maintient un fork :
[maker-fab/hydra5x-slicer](https://github.com/maker-fab/hydra5x-slicer).
C'est lui que `docs/install.md` clone. Voir `decisions.md` D7 pour le
pourquoi. Tout ce qui suit décrit le code des deux, sauf mention contraire.

Seul slicer multidirectionnel libre et utilisable. Open5x exige
Rhino/Grasshopper (payant), le non-planaire continu n'a que du code
d'article.

## Installation

`tools/requirements-cortex-headless.txt` donne la recette qui marche.
**L'installation documentée échoue immédiatement** — cinq dépendances
manquent au README : `scipy`, `manifold3d`, `networkx`, `rtree`,
`mapbox_earcut`.

Piège de version : `scipy` récent tire `numpy>=2`, or `trimesh 4.3.1`
utilise `ndarray.ptp()`, supprimé dans NumPy 2. Épingler `scipy==1.13.1`.

Pour le GUI : `pyglet==1.5.28`, `glooey==0.3.6`, `PyOpenGL==3.1.0`, et
`more_itertools==8.14.0` (la 11.x casse glooey avec
`TypeError: unhashable type: 'dict'`).

Les 4 erreurs de casse dans les chemins de ressources — sans correction le
GUI ne démarre pas du tout sous Linux, et elles sont invisibles sous
Windows — sont déjà corrigées dans le fork. `patches/cortex-gui-linux.patch`
les conserve en diff pour qui part du dépôt d'origine.

## Architecture

6 620 lignes, 4 fichiers. **Le cœur de slicing est découplé du GUI** :

| Fichier | Lignes | Dépendances |
|---|---|---|
| `slicing_functions.py` | 1794 | trimesh/shapely/numpy — **réutilisable seul** |
| `slicer_main.py` | 1622 | pyglet + OpenGL |
| `widget_functions.py` | 1704 | pyglet + tkinter |
| `fractal_widgets.py` | 1500 | glooey |

Pipeline : `mesh.slice_plane` par chunk, différence booléenne
(« chiselling »), puis coques → remplissage → chemins → G-code.
48 fonctions, 0 classe.

## Ce qu'il fait — et ne fait pas

**Il produit du vrai G-code multidirectionnel.** Validé sur
`pipe_fitting.stl` (12 448 faces, raccord coudé avec branche) :
2 directions → 523 501 lignes, 4 rotations, extrusion continue à travers
les réorientations, **0 recul anormal**. Non-régression matière contre le
baseline 3 axes : **−0,1 %**.

**Il n'a aucun test de collision buse-pièce.** Uniquement buse-plateau,
avec une garde en dur de 12 mm. Le commentaire de `create_chunkList`
affirme que le chiselling « ensure no collisions between the printhead and
the in-process part » — c'est un argument d'ordonnancement, pas une
vérification. Rien ne teste que le corps de la buse atteint la zone sans
toucher la matière déjà déposée. **Bloquant pour les géométries denses.**

**Le slicing depuis le GUI se fige.** Voir `decisions.md` D4. Utiliser le
cœur en headless.

## Défauts corrigés

Déjà dans le fork. `patches/cortex-fixes.patch`, 153 lignes, réapplicable
au dépôt d'origine
(`patch --dry-run` OK). Proposés en amont :
[PR #4](https://github.com/fractalrobotics/Fractal-Cortex/pull/4).

1. **garde anti-dégénérescence** avant `orient()` de shapely — les
   polygones d'aire nulle issus de plans tangents faisaient lever une
   `IndexError`
2. **`except` qui lève** au lieu d'imprimer et de sauter la couche
3. **diagnostic contextualisé** sur section invalide — nomme le plan, la
   couche et le z, au lieu d'une exception trimesh opaque
4. **`cap=True` → intersection demi-espace** via manifold3d — la
   triangulation du bouchon par trimesh produisait des sections dégénérées
   juste sous chaque coupe
5. **refus de collision explicite** au lieu d'un `break` laissant des
   dictionnaires incomplets, qui remontait en `KeyError` bien plus loin

L'ordre compte : sans le 1, le 2 ferait échouer des slicings valides sur du
bruit. Et le 3 a permis de localiser le vrai coupable du 4.

Non-régression : **G-code identique octet pour octet** sur les cas qui
fonctionnaient.

## Enveloppe pratique constatée

Inclinaisons modérées. 30° passe largement, 45° échoue ou est refusé pour
collision selon la pièce. Géométries planes comme courbes.

Après correctifs, sur les 6 cas de test d'origine : score inchangé (3/6)
mais **plus aucun échec opaque** — les trois échecs restants ont la même
cause identifiée (garde de 12 mm), chacun nommant son plan, son angle et
l'écart manquant.

## Sortie

G-code Klipper, **codé en dur pour la machine de l'auteur** :
`stepper_a`/`stepper_b` sont ses noms de config, `G0 X0.0 Y-175.0` sa
position de parking. Pour une autre machine, `write_5_axis_gcode`
(368 lignes) est à réécrire.

Entre chunks : lever Z, parquer la tête, tourner le plateau via
`MANUAL_STEPPER`, reprendre. **La buse n'imprime jamais inclinée.**

## Verdict

Référence et point de départ, **pas une dépendance**. L'adopter, c'est en
devenir le mainteneur — l'auteur a arrêté après quatorze mois.

- à reprendre : découpage en chunks + génération de chemins (~1 000 lignes)
- à réécrire de toute façon : `write_5_axis_gcode`
- à écrire : le test de collision buse-pièce
