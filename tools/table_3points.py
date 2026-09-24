#!/usr/bin/env python3
"""Inclinaison d'une table a trois points, azimut par azimut.

Trois actionneurs verticaux sous un plateau lui donnent `Z` plus le
basculement dans n'importe quel azimut. Mais **le debattement n'est pas le
meme dans tous les azimuts** : il depend de l'etalement des trois appuis
dans la direction ou l'on bascule.

    z_i = g . (p_i . u)        plan incline de gradient g, direction u
    ecart = g . (max_i s_i - min_i s_i)    avec s_i = p_i . u

L'actionneur le plus haut et le plus bas doivent tenir dans la course
differentielle disponible, donc

    theta(u) = arctan( course_differentielle / portee(u) )

ou `portee(u)` est l'etendue des trois appuis projetee sur `u`. La limite
de la machine est le **minimum sur tous les azimuts** -- c'est-a-dire
l'azimut de plus grande portee.

**Ce que ca corrige.** Une premiere version prenait un bras de levier de
1,5 x rayon pour un triangle equilateral. C'est l'azimut FAVORABLE. Le
defavorable vaut 1,732 x rayon (racine de 3), soit 15 % de portee en plus
et autant d'inclinaison en moins. Les limites annoncees ici sont les pires
cas.

**Consequence pour un plateau carre** : les trois appuis ne peuvent pas
epouser un carre. Le triangle reste triangulaire sous un plateau carre,
donc l'anisotropie est encore plus marquee -- et l'azimut faible ne tombe
pas forcement la ou la piece en a besoin.
"""
import argparse
import sys

import numpy as np


# Dispositions d'appuis, coordonnees relatives au CENTRE du plateau, en mm.
# `--echelle` les met a l'echelle d'un plateau donne.
DISPOSITIONS = {
    # triangle equilateral inscrit, rayon 1 : le plus isotrope possible
    "equilateral": [(0.0, 1.0), (-0.866, -0.5), (0.866, -0.5)],
    # Voron Trident : deux appuis devant, un au fond au milieu.
    # Normalise sur un plateau de cote 2 (soit rayon 1).
    "trident": [(-1.333, -0.88), (0.0, 1.32), (1.333, -0.88)],
    # trois appuis sur trois cotes d'un carre, un par cote
    "carre-3-cotes": [(-1.0, -1.0), (1.0, -1.0), (0.0, 1.0)],
}


def portee(points, azimut_deg):
    """Etendue des appuis projetee sur l'azimut, mm."""
    u = np.array([np.cos(np.radians(azimut_deg)),
                  np.sin(np.radians(azimut_deg))])
    s = np.array(points) @ u
    return float(s.max() - s.min())


def inclinaison(points, course_differentielle, azimut_deg):
    """Inclinaison atteignable dans cet azimut, degres."""
    p = portee(points, azimut_deg)
    if p <= 0:
        return 90.0
    return float(np.degrees(np.arctan2(course_differentielle, p)))


def balayage(points, course_differentielle, pas=5.0):
    """(azimut, inclinaison) sur un demi-tour ; le reste est symetrique."""
    azimuts = np.arange(0.0, 180.0, pas)
    return azimuts, np.array([inclinaison(points, course_differentielle, a)
                              for a in azimuts])


def pire_cas(points, course_differentielle, pas=1.0):
    """Inclinaison garantie et azimut ou elle se joue."""
    a, incl = balayage(points, course_differentielle, pas)
    i = int(incl.argmin())
    return float(incl[i]), float(a[i])


def mise_a_echelle(points, demi_cote):
    return [(x * demi_cote, y * demi_cote) for x, y in points]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--disposition", choices=sorted(DISPOSITIONS),
                    default="equilateral")
    ap.add_argument("--plateau", type=float, default=200.0,
                    help="cote du plateau carre (ou diametre si rond), mm")
    ap.add_argument("--course", type=float, nargs="+", default=[100.0, 150.0, 200.0],
                    help="courses differentielles a comparer, mm")
    ap.add_argument("--marge", type=float, default=0.80)
    args = ap.parse_args()

    pts = mise_a_echelle(DISPOSITIONS[args.disposition], args.plateau / 2)
    print(f"=== appuis « {args.disposition} », plateau {args.plateau:.0f} mm ===")
    for x, y in pts:
        print(f"    appui  X{x:+8.1f}  Y{y:+8.1f}")

    print(f"\n  portee selon l'azimut :")
    for a in (0, 30, 45, 60, 90, 120, 150):
        print(f"    {a:3.0f}°  {portee(pts, a):7.1f} mm")

    print(f"\n  {'course diff.':>13s} {'pire':>8s} {'azimut':>8s} "
          f"{'meilleur':>9s} {'utile':>8s}")
    for c in args.course:
        pire, az = pire_cas(pts, c)
        _, incl = balayage(pts, c, 1.0)
        print(f"  {c:12.0f} mm {pire:7.1f}° {az:7.0f}° "
              f"{incl.max():8.1f}° {pire*args.marge:7.1f}°")
    print(f"\n  (« utile » = pire cas x {args.marge*100:.0f} % de marge)")
    return 0


if __name__ == "__main__":
    sys.exit(main())


def inclinaison_cardan(alpha_max, beta_max, azimuts, pas=0.5):
    """Inclinaison atteignable par azimut avec un plateau a DEUX axes.

    Un cardan compose deux rotations orthogonales. La normale du plateau
    devient (cos a . sin b, -sin a, cos a . cos b), donc

        cos(theta) = cos(alpha) . cos(beta)

    L'inclinaison totale depasse chacune des deux : 45° sur chaque axe
    donnent **60°** de bascule reelle, dans l'azimut diagonal.

    L'anisotropie est **inverse de celle d'une table a trois points** : le
    cardan est fort en diagonale et faible sur ses axes, le triangle
    equilateral l'inverse. Retenu : un cardan sous un plateau CARRE fait
    coincider son azimut fort avec la diagonale du plateau, c'est-a-dire
    avec la direction ou la piece deborde le plus. Les deux defauts se
    cumulent la aussi.

    Retourne {azimut demande : inclinaison max atteignable}.
    """
    cibles = np.asarray(azimuts, dtype=float)
    table = {float(c): 0.0 for c in cibles}
    for a in np.arange(-alpha_max, alpha_max + pas, pas):
        for b in np.arange(0.0, beta_max + pas, pas):
            ra, rb = np.radians(a), np.radians(b)
            theta = np.degrees(np.arccos(np.clip(np.cos(ra) * np.cos(rb),
                                                 -1.0, 1.0)))
            phi = np.degrees(np.arctan2(np.sin(ra), np.cos(ra) * np.sin(rb))) % 180
            # ecart angulaire modulo 180, l'azimut oppose est le meme
            ecart = np.abs(((cibles - phi + 90.0) % 180.0) - 90.0)
            cle = float(cibles[int(ecart.argmin())])
            if theta > table[cle]:
                table[cle] = float(theta)
    return table
