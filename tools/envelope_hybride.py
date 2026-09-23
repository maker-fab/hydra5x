#!/usr/bin/env python3
"""Enveloppe angulaire quand table ET tete s'inclinent, avec plafond.

Tout le depot raisonnait jusqu'ici en « table ou tete ». C'est un faux
choix : l'inclinaison demandee se REPARTIT, et les deux contraintes sont
de nature differente, donc independantes.

    theta_table + theta_tete >= theta_demande

**Table.** Bornee par la garde plateau-buse. Modele de Cortex :
`garde = z / sin(theta)`, refus sous `G` mm. D'ou

    theta_t_max(z) = arcsin(min(1, z / G))

Elle depend de `z`, hauteur du point le plus bas du chunk au-dessus du
plateau, et elle vaut **zero a z = 0** : une piece au contact du plateau
interdit tout basculement.

**Tete.** Bornee par sa propre geometrie, pas par la piece. Avec le modele
de buse deja utilise pour les collisions -- le corps monte de `r/tan(alpha)`
a la distance `r` -- le flanc du cone devient parallele a la surface quand
l'axe s'incline de `alpha`. D'ou

    theta_h_max = alpha

Constante, independante de `z`. C'est la propriete qui rend le cumul
interessant : **la tete couvre exactement la ou la table est impuissante.**

Reserve importante, heritee de envelope.md : le raisonnement physique
derriere `z/sin(theta)` n'est pas reconstituable depuis le code de Cortex
et n'a jamais ete confronte a une distance geometrique reelle. Tout ce
fichier en herite. A verifier sur le materiel avant de s'y fier.
"""
import argparse
import sys

import numpy as np

GARDE_DEFAUT = 12.0      # mm, minAcceptableBedToNozzleClearance de Cortex
ALPHA_DEFAUT = 45.0      # deg, demi-angle du cone de buse
MARGE_DEFAUT = 0.80      # on n'exploite que 80 % de chaque limite


def limite_table(z, garde=GARDE_DEFAUT):
    """Inclinaison max du plateau pour un point le plus bas a la hauteur z."""
    return float(np.degrees(np.arcsin(np.clip(z / garde, 0.0, 1.0))))


def limite_tete(alpha=ALPHA_DEFAUT, bride=None):
    """Inclinaison max de la tete.

    `bride` permet de brider en dessous du cone : bloc chauffant, ventilation,
    passage du filament. C'est la valeur a renseigner depuis la CAO reelle.
    """
    return float(min(alpha, bride) if bride is not None else alpha)


def enveloppe(z, garde=GARDE_DEFAUT, alpha=ALPHA_DEFAUT, bride=None,
              marge=MARGE_DEFAUT):
    """Inclinaison totale atteignable, et sa repartition."""
    t = limite_table(z, garde) * marge
    h = limite_tete(alpha, bride) * marge
    return t + h, t, h


def repartir(theta_demande, z, garde=GARDE_DEFAUT, alpha=ALPHA_DEFAUT,
             bride=None, marge=MARGE_DEFAUT):
    """Repartition qui satisfait la demande, ou None si hors d'atteinte.

    On charge la TETE en priorite : sa limite ne depend pas de `z`, alors
    que celle de la table s'effondre quand la piece descend. Garder de la
    marge sur la table est donc ce qui a de la valeur.
    """
    total, t_max, h_max = enveloppe(z, garde, alpha, bride, marge)
    if theta_demande > total:
        return None
    h = min(h_max, theta_demande)
    return (theta_demande - h, h)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--garde", type=float, default=GARDE_DEFAUT)
    ap.add_argument("--alpha", type=float, default=ALPHA_DEFAUT)
    ap.add_argument("--bride", type=float, default=None,
                    help="bridage de la tete en deg (bloc chauffant, filament)")
    ap.add_argument("--marge", type=float, default=MARGE_DEFAUT)
    ap.add_argument("--vise", type=float, default=45.0,
                    help="inclinaison utile visee, en deg")
    args = ap.parse_args()

    h_max = limite_tete(args.alpha, args.bride)
    print(f"Garde plateau-buse {args.garde:.0f} mm | cone de buse "
          f"{args.alpha:.0f} deg" + (f" bride a {args.bride:.0f} deg" if args.bride else ""))
    print(f"Marge de securite {args.marge*100:.0f} % sur chaque axe "
          f"-> table utile x{args.marge:.2f}, tete {h_max*args.marge:.1f} deg\n")

    print(f"  {'z (mm)':>7s} {'table seule':>12s} {'+ tete':>9s} {'total':>8s}"
          f"  {'reparti pour ' + str(int(args.vise)) + ' deg':>26s}")
    for z in (0.0, 0.5, 1.0, 2.0, 4.0, 6.0, 8.5, 12.0):
        brut = limite_table(z, args.garde)
        total, t, h = enveloppe(z, args.garde, args.alpha, args.bride, args.marge)
        r = repartir(args.vise, z, args.garde, args.alpha, args.bride, args.marge)
        txt = (f"table {r[0]:5.1f} + tete {r[1]:5.1f}" if r else "hors d'atteinte")
        print(f"  {z:7.1f} {brut:11.1f}° {h:8.1f}° {total:7.1f}°  {txt:>26s}")

    z_seuil_table = args.garde * np.sin(np.radians(args.vise / args.marge))
    reste = max(0.0, args.vise - h_max * args.marge)
    z_seuil_hybride = (args.garde * np.sin(np.radians(reste / args.marge))
                       if reste > 0 else 0.0)
    print(f"\n  hauteur minimale pour atteindre {args.vise:.0f}° :")
    print(f"    table seule   : z >= {z_seuil_table:5.2f} mm")
    print(f"    table + tete  : z >= {z_seuil_hybride:5.2f} mm"
          + ("   (aucune contrainte de hauteur)" if z_seuil_hybride <= 0 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
