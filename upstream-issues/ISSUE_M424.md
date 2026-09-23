Titre : Build guide : la doc renvoie vers M424 pour régler LC/LB, la commande réelle est M665 J/K

## Problème

`build-guide/universal-parts/firmware/Configuration.h`, ligne 1968 :

```
 * These values are determined through the Rep5x calibration procedure.
 * Use M424 Y<LC> Z<LB> to set at runtime, or update these defaults.
```

`M424` n'existe pas dans le firmware. Aucun `case 424` dans `gcode.cpp`, aucun fichier source, et `grep -rn "M424" Marlin/src/` ne renvoie rien.

Vérifié sur un build `env:linux_native` :

```
> M424 Y1.6 Z54.67
echo:Unknown command: "M424 Y1.6 Z54.67"
ok
```

## La commande correcte

C'est `M665 J<LC> K<LB>`, implémentée dans `Marlin/src/gcode/calibrate/M665.cpp` :

```cpp
if (parser.seenval('J')) rotational_offset_y = parser.value_linear_units();  // LC
if (parser.seenval('K')) rotational_offset_z = parser.value_linear_units();  // LB
```

Elle fonctionne :

```
> M665 J1.6 K54.67
ok
> M665
  M665 S0.00 J1.60 K54.67
ok
```

À noter : `tools/shared/printer-interface.js` ligne 360 utilise déjà le bon format, avec le commentaire `// Marlin PENTA_AXIS_HH format: M665 S200 J1.6 K54.67`. Seule la documentation du build guide est décalée.

## Pourquoi ça compte

Le même fichier livre `DEFAULT_ROTATIONAL_JOINT_OFFSET_Y 0.0` (LC = 0). Un utilisateur qui suit la procédure de calibration, obtient son LC et tente de l'appliquer avec la commande documentée reçoit `Unknown command` — et sans autre indication, doit recompiler pour appliquer une valeur mesurée.

## Origine probable

Ligne 2232 du même fichier, un commentaire hérité de Marlin amont :

```
 * Add Z offset (M424 Z) that applies to all moves at the planner level.
```

Ça concerne `GLOBAL_MESH_Z_OFFSET` (offset Z de maillage, désactivé ici) et n'a aucun rapport avec LC/LB. Le « M424 » de la ligne 1968 vient vraisemblablement de là.

## Correctif

Ligne 1968 de `build-guide/universal-parts/firmware/Configuration.h` :

```diff
- * Use M424 Y<LC> Z<LB> to set at runtime, or update these defaults.
+ * Use M665 J<LC> K<LB> to set at runtime, or update these defaults.
```

Le `Configuration.h` à la racine du dépôt ne porte pas cette mention et n'est donc pas concerné.
