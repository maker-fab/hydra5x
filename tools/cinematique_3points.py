#!/usr/bin/env python3
"""Inclinaison d'un plateau porte par trois verins verticaux : validation.

But de ce fichier : **verifier que le plateau atteint bien l'angle vise,
dans tous les azimuts**, et donner les trois hauteurs a commander. Rien de
plus. Le plateau est traite comme ce qu'il est -- un plan rigide -- et les
trois verins comme trois hauteurs imposees.

    h_i = z + R . cos(azimut_i - phi) . tan(theta)

**tan, pas sin** : les verins sont verticaux, donc les points d'appui
gardent leur distance HORIZONTALE au centre. La hauteur d'un plan de pente
theta a la distance d vaut d.tan(theta). C'est toute la cinematique tant
qu'on valide l'inclinaison -- le plan qui passe par trois hauteurs est
unique, et son inclinaison se lit directement.

Convention : `theta` inclinaison, `phi` azimut de la plus grande pente, `z`
hauteur du centre. Verins a 90°, 210°, 330° sur un cercle de rayon `R`.

**Note mecanique, pour plus tard et pas pour maintenant** : trois rotules
rigides sur trois verticales se bloqueraient, les distances entre points
d'un plateau rigide etant fixes. Il faudra liberer un degre lateral par
jambe. Ca ne change **pas** les angles calbecules ici, seulement la
conception des appuis.
"""
import argparse
import sys

import numpy as np

AZIMUTS_VERINS = (90.0, 210.0, 330.0)


def hauteurs(theta_deg, phi_deg, z, rayon):
    """Hauteur de chaque verin pour une pose donnee, mm."""
    a = np.radians(np.array(AZIMUTS_VERINS))
    return (z + rayon * np.cos(a - np.radians(phi_deg))
            * np.tan(np.radians(theta_deg)))


def hauteurs_normale(normale, z, rayon):
    """Hauteurs des verins pour un plateau de normale donnee.

    Formulation sans convention d'azimut, donc sans piege de signe : un
    plan de normale `m` passant par (0, 0, z) a pour hauteur, au point
    horizontal `p`,

        h(p) = z - (m_x.p_x + m_y.p_y) / m_z
    """
    m = np.asarray(normale, dtype=float)
    m = m / np.linalg.norm(m) * np.sign(m[2])
    a = np.radians(np.array(AZIMUTS_VERINS))
    px, py = rayon * np.cos(a), rayon * np.sin(a)
    return z - (m[0] * px + m[1] * py) / m[2]


def normale_plateau(theta_deg, phi_deg):
    """Normale que le PLATEAU doit prendre pour imprimer ce chunk.

    Cortex designe une direction de tranchage par `spherical_to_normal` :
    n = (sin.cos, sin.sin, cos) dans le repere de la piece. Imprimer ce
    chunk demande que **n devienne verticale** une fois la piece inclinee
    avec le plateau. La rotation qui amene n sur +Z tourne de theta autour
    de l'axe n x Z ; la normale du plateau est l'image de +Z par cette
    meme rotation.

    Verifie ici meme : on applique la rotation a n et on controle qu'elle
    tombe bien sur +Z. Si la convention amont change, ce controle le dit
    au lieu de produire des angles faux.
    """
    t, p = np.radians(theta_deg), np.radians(phi_deg)
    n = np.array([np.sin(t) * np.cos(p), np.sin(t) * np.sin(p), np.cos(t)])
    axe = np.array([np.sin(p), -np.cos(p), 0.0])
    if np.linalg.norm(axe) < 1e-12:
        axe = np.array([1.0, 0.0, 0.0])
    c, s = np.cos(t), np.sin(t)
    k = np.array([[0.0, -axe[2], axe[1]],
                  [axe[2], 0.0, -axe[0]],
                  [-axe[1], axe[0], 0.0]])
    m = np.eye(3) + s * k + (1 - c) * (k @ k)
    ecart = float(np.linalg.norm(m @ n - np.array([0.0, 0.0, 1.0])))
    if ecart > 1e-9:
        raise ValueError(f"la rotation ne ramene pas la normale sur +Z "
                         f"(ecart {ecart:.3e}) : convention d'angles a revoir")
    return m @ np.array([0.0, 0.0, 1.0])


def pose(h, rayon):
    """Trois hauteurs -> (theta, phi, z). Reciproque exacte de `hauteurs`."""
    a = np.radians(np.array(AZIMUTS_VERINS))
    h = np.asarray(h, dtype=float)
    z = float(h.mean())
    # h - z = R.sin(theta).cos(a - phi) = A.cos(a) + B.sin(a)
    m = np.column_stack([np.cos(a), np.sin(a)])
    coef, *_ = np.linalg.lstsq(m, h - z, rcond=None)
    amp = float(np.hypot(*coef)) / rayon
    theta = float(np.degrees(np.arctan(amp)))
    phi = float(np.degrees(np.arctan2(coef[1], coef[0]))) % 360.0
    return theta, phi, z


# max - min de cos(a - phi) sur trois azimuts a 120° : varie entre 1,5
# (azimut favorable, la pente passe entre deux verins) et racine de 3
# (azimut defavorable, elle passe par un verin). Le dimensionnement se fait
# sur le pire.
ETALEMENT_PIRE = np.sqrt(3.0)
ETALEMENT_MEILLEUR = 1.5


def course_necessaire(theta_deg, rayon, etalement=ETALEMENT_PIRE):
    """Ecart de hauteur entre le verin le plus haut et le plus bas, mm.

    C'est cet ecart, et lui seul, que la course des vis doit offrir en plus
    de la course d'impression.
    """
    return etalement * rayon * np.tan(np.radians(theta_deg))


def angle_max(rayon, course_differentielle, etalement=ETALEMENT_PIRE):
    """Inclinaison garantie dans TOUT azimut, degres."""
    return float(np.degrees(np.arctan2(course_differentielle,
                                       etalement * rayon)))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rayon", type=float, default=150.0,
                    help="rayon du cercle des trois verins, mm")
    ap.add_argument("--course-diff", type=float, default=182.0,
                    help="course differentielle disponible, mm")
    ap.add_argument("--vise", type=float, default=35.0,
                    help="inclinaison visee, degres")
    ap.add_argument("--z", type=float, default=200.0,
                    help="hauteur du centre du plateau pour l'exemple, mm")
    ap.add_argument("--marge", type=float, default=0.80)
    args = ap.parse_args()

    amax = angle_max(args.rayon, args.course_diff)
    besoin = course_necessaire(args.vise, args.rayon)

    print(f"=== trois verins a R={args.rayon:.0f} mm, "
          f"course differentielle {args.course_diff:.0f} mm ===\n")
    print(f"  inclinaison atteignable   {amax:6.2f}°")
    print(f"  dont utile (marge {args.marge*100:.0f} %)  {amax*args.marge:6.2f}°")
    print(f"  inclinaison visee         {args.vise:6.2f}°  "
          f"-> {'OK' if args.vise <= amax * args.marge else 'INSUFFISANT'}")
    print(f"  course necessaire pour {args.vise:.0f}° : {besoin:.1f} mm "
          f"sur {args.course_diff:.0f} disponibles")

    print(f"\n  hauteurs des verins a {args.vise:.0f}°, "
          f"centre a z={args.z:.0f} mm :\n")
    print(f"  {'azimut':>7s} " + " ".join(f"{'V%d' % (i+1):>9s}"
                                          for i in range(3))
          + f" {'ecart':>8s} {'controle':>10s}")
    pire = 0.0
    for phi in np.arange(0.0, 360.0, 30.0):
        h = hauteurs(args.vise, phi, args.z, args.rayon)
        th, ph, z = pose(h, args.rayon)
        ecart = float(h.max() - h.min())
        pire = max(pire, ecart)
        ok = abs(th - args.vise) < 1e-6 and abs(z - args.z) < 1e-6
        print(f"  {phi:6.0f}° " + " ".join(f"{v:9.2f}" for v in h)
              + f" {ecart:8.2f} {'exact' if ok else 'ECART':>10s}")
    print(f"\n  ecart maximal sur tous les azimuts : {pire:.2f} mm")
    print(f"  -> il DEPEND de l'azimut : {ETALEMENT_MEILLEUR:.3f} x R x tan(theta) "
          f"au mieux, {ETALEMENT_PIRE:.3f} au pire.")
    print(f"     Ecart de {100*(ETALEMENT_PIRE/ETALEMENT_MEILLEUR - 1):.0f} % "
          f"entre les deux : dimensionner sur le pire.")

    print(f"\n  course des vis = course d'impression + {besoin:.0f} mm")
    pour_marge = course_necessaire(args.vise / args.marge, args.rayon)
    print(f"  avec la marge de {args.marge*100:.0f} %, il faut pouvoir "
          f"atteindre {args.vise/args.marge:.1f}° : {pour_marge:.0f} mm")
    return 0


if __name__ == "__main__":
    sys.exit(main())
