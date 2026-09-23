#!/usr/bin/env python3
"""Mesure l'inclinaison maximale d'une tete depuis sa CAO.

`encombrement_tete.py` attend des cotes relevees a la main. Celui-ci les
extrait directement d'un STEP -- les projets d'imprimantes ouverts en
publient : Voron Stealthburner fournit des tetes completes (V6, Dragon,
Rapido, Revo, Chube) sous GPL-3.0, conduit de refroidissement compris.

C'est mieux qu'un pied a coulisse : on mesure l'assemblage entier, pas
seulement le hotend, donc la ventilation et le support sont dedans.

**Etat** : l'outil fonctionne, mais la CAO Voron Stealthburner ne contient
que les CARENAGES imprimes, pas le hotend -- Voron ne publie pas la
geometrie d'un composant qui ne lui appartient pas. Verifie sur les
versions V6, Rapido et RevoVoron : 3 a 5 solides, Z de 2,4 a 65,5, aucune
buse. Le carenage reste utile -- c'est le conduit de refroidissement, l'une
des quatre cotes cherchees -- mais il faut d'abord localiser la pointe dans
son repere.

Reste a trouver : une CAO de hotend seule. E3D publie une CAO de reference
Revo sur Printables, GrabCAD en heberge plusieurs ; toutes derriere un
compte. A recuperer manuellement, puis passer ici.

**Methode.** L'origine est la pointe de la buse, point le plus bas de
l'assemblage. On construit le profil de silhouette

    h(r) = hauteur MINIMALE de matiere a la distance horizontale r

puis la limite d'inclinaison est le minimum sur tout le profil :

    theta_max = min_r  arctan( h(r) / r )

Traiter chaque piece comme un point unique -- ce que fait
`encombrement_tete.py` -- majore ou minore selon la piece. Le profil ne
suppose rien : il interroge la geometrie a chaque rayon.
"""
import argparse
import sys
from pathlib import Path

import numpy as np


def charger_step(chemin, tolerance=0.3):
    """STEP -> nuage de sommets tesselles.

    Pas de trimesh ici : il exige numpy<2 quand cadquery exige numpy>=2,
    et les deux ne cohabitent pas (voir docs/install.md). La tesselation
    d'OCP donne les sommets, c'est tout ce dont le profil a besoin.
    """
    import cadquery as cq
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE
    from OCP.BRep import BRep_Tool
    from OCP.TopoDS import TopoDS

    forme = cq.importers.importStep(str(chemin))
    solides = forme.solids().vals()
    pts = []
    for s in solides:
        brut = s.wrapped
        BRepMesh_IncrementalMesh(brut, tolerance, False, 0.5, True)
        exp = TopExp_Explorer(brut, TopAbs_FACE)
        while exp.More():
            face = TopoDS.Face_s(exp.Current())
            loc = face.Location()
            tri = BRep_Tool.Triangulation_s(face, loc)
            if tri is not None:
                trsf = loc.Transformation()
                for i in range(1, tri.NbNodes() + 1):
                    p = tri.Node(i).Transformed(trsf)
                    pts.append((p.X(), p.Y(), p.Z()))
            exp.Next()
    if not pts:
        raise RuntimeError(f"aucun solide exploitable dans {chemin.name}")
    return np.array(pts), len(solides)


def profil_silhouette(points, pointe, r_max=25.0, pas=0.25):
    """h(r) : hauteur minimale de matiere a chaque distance de l'axe."""
    d = np.hypot(points[:, 0] - pointe[0], points[:, 1] - pointe[1])
    z = points[:, 2] - pointe[2]
    rayons = np.arange(pas, r_max + pas, pas)
    h = np.full(len(rayons), np.inf)
    for i, r in enumerate(rayons):
        dans = (d >= r - pas) & (d < r + pas)
        if dans.any():
            h[i] = float(z[dans].min())
    return rayons, h


def limite(rayons, h, r_min=1.0):
    """Inclinaison max et rayon ou elle se joue.

    `r_min` exclut le meplat de la pointe. Une buse a une face plate de
    l'ordre du millimetre : c'est le PIVOT, pas un obstacle. L'inclure fait
    sortir 0° puisque h y vaut zero par construction.
    """
    valide = np.isfinite(h) & (rayons >= r_min)
    angles = np.degrees(np.arctan2(np.maximum(h[valide], 0.0), rayons[valide]))
    i = int(angles.argmin())
    return float(angles[i]), float(rayons[valide][i]), float(h[valide][i])


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", type=Path, nargs="+")
    ap.add_argument("--r-max", type=float, default=25.0)
    ap.add_argument("--r-min", type=float, default=1.4,
                    help="rayon du meplat de pointe, exclu du calcul")
    ap.add_argument("--marge", type=float, default=0.80)
    ap.add_argument("--tolerance", type=float, default=0.3,
                    help="finesse de tesselation, mm")
    args = ap.parse_args()

    for chemin in args.step:
        print(f"\n=== {chemin.name} ===")
        pts, n_solides = charger_step(chemin, args.tolerance)
        pointe = pts[pts[:, 2].argmin()]
        print(f"  {n_solides} solides, {len(pts)} sommets")
        print(f"  pointe supposee : X{pointe[0]:.2f} Y{pointe[1]:.2f} "
              f"Z{pointe[2]:.2f}")

        rayons, h = profil_silhouette(pts, pointe, args.r_max)
        angle, r, hauteur = limite(rayons, h, args.r_min)
        print(f"\n  limite brute  {angle:5.1f}°  "
              f"(matiere a r={r:.2f} mm, h={hauteur:.2f} mm)")
        print(f"  limite utile  {angle*args.marge:5.1f}°  "
              f"(marge {args.marge*100:.0f} %)")

        print("\n  profil de silhouette :")
        print(f"  {'r (mm)':>8s} {'h (mm)':>8s} {'angle':>8s}")
        for r_ in (1, 1.5, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20):
            i = int(np.argmin(np.abs(rayons - r_)))
            if not np.isfinite(h[i]):
                continue
            a = np.degrees(np.arctan2(max(h[i], 0.0), rayons[i]))
            print(f"  {rayons[i]:8.2f} {h[i]:8.2f} {a:7.1f}°")
    return 0


if __name__ == "__main__":
    sys.exit(main())
