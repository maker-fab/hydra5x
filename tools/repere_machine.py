#!/usr/bin/env python3
"""Transpose un G-code de chunk du repere « pose a plat » vers la machine.

**Le verrou de D30.** Quand c'est le PLATEAU qui bascule, incliner le
plateau defait exactement la mise a plat du chunk : les coordonnees du
G-code sont deja les bonnes, a une translation pres. Quand c'est la TETE
qui s'incline, la piece ne bouge plus -- et il faut faire tourner la
trajectoire elle-meme.

C'est le prix du choix de D30, et il est entierement logiciel.

**La transformation.** Pour un chunk de direction `n`, soit `R` la rotation
qui amene `n` sur +Z (celle qui a servi a poser le chunk a plat) et `d` la
translation que la mise a plat a retiree. Un point du G-code revient dans
le repere machine par

    XYZ = R^-1 . (gcode - centre_slicer + d + (0, 0, p)) + position_piece

ou `p` est la distance du centre de bascule de la platine a la pointe de
la buse. Le terme en `p` est la compensation du point pilote : la machine
positionne la PLATINE, l'utilisateur veut positionner la POINTE.

Tout cela est **une seule transformation affine par chunk**, parce qu'en
regime indexe l'orientation ne change pas pendant le bloc. La compensation
de pointe n'est donc pas un calcul par segment : c'est un terme constant,
absorbe dans la meme matrice.

**Ce qui doit etre refuse plutot que mal fait** :

- les arcs `G2`/`G3` : une rotation hors du plan ne conserve pas un arc
  circulaire dans le plan machine. Il faut les desactiver au tranchage ;
- le mode relatif `G91` sur les axes de position : les deplacements
  relatifs se transforment en vecteurs, pas en points, et melanger les
  deux silencieusement produirait une derive.

`E` et `F` traversent sans changement : une rotation conserve les
longueurs, donc les volumes extrudes et les vitesses.
"""
import re
import sys
from pathlib import Path

import numpy as np

MOUVEMENT = re.compile(r"^\s*(G0|G1)\b", re.I)
CHAMP = re.compile(r"([XYZEF])(-?\d*\.?\d+)", re.I)


class SectionIllisible(RuntimeError):
    """Une construction que la transformation ne sait pas traiter."""


def matrice(rotation, decalage, pivot, position_piece, centre_slicer):
    """Matrice 4x4 du repere chunk vers le repere machine."""
    m = np.eye(4)
    m[:3, :3] = np.asarray(rotation)[:3, :3].T          # R^-1, R orthogonale
    avant = (np.asarray(decalage, dtype=float)
             + np.array([0.0, 0.0, pivot])
             - np.array([centre_slicer[0], centre_slicer[1], 0.0]))
    m[:3, 3] = m[:3, :3] @ avant + np.asarray(position_piece, dtype=float)
    return m


def appliquer(m, point):
    return (m[:3, :3] @ np.asarray(point, dtype=float)) + m[:3, 3]


def transformer(lignes, m, depart=(0.0, 0.0, 0.0)):
    """Reecrit les mouvements d'un bloc dans le repere machine.

    Les coordonnees sont **toujours reemises en entier**. Une rotation
    couple les trois axes : un `G1 X10` du repere chunk devient un
    mouvement qui change aussi Y et Z. Ne reemettre que X produirait une
    trajectoire fausse et silencieuse.
    """
    position = np.array(depart, dtype=float)
    sortie = []
    for numero, ligne in enumerate(lignes, 1):
        nu = ligne.split(";")[0]
        if re.match(r"^\s*(G2|G3)\b", nu, re.I):
            raise SectionIllisible(
                f"ligne {numero} : arc G2/G3. Une rotation hors plan ne "
                "conserve pas l'arc -- trancher sans ajustement d'arcs "
                "(PrusaSlicer : --gcode-arcs=0)")
        if re.match(r"^\s*G91\b", nu, re.I):
            raise SectionIllisible(
                f"ligne {numero} : G91. Le mode relatif sur les axes de "
                "position n'est pas traite ; le G-code doit etre en G90")
        if not MOUVEMENT.match(nu):
            sortie.append(ligne)
            continue

        champs = {c.upper(): float(v) for c, v in CHAMP.findall(nu)}
        bouge = any(a in champs for a in "XYZ")
        if bouge:
            for i, axe in enumerate("XYZ"):
                if axe in champs:
                    position[i] = champs[axe]
        commande = nu.strip().split()[0].upper()
        morceaux = [commande]
        if "F" in champs:
            morceaux.append(f"F{champs['F']:.0f}")
        if bouge:
            q = appliquer(m, position)
            morceaux += [f"X{q[0]:.4f}", f"Y{q[1]:.4f}", f"Z{q[2]:.4f}"]
        if "E" in champs:
            morceaux.append(f"E{champs['E']:.5f}")
        commentaire = ligne.split(";", 1)
        suffixe = f" ;{commentaire[1]}" if len(commentaire) > 1 else ""
        sortie.append(" ".join(morceaux) + suffixe)
    return sortie, position
