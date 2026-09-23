# Spec — cinématique PENTA_AXIS_HH (Rep5x)

Machine 5 axes tête-tête : table XYZ + tête portant buse avec 2 axes rotatifs.
Convention calquée sur le firmware Rep5x (`dennisklappe/rep5x-marlin`,
`AXIS4_NAME='C'`, `AXIS5_NAME='B'`) — le firmware a le dernier mot.

## Axes et unités

- X, Y, Z : linéaires, mm.
- C : rotation yaw (lacet) autour de Z, degrés. Coordonnée G-code `I`.
- B : rotation tilt (inclinaison) autour de l'axe horizontal perpendiculaire
  à C après rotation de C, degrés. Coordonnée G-code `J`. B=0° = buse verticale.
- Ordre des rotations : C (yaw) appliqué, puis B (tilt) dans le repère tourné par C.

## Paramètres machine

- `LC` (`rotational_offset_y`) : mm, offset Y entre l'axe du pivot C et l'axe
  du pivot B. Mesuré par l'outil de calibration Rep5x (`lc-lb-measure`).
- `LB` (`rotational_offset_z`) : mm, offset Z entre la pointe de buse et le
  pivot B, buse verticale (B=0°). Mesuré par le même outil.
- Offset hotend (X, Y, Z) : optionnel, ignoré dans cette spec (mettre à 0).

## Deux systèmes de coordonnées

- **native** (alias TCP, "pointe d'outil") : position (X,Y,Z) de la pointe de
  buse dans le repère machine, plus angles (C,B). C'est ce qu'on envoie en
  G-code sous G43.4 (tool center point control actif).
- **joint** (alias machine) : position (X,Y,Z) du point de pivot du chariot
  (avant déport par la géométrie de la tête), plus mêmes angles (C,B)
  inchangés (pass-through).

## Fonctions à implémenter

```
inverse(native: (x,y,z,c_deg,b_deg), LC, LB) -> joint: (x,y,z,c_deg,b_deg)
forward(joint: (x,y,z,c_deg,b_deg), LC, LB) -> native: (x,y,z,c_deg,b_deg)
```

Contrainte dure : `forward(inverse(native, LC, LB), LC, LB) == native` pour
tout native et tout LC, LB (aller-retour exact, tolérance 1e-9 en calcul
double précision). C'est le test de cohérence principal.

## Cas de référence attendus (LC=5.0, LB=47.9)

1. B=0°, C=0° (buse verticale, yaw nul) : joint == native (aucun déport).
2. B=0°, C=90° : joint != native si LC != 0 — l'offset LC (bras de levier
   entre pivot C et pivot B) tourne avec le yaw même à tilt nul. Attendu :
   dx = -sin(C)*LC, dy = (cos(C)-1)*LC, dz = 0.
   ATTENTION : ce n'est PAS "joint==native quel que soit C à B=0" (erreur
   corrigée dans cette révision de la spec — LC=0 est un cas particulier,
   pas la règle générale).
3. Aller-retour : pour tout (x,y,z,c,b) aléatoire, forward(inverse(p)) == p
   à 1e-9 près.

## Format d'entrée/sortie pour comparaison

Tableau numpy `(N, 5)` : colonnes `[x, y, z, c_deg, b_deg]`, dtype float64.
Fonction vectorisée si possible, sinon boucle point par point — peu importe,
seule la sortie numérique compte.

## Ce qui n'est PAS dans le scope

- Compensation Fourier des rotatifs (M667, coefficients EEPROM) — précision
  mécanique, hors cinématique géométrique pure.
- Cinématique inverse pour orientation de buse (vecteur normal -> C,B) —
  cette spec ne couvre que la conversion native<->joint à (C,B) donnés.
