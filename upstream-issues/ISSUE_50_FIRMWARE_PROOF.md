Vérification faite en exécutant le firmware lui-même, plutôt qu'en raisonnant sur le source. Il confirme le défaut sans référence externe. J'en profite pour corriger le cadrage de mon message d'ouverture, qui était trop alarmant.

## D'abord : ça n'affecte pas l'impression

Après avoir tracé les chemins d'appel, le défaut est **latent**. Une machine Rep5x imprime correctement, et voici pourquoi :

- `native_to_joint()` pilote tout le mouvement (via `inverse_kinematics()`), et elle est correcte — vérifiée ci-dessous.
- `joint_to_native()` ne sert qu'à relire la position depuis les moteurs.
- `G28.cpp` désactive explicitement `tool_centerpoint_control` pendant le homing et le restaure après, donc `joint_to_native()` y est un passthrough.

Le seul chemin qui écrit une position corrompue dans `current_position` est `set_current_from_steppers_for_axis()`, appelé depuis :

| Appelant | Déclencheur |
|---|---|
| `quickstop_stepper()` | M410, arrêt d'urgence, kill, endstop touché en cours de mouvement, fin de filament |
| `probe.cpp:758` | déclenchement de palpeur (G29/G30) |
| `M852.cpp`, `G425.cpp` | calibration skew / cube |
| menus LCD tramming | réglage manuel |

Plus `report_real_position()` et `report_current_position_moving()`, en lecture seule vers l'hôte.

Aucun n'est dans la boucle d'impression normale. C'est précisément pour ça que le défaut a survécu : rien ne le signale tant qu'on imprime.

Impact réel : reprise après arrêt d'urgence ou endstop touché, palpage avec TCP actif, G425/M852, et les remontées de position vers l'hôte.

## Le firmware constate l'erreur lui-même

Build `env:linux_native` (`MOTHERBOARD BOARD_SIMULATED`), avec `M114_DETAIL` activé. `M114 D` expose trois lignes utiles : `DeltaK:` (sortie de `inverse_kinematics()`), `FromStp:` (sortie de `forward_kinematics()`, donc `joint_to_native()`), et `Diff:`.

Avec les valeurs par défaut du `Configuration.h` à la racine du dépôt (`LC = 1.6`, `LB = 54.67`), moteurs à l'origine et B = 0 :

```
Stepper: X:0 Y:0 Z:0 C:0 B:0 E:0
FromStp: X:-0.000 Y: 0.000 Z: 109.340 C: 0.000 B: 0.000 E: 0.000
```

À l'origine articulaire avec une inclinaison nulle, la pointe d'outil **est** à l'origine : la cinématique directe doit rendre l'identité. Le firmware la place 109,340 mm plus haut.

```
109.340 = 2 × 54.67 = 2 × LB
```

C'est exactement l'erreur `+2·LB` prédite dans le message d'ouverture, au chiffre près, calculée par le firmware avec sa propre arithmétique.

## `native_to_joint()` est correcte

Même build, après `G43.4` puis `G1 B30 C45` :

```
Raw:     X: 200.000 Y:-40.000 Z: 174.600
DeltaK:  X: 161.528 Y:-77.809 Z: 105.780
```

Une implémentation indépendante de la même formule, en double précision hors firmware, donne `161.528 / -77.8089 / 105.780` pour les mêmes entrées. Identique à la précision d'affichage.

Donc la fonction qui pilote le mouvement est saine, et c'est bien `joint_to_native()` seule qui est à reprendre. Ça confirme aussi le sens du correctif proposé : inverser algébriquement `native_to_joint()`, et non l'inverse.

## Reproduction

```bash
# Configuration.h : MOTHERBOARD BOARD_SIMULATED
# Configuration_adv.h : #define M114_DETAIL
pio run -e linux_native
printf 'M211 S0\nG43.4\nG91\nG1 B30 C45 F3000\nG90\nM400\nM114 D\n' \
  | ./.pio/build/linux_native/program
```

Modifications nécessaires pour ce build de test, aucune ne touche la cinématique :

- `SDSUPPORT`, `BTT_MINI_12864`, `NEOPIXEL_LED`, `ADVANCED_PAUSE_FEATURE`, `CUSTOM_MENU_MAIN` désactivés (non supportés par `HAL/LINUX`)
- drivers passés en `A4988` (le software serial des TMC220x n'est pas supporté par `HAL/LINUX`)
- pins factices pour I/J dans `pins_RAMPS_NATIVE.h`, `KILL_PIN` retiré
- `rotational_offset_y` / `rotational_offset_z` initialisés à leurs `DEFAULT_*` à la déclaration

Ce dernier point mérite une remarque à part, voir plus bas. Le corps de `native_to_joint()` et de `joint_to_native()` est resté strictement identique à l'original (vérifié par `git diff --quiet` sur le fichier après restauration).

## Limite de la méthode

Les compteurs moteurs restent à zéro sous `linux_native` (pas d'ISR stepper temps réel), donc `joint_to_native()` n'a pu être sondée qu'à l'origine articulaire. Un seul point — mais c'est le cas le plus propre qui soit, puisque le résultat attendu y est l'identité, sans convention ni paramètre à discuter.

J'ai tenté `env:simulator_linux_debug` pour obtenir une vraie simulation de mouvement, sans succès : `MarlinSimUI` attend une géométrie standard et échoue à la compilation sur `X_MIN_ENDSTOP_HIT_STATE` avec `PENTA_AXIS_HH`. Ça pourrait valoir une issue séparée si la simulation vous intéresse.

## Remarque annexe : initialisation des offsets

`rotational_offset_y` et `rotational_offset_z` sont des globales sans initialiseur, avec le commentaire « Initialized by settings.load() ». Si `settings.load()` ne s'applique pas, elles valent 0, et `native_to_joint()` devient silencieusement l'identité — la cinématique 5 axes ne fait plus rien, sans aucun message.

C'est ce qui m'est arrivé sous `linux_native` (pas d'EEPROM) et ça m'a coûté un moment avant de comprendre. Sur matériel réel, `settings.reset()` couvre correctement le cas pour `PENTA_AXIS_HH`, donc ce n'est pas un défaut actif. Mais une initialisation à la déclaration coûterait deux mots et supprimerait un mode de panne silencieux :

```cpp
float rotational_offset_z = DEFAULT_ROTATIONAL_JOINT_OFFSET_Z;
float rotational_offset_y = DEFAULT_ROTATIONAL_JOINT_OFFSET_Y;
```
