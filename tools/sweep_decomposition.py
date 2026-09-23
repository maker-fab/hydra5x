#!/usr/bin/env python3
"""Cherche une decoupe du Y qui passe reellement le test de collision.

Le detecteur de `check_collision.py` travaille sur un G-code existant, ce
qui impose de trancher avant de savoir. Ici on court-circuite : la buse
doit atteindre chaque point de la section du chunk a chaque couche, donc
echantillonner les sections suffit a majorer le risque, sans slicer.

On balaie la hauteur du plan de coupe des bras et leur inclinaison, et on
cherche le premier couple qui ne collisionne plus.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).parent))
from export_chunks import decouper, spherical_to_normal, transform_a_plat  # noqa: E402
from check_collision import carte_hauteurs, disque  # noqa: E402


class SectionIllisible(Exception):
    """Section que trimesh ne sait pas reduire en polygones."""


def points_de_section(maillage, z, pas=1.0):
    """Grille de points a l'interieur de la section du maillage a l'altitude z.

    `polygons_full` est une propriete paresseuse : elle leve a l'acces, pas
    a la construction. L'englober est indispensable, et l'echec doit
    REMONTER -- une section avalee en silence rendrait le test aveugle sur
    cette couche et produirait un "pas de collision" sans fondement.
    """
    try:
        coupe = maillage.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if coupe is None:
            return np.empty((0, 3))
        plan, _ = coupe.to_planar()
        polygones = list(plan.polygons_full)
    except Exception as e:
        raise SectionIllisible(f"section a z={z:.2f} : {e}") from e
    pts = []
    for polygone in polygones:
        x0, y0, x1, y1 = polygone.bounds
        xs = np.arange(x0, x1 + pas, pas)
        ys = np.arange(y0, y1 + pas, pas)
        from shapely.geometry import Point
        for x in xs:
            for y in ys:
                if polygone.contains(Point(x, y)):
                    pts.append((x, y, z))
    return np.array(pts) if pts else np.empty((0, 3))


def penetration_max(deja, chunk, alpha, rayon, couche=0.2, pas_test=1.0):
    """Pire penetration sur toutes les couches du chunk."""
    grille, x0, y0, pas = carte_hauteurs(deja)
    dx, dy, dist, garde = disque(rayon, pas, alpha)
    nx, ny = grille.shape
    zmin, zmax = chunk.bounds[0][2], chunk.bounds[1][2]
    pire, ou = 0.0, None
    sautees = 0
    for z in np.arange(zmin + couche, zmax, max(couche, 0.4)):
        try:
            points = points_de_section(chunk, z, pas_test)
        except SectionIllisible:
            sautees += 1
            continue
        for x, y, zz in points:
            ix = int((x - x0) / pas) + dx
            iy = int((y - y0) / pas) + dy
            ok = (ix >= 0) & (ix < nx) & (iy >= 0) & (iy < ny)
            if not ok.any():
                continue
            d = grille[ix[ok], iy[ok]] - (zz + garde[ok])
            m = float(d.max())
            if m > pire:
                pire, ou = m, (float(x), float(y), float(zz))
    if sautees:
        print(f"      ATTENTION : {sautees} section(s) illisible(s), "
              f"non testees")
    return pire, ou


VOLUME_MINI = 0.02   # fraction du volume total sous laquelle un chunk ne compte pas


def evaluer(angle_bras, z_coupe, alpha, rayon):
    """Pire penetration de tous les chunks, ou None si la decoupe degenere.

    Garde-fou indispensable : si le plan de coupe passe au-dessus de la
    piece, les chunks "reorientes" pesent quelques centiemes de mm3 et le
    test ne trouve evidemment rien. Un zero obtenu ainsi ne signifie pas
    "pas de collision" mais "plus de multidirectionnel" -- exactement le
    faux negatif qu'on cherche a eviter.
    """
    from test_slice import make_y_part
    piece = make_y_part(angle=angle_bras)
    directions = [(0.0, 0.0), (angle_bras, 0.0), (angle_bras, 180.0)]
    departs = [[0.0, 0.0, 0.0], [0.0, 0.0, z_coupe], [0.0, 0.0, z_coupe]]
    try:
        chunks = decouper(piece, directions, departs)
    except Exception as e:
        return None, f"decoupe impossible : {e}"

    utiles = [c.volume for c in chunks[1:] if c is not None]
    if not utiles or max(utiles) < VOLUME_MINI * piece.volume:
        return None, "degeneree : les chunks reorientes sont negligeables"

    pire, ou = 0.0, None
    for k in range(1, len(chunks)):
        if chunks[k] is None:
            continue
        precedents = [c for j, c in enumerate(chunks) if j < k and c is not None]
        if not precedents:
            continue
        T = transform_a_plat(chunks[k], spherical_to_normal(*directions[k]))
        poses = []
        for m in precedents:
            c = m.copy()
            c.apply_transform(T)
            poses.append(c)
        courant = chunks[k].copy()
        courant.apply_transform(T)
        p, o = penetration_max(trimesh.util.concatenate(poses), courant,
                               alpha, rayon)
        if p > pire:
            pire, ou = p, o
    return pire, ou


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--alpha", type=float, default=45.0)
    ap.add_argument("--rayon", type=float, default=15.0)
    ap.add_argument("--angles", type=float, nargs="+", default=[20.0, 30.0, 40.0])
    ap.add_argument("--z", type=float, nargs="+",
                    default=[24.0, 26.0, 28.0, 30.0, 32.0])
    args = ap.parse_args()

    print(f"Cone a {args.alpha:.0f} deg, rayon utile {args.rayon:.0f} mm")
    print(f"{'':10s}" + "".join(f"{z:>9.0f}" for z in args.z)
          + "   <- hauteur du plan de coupe (mm)")
    bons = []
    for angle in args.angles:
        ligne = f"  bras {angle:3.0f} "
        for z in args.z:
            pire, ou = evaluer(angle, z, args.alpha, args.rayon)
            if pire is None:
                ligne += f"{'n/a':>9s}"
            else:
                ligne += f"{pire:9.2f}"
                if pire <= 0.0:
                    bons.append((angle, z))
        print(ligne)
    print("\n  valeurs = penetration max en mm ; 0.00 = aucune collision")
    if bons:
        print(f"  decoupes sans collision : {bons}")
    else:
        print("  AUCUNE decoupe testee ne passe")
    return 0


if __name__ == "__main__":
    sys.exit(main())
