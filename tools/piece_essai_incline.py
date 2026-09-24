#!/usr/bin/env python3
"""Piece d'essai pour le depot sur couche inclinee.

La seule question que le calcul ne tranche pas (D21, D22, D27) : **le
cordon fondu tient-il quand le plan de depot n'est pas horizontal ?** Le
plateau basculant garde ce plan horizontal, la tete inclinable non. Tout
l'arbitrage d'architecture en depend.

**L'essai ne demande aucune machine 5 axes.** Incliner une imprimante 3
axes entiere reproduit exactement la posture d'une tete inclinable : buse
et plateau gardent leur geometrie relative, seule la gravite change de
direction par rapport a la couche. C'est la meme physique, pour le prix
d'une cale.

**Geometrie choisie : un cylindre creux, une paroi, un seul cordon par
couche.** Chaque couche parcourt donc *toutes* les directions par rapport
a la pente. Le defaut ne se cherche pas, il se lit : le cordon flue vers
l'aval, la paroi s'epaissit en bas de pente et s'amincit en haut, et le
cylindre devient excentre. Un seul objet donne la courbe complete au lieu
d'un point.

Les quatre ergots reperent les azimuts a 0, 90, 180 et 270° pour que
l'orientation reste lisible sur la piece une fois detachee -- sans eux,
impossible de savoir ou etait l'amont apres coup.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import trimesh


def cylindre_creux(diametre, hauteur, paroi, segments=128):
    """Tube mince : une seule paroi, donc un seul cordon par couche."""
    ext = trimesh.creation.cylinder(radius=diametre / 2.0, height=hauteur,
                                    sections=segments)
    interne = trimesh.creation.cylinder(radius=diametre / 2.0 - paroi,
                                        height=hauteur * 1.2, sections=segments)
    tube = ext.difference(interne)
    tube.apply_translation((0.0, 0.0, hauteur / 2.0))
    return tube


def embase(cote, epaisseur):
    """Socle carre : adherence franche, et reference plane pour mesurer."""
    s = trimesh.creation.box(extents=(cote, cote, epaisseur))
    s.apply_translation((0.0, 0.0, epaisseur / 2.0))
    return s


def ergots(rayon, hauteur, taille):
    """Quatre reperes d'azimut, a 0, 90, 180 et 270 degres."""
    pieces = []
    for i, a in enumerate(np.radians([0.0, 90.0, 180.0, 270.0])):
        # un ergot de longueur croissante : l'azimut se lit sans ambiguite
        longueur = taille * (1.0 + 0.6 * i)
        e = trimesh.creation.box(extents=(longueur, taille, hauteur))
        e.apply_translation((longueur / 2.0, 0.0, hauteur / 2.0))
        e.apply_transform(trimesh.transformations.rotation_matrix(a, [0, 0, 1]))
        e.apply_translation((rayon * np.cos(a), rayon * np.sin(a), 0.0))
        pieces.append(e)
    return pieces


def construire(diametre, hauteur, paroi, socle, ep_socle):
    piece = trimesh.util.concatenate(
        [embase(socle, ep_socle),
         cylindre_creux(diametre, hauteur, paroi)]
        + ergots(diametre / 2.0 - paroi / 2.0, ep_socle, 3.0))
    piece.merge_vertices()          # sans quoi l'export STL rend des faces degenerees
    return piece


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path,
                    default=Path("testparts/essai_depot_incline.stl"))
    ap.add_argument("--diametre", type=float, default=40.0)
    ap.add_argument("--hauteur", type=float, default=60.0)
    ap.add_argument("--paroi", type=float, default=0.8,
                    help="une largeur de cordon, buse 0,4 mm")
    ap.add_argument("--socle", type=float, default=52.0)
    ap.add_argument("--ep-socle", type=float, default=1.2)
    args = ap.parse_args()

    piece = construire(args.diametre, args.hauteur, args.paroi,
                       args.socle, args.ep_socle)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    piece.export(args.out)

    relu = trimesh.load(args.out)
    print(f"  {args.out}")
    print(f"  cylindre Ø{args.diametre:.0f} x {args.hauteur:.0f} mm, "
          f"paroi {args.paroi:.1f} mm, socle {args.socle:.0f} mm")
    print(f"  {len(relu.faces)} faces, volume {relu.volume/1000:.1f} cm3, "
          f"etanche : {relu.is_watertight}")
    if not relu.is_watertight:
        raise SystemExit("le STL relu n'est pas etanche -- inexploitable")
    duree = relu.volume / 1000.0 * 2.5
    print(f"  ~{duree:.0f} min par exemplaire, ~{duree*4/60:.1f} h "
          f"pour la serie de quatre angles")
    return 0


if __name__ == "__main__":
    sys.exit(main())
