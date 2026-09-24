#!/usr/bin/env python3
"""Modele CAO parametrique de la machine, en code.

**Un modele d'implantation, pas un jeu de pieces.** Il pose les volumes et
les interfaces -- bati, portique, platine, plateau -- pour repondre aux
questions qui se posent maintenant : est-ce que ca tient ensemble, est-ce
que la tete inclinee degage le bati, ou passent les courses. Le dessin de
detail vient apres, et une bonne part sera repris de Voron.

**Pourquoi en code et pas dans une interface.** Le bati suit des cotes qui
bougent encore. Un modele parametrique se regenere ; un modele dessine se
redessine. Generation One fait le meme pari, dans Fusion ; ici c'est
CadQuery, libre et versionnable, et le depot contient deja de quoi en
sortir des DXF de decoupe (`fabrication/`).

**La cinematique n'est pas redite ici.** `cad/machine.py` importe
`tools/cinematique_3points.py`, celui-la meme qui pilote le G-code. Les
hauteurs de verins dessinees sont donc, au flottant pres, celles que la
machine recevra -- il ne peut pas y avoir de derive entre le dessin et la
commande.

Environnement : `.venv-dxf` (cadquery 2.8, numpy >= 2). Pas trimesh, qui
exige numpy < 2 -- voir docs/install.md.

    .venv-dxf/bin/python cad/machine.py --step cad/hydra5x.step
"""
import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import cadquery as cq
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import cinematique_3points as c3  # noqa: E402


@dataclass
class Machine:
    """Toutes les cotes en un seul endroit. Rien n'est en dur ailleurs."""
    cote_bati: float = 400.0          # interieur du cadre, mm
    hauteur_bati: float = 520.0
    profile: float = 30.0             # profile alu carre
    plateau: float = 400.0
    ep_plateau: float = 8.0
    hauteur_plateau: float = 60.0     # dessus du plateau, bas de course
    rayon_verins: float = 50.0        # cercle des trois verins de platine
    course_verins: float = 70.0       # course differentielle disponible
    diam_platine: float = 130.0
    ep_platine: float = 10.0
    pivot_pointe: float = 80.0        # centre de platine -> pointe de buse
    diam_tete: float = 50.0           # dissipateur + ventilation annulaire
    inclinaison_max: float = 35.0

    @property
    def exterieur(self):
        return self.cote_bati + 2 * self.profile


def bati(m):
    """Douze profiles formant la cage. Origine au centre du plateau."""
    demi = m.cote_bati / 2 + m.profile / 2
    h = m.hauteur_bati
    piece = None
    for x, y in ((-demi, -demi), (demi, -demi), (demi, demi), (-demi, demi)):
        montant = (cq.Workplane("XY").center(x, y)
                   .box(m.profile, m.profile, h, centered=(True, True, False)))
        piece = montant if piece is None else piece.union(montant)
    for z in (m.profile / 2, h - m.profile / 2):
        for signe in (-1, 1):
            piece = piece.union(cq.Workplane("XY").workplane(offset=z)
                                .center(0, signe * demi)
                                .box(m.cote_bati, m.profile, m.profile))
            piece = piece.union(cq.Workplane("XY").workplane(offset=z)
                                .center(signe * demi, 0)
                                .box(m.profile, m.cote_bati, m.profile))
    return piece


def plateau(m):
    """Plaque chauffante. Fixe en orientation : elle ne descend qu'en Z."""
    return (cq.Workplane("XY").workplane(offset=m.hauteur_plateau)
            .box(m.plateau, m.plateau, m.ep_plateau,
                 centered=(True, True, False)))


def portique(m, z):
    """Poutre du CoreXY. Horizontale en permanence."""
    return (cq.Workplane("XY").workplane(offset=z)
            .box(m.cote_bati, m.profile * 2, m.profile,
                 centered=(True, True, False)))


def tete(m, theta=0.0, phi=0.0):
    """Platine, trois verins et hotend, inclines de (theta, phi).

    Le solide est construit droit puis bascule d'un bloc : c'est
    exactement ce que fait le mecanisme, et ca evite de composer des
    rotations a la main dans chaque sous-piece.
    """
    corps = (cq.Workplane("XY").circle(m.diam_platine / 2)
             .extrude(m.ep_platine))
    for a in np.radians(c3.AZIMUTS_VERINS):
        corps = corps.union(
            cq.Workplane("XY")
            .center(m.rayon_verins * np.cos(a), m.rayon_verins * np.sin(a))
            .circle(6.0).extrude(m.course_verins + 20.0))
    corps = corps.union(cq.Workplane("XY")
                        .circle(m.diam_tete / 2)
                        .extrude(-(m.pivot_pointe - 12.0)))
    corps = corps.union(cq.Workplane("XY")
                        .workplane(offset=-(m.pivot_pointe - 12.0))
                        .circle(8.0).extrude(-12.0))
    if theta:
        axe = (-np.sin(np.radians(phi)), np.cos(np.radians(phi)), 0.0)
        corps = corps.rotate((0, 0, 0), axe, theta)
    return corps


def assemblage(m, theta=0.0, phi=0.0, z_portique=None, xy_tete=(0.0, 0.0)):
    """Machine entiere dans une pose donnee."""
    if z_portique is None:
        z_portique = m.hauteur_bati - 120.0
    z_platine = z_portique - m.profile - 20.0
    a = cq.Assembly(name="HYDRA5X")
    a.add(bati(m), name="bati", color=cq.Color(0.25, 0.27, 0.30))
    a.add(plateau(m), name="plateau", color=cq.Color(0.85, 0.62, 0.25))
    a.add(portique(m, z_portique), name="portique",
          color=cq.Color(0.35, 0.38, 0.42))
    a.add(tete(m, theta, phi), name="tete", color=cq.Color(0.20, 0.55, 0.60),
          loc=cq.Location(cq.Vector(xy_tete[0], xy_tete[1], z_platine)))
    return a


def degagement(m, theta, phi, z_platine, xy_tete=(0.0, 0.0)):
    """Ce qui separe la tete inclinee du bati et du plateau, en mm.

    **C'est ce que le modele apporte que la formule ne donnait pas.**
    `debord_tete` reduit la tete a un coin ; ici on prend l'encombrement
    reel du solide incline, verins compris. Un debord negatif veut dire
    que ca touche.
    """
    solide = tete(m, theta, phi).val()
    b = solide.BoundingBox()
    demi_interieur = m.cote_bati / 2
    return {
        "debord_lateral": float(max(abs(b.xmin), abs(b.xmax),
                                    abs(b.ymin), abs(b.ymax))),
        "course_utile": float(m.cote_bati - 2 * max(
            abs(b.xmin), abs(b.xmax), abs(b.ymin), abs(b.ymax))),
        "pointe_z": float(b.zmin + z_platine),
        "hauteur_au_dessus_plateau": float(
            b.zmin + z_platine - (m.hauteur_plateau + m.ep_plateau)),
    }


def verins(m, theta, phi):
    """Hauteurs des trois verins, par la meme fonction que le G-code."""
    return c3.hauteurs(theta, phi, 0.0, m.rayon_verins)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--step", type=Path, default=Path("cad/hydra5x.step"))
    ap.add_argument("--inclinaison", type=float, default=None,
                    help="pose dessinee, degres (defaut : le maximum)")
    ap.add_argument("--azimut", type=float, default=0.0)
    args = ap.parse_args()

    m = Machine()
    theta = m.inclinaison_max if args.inclinaison is None else args.inclinaison

    print(f"=== HYDRA5X, modele d'implantation ===")
    print(f"  bati          {m.exterieur:.0f} x {m.exterieur:.0f} x "
          f"{m.hauteur_bati:.0f} mm hors tout")
    print(f"  plateau       {m.plateau:.0f} mm, fixe en orientation")
    print(f"  platine       Ø{m.diam_platine:.0f}, verins a R{m.rayon_verins:.0f}")
    print(f"  pivot-pointe  {m.pivot_pointe:.0f} mm")

    print(f"\n  verins a {theta:.0f}° (mm, autour de la pose a plat) :")
    h = verins(m, theta, args.azimut)
    print(f"    V1 {h[0]:+7.2f}   V2 {h[1]:+7.2f}   V3 {h[2]:+7.2f}"
          f"   ecart {h.max()-h.min():.2f} sur {m.course_verins:.0f}")
    if h.max() - h.min() > m.course_verins:
        raise SystemExit("la pose demandee depasse la course des verins")

    print(f"\n  Ce que la tete retire aux courses, azimut le plus defavorable.")
    print(f"  La course utile est ce qui reste quand la tete doit pouvoir")
    print(f"  atteindre les deux bords sans toucher le bati.\n")
    print(f"  {'incl.':>6s} {'demi-encombrement':>19s} {'course utile X/Y':>18s}")
    for t in (0.0, 15.0, 25.0, theta):
        pire = min((degagement(m, t, p, 300.0) for p in (0, 30, 45, 60, 90)),
                   key=lambda d: d["course_utile"])
        etat = "" if pire["course_utile"] > 0 else "   IMPOSSIBLE"
        print(f"  {t:5.0f}° {pire['debord_lateral']:18.1f} "
              f"{pire['course_utile']:17.1f}{etat}")

    print(f"\n  D'ou vient l'encombrement, a {theta:.0f}° :\n")
    print(f"  {'variante':<34s} {'demi-enc.':>10s} {'course utile':>14s}")
    essais = [
        ("reference", Machine()),
        ("platine Ø100 au lieu de 130", Machine(diam_platine=100.0)),
        ("verins a R40 au lieu de 50", Machine(rayon_verins=40.0)),
        ("verins de 40 mm au lieu de 70", Machine(course_verins=40.0)),
        ("les deux : R40 et 40 mm", Machine(rayon_verins=40.0,
                                            course_verins=40.0)),
    ]
    for nom, essai in essais:
        pire = min((degagement(essai, theta, p, 300.0)
                    for p in (0, 30, 45, 60, 90)),
                   key=lambda x: x["course_utile"])
        print(f"  {nom:<34s} {pire['debord_lateral']:9.1f} "
              f"{pire['course_utile']:13.1f}")
    print("\n  Ce ne sont PAS le diametre de la platine ni le rayon des verins")
    print("  qui dominent : ce sont les COLONNES DE VERINS, qui se couchent")
    print("  en s'inclinant. Leur hauteur est le levier -- les raccourcir, ou")
    print("  les remplacer par des biellettes tirees d'en haut.")

    args.step.parent.mkdir(parents=True, exist_ok=True)
    assemblage(m, theta, args.azimut).export(str(args.step))
    print(f"\n  {args.step}  "
          f"{args.step.stat().st_size/1024:.0f} Ko")
    return 0


if __name__ == "__main__":
    sys.exit(main())

