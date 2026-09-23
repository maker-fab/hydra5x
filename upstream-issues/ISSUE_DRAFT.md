Titre : PENTA_AXIS_HH: joint_to_native() n'est pas l'inverse exacte de native_to_joint() (erreur de signe en Z)

## Résumé

Dans `Marlin/src/module/penta_axis_head_head.cpp`, `joint_to_native()`
(cinématique directe) ne reconstruit pas exactement la position d'origine
transformée par `native_to_joint()` (cinématique inverse). L'écart mesuré
est de `+2 × rotational_offset_z` sur Z quand B=0°, soit 95.8mm pour la
valeur par défaut LB=47.9mm.

Comme `forward_kinematics()` appelle `joint_to_native()` pour resynchroniser
la position cartésienne affichée/trackée après chaque mouvement, cette
divergence fausse le suivi de position TCP dès que le tilt (B) est non nul.

## Cause

`joint_to_native()` calcule :

```cpp
const float rz = - pivot_length * cosf(RADIANS(180.0f - joints_pos.j));
...
native_pos.z = joints_pos.z + pivot_length + rz;
```

`cos(180° − b) = −cos(b)`, donc `rz = pivot_length·cos(b)`, et
`native_pos.z = joints_pos.z + pivot_length·(1 + cos(b))`.

Or `native_to_joint()` construit `joints_pos.z` avec :

```cpp
joints_pos.z = pos.z + (cos_b - 1.0f) * pivot_length;
```

soit `pos.z = joints_pos.z + pivot_length·(1 − cos(b))` pour retrouver `pos.z`
exactement — pas `pivot_length·(1 + cos(b))`. Les deux formules divergent
sauf quand `cos(b) = 0` (B = 90°).

## Comparaison avec la référence citée

Le fichier se réclame dérivé de LinuxCNC `5axiskins.c`
(https://github.com/LinuxCNC/linuxcnc/blob/master/src/emc/kinematics/5axiskins.c).
Dans ce fichier, forward et inverse utilisent la **même** fonction `s2r()`
pour calculer le vecteur de déport `r` :

```c
// forward:  pos = joint + r
// inverse:  joint = pos - r
```

`r` étant calculé identiquement des deux côtés, l'aller-retour y est garanti
par construction. Le port vers `penta_axis_head_head.cpp` a réécrit les deux
directions séparément plutôt que de partager le calcul de déport, et la
réécriture de `joint_to_native()` a introduit une négation en trop.

## Correctif proposé

Reconstruire `joint_to_native()` en inversant algébriquement les formules de
`native_to_joint()` (même convention d'angle B, sans passer par `180 − b`) :

```cpp
xyz_pos_t joint_to_native(const xyz_pos_t &joints_pos) {
  if (!tool_centerpoint_control) return joints_pos;

  const float pivot_length = DIFF_TERN(HAS_HOTEND_OFFSET, rotational_offset_z, hotend_offset[active_extruder].z);

  #if AXIS4_NAME == 'C'
    const float b_rad = RADIANS(joints_pos.j);
    const float c_rad = RADIANS(joints_pos.i);
  #elif AXIS5_NAME == 'C'
    const float b_rad = RADIANS(joints_pos.i);
    const float c_rad = RADIANS(joints_pos.j);
  #endif

  const float sin_b = sinf(b_rad), cos_b = cosf(b_rad);
  const float sin_c = sinf(c_rad), cos_c = cosf(c_rad);

  const xyz_pos_t native_pos = NUM_AXIS_ARRAY(
    joints_pos.x + sin_c * rotational_offset_y - cos_c * sin_b * pivot_length,
    joints_pos.y + (1.0f - cos_c) * rotational_offset_y - sin_c * sin_b * pivot_length,
    joints_pos.z + (1.0f - cos_b) * pivot_length,
    joints_pos.i,
    joints_pos.j
  );

  return native_pos;
}
```

## Reproduction

Extraction autonome des deux fonctions (mêmes formules, hors dépendances
Marlin), testée en C++ (double précision) et croisée avec une seconde
implémentation indépendante en Python/numpy :

- Avant correctif : à B=0°, C=90°, LB=47.9mm — `joint_to_native(native_to_joint(p))`
  redonne `p.z + 95.8mm` au lieu de `p.z`.
- Après correctif : aller-retour exact sur 20 000 points aléatoires
  (X,Y,Z ∈ [-100,100]mm, C ∈ [0°,360°[, B ∈ [0°,90°]) — écart max
  2.8×10⁻¹⁴mm (bruit flottant, négligeable).

Repo de test (extraction + comparateur) disponible si utile pour vérifier
indépendamment.

## Question ouverte

Le fichier gère aussi le cas `AXIS5_NAME == 'C'` (axes inversés) — le
correctif ci-dessus couvre les deux branches par symétrie, mais je n'ai
testé que la config par défaut du firmware-builder Rep5x
(`AXIS4_NAME='C'`, `AXIS5_NAME='B'`). Si une machine utilise l'autre
convention, ça vaut la peine de la tester aussi avant merge.
