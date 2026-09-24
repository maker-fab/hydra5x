#!/usr/bin/env python3
"""Volume imprimable reellement utilisable sur une machine a plateau inclinable.

Une 5 axes a plateau inclinable **perd du volume** par rapport a la 3 axes
batie dans le meme cadre. Personne ne chiffre cette perte ; les fiches
annoncent le volume a inclinaison nulle. Ce fichier la calcule.

**Pourquoi il y a une perte.** Quand le plateau s'incline de theta, la
piece bascule avec lui :

- son point haut monte -- il faut de la course Z pour que la buse
  l'atteigne encore ;
- son enveloppe s'elargit -- il faut de la course X/Y ;
- le bord du plateau plonge -- il faut du vide sous le plateau.

Modele. Pivot dans le PLAN du plateau, en son centre (`--pivot` pour le
cas general). Piece = cylindre centre, rayon `r`, hauteur `H`. En inclinant
de theta, le point le plus defavorable est le bord haut oppose au sens de
bascule :

    Z_haut = r.sin(theta) + H.cos(theta)      course Z necessaire
    demi_largeur = r.cos(theta) + H.sin(theta)  course X/Y necessaire / 2
    plongee = R_plateau.sin(theta)            vide sous le plateau

Avec une table a trois points l'azimut de bascule est quelconque, donc la
contrainte porte sur **min(course_X, course_Y)**.

**Ce que le calcul montre tout de suite** : le terme `H.sin(theta)` est le
cout dominant. Une piece haute coute beaucoup plus cher en volume qu'une
piece large. Une machine 5 axes est donc naturellement **plus plate** que
la 3 axes de meme cadre -- et la contrainte tombe sur le cadre, pas sur la
cinematique.
"""
import argparse
import sys

import numpy as np


def faisable(r, h, theta_deg, course_xy, course_z, pivot=0.0):
    """La piece (r, h) tient-elle dans les courses a cette inclinaison ?"""
    t = np.radians(theta_deg)
    haut = max(h - pivot, 0.0)
    bas = max(pivot, 0.0)
    z_requis = r * np.sin(t) + haut * np.cos(t) + bas
    demi = r * np.cos(t) + max(haut, bas) * np.sin(t)
    return z_requis <= course_z and 2 * demi <= course_xy


def meilleur_cylindre(theta_deg, course_xy, course_z, pivot=0.0, pas=1.0):
    """Cylindre centre de plus grand volume qui reste faisable a theta."""
    meilleur = (0.0, 0.0, 0.0)
    for r in np.arange(pas, course_xy / 2 + pas, pas):
        for h in np.arange(pas, course_z + pas, pas):
            if not faisable(r, h, theta_deg, course_xy, course_z, pivot):
                continue
            v = np.pi * r * r * h
            if v > meilleur[2]:
                meilleur = (float(r), float(h), float(v))
    return meilleur


def plongee(rayon_plateau, theta_deg):
    """Vide necessaire sous le plateau, mm."""
    return rayon_plateau * np.sin(np.radians(theta_deg))


def inclinaison_table(rayon_points, course_differentielle):
    """Inclinaison max d'une table a trois points, degres.

    Trois points a 120 deg sur un cercle de rayon `rayon_points`. En
    basculant autour d'un axe passant par un point et le milieu des deux
    autres, le bras de levier vaut 1,5 x rayon. `course_differentielle` est
    l'ecart de hauteur que les actionneurs peuvent creuser entre eux.

    C'est la borne dure de l'architecture : elle ne depend que de
    l'encombrement au sol et de la course des vis, jamais de la tete.
    """
    import math
    return math.degrees(math.atan2(course_differentielle,
                                   1.5 * rayon_points))


def cout_outils(n, largeur_dock, profondeur_dock, course_x, course_y):
    """Ce que N outils parques retirent aux courses. (course_x, course_y)."""
    if n <= 1:
        return course_x, course_y
    if n * largeur_dock > course_x:
        raise ValueError(f"{n} docks de {largeur_dock} mm ne tiennent pas "
                         f"dans {course_x} mm de course X")
    return course_x, course_y - profondeur_dock


CADRES = {
    # nom : (course_X, course_Y, course_Z, diametre utile du plateau)
    "Voron Trident 300": (300, 300, 250, 300),
    "Voron Trident 350": (350, 350, 250, 350),
    "Voron 2.4 350": (350, 350, 310, 350),
    "Fractal 5 Pro": (200, 200, 200, 324),
    "Archer Demonstrator": (300, 300, 350, 300),
}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cadre", choices=sorted(CADRES), default=None)
    ap.add_argument("--course", type=float, nargs=3, metavar=("X", "Y", "Z"))
    ap.add_argument("--plateau", type=float, help="diametre utile, mm")
    ap.add_argument("--inclinaison", type=float, default=45.0,
                    help="inclinaison max de la table, degres")
    ap.add_argument("--pivot", type=float, default=0.0,
                    help="hauteur du pivot au-dessus du plateau, mm")
    ap.add_argument("--outils", type=int, default=1)
    ap.add_argument("--dock", type=float, nargs=2, default=(55.0, 60.0),
                    metavar=("LARGEUR", "PROFONDEUR"),
                    help="encombrement d'un dock d'outil, mm")
    ap.add_argument("--pas", type=float, default=2.0,
                    help="pas de balayage r/H, mm")
    args = ap.parse_args()

    if args.cadre:
        cx, cy, cz, plateau = CADRES[args.cadre]
        nom = args.cadre
    elif args.course and args.plateau:
        cx, cy, cz = args.course
        plateau = args.plateau
        nom = "cadre fourni"
    else:
        ap.error("donner --cadre, ou --course X Y Z avec --plateau")

    cx, cy = cout_outils(args.outils, args.dock[0], args.dock[1], cx, cy)
    # le plateau borne le rayon au meme titre que les courses : une piece
    # plus large que lui ne tient nulle part
    course_xy = min(cx, cy, plateau)

    print(f"=== {nom} ===")
    print(f"  courses apres {args.outils} outil(s) : "
          f"X{cx:.0f} Y{cy:.0f} Z{cz:.0f}, plateau Ø{plateau:.0f}")
    if args.outils > 1:
        print(f"  ({args.outils} docks de {args.dock[0]:.0f} mm : "
              f"{args.outils*args.dock[0]:.0f} mm occupes en X, "
              f"-{args.dock[1]:.0f} mm en Y)")

    r0, h0, v0 = meilleur_cylindre(0.0, course_xy, cz, args.pivot, args.pas)
    print(f"\n  {'incl.':>6s} {'rayon':>7s} {'hauteur':>8s} "
          f"{'volume':>9s} {'perte':>7s} {'vide sous plateau':>19s}")
    for theta in (0, 10, 15, 20, 25, 30, 35, 40, 45, 50, 60):
        if theta > args.inclinaison:
            break
        r, h, v = meilleur_cylindre(theta, course_xy, cz, args.pivot, args.pas)
        perte = 100.0 * (1 - v / v0) if v0 else 0.0
        print(f"  {theta:5.0f}° {r:6.0f} {h:7.0f} "
              f"{v/1e6:8.2f} L {perte:6.1f}% {plongee(plateau/2, theta):15.0f} mm")

    r, h, v = meilleur_cylindre(args.inclinaison, course_xy, cz,
                                args.pivot, args.pas)
    print(f"\n  A {args.inclinaison:.0f}° : cylindre Ø{2*r:.0f} x {h:.0f} mm, "
          f"{v/1e6:.2f} L")
    print(f"  Course Z consommee par la bascule seule : "
          f"{r*np.sin(np.radians(args.inclinaison)):.0f} mm")
    print(f"  Vide a prevoir sous le plateau : "
          f"{plongee(plateau/2, args.inclinaison):.0f} mm")
    return 0


if __name__ == "__main__":
    sys.exit(main())

