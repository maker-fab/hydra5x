Complément après vérification plus poussée — le diagnostic initial était incomplet, et le patch proposé plus haut touche à plus de choses que ce que le titre laisse entendre. Voici pourquoi.

## `joint_to_native()` est la forward de LinuxCNC recopiée verbatim

En comparant point par point `joint_to_native()` avec `fiveaxis_KinematicsForward()` de `5axiskins.c`, les deux sont **rigoureusement identiques** une fois la négation sur `rz` retirée — écart `0.000e+00` sur 20 000 points aléatoires.

```
Rep5x joint_to_native  VS  LinuxCNC forward, 20000 points :
  tel quel (avec la négation rz) : écart max = 95.8000 mm
  négation rz retirée            : écart max = 0.000e+00 mm
```

Autrement dit : un seul caractère sépare `joint_to_native()` de la fonction LinuxCNC d'origine.

## Mais les deux fonctions ne suivent pas la même convention

`native_to_joint()`, elle, a divergé de LinuxCNC sur deux points qui semblent délibérés :

1. **Sens de l'axe B inversé** — les termes `sin_b * pivot_length` en X/Y ont le signe opposé à LinuxCNC. (`5axiskins.c` note d'ailleurs lui-même, point 10 de son en-tête, que son axe de tilt va dans le sens inverse du sens conventionnel — un port qui remet le sens conventionnel est cohérent.)
2. **Terme `rotational_offset_y` (LC)** — absent de LinuxCNC, dont le modèle est un pivot simple sans offset entre les deux axes rotatifs. C'est un ajout propre à Rep5x.

`joint_to_native()` n'a reçu ni l'un ni l'autre. Elle est restée la version LinuxCNC.

## Conséquence : trois écarts, pas un seul

| | `native_to_joint` (Rep5x) | `joint_to_native` (LinuxCNC) |
|---|---|---|
| Terme LC | présent | **absent** |
| Signe `LB·sin_b` en X/Y | convention Rep5x | convention LinuxCNC (opposée) |
| Terme Z | `(cos_b - 1)·LB` | `(1 + cos_b)·LB` au lieu de `(1 - cos_b)·LB` |

Erreurs d'aller-retour mesurées (LC=5.0, LB=47.9) :

```
C=  0° B= 0° → X  +0.00  Y  +0.00  Z +95.80 mm
C= 90° B= 0° → X  -5.00  Y  -5.00  Z +95.80 mm
C= 45° B=30° → X +30.33  Y +32.41  Z +82.97 mm
C=  0° B=90° → X +95.80  Y  +0.00  Z  +0.00 mm
```

À noter : à B=90° l'erreur en Z s'annule complètement (cos_b = 0) alors que l'erreur en XY est maximale. Un test mené uniquement à cet angle ne verrait rien en Z. Inversement, un test à C=0/B=0 ne montre que l'erreur Z et masque celles en XY.

Avec la valeur par défaut du `Configuration.h` à la racine du dépôt (`DEFAULT_ROTATIONAL_JOINT_OFFSET_Z 54.67`), l'erreur Z à B=0 est de **109,34 mm** plutôt que les 95,8 mm cités plus haut (qui correspondent au LB=47.9 du build-guide).

## Pourquoi le bug est passé inaperçu

`native_to_joint()` pilote le mouvement réel (via `inverse_kinematics()`), et elle est correcte — les machines impriment. `joint_to_native()` ne sert qu'à `forward_kinematics()`, donc à la resynchronisation de la position cartésienne. Le défaut ne casse pas l'impression, il corrompt le suivi de position. Silencieux.

## Sur le correctif proposé

Le patch donné dans le message d'ouverture reste valable : il inverse algébriquement `native_to_joint()`, donc il rétablit la cohérence quelle que soit la convention retenue pour B. Vérifié sur 50 000 points, écart max 2,8e-14 mm.

Ce que je ne peux pas trancher à votre place : **quelle convention vous voulez pour B**. Si l'inversion de sens dans `native_to_joint()` est bien volontaire, le patch est correct tel quel. Si c'était au contraire `native_to_joint()` qui avait dérivé par accident, il faudrait aligner dans l'autre sens — mais vu que les machines impriment correctement, ça semble peu probable.

Le point qui tient dans les deux cas : les deux fonctions doivent être inverses mutuelles exactes, et elles ne le sont pas aujourd'hui.
