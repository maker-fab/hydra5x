#!/usr/bin/env python3
"""Compare les trois familles d'architecture sur des criteres chiffres.

- **plateau** : le plateau bascule, la piece avec (D23, D24)
- **portique** : le portique CoreXY entier bascule, la piece ne bouge pas (D28)
- **platine** : une petite platine incline la tete seule (D27)

Ce qui NE differencie pas les trois, et qu'il ne faut pas compter deux fois :

- **la collision buse-piece**, qui ne depend que de la pose relative. Verifie
  sur G-code : les sorties berceau et trois-verins rendent le meme verdict.
- **le tranchage**, identique : `stitch_chunks.py` ne change que ses
  commandes machine.
- **le firmware**, a ecrire dans les trois cas.

Ce qui les differencie vraiment se ramene a une seule question : **quelle
masse, et sur quelle envergure, faut-il incliner ?** Tout le reste en
decoule -- la course des vis, la hauteur du bati, le temps de bascule, et
la capacite a passer un jour au non-planaire continu.
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import cinematique_3points as c3  # noqa: E402
import volume_utile as vu  # noqa: E402


class Famille:
    """Une architecture, ramenee a ce qui la distingue."""

    def __init__(self, nom, portee, masse, vitesse_verin, piece_bouge,
                 commentaire):
        self.nom = nom
        self.portee = portee            # mm entre appuis extremes
        self.masse = masse              # kg bascules
        self.vitesse = vitesse_verin    # mm/s admissible
        self.piece_bouge = piece_bouge
        self.commentaire = commentaire

    def course(self, theta):
        """Course differentielle, mm. Portee x tangente."""
        return self.portee * np.tan(np.radians(theta))

    def duree(self, theta):
        """Temps d'une reorientation, s."""
        return self.course(theta) / self.vitesse

    def cadre(self, cible, theta, tete=(70.0, 25.0)):
        """Cadre X/Y/Z necessaire pour la piece visee, mm."""
        x, y, h = cible
        if self.piece_bouge:
            return vu.courses_requises("carre", max(x, y) / 2.0, h, theta)
        # piece fixe : seul l'organe incline mord sur l'enveloppe
        perte = 2 * (vu.debord_tete(tete[0], tete[1], theta)
                     - vu.debord_tete(tete[0], tete[1], 0.0))
        return x + perte, y + perte, h


FAMILLES = [
    Famille("plateau", 260.0, 6.5, 15.0, True,
            "plateau 400 sur appuis a R=150 ; plan de depot horizontal"),
    Famille("portique (appuis milieux)", 300.0, 7.0, 15.0, False,
            "moteurs CoreXY embarques ; docks solidaires, donc indifferents"),
    Famille("portique (4 coins)", 566.0, 7.0, 15.0, False,
            "portee par la diagonale : le pire cas d'implantation"),
    Famille("platine de tete", 87.0, 1.5, 40.0, False,
            "faible masse et faible course ; compensation de pointe a ecrire"),
]


def tableau(cible, theta, continu_pas):
    print(f"=== piece visee {cible[0]:.0f} x {cible[1]:.0f} x {cible[2]:.0f} mm, "
          f"inclinaison {theta:.0f}° ===\n")
    print(f"  {'famille':<26s} {'course':>8s} {'vis':>7s} {'cadre X/Y':>10s} "
          f"{'cadre Z':>8s} {'bascule':>9s} {'masse':>7s}")
    for f in FAMILLES:
        c = f.course(theta)
        cx, cy, cz = f.cadre(cible, theta)
        print(f"  {f.nom:<26s} {c:7.0f}  {cible[2]+c:6.0f} {max(cx,cy):9.0f} "
              f"{cz:8.0f} {f.duree(theta):8.1f} s {f.masse:6.1f} kg")

    print(f"\n  « vis » = course d'un verin : hauteur d'impression + differentiel.")
    print(f"  « bascule » = duree d'UNE reorientation.\n")

    print(f"  En INDEXE, la bascule a lieu entre deux blocs. Pour "
          f"{continu_pas} blocs :\n")
    print(f"  {'famille':<26s} {'total bascule':>14s}   part d'une impression de 6 h")
    for f in FAMILLES:
        t = f.duree(theta) * continu_pas
        print(f"  {f.nom:<26s} {t/60:10.1f} min   {100*t/(6*3600):5.2f} %")
    print("\n  -> en indexe, la duree de bascule ne departage rien.\n")

    print("  En CONTINU (non-planaire, D17), la bascule suit le cordon.")
    print("  L'inertie devient la contrainte, et elle croit en masse x portee^2 :\n")
    ref = None
    print(f"  {'famille':<26s} {'inertie relative':>17s}")
    for f in FAMILLES:
        i = f.masse * (f.portee / 1000.0) ** 2
        ref = i if ref is None else ref
        print(f"  {f.nom:<26s} {i/FAMILLES[-1].masse/(FAMILLES[-1].portee/1000.0)**2:14.0f} x")
    print("\n  -> la platine de tete est le seul organe qu'on peut esperer")
    print("     piloter en continu. Les autres sont des mecanismes d'indexation.")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cible", type=float, nargs=3, default=(200.0, 200.0, 200.0),
                    metavar=("X", "Y", "Z"))
    ap.add_argument("--inclinaison", type=float, default=35.0)
    ap.add_argument("--blocs", type=int, default=12,
                    help="nombre de reorientations dans une impression")
    args = ap.parse_args()
    tableau(args.cible, args.inclinaison, args.blocs)
    print("\n  Commentaires :")
    for f in FAMILLES:
        print(f"    {f.nom:<26s} {f.commentaire}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
