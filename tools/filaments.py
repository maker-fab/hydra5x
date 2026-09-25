#!/usr/bin/env python3
"""Choix de filament technique : charges, derive thermique, et le reste.

Pour les pieces imprimees de la machine -- changeur d'outil en premier.
Un changeur vit ou meurt sur sa **repetabilite** : les offsets d'outil
sont etalonnes a une temperature, et si le caisson derive, les pieces
bougent. C'est le critere que ce fichier chiffre.

**Trois familles de charges, et elles ne servent pas a la meme chose.**

- **CF, fibre de carbone** -- la plus raide, le coefficient de dilatation
  le plus bas. Trois defauts : **elle conduit l'electricite**, elle
  n'existe qu'en noir, et elle casse net.
- **GF, fibre de verre** -- moins raide que le CF, mais elle garde
  nettement plus de tenacite, **elle est isolante**, et elle se colore.
  C'est souvent le bon compromis quand la piece prend des chocs ou porte
  de l'electronique.
- **charges minerales** (craie, ceramique, talc) -- c'est ce qui rend un
  filament « mat ». Elles reduisent le retrait, donc le gauchissement,
  mais elles n'apportent ni raideur ni tenue en temperature. Un filament
  mat est un filament charge : meme abrasivite, meme buse durcie.

**Le point qu'on oublie : le CF conduit.** Sur une tete qui porte une
carte, des nappes, un capteur et des LED, c'est un vrai risque de fuite,
et la poussiere de ponçage l'est encore plus. La fibre de verre n'a pas ce
defaut.

**Les valeurs ci-dessous sont des ordres de grandeur de fiches
techniques, pas des mesures faites ici.** Elles varient d'un fabricant a
l'autre, surtout le taux de charge. Ce qui est calcule en revanche -- la
derive -- l'est exactement a partir d'elles.
"""
import argparse
import sys

# (CTE um/m/K, module GPa, tenacite relative a l'ASA, service continu °C,
#  conducteur, couleurs, aspect, reprise d'humidite %, fluage relatif,
#  usure relative -- plus bas = mieux pour les deux derniers)
#
# Les trois dernieres colonnes sont celles qui decident quand on veut TOUT
# imprimer, et elles manquaient a la premiere version de cette table :
#
# - **reprise d'humidite** : un PA6 qui gonfle de 1 % fait 1 mm sur 100.
#   Aucune repetabilite ne survit a ca. C'est LE defaut des polyamides, et
#   il ne se voit pas sur une fiche de traction.
# - **fluage** : une piece sous precharge permanente -- ressort de
#   verrouillage, bossage d'insert -- se deforme lentement a charge
#   constante. L'ASA flue notablement des 60 °C.
# - **usure** : au contact repete. Les polyamides sont autolubrifiants,
#   c'est leur qualite historique de materiau de palier.
FILAMENTS = {
    "ASA":        (90, 2.1, 1.00,  90, False, "toutes",   "semi-mat",      0.4, 1.00, 1.00),
    "ASA mat":    (75, 2.0, 0.85,  90, False, "toutes",   "mat",           0.4, 1.00, 1.00),
    "ASA-GF":     (50, 4.0, 0.55,  95, False, "claires",  "mat",           0.4, 0.60, 0.85),
    "ASA-CF":     (35, 5.5, 0.35,  95, True,  "noir",     "mat",           0.4, 0.50, 0.80),
    "ABS":        (90, 2.0, 0.95,  85, False, "toutes",   "semi-brillant", 0.5, 1.10, 1.05),
    "PETG":       (70, 2.0, 0.90,  68, False, "toutes",   "brillant",      0.3, 1.40, 0.95),
    "PETG-CF":    (30, 5.0, 0.30,  72, True,  "noir",     "mat",           0.3, 0.90, 0.70),
    "PA6-GF":     (55, 5.0, 0.70, 120, False, "naturel",  "mat",           3.0, 0.55, 0.35),
    "PA6-CF":     (40, 7.0, 0.45, 130, True,  "noir",     "mat",           3.0, 0.45, 0.30),
    "PA12-GF":    (60, 4.0, 0.85, 110, False, "naturel",  "mat",           0.8, 0.60, 0.30),
    "PPA-GF":     (45, 6.0, 0.60, 150, False, "naturel",  "mat",           1.2, 0.35, 0.35),
    "PC":         (68, 2.3, 1.20, 120, False, "toutes",   "brillant",      0.2, 0.30, 0.90),
    "PC-GF":      (40, 5.0, 0.75, 125, False, "claires",  "mat",           0.2, 0.25, 0.75),
    "PC-CF":      (25, 7.0, 0.40, 125, True,  "noir",     "mat",           0.2, 0.20, 0.70),
    "PPS-GF":     (30, 7.0, 0.55, 200, False, "naturel",  "mat",           0.03, 0.15, 0.40),
    "PPS-CF":     (20, 9.0, 0.35, 200, True,  "noir",     "mat",           0.03, 0.12, 0.35),
    "PLA mat":    (65, 3.5, 0.45,  50, False, "toutes",   "mat",           0.3, 2.50, 1.60),
}

REFERENCE = ("alu 6061", 23)


def derive(cte, longueur_mm, delta_k):
    """Dilatation d'une piece, mm."""
    return cte * (longueur_mm / 1000.0) * delta_k / 1000.0


# Ce que chaque poste exige vraiment, dans l'ordre.
POSTES = {
    "Gantry / Dock":      ("portent les offsets d'outil",
                           ["derive faible", "gauchissement faible"]),
    "ToolLock, corps":    ("2000 chocs, 9 inserts M3 sous charge",
                           ["tenacite", "tenue des inserts"]),
    "ToolLock, contacts": ("le contact repete qui FAIT la reference",
                           ["usure faible"]),
    "Bossages sous precharge": ("ressorts, inserts charges en permanence",
                                ["fluage faible"]),
    "Toolhead":           ("carte, nappes, capteur, LED, contre le bloc",
                           ["isolant electrique", "service > 85 °C"]),
}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--longueur", type=float, default=100.0,
                    help="longueur de piece consideree, mm")
    ap.add_argument("--delta", type=float, default=40.0,
                    help="variation de temperature du caisson, K")
    ap.add_argument("--tolerance", type=float, default=0.10,
                    help="repetabilite visee sur l'offset d'outil, mm")
    ap.add_argument("--service", type=float, default=85.0,
                    help="temperature de service minimale exigee, °C")
    args = ap.parse_args()

    print(f"=== piece de {args.longueur:.0f} mm, caisson a "
          f"±{args.delta:.0f} K, tolerance {args.tolerance:.2f} mm ===\n")
    print(f"  {'filament':<11s} {'derive':>8s} {'choc':>6s} {'humid.':>7s} "
          f"{'fluage':>7s} {'usure':>6s} {'service':>8s} {'elec':>8s} "
          f"{'couleurs':>9s}")
    for nom, v in FILAMENTS.items():
        cte, e, choc, serv, cond, coul, aspect, hum, flu, us = v
        d = derive(cte, args.longueur, args.delta)
        drapeaux = ""
        if d > args.tolerance:
            drapeaux += " derive"
        if serv < args.service:
            drapeaux += " chaud"
        if hum >= 1.0:
            drapeaux += " HUMIDITE"
        print(f"  {nom:<11s} {d:7.3f} {choc:6.2f} {hum:6.1f}% {flu:7.2f} "
              f"{us:6.2f} {serv:7.0f}° "
              f"{'CONDUIT' if cond else 'isolant':>8s} {coul:>9s}{drapeaux}")
    nom, cte = REFERENCE
    print(f"  {nom:<11s} {derive(cte, args.longueur, args.delta):7.3f}"
          f"   (reference)")

    print(f"\n  « derive » : dilatation sur {args.longueur:.0f} mm pour "
          f"{args.delta:.0f} K. Marquee si elle depasse la tolerance.")
    print(f"  « choc », « fluage », « usure » : relatifs a l'ASA non charge.")
    print(f"  « humid. » : reprise d'eau a saturation. Au-dela de 1 %, la")
    print(f"      piece gonfle plus que sa tolerance -- marque HUMIDITE.")
    print(f"  « chaud » : service continu sous {args.service:.0f} °C.\n")

    for poste, (quoi, exigences) in POSTES.items():
        print(f"  --- {poste} : {quoi}")
        print(f"      exige : {', '.join(exigences)}")
        if "usure faible" in exigences:
            choix = [n for n, v in FILAMENTS.items()
                     if v[9] <= 0.45 and v[7] < 1.0 and v[3] >= args.service]
        elif "fluage faible" in exigences:
            choix = [n for n, v in FILAMENTS.items()
                     if v[8] <= 0.40 and v[7] < 1.0 and v[3] >= args.service]
        elif "isolant electrique" in exigences:
            choix = [n for n, v in FILAMENTS.items()
                     if not v[4] and v[3] >= args.service]
        elif "tenacite" in exigences:
            choix = [n for n, v in FILAMENTS.items()
                     if v[2] >= 0.55 and v[3] >= args.service and not v[4]]
        else:
            choix = [n for n, v in FILAMENTS.items()
                     if derive(v[0], args.longueur, args.delta) <= args.tolerance
                     and v[3] >= args.service]
        print(f"      candidats : {', '.join(choix) if choix else 'aucun'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())


