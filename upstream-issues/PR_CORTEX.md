Titre : Linux : le GUI ne démarre pas, le slicing avale des erreurs — 7 correctifs testés

## Contexte

J'évalue Fractal Cortex pour un projet de machine 5 axes. Tout a été
exécuté sur Linux / Python 3.12, hors de la cible documentée
(Windows 10 / Python 3.10.11). Les correctifs ci-dessous sont testés en
non-régression : sur les cas qui fonctionnaient déjà, la sortie G-code est
inchangée — pour l'un d'eux, identique octet pour octet.

Je comprends que le projet n'ait plus d'activité depuis juillet 2025. Cette
PR est déposée sans attente particulière : si elle sert à quelqu'un, tant
mieux.

## 1. Le GUI ne démarre pas sous Linux — 4 erreurs de casse

Le code référence des chemins qui n'existent pas tels quels :

| déclaré | réel |
|---|---|
| `image_resources/Checkbox_Images` | `image_resources/CheckBox_Images` |
| `apply_Button_Images/Base.png` | `apply_Button_Images/base.png` |
| `apply_Button_Images/Down.png` | `.../down.png` |
| `apply_Button_Images/Over.png` | `.../over.png` |

Invisible sous Windows, dont le système de fichiers est insensible à la
casse. Sous Linux, `pyglet.resource` lève
`ResourceNotFoundException: Resource "checkedBase.png" was not found` et le
GUI ne s'ouvre pas du tout.

Après correction, l'interface se lance et fonctionne (viewport 3D, bascule
5-Axis / 3-Axis, plans de coupe, panneau de réglages).

Une dépendance est aussi à épingler : `more_itertools` 11.x casse glooey
avec `TypeError: unhashable type: 'dict'` dans `unique_everseen`.
`more_itertools==8.14.0` fonctionne.

## 2. Dépendances manquantes dans le README

L'installation documentée échoue immédiatement. Cinq paquets requis ne sont
pas listés :

```
scipy           requis par trimesh.slice_plane
manifold3d      requis par la difference booleenne (chiselling)
networkx        requis par trimesh.path
rtree           requis par trimesh.path
mapbox_earcut   requis par la triangulation
```

Plus un piège de version : `scipy` récent tire `numpy>=2`, or
`trimesh 4.3.1` utilise `ndarray.ptp()`, supprimé dans NumPy 2.0. Il faut
épingler `scipy==1.13.1` pour rester compatible `numpy==1.26.4`.

## 3. Erreurs de couche avalées silencieusement

```python
except Exception as e:  # If there is some problem with the area
                        # calculations, just skip this layer to move on
    print("2. Error Processing Layer", str(layer), str(e))
```

Se déclenchait sur 3 à 7 couches par pièce, y compris sur un simple cube.

**Diagnostic** : cascade de deux replis. `safe_unary_union` échoue et
retourne `Polygon([])` — son propre repli silencieux — puis
`fix_polygon_or_multipolygon_ring_orientation` appelle `orient()` de
shapely dessus, qui fait `coords[1]` sur une séquence vide.

**Vérifié avant de conclure** : les couches fautives ont `n_polygones=1` et
`aire_totale=0.000000` — un polygone dégénéré d'aire nulle, issu d'un plan
de coupe tangent à une face. **Aucune matière n'était perdue.**

Correctif en deux temps :

1. garde `if geometry.is_empty or geometry.area == 0.0: return geometry`
   avant `orient()` → supprime le faux positif à la source
2. le `except` lève un `RuntimeError` explicite au lieu d'imprimer et
   continuer → toute panne réelle devient visible

L'ordre compte : sans le point 1, le point 2 ferait échouer des slicings
valides sur du bruit.

**Vérification** : plus aucun message d'erreur, et G-code **identique
octet pour octet** avant/après (`cmp`).

## 4. `unable to recover polygon!` sans aucun contexte

trimesh lève cette exception depuis `repair_invalid`, sans indiquer quel
plan de coupe ni quelle hauteur est en cause.

La liste en compréhension qui déclenche le calcul paresseux devient une
boucle qui rattrape et nomme le fautif :

```
Section transverse invalide.
  plan de coupe #0 : theta=0.0 deg, phi=0.0 deg, origine=[0, 0, 0]
  couche #138 sur 167, z=27.7 mm (repere local du chunk)
  cause : ValueError: unable to recover polygon!
  note : le chunk #0 a ete taille par les plans suivants (chiselling)...
```

Ce diagnostic a servi immédiatement : il a montré que l'échec tombait
systématiquement ~0,3 mm sous la hauteur des plans inclinés — donc au
niveau du cap généré par `slice_plane(cap=True)` — et non à la jonction de
la pièce comme je le supposais.

## 5. `cap=True` produit des sections dégénérées

Cause du point 4. Dans `create_chunkList()` :

```python
unprocessedChunk = mesh.slice_plane(currentStart, currentNormal, cap=True, ...)
```

La triangulation du bouchon par trimesh produit des sections transverses
dégénérées juste sous la coupe. Remplacé par une intersection booléenne
avec un demi-espace (boîte de 3× la diagonale, face posée sur le plan,
orientée par `align_vectors`), donc via **manifold3d**, nettement plus
robuste. Repli sur la méthode d'origine si l'intersection échoue.

Validé isolément : volumes identiques (1663,95 dans les deux cas) mais
300 faces au lieu de 360.

| Cas | avant | après |
|---|---|---|
| L boîtes / 2 directions | OK 16 587 | OK 16 581 |
| Y boîtes 30° | OK 11 735 | OK 9 800 |
| Y cylindres 30° grand | OK 96 846 | OK 100 499 |
| **Y cylindres 30° petit** | ÉCHEC `polygon` | **OK 45 113** |
| Y cylindres 45° | ÉCHEC `polygon` | ÉCHEC collision (contrainte machine réelle) |

**La classe `unable to recover polygon!` disparaît.** Non-régression
matière vérifiée : extrusion nette +2,59 % sur le gros Y cylindrique
(1273,10 → 1306,09 mm), pas de perte.

## 6. Le refus de collision plante en `KeyError`

`checkForBedNozzleCollisions` détecte correctement la collision, affiche
`Slicing Stopped. Detected collision between bed and nozzle.`, puis fait
`break` — en laissant les dictionnaires de chunks incomplets. Le
`KeyError: '1'` tombe plus tard dans `write_5_axis_gcode`, sans rapport
visible avec la cause.

Le détail est désormais mémorisé (`collisionDetail`) et le site d'arrêt
lève :

```
Collision plateau-buse : le plan de coupe #1 (theta=45.0 deg, phi=0.0 deg)
incline trop la piece.
  couche #0, z=7.86 mm
  garde disponible 11.11 mm < minimum requis 12.0 mm
  piste : reduire l'angle theta de ce plan, ou le remonter...
```

Conseil vérifié sur pièce fixe, angle seul variant : 30° refusé, puis
25/22/21/18/15° tous acceptés. Monotone.

## Résultat global

`test_limits.py` sur les 6 cas d'origine : score inchangé (3/6), mais **la
nature des échecs change du tout au tout** — les trois échecs restants ont
désormais la même cause identifiée (garde de 12 mm), chacun nommant son
plan, son angle et l'écart manquant. Plus aucun échec opaque.

## Ce que je n'ai pas corrigé

**Le slicing depuis le GUI se fige.** Le calcul démarre normalement puis
bloque sur « Manifold Infill » : 33 min sans progression, CPU 282 %
constant, **0 processus enfant**, RSS strictement figé,
`utime=363 962 / stime=266 471` — 42 % du temps CPU en temps système, soit
de la contention de verrous, pas du travail.

C'est le danger annoncé par le `DeprecationWarning` émis à chaque étape
parallèle : `fork()` depuis un processus multi-threadé (boucle pyglet +
thread de slicing). En headless le processus est mono-thread, d'où
l'absence du problème.

Trois correctifs tentés, aucun ne tient :

- `ThreadPoolExecutor` — l'optimisation des chemins est du Python pur, donc
  tenue par le GIL : les threads se piétinent
- `mp_context='forkserver'` — `_fixup_main_from_path` ré-exécute le module
  principal dans le worker
- `mp_context='spawn'` — même problème de ré-import

Le correctif qui marcherait : créer le pool **une seule fois à l'import**
de `slicing_functions`, avant que pyglet ne lance ses threads. Demande de
refondre les 8 sites d'appel et leurs blocs `with`, ce qui dépassait mon
besoin — j'utilise le cœur en headless, qui s'importe seul sans dépendance
GUI.

**Il n'y a pas non plus de test de collision buse-pièce.** Le commentaire
de `create_chunkList` indique que le chiselling « ensure no collisions
between the printhead and the in-process part », mais c'est un argument
d'ordonnancement, pas une vérification : rien ne teste que le corps de la
buse atteint la zone sans toucher la matière déjà déposée. Bloquant pour
les géométries denses ; sans effet sur les pièces que j'ai essayées.
