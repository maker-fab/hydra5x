#!/usr/bin/env python3
"""De combien une lame flexible borne-t-elle l'angle ?

Une articulation flexible supprime le jeu -- pas de contact glissant, donc
rien a rattraper. C'est exactement ce que demandent les 0,1° admissibles a
la platine (0,12 mm a la pointe). Elle le paie en course angulaire.

**La borne vient de la deformation de la matiere, pas de la geometrie.**
Une section flechie sur une longueur L jusqu'a un angle theta prend un
rayon de courbure `R = L / theta`. La fibre la plus tendue subit alors

    epsilon = c / R = c . theta / L

ou `c` est la demi-epaisseur (lame) ou le rayon (barreau). D'ou

    theta_max = epsilon_adm . L / c

Tout est dans le rapport **longueur sur epaisseur**. Doubler la longueur
double l'angle ; c'est le seul levier, et il se heurte au flambage.

**Deux familles, et elles ne se valent pas ici :**

- **lame** : flechit dans UN plan. Un pivot a lames croisees donne un axe
  propre et raide, mais un seul axe.
- **barreau** ou col mince : flechit dans TOUTES les directions, donc les
  deux degres qu'il nous faut -- mais `c` est le rayon complet, pas une
  demi-epaisseur, et la section resiste a la flexion dans les deux sens a
  la fois. C'est la famille exigee par une platine inclinable en azimut
  quelconque, et c'est la plus defavorable.

**Le contre-critere, sans lequel le chiffre ne veut rien dire** : le pivot
central porte l'effort de depot et le verrouillage d'outil. Un col assez
mince pour flechir de 35° flambe sous une charge axiale modeste. Les deux
calculs sont donc rendus ensemble.

Deformations admissibles retenues : en fatigue illimitee, pas a la
rupture. Un pivot d'imprimante voit des millions de cycles.
"""
import argparse
import sys

import numpy as np

# (module d'Young GPa, deformation admissible en fatigue, nom long)
MATERIAUX = {
    "acier ressort": (200.0, 0.0030, "1.4310 / 301, ecroui"),
    "beryllium-cuivre": (128.0, 0.0040, "C17200, revenu"),
    "titane Gr5": (114.0, 0.0060, "TA6V"),
    "polypropylene": (1.5, 0.0500, "charniere vivante -- flue sous charge"),
}


def angle_max(longueur, demi_epaisseur, epsilon):
    """Angle de flexion admissible, degres."""
    return float(np.degrees(epsilon * longueur / demi_epaisseur))


def longueur_requise(angle_deg, demi_epaisseur, epsilon):
    """Longueur libre necessaire pour atteindre cet angle, mm."""
    return float(np.radians(angle_deg) * demi_epaisseur / epsilon)


def flambage_barreau(diametre, longueur, module_gpa, k=0.5):
    """Charge critique d'Euler pour un col cylindrique, N.

    `k = 0.5` : encastre aux deux bouts, ce qu'est un col usine dans la
    masse. C'est le cas le plus favorable ; toute liberte de rotation aux
    extremites le degrade.
    """
    i = np.pi * diametre ** 4 / 64.0
    return float(np.pi ** 2 * module_gpa * 1e3 * i / (k * longueur) ** 2)


def raideur_angulaire(diametre, longueur, module_gpa):
    """Couple necessaire pour flechir d'un degre, N.mm/deg.

    C'est ce que les actionneurs devront fournir EN PLUS du reste, a
    chaque instant : un pivot flexible rappelle toujours vers sa position
    neutre.
    """
    i = np.pi * diametre ** 4 / 64.0
    return float(module_gpa * 1e3 * i / longueur * np.radians(1.0))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vise", type=float, default=35.0,
                    help="inclinaison visee, degres")
    ap.add_argument("--charge", type=float, default=50.0,
                    help="charge axiale a tenir, N")
    ap.add_argument("--securite", type=float, default=3.0,
                    help="coefficient de securite au flambage")
    args = ap.parse_args()

    print(f"=== col cylindrique, deux degres de liberte, vise {args.vise:.0f}° ===")
    print(f"\n  {'diametre':>9s} {'longueur':>9s}" +
          "".join(f"{n:>17s}" for n in MATERIAUX))
    print(f"  {'':>9s} {'':>9s}" +
          "".join(f"{'angle  flambage':>17s}" for _ in MATERIAUX))
    for d in (1.0, 1.5, 2.0, 3.0):
        for l in (20.0, 40.0):
            ligne = f"  {d:8.1f} {l:8.1f}"
            for nom, (e_gpa, eps, _) in MATERIAUX.items():
                a = angle_max(l, d / 2.0, eps)
                f = flambage_barreau(d, l, e_gpa)
                ligne += f"{a:9.1f}°{f:7.0f}N"
            print(ligne)

    print(f"\n  Pour atteindre {args.vise:.0f}°, longueur libre necessaire :\n")
    print(f"  {'materiau':<18s} {'d=1 mm':>9s} {'d=2 mm':>9s} {'d=3 mm':>9s}")
    for nom, (e_gpa, eps, _) in MATERIAUX.items():
        ligne = f"  {nom:<18s}"
        for d in (1.0, 2.0, 3.0):
            ligne += f"{longueur_requise(args.vise, d/2.0, eps):8.0f} mm"
        print(ligne)

    print(f"\n  Et ce que ces cols tiennent vraiment "
          f"(charge visee {args.charge:.0f} N, securite {args.securite:.0f}) :\n")
    print(f"  {'materiau':<18s} {'d':>4s} {'L':>6s} {'angle':>7s} "
          f"{'flambage':>10s} {'verdict':>12s} {'couple/deg':>12s}")
    besoin = args.charge * args.securite
    for nom, (e_gpa, eps, _) in MATERIAUX.items():
        for d in (2.0, 3.0):
            l = longueur_requise(args.vise, d / 2.0, eps)
            f = flambage_barreau(d, l, e_gpa)
            verdict = "tient" if f >= besoin else "FLAMBE"
            print(f"  {nom:<18s} {d:3.0f} {l:5.0f} {args.vise:6.0f}° "
                  f"{f:9.0f}N {verdict:>12s} "
                  f"{raideur_angulaire(d, l, e_gpa):9.1f} N.mm")
    print(f"\n  Il faut {besoin:.0f} N de charge critique pour {args.charge:.0f} N "
          f"de charge reelle.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

