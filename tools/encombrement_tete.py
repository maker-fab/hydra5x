#!/usr/bin/env python3
"""Inclinaison maximale de la tete, deduite de l'encombrement du hotend.

`envelope_hybride.py` prend le bridage de la tete en parametre sans savoir
d'ou il vient. C'est ce fichier qui le calcule.

**Modele.** Pivot au bout de la buse. Chaque obstacle du hotend est reduit
a un point : son debord lateral `w` depuis l'axe, et sa hauteur `d`
au-dessus de la pointe. En inclinant de theta, ce point descend a

    h(theta) = d.cos(theta) - w.sin(theta)

Il touche la surface en cours d'impression quand h = 0, soit

    theta_max = arctan(d / w)

La tete est bornee par le PLUS CONTRAIGNANT de ses obstacles -- coin bas du
bloc chauffant, chaussette silicone, buse de ventilation, dissipateur.

**Ce que la formule dit tout de suite** : allonger la buse sous le bloc
(`d`) ou retrecir le bloc (`w`) achete de l'inclinaison, et les deux
comptent autant. Un chanfrein sur le coin bas du bloc agit sur les deux.

**Ce que la formule dit aussi** : la rallonge du Volcano est dans la zone
de fusion, DANS le bloc. Elle n'augmente pas `d`. Elle ne paie donc rien en
inclinaison -- elle ne fait qu'ajouter de la masse et de la longueur en
amont.

Reserve : les cotes de protrusion sous bloc ne sont pas publiees par E3D.
Celles utilisees ici sont a relever au pied a coulisse ou sur la CAO avant
d'etre prises au serieux. Le tableau de sensibilite est plus solide que les
valeurs absolues.
"""
import argparse
import sys

import numpy as np


def theta_max(obstacles):
    """Inclinaison max, en degres, imposee par le plus contraignant."""
    pire, cause = 90.0, None
    for nom, w, d in obstacles:
        if w <= 0:
            continue
        a = float(np.degrees(np.arctan2(d, w)))
        if a < pire:
            pire, cause = a, nom
    return pire, cause


# Cotes : (nom, debord lateral w mm, hauteur au-dessus de la pointe d mm)
# Bloc Volcano 20x20x11,5 confirme. Protrusion de buse ESTIMEE.
HOTENDS = {
    "Volcano (Fractal)": [
        ("coin bas du bloc", 10.0, 4.5),
        ("chaussette silicone", 12.0, 4.0),
        ("dissipateur", 15.0, 16.0),
    ],
    "V6 standard": [
        ("coin bas du bloc", 8.0, 4.0),
        ("chaussette silicone", 10.0, 3.5),
        ("dissipateur", 11.0, 15.5),
    ],
    "bloc chanfreine": [
        ("coin bas du bloc", 6.0, 4.0),
        ("chaussette silicone", 8.0, 3.5),
        ("dissipateur", 11.0, 15.5),
    ],
    "buse longue + bloc etroit": [
        ("coin bas du bloc", 6.0, 8.0),
        ("chaussette silicone", 8.0, 7.5),
        ("dissipateur", 11.0, 19.0),
    ],
    # Les trois obstacles proches traites : chaussette retiree, ventilation
    # deportee par conduit, coin du bloc chanfreine. Le dissipateur devient
    # le facteur limitant, au-dela des 45 deg utiles.
    "Volcano degage (3 modifs)": [
        ("coin bas chanfreine", 7.0, 4.5),
        ("dissipateur", 15.0, 16.0),
    ],
}

# Obstacles qu'on croit contraignants et qui ne le sont pas : `arctan(d/w)`
# leur est tres favorable des qu'ils sont hauts. Deporter l'electronique ou
# choisir un extrudeur compact n'achete AUCUN degre.
NON_CONTRAIGNANTS = [
    ("moteur direct drive standard", 30.0, 45.0),
    ("moteur LGX Lite compact", 25.0, 40.0),
]


COTES_A_RELEVER = """
Quatre cotes a prendre au pied a coulisse. Origine = POINTE de la buse.

  1. protrusion    hauteur de la face basse du bloc au-dessus de la pointe
  2. bloc          plus grande demi-DIAGONALE du bloc, pas la demi-largeur
                   (un bloc 20x20 mesure 14,1 et non 10)
  3. chaussette    debord lateral max de la chaussette, et sa hauteur
  4. ventilation   debord lateral max de la buse de refroidissement,
                   et sa hauteur au-dessus de la pointe

Tout obstacle plus haut que ~20 mm est sans effet : arctan(d/w) lui est
tres favorable. Inutile de mesurer le dissipateur ou l'extrudeur.
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--marge", type=float, default=0.80)
    ap.add_argument("--cotes", action="store_true",
                    help="afficher ce qu'il faut mesurer, et sortir")
    ap.add_argument("--protrusion", type=float,
                    help="hauteur de la face basse du bloc au-dessus de la pointe, mm")
    ap.add_argument("--bloc", type=float,
                    help="demi-diagonale du bloc, mm")
    ap.add_argument("--chaussette", type=float, nargs=2, metavar=("W", "D"),
                    help="debord et hauteur de la chaussette, mm")
    ap.add_argument("--ventilation", type=float, nargs=2, metavar=("W", "D"),
                    help="debord et hauteur de la buse de refroidissement, mm")
    args = ap.parse_args()

    if args.cotes:
        print(COTES_A_RELEVER)
        return 0

    if args.bloc and args.protrusion:
        mesure = [("coin bas du bloc", args.bloc, args.protrusion)]
        if args.chaussette:
            mesure.append(("chaussette", args.chaussette[0], args.chaussette[1]))
        if args.ventilation:
            mesure.append(("ventilation", args.ventilation[0], args.ventilation[1]))
        brut, cause = theta_max(mesure)
        print("Hotend mesure\n")
        for nom, w, d in mesure:
            print(f"  {nom:<22s} w={w:5.1f} d={d:5.1f} -> "
                  f"{np.degrees(np.arctan2(d, w)):5.1f}°")
        print(f"\n  limite brute  {brut:5.1f}°")
        print(f"  limite utile  {brut*args.marge:5.1f}°   (marge {args.marge*100:.0f} %)")
        print(f"  facteur limitant : {cause}")
        manque = max(0.0, 45.0 - brut * args.marge)
        print(f"\n  reste a fournir par la table pour atteindre 45° : {manque:.1f}°")
        if manque > 0:
            z = 12.0 * np.sin(np.radians(manque / args.marge))
            print(f"  -> hauteur minimale du point le plus bas : z >= {z:.2f} mm")
        else:
            print("  -> la tete suffit seule, la garde plateau-buse ne mord plus")
        return 0

    print("Inclinaison maximale de tete, par hotend\n")
    print(f"  {'hotend':<26s} {'brut':>7s} {'utile':>7s}   facteur limitant")
    for nom, obstacles in HOTENDS.items():
        brut, cause = theta_max(obstacles)
        print(f"  {nom:<26s} {brut:6.1f}° {brut*args.marge:6.1f}°   {cause}")

    print(f"\n  (marge de securite {args.marge*100:.0f} %)")
    print("\n  Ce qui N'EST PAS contraignant :")
    for nom, w, d in NON_CONTRAIGNANTS:
        print(f"    {nom:<32s} w={w:5.1f} d={d:5.1f} -> "
              f"{np.degrees(np.arctan2(d, w)):5.1f}°")
    print("    -> deporter l'electronique ou alleger la tete n'achete aucun degre")
    print("\n  Sensibilite du coin bas du bloc -- theta = arctan(d/w) :\n")
    print(f"  {'d \\\\ w':>7s}" + "".join(f"{w:>8.0f}" for w in (6, 8, 10, 12)))
    for d in (3.0, 4.0, 6.0, 8.0, 10.0):
        ligne = f"  {d:7.1f}"
        for w in (6.0, 8.0, 10.0, 12.0):
            ligne += f"{np.degrees(np.arctan2(d, w)):8.1f}"
        print(ligne)
    print("\n  d = protrusion de buse sous le bloc, w = demi-largeur du bloc, en mm")
    return 0


if __name__ == "__main__":
    sys.exit(main())
