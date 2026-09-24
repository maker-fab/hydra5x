#!/usr/bin/env python3
"""Quatre concepts de tete inclinable, mesures plutot que decrits.

Le modele d'implantation a montre que ce qui coute de la course, ce ne
sont ni la platine ni le rayon des verins : ce sont **les colonnes qui se
couchent** en s'inclinant. Ce fichier construit quatre mecanismes
differents et mesure, sur le solide, ce que chacun retire aux courses.

Critere commun : demi-encombrement au pire azimut, a 35°, pointe de buse
a l'origine. La course utile d'un bati de 400 mm vaut
`400 - 2 x demi-encombrement`.

Les quatre concepts :

1. **Colonnes** -- trois verins verticaux montes sur la platine. Le plus
   direct, celui qui est dessine dans `machine.py`. Les colonnes depassent
   vers le haut et balaient en s'inclinant.
2. **Biellettes** -- les actionneurs restent sur le chariot, trois
   biellettes courtes tirent la platine. Rien de haut ne bouge avec elle.
3. **Cardan serie** -- deux axes rotatifs A et B, une chape autour du
   hotend. Pas de parallelisme, pas de mouvement parasite, mais une chape
   la ou la matiere deja deposee se trouve.
4. **Pivot central** -- un joint de cardan au centre prend les
   contraintes laterales, trois biellettes ne font que pousser. Le pivot
   est alors *choisi*, pas subi.

Ce fichier ne tranche pas : il donne les chiffres. Le choix depend aussi
du jeu admissible et de ce qu'on sait fabriquer.
"""
import argparse
import sys
from pathlib import Path

import cadquery as cq
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import cinematique_3points as c3  # noqa: E402

RAYON = 45.0            # cercle des points d'attaque
PIVOT_POINTE = 80.0     # centre de platine -> pointe de buse
DIAM_TETE = 50.0        # dissipateur + refroidissement annulaire
EP_PLATINE = 10.0


# Buse : meplat de 0,8 mm, cone a ~60°, puis le corps. Une buse droite
# donnerait une silhouette nulle -- de la matiere a z=0 jusqu'a son rayon --
# et la mesure d'inclinaison locale n'aurait aucun sens.
BUSE = [(0.4, 0.0), (3.5, 5.0), (8.0, 11.0), (8.0, 16.0)]


def _hotend(haut=PIVOT_POINTE):
    """Corps commun a tous les concepts : buse conique, bloc, dissipateur."""
    c = (cq.Workplane("XZ")
         .moveTo(BUSE[0][0], BUSE[0][1]))
    for r, z in BUSE[1:]:
        c = c.lineTo(r, z)
    c = (c.lineTo(DIAM_TETE / 2, 22.0)
         .lineTo(DIAM_TETE / 2, haut)
         .lineTo(0.0, haut).lineTo(0.0, 0.0).close()
         .revolve(360, (0, 0, 0), (0, 1, 0)))
    return c.translate((0, 0, -haut)).translate((0, 0, haut - haut))


def colonnes(course=70.0):
    """1. Trois verins verticaux portes par la platine."""
    c = cq.Workplane("XY").circle(RAYON + 15).extrude(EP_PLATINE)
    for a in np.radians(c3.AZIMUTS_VERINS):
        c = c.union(cq.Workplane("XY")
                    .center(RAYON * np.cos(a), RAYON * np.sin(a))
                    .circle(6.0).extrude(course + 20.0))
    return c.union(_hotend())


def biellettes(longueur=35.0):
    """2. Actionneurs restes en haut, biellettes courtes sur la platine.

    Seules les chapes bougent avec la platine. C'est la reponse directe a
    ce que le modele d'implantation a trouve.
    """
    c = cq.Workplane("XY").circle(RAYON + 15).extrude(EP_PLATINE)
    for a in np.radians(c3.AZIMUTS_VERINS):
        c = c.union(cq.Workplane("XY").workplane(offset=EP_PLATINE)
                    .center(RAYON * np.cos(a), RAYON * np.sin(a))
                    .circle(5.0).extrude(longueur))
    return c.union(_hotend())


def cardan_serie(rayon_chape=38.0):
    """3. Deux axes rotatifs, chape autour du hotend."""
    c = (cq.Workplane("XZ").workplane(offset=-rayon_chape)
         .moveTo(-rayon_chape, -PIVOT_POINTE * 0.55)
         .lineTo(-rayon_chape, 6.0).lineTo(rayon_chape, 6.0)
         .lineTo(rayon_chape, -PIVOT_POINTE * 0.55)
         .lineTo(rayon_chape - 8.0, -PIVOT_POINTE * 0.55)
         .lineTo(rayon_chape - 8.0, -2.0).lineTo(-(rayon_chape - 8.0), -2.0)
         .lineTo(-(rayon_chape - 8.0), -PIVOT_POINTE * 0.55).close()
         .extrude(2 * rayon_chape))
    c = c.union(cq.Workplane("XY").circle(rayon_chape).extrude(EP_PLATINE))
    return c.union(_hotend())


def pivot_central(longueur=35.0, diam_colonne=22.0):
    """4. Cardan central porteur, trois biellettes qui ne font que pousser."""
    c = biellettes(longueur)
    return c.union(cq.Workplane("XY").circle(diam_colonne / 2)
                   .extrude(EP_PLATINE + longueur))


CONCEPTS = {
    "colonnes": colonnes,
    "biellettes": biellettes,
    "cardan serie": cardan_serie,
    "pivot central": pivot_central,
}


def demi_encombrement(solide, theta, azimuts=(0, 30, 45, 60, 90)):
    """Demi-encombrement au pire azimut, pointe de buse a l'origine.

    La pointe est ramenee a l'origine AVANT de basculer : c'est elle que
    la machine pilote, donc c'est autour d'elle qu'il faut mesurer ce qui
    deborde.
    """
    pire = 0.0
    for phi in azimuts:
        axe = (-np.sin(np.radians(phi)), np.cos(np.radians(phi)), 0.0)
        s = (solide.translate((0, 0, PIVOT_POINTE))
             .rotate((0, 0, 0), axe, theta) if theta
             else solide.translate((0, 0, PIVOT_POINTE)))
        b = s.val().BoundingBox()
        pire = max(pire, abs(b.xmin), abs(b.xmax), abs(b.ymin), abs(b.ymax))
    return float(pire)


def silhouette(solide, r_max=60.0, pas=0.5, r_min=1.4):
    """Inclinaison que la GEOMETRIE LOCALE autorise, degres.

    Deuxieme critere, independant du premier et souvent oppose. Le
    demi-encombrement dit ce que la tete coute en course de bati ; la
    silhouette dit jusqu'ou elle peut plonger dans une concavite avant de
    toucher la matiere deja deposee.

    Meme methode que `tools/mesurer_tete.py` : profil de hauteur minimale
    a chaque rayon, puis theta_max = min_r arctan(h(r) / r).
    """
    sommets, _ = solide.val().tessellate(0.3)
    pts = np.array([[v.x, v.y, v.z + PIVOT_POINTE] for v in sommets])
    d = np.hypot(pts[:, 0], pts[:, 1])
    rayons = np.arange(r_min, r_max + pas, pas)
    angles = []
    for r in rayons:
        dans = (d >= r - pas) & (d < r + pas)
        if dans.any():
            angles.append(np.degrees(np.arctan2(max(pts[dans, 2].min(), 0.0), r)))
    return float(min(angles)) if angles else 90.0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inclinaison", type=float, default=35.0)
    ap.add_argument("--bati", type=float, default=400.0)
    ap.add_argument("--step", type=Path, default=None,
                    help="exporter les quatre concepts cote a cote")
    args = ap.parse_args()

    print(f"=== quatre concepts de tete, a {args.inclinaison:.0f}°, "
          f"bati {args.bati:.0f} mm ===\n")
    print(f"  {'concept':<16s} {'demi-enc.':>10s} {'course utile':>13s} "
          f"{'silhouette':>12s}")
    resultats = {}
    for nom, f in CONCEPTS.items():
        s = f()
        incl = demi_encombrement(s, args.inclinaison)
        course = args.bati - 2 * incl
        sil = silhouette(s)
        resultats[nom] = (incl, course, sil)
        marque = "" if sil >= args.inclinaison else "   < vise"
        print(f"  {nom:<16s} {incl:9.1f} {course:12.1f} "
              f"{sil:11.1f}°{marque}")
    print(f"\n  « demi-enc. » : ce que la tete retire au bati (collision "
          f"tete-bati).")
    print(f"  « silhouette » : jusqu'ou elle plonge dans une concavite "
          f"(collision tete-piece).")
    print(f"  Les deux criteres sont independants, et souvent opposes.")

    meilleur = max(resultats, key=lambda n: resultats[n][1])
    pire = min(resultats, key=lambda n: resultats[n][1])
    ecart = resultats[meilleur][1] - resultats[pire][1]
    print(f"\n  « {meilleur} » rend {ecart:.0f} mm de course de plus que "
          f"« {pire} ».")
    print(f"  Sur un bati de {args.bati:.0f} mm, c'est "
          f"{100*ecart/args.bati:.0f} % de la course.")

    print(f"\n  Course des actionneurs, meme pour tous "
          f"(V3 . R . tan) : "
          f"{c3.course_necessaire(args.inclinaison, RAYON):.1f} mm a R{RAYON:.0f}")
    print(f"  Resolution exigee pour 0,1° a la platine : "
          f"{c3.course_necessaire(0.1, RAYON)*1000:.0f} um")

    if args.step:
        a = cq.Assembly(name="concepts")
        for i, (nom, f) in enumerate(CONCEPTS.items()):
            a.add(f().rotate((0, 0, 0), (0, 1, 0), args.inclinaison),
                  name=nom.replace(" ", "_"),
                  loc=cq.Location(cq.Vector(i * 220.0, 0, 0)))
        args.step.parent.mkdir(parents=True, exist_ok=True)
        a.export(str(args.step))
        print(f"\n  {args.step}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
