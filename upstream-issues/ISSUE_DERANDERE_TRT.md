Titre : penta_axis_trt.cpp et penta_axis_head_head.cpp : joint_to_native() n'est pas l'inverse exacte de native_to_joint()

## Résumé

Dans les deux fichiers, `joint_to_native()` (cinématique directe) ne
reconstruit pas la position transformée par `native_to_joint()`
(cinématique inverse). Comme `forward_kinematics()` sert à resynchroniser
la position cartésienne depuis les compteurs moteurs, le suivi de position
dérive dès que les axes rotatifs quittent zéro.

Vérifié sur la branche `Marlin2ForPipetBot`, les deux défauts sont présents
inchangés.

## 1. PENTA_AXIS_HH — une négation en trop sur `rz`

`penta_axis_head_head.cpp`, lignes 167 et 171 (les DEUX branches
`AXIS4_NAME`/`AXIS5_NAME` sont touchées) :

```cpp
const float rz = - pivot_length * cosf(RADIANS(180.0f - joints_pos.j));
```

`cos(180° − b) = −cos(b)`, donc `rz = +pivot_length·cos(b)` et
`native_pos.z = joints_pos.z + pivot_length·(1 + cos b)`.

Or `native_to_joint()` construit :

```cpp
joints_pos.z = pos.z + (cos_b - 1.0f) * pivot_length;
```

L'inverse exacte demande `pivot_length·(1 − cos b)`, pas `(1 + cos b)`.

**Écart : `+2 × pivot_length` en Z à B=0°** — soit 109,34 mm pour
`DEFAULT_ROTATIONAL_JOINT_OFFSET_Z = 54.67`.

Comparaison avec la source citée en en-tête, LinuxCNC `5axiskins.c` : elle
utilise la **même** fonction `s2r()` des deux côtés (`pos = joint + r` en
forward, `joint = pos - r` en inverse). L'aller-retour y est donc garanti
par construction. Le portage a réécrit les deux directions séparément au
lieu de partager le calcul du déport, et la réécriture a introduit cette
négation.

## 2. PENTA_AXIS_TRT — deux erreurs de signe

`penta_axis_trt.cpp`, `joint_to_native()`, branche `AXIS4_NAME == 'A'` :

```diff
  // composante X
- + sin_j * cos_i * (pivot_length_y - rotational_offset_y)
+ - sin_j * cos_i * (pivot_length_y - rotational_offset_y)

  // composante Y
- - cos_j * rotational_offset_y
+ + cos_j * rotational_offset_y
```

**Erreur X** : une rotation s'inverse par sa transposée. Les matrices des
coefficients de `(pl_x, pl_y, pl_z)` :

```
native_to_joint           joint_to_native          transposee attendue
X [ cj,     sj,    0  ]   X [ cj,  sj·ci, sj·si]   X [ cj, -sj·ci, sj·si]
Y [-sj·ci, cj·ci, si  ]   Y [ sj,  cj·ci,-cj·si]   Y [ sj,  cj·ci,-cj·si]
Z [ sj·si,-cj·si, ci  ]   Z [ 0,   si,    ci   ]   Z [ 0,   si,    ci   ]
```

Les lignes Y et Z correspondent. La ligne X a `+sj·ci` là où la transposée
exige `−sj·ci`. Erreur mesurée jusqu'à **547 mm**, proportionnelle à la
taille de pièce.

**Erreur Y** : dérivation manuelle de l'inverse exacte. En posant
`c_y = ROY(1−cos i) − sin i·ROZ` et `c_z = ROZ(1−cos i) + sin i·ROY`,
l'inverse correcte donne `+cos j·ROY(1−cos i)`, alors que le code produit
`−cos j·ROY(1+cos i)`. Différence : `−2·cos j·ROY`.
**Erreur constante de `2 × rotational_offset_y`**, indépendante des angles.

La composante Z est correcte (vérifiée à 4×10⁻¹⁴).

## Vérification

Extraction autonome des fonctions (mêmes formules, hors dépendances
Marlin), testée en double précision :

| | avant | après les correctifs |
|---|---|---|
| HH, aller-retour 20 000 points | +95,8 mm en Z à B=0 | 2,8×10⁻¹⁴ mm |
| TRT, aller-retour 50 000 points | X 547 mm / Y 6,00 mm | 0,0000 / 0,0000 |

Pour HH, le firmware compilé le confirme lui-même. Build `env:linux_native`
avec `M114_DETAIL`, moteurs à l'origine et B=0 :

```
Stepper: X:0 Y:0 Z:0 C:0 B:0 E:0
FromStp: X:-0.000 Y: 0.000 Z: 109.340 C: 0.000 B: 0.000 E: 0.000
```

À l'origine articulaire avec inclinaison nulle, la pointe d'outil **est** à
l'origine : la cinématique directe doit rendre l'identité. Elle la place
109,340 mm plus haut, soit exactement `2 × 54,67`.

Au même endroit, `DeltaK` (sortie de `native_to_joint()`) vaut
`161.528 / -77.809 / 105.780`, identique à une implémentation indépendante
de la même formule. **La fonction qui pilote le mouvement est saine** —
c'est bien `joint_to_native()` seule qui est à reprendre.

## Portée

Le défaut est **latent** : `native_to_joint()` pilote tout le mouvement et
est correcte, `G28` désactive `tool_centerpoint_control` pendant le homing,
et le seul chemin qui écrit une position corrompue dans `current_position`
est `set_current_from_steppers_for_axis()` — appelé depuis
`quickstop_stepper()` (M410, arrêt d'urgence, endstop touché), le palpage,
`M852`, `G425` et les menus LCD. Aucun n'est dans la boucle d'impression
normale.

Impact réel : reprise après arrêt d'urgence, palpage avec TCP actif,
`G425`/`M852`, et les remontées de position vers l'hôte.

## La remarque qui me semble la plus utile

HH et TRT sont **deux portages indépendants, depuis deux sources LinuxCNC
différentes** (`5axiskins.c` et `trtfuncs.c`), et tous deux portent le même
type d'erreur. Ça ne ressemble pas à de la malchance mais au motif
lui-même : forward et inverse écrites comme deux formules séparées,
communiquant par variables globales, sans rien qui vérifie qu'elles
s'inversent.

LinuxCNC calcule le déport une fois et l'applique `+`/`−` — correct par
construction. Reprendre cette structure rendrait toute désynchronisation
future impossible, et un test d'aller-retour de quelques lignes suffirait à
verrouiller l'invariant.

## Note annexe

`rotational_offset_y` et `rotational_offset_z` sont des globales sans
initialiseur, commentées « Initialized by settings.load() ». Si `load()` ne
s'applique pas, elles valent 0 et la cinématique devient silencieusement
l'identité, sans message. Rencontré sous `linux_native` (pas d'EEPROM).
Sur matériel réel `settings.reset()` couvre le cas, donc ce n'est pas un
défaut actif — mais une initialisation à la déclaration supprimerait un
mode de panne silencieux.
