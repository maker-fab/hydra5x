#!/usr/bin/env python3
"""Le cordon flue-t-il quand la couche est inclinee ? Modele reduit.

Trois architectures attendent cette reponse (D23, D27, D28). Faute de
machine, on peut au moins **comparer les forces en presence** au lieu de
les invoquer.

**L'erreur que ce fichier corrige.** Les notes precedentes disaient « a 30°
la gravite tire le cordon avec 50 % de son poids ». C'est exact et sans
portee : une composante de force ne dit rien tant qu'on ne la compare pas
a ce qui lui resiste. Ici resistent la **viscosite** du polymere fondu et
la **tension superficielle**, et les deux deviennent ecrasantes quand
l'epaisseur tombe a 0,2 mm.

**Deux nombres sans dimension suffisent a trancher le regime.**

1. Nombre de Bond -- gravite contre tension superficielle :

       Bo = rho . g . h^2 . sin(theta) / sigma

   Bo << 1 : la tension superficielle tient le cordon en place.

2. Ecoulement visqueux d'un film mince sur une pente (Nusselt), pendant
   le temps ou le polymere est encore fondu :

       u = rho . g . sin(theta) . h^2 / (3 . mu)
       derive = u . t_fige

   A comparer a la hauteur de couche : si la derive est mille fois plus
   petite, la question ne se pose pas.

Les deux varient en **h^2**. C'est toute l'affaire : le meme raisonnement
applique a une coulee de beton donnerait l'inverse.

**Ce que ce modele ne couvre pas**, et qu'il ne faut pas lui faire dire :

- les **ponts et surplombs non soutenus** -- la, il n'y a pas de substrat
  et le cordon pend ; mais c'est precisement ce que la 5 axes evite ;
- le **cisaillement de la buse** sur le cordon, qui domine largement la
  gravite et n'est pas directionnel ;
- le **decollement de la piece**, qui ne concerne que le plateau basculant ;
- la **rheologie non newtonienne** : un polymere fondu est rheofluidifiant,
  donc a faible cisaillement sa viscosite est la plus HAUTE. Prendre une
  viscosite newtonienne a bas cisaillement est donc conservateur dans le
  bon sens... mais on balaye quand meme quatre decades.
"""
import argparse
import sys

import numpy as np

G = 9.81

# Ordres de grandeur de la litterature sur les fondus techniques.
# `mu` est la viscosite a bas cisaillement, la plus defavorable au repos.
MATERIAUX = {
    #            rho     mu       sigma   T_depot  T_fige
    "PLA":      (1200.0,  500.0,  0.030,  205.0,   100.0),
    "ABS":      (1040.0, 1000.0,  0.033,  245.0,   105.0),
    "PETG":     (1270.0,  800.0,  0.035,  240.0,    85.0),
    "TPU":      (1200.0, 2000.0,  0.030,  225.0,    60.0),
}


def bond(rho, sigma, h, theta_deg):
    """Gravite / tension superficielle. Sous 1, la capillarite tient."""
    return rho * G * h ** 2 * np.sin(np.radians(theta_deg)) / sigma


def derive_visqueuse(rho, mu, h, theta_deg, t_fige):
    """Deplacement du cordon avant figeage, en metres."""
    u = rho * G * np.sin(np.radians(theta_deg)) * h ** 2 / (3.0 * mu)
    return u * t_fige


def verdict(bo, rapport):
    """Regime, a partir des deux indicateurs."""
    if bo < 0.1 and rapport < 0.01:
        return "aucun effet"
    if bo < 1.0 and rapport < 0.1:
        return "negligeable"
    if bo < 3.0 and rapport < 0.5:
        return "marginal"
    return "le cordon flue"


def balayage(mat, h, t_fige, angles):
    rho, mu, sigma, _, _ = MATERIAUX[mat]
    lignes = []
    for theta in angles:
        bo = bond(rho, sigma, h, theta)
        d = derive_visqueuse(rho, mu, h, theta, t_fige)
        lignes.append((theta, bo, d, d / h, verdict(bo, d / h)))
    return lignes


def sensibilite(mat, h, angle, t_fige):
    """Balaye viscosite et temps de figeage sur quatre decades.

    Un resultat qui ne tient que pour la valeur centrale ne tranche rien.
    Celui-ci doit survivre a l'incertitude sur les deux parametres les plus
    mal connus.
    """
    rho, _, sigma, _, _ = MATERIAUX[mat]
    mus = [1.0, 10.0, 100.0, 1000.0, 10000.0]
    temps = [0.1, 0.5, 1.0, 5.0, 20.0]
    table = []
    for mu in mus:
        ligne = []
        for t in temps:
            d = derive_visqueuse(rho, mu, h, angle, t)
            ligne.append(d / h)
        table.append((mu, ligne))
    return mus, temps, table


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--materiau", choices=sorted(MATERIAUX), default="PLA")
    ap.add_argument("--couche", type=float, default=0.2,
                    help="hauteur de couche, mm")
    ap.add_argument("--fige", type=float, default=1.0,
                    help="temps pendant lequel le cordon reste fondu, s")
    args = ap.parse_args()

    h = args.couche / 1000.0
    rho, mu, sigma, t_dep, t_fig = MATERIAUX[args.materiau]

    print(f"=== {args.materiau}, couche {args.couche:.2f} mm, "
          f"fondu pendant {args.fige:.1f} s ===")
    print(f"  rho {rho:.0f} kg/m3   mu {mu:.0f} Pa.s   sigma {sigma:.3f} N/m")
    print(f"  depose a {t_dep:.0f} °C, fige vers {t_fig:.0f} °C\n")

    print(f"  {'incl.':>6s} {'Bond':>9s} {'derive':>11s} "
          f"{'/ couche':>10s}   regime")
    for theta, bo, d, r, v in balayage(args.materiau, h, args.fige,
                                       (0, 15, 30, 45, 60, 75, 90)):
        print(f"  {theta:5.0f}° {bo:9.4f} {d*1e6:8.3f} um "
              f"{r:9.5f}   {v}")

    print(f"\n  Sensibilite a 45°, derive rapportee a la hauteur de couche :")
    mus, temps, table = sensibilite(args.materiau, h, 45.0, args.fige)
    print(f"  {'mu (Pa.s)':>10s}" + "".join(f"{t:>10.1f} s" for t in temps))
    for mu_, ligne in table:
        print(f"  {mu_:10.0f}" + "".join(f"{r:12.2e}" for r in ligne))
    print("\n  Un polymere fondu se situe entre 100 et 10 000 Pa.s ;")
    print("  1 Pa.s serait de l'eau tiede, il n'est la que comme borne absurde.")

    # hauteur de couche a laquelle le probleme apparaitrait vraiment
    cible = 1.0                       # Bond = 1
    h_crit = np.sqrt(cible * sigma / (rho * G * np.sin(np.radians(45.0))))
    print(f"\n  La capillarite cesse de dominer (Bond = 1) a une couche de "
          f"{h_crit*1000:.2f} mm.")
    print(f"  Soit {h_crit/h:.0f} fois la couche consideree ici.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
