#!/usr/bin/env python3
"""Volume imprimable reellement utilisable sur une machine a plateau inclinable.

Une 5 axes a plateau inclinable **perd du volume** par rapport a la 3 axes
batie dans le meme cadre. Personne ne chiffre cette perte ; les fiches
annoncent le volume a inclinaison nulle. Ce fichier la calcule, pour un
plateau et une piece **ronds ou carres**.

**Pourquoi il y a une perte.** Quand le plateau s'incline de theta, la
piece bascule avec lui : son point haut monte (course Z), son enveloppe
s'elargit (course X/Y), le bord du plateau plonge (vide sous le plateau).

**Modele.** Pivot au centre du plateau, dans son plan. Piece centree. Pour
un azimut de bascule `phi`, on a besoin de l'etendue de l'empreinte dans
cette direction -- sa fonction d'appui :

    rond,  rayon r      : e(phi) = r                   (isotrope)
    carre, demi-cote a  : e(phi) = a.(|cos phi| + |sin phi|)   jusqu'a a.V2

C'est **toute la difference entre rond et carre** : le carre presente sa
diagonale dans les azimuts a 45°, soit 41 % d'etendue en plus, et c'est
exactement la ou une table a trois points equilaterale est deja la plus
faible. Les deux anisotropies ne se compensent pas, elles se cumulent.

Puis, a l'inclinaison theta :

    Z_haut = e(phi).sin(theta) + H.cos(theta)         course Z
    E      = e(phi).cos(theta) + H.sin(theta)         etendue le long de phi
    F      = e(phi + 90)                              etendue en travers

et dans le repere machine, demi-course X = E.|cos phi| + F.|sin phi|,
demi-course Y = E.|sin phi| + F.|cos phi|. On balaye phi et on retient le
pire.

**Ce que le calcul montre tout de suite** : le terme `H.sin(theta)` domine.
Une piece haute coute bien plus cher en volume qu'une piece large. Une 5
axes a plateau inclinable est donc naturellement **plate**.

Le debattement reel de la table, azimut par azimut, vient de
`table_3points.py`.
"""
import argparse
import sys

import numpy as np

import table_3points as t3


def sommets(forme, taille, h, n=24):
    """Sommets de l'enveloppe de la piece, repere plateau.

    Le maximum d'une fonction lineaire sur un convexe est atteint sur un
    sommet : il suffit donc de transformer ceux-la. Un carre en a huit, un
    cylindre est echantillonne.
    """
    if forme == "carre":
        base = [(-taille, -taille), (taille, -taille),
                (taille, taille), (-taille, taille)]
    else:
        a = np.linspace(0, 2 * np.pi, n, endpoint=False)
        base = list(zip(taille * np.cos(a), taille * np.sin(a)))
    return np.array([(x, y, z) for x, y in base for z in (0.0, h)])


def basculer(pts, theta_deg, phi_deg, pivot=0.0):
    """Bascule de theta dans l'azimut phi, pivot a `pivot` sur l'axe."""
    t, p = np.radians(theta_deg), np.radians(phi_deg)
    u, v = np.array([np.cos(p), np.sin(p)]), np.array([-np.sin(p), np.cos(p)])
    s = pts[:, :2] @ u
    w = pts[:, :2] @ v
    z = pts[:, 2] - pivot
    s2 = s * np.cos(t) + z * np.sin(t)
    z2 = -s * np.sin(t) + z * np.cos(t) + pivot
    return np.column_stack([s2 * u[0] + w * v[0], s2 * u[1] + w * v[1], z2])


def faisable(forme, taille, h, theta_deg, phi_deg, courses):
    """La piece tient-elle dans les courses, basculee de theta vers phi ?

    La hauteur du pivot n'intervient pas : deplacer le centre de rotation
    ajoute une TRANSLATION, et l'encombrement d'un solide est invariant par
    translation. Le pivot change ou la piece se trouve, pas la course
    qu'il faut pour la promener. Il ne compte que pour la plongee du
    plateau sous son plan de depart.
    """
    cx, cy, cz = courses
    q = basculer(sommets(forme, taille, h), theta_deg, phi_deg)
    eps = 1e-6                      # tolerance : 200,0000001 tient dans 200
    if q[:, 2].max() - min(q[:, 2].min(), 0.0) > cz + eps:
        return False
    return (q[:, 0].ptp() <= cx + eps) and (q[:, 1].ptp() <= cy + eps)


def volume(forme, taille, h):
    return np.pi * taille * taille * h if forme == "rond" else 4 * taille * taille * h


def taille_max_sur_plateau(forme_piece, forme_plateau, cote_plateau):
    """Plus grande piece qui tient a plat sur le plateau (rayon ou demi-cote).

    `cote_plateau` = diametre si rond, cote si carre.
    """
    demi = cote_plateau / 2.0
    if forme_piece == "rond":
        return demi
    return demi if forme_plateau == "carre" else demi / np.sqrt(2)


def meilleure_piece(forme, taille_max, courses, incl_azimut, pas=2.0):
    """Plus gros volume faisable dans TOUS les azimuts.

    `incl_azimut` : dict azimut -> inclinaison max a tenir dans cet azimut.
    """
    best = (0.0, 0.0, 0.0)
    for taille in np.arange(pas, taille_max + pas, pas):
        for h in np.arange(pas, courses[2] + pas, pas):
            v = volume(forme, taille, h)
            if v <= best[2]:
                continue
            if all(faisable(forme, taille, h, th, phi, courses)
                   for phi, th in incl_azimut.items()):
                best = (float(taille), float(h), float(v))
    return best


def plongee(forme_plateau, cote_plateau, theta_deg, phi_deg=45.0, pivot=0.0):
    """Vide necessaire sous le plateau dans cet azimut, mm.

    Seul endroit ou la hauteur du pivot compte : un cardan place SOUS le
    plateau fait plonger ses bords d'autant plus bas.
    """
    demi = cote_plateau / 2.0
    q = basculer(sommets(forme_plateau, demi, 0.0), theta_deg, phi_deg, pivot)
    return float(-q[:, 2].min())


def debord_tete(longueur, demi_largeur, b_deg):
    """Debord lateral d'une tete inclinee de B autour de la pointe, mm.

    La tete pivote autour de la pointe de buse. Son coin le plus exterieur
    est a `longueur` au-dessus et `demi_largeur` de cote :

        debord(B) = longueur.sin(B) + demi_largeur.cos(B)

    A B = 0 il vaut la demi-largeur : c'est l'encombrement qu'une tete
    fixe coute deja. Seule la DIFFERENCE se paie en bascule.
    """
    r = np.radians(b_deg)
    return longueur * np.sin(r) + demi_largeur * np.cos(r)


def courses_tete_inclinable(courses, longueur, demi_largeur, b_deg):
    """Courses restantes quand c'est la TETE qui s'incline.

    La piece ne bouge pas : elle ne balaie rien, elle ne se decolle pas,
    et elle ne coute donc **aucune** course. Ce qui coute, c'est le corps
    de la tete qui se couche vers le bati.

    Difference de nature avec un plateau basculant : ici le cout est
    borne par la TAILLE DE LA TETE, la-bas il croit avec la taille de la
    PIECE. C'est la seule asymetrie structurelle entre les deux
    architectures.
    """
    cx, cy, cz = courses
    perte = 2 * (debord_tete(longueur, demi_largeur, b_deg)
                 - debord_tete(longueur, demi_largeur, 0.0))
    return max(cx - perte, 0.0), max(cy - perte, 0.0), cz


def courses_requises(forme, taille, h, theta_deg, pas_phi=2.0):
    """Courses X, Y, Z necessaires pour une piece donnee, a cette inclinaison.

    **Le calcul inverse, et c'est le bon sens de lecture.** Fixer le cadre
    et regarder le volume fondre fait croire a une perte de capacite. Il
    n'y en a pas : un cadre est fait de profiles et de courroies, on peut
    l'agrandir. Ce que la bascule coute reellement, c'est **une machine
    plus grosse pour la meme piece** -- pas une piece plus petite.

    Lu dans ce sens, l'ecart entre les deux architectures se deplace :
    l'empreinte au sol est comparable, c'est la HAUTEUR qui separe.
    """
    cx = cy = cz = 0.0
    for phi in np.arange(0.0, 180.0, pas_phi):
        q = basculer(sommets(forme, taille, h), theta_deg, phi)
        cx = max(cx, q[:, 0].ptp())
        cy = max(cy, q[:, 1].ptp())
        cz = max(cz, q[:, 2].max() - min(q[:, 2].min(), 0.0))
    return cx, cy, cz


def courses_requises_tete(cote_x, cote_y, h, longueur, demi_largeur, b_deg):
    """Idem, quand c'est la tete qui s'incline : la piece ne bouge pas."""
    perte = 2 * (debord_tete(longueur, demi_largeur, b_deg)
                 - debord_tete(longueur, demi_largeur, 0.0))
    return cote_x + perte, cote_y + perte, h


def cout_outils(n, largeur_dock, profondeur_dock, cx, cy):
    """Ce que N outils parques retirent aux courses."""
    if n <= 1:
        return cx, cy
    if n * largeur_dock > cx:
        raise ValueError(f"{n} docks de {largeur_dock} mm ne tiennent pas "
                         f"dans {cx} mm de course X")
    return cx, cy - profondeur_dock


def profil_inclinaison(args, pas=15.0):
    """azimut -> inclinaison max, selon le mecanisme de bascule."""
    azimuts = np.arange(0.0, 180.0, pas)
    if args.bascule == "cardan":
        brut = t3.inclinaison_cardan(args.axes[0], args.axes[1], azimuts)
        return {a: min(args.inclinaison, v) for a, v in brut.items()}
    if args.bascule == "3points":
        pts = t3.mise_a_echelle(t3.DISPOSITIONS[args.appuis], args.plateau / 2)
        return {float(a): min(args.inclinaison,
                              t3.inclinaison(pts, args.course_diff, a))
                for a in azimuts}
    return {float(a): args.inclinaison for a in azimuts}


def courses_requises_mixte(forme, taille, h, alpha, beta,
                           longueur, demi_largeur, pas_phi=2.0):
    """Cadre necessaire quand plateau ET tete s'inclinent.

    Les deux couts **s'additionnent**. Le plateau fait balayer la piece,
    la tete fait balayer son propre corps, et aucune des deux excursions ne
    prend la place de l'autre : elles se produisent au meme instant, dans
    la meme direction, et elles s'ajoutent bout a bout.

    C'est le point que la notion de redondance peut faire manquer. Repartir
    l'inclinaison entre deux organes ne repartit pas la place qu'ils
    consomment -- elle la cumule.
    """
    cx, cy, cz = courses_requises(forme, taille, h, alpha, pas_phi)
    marge = 2 * (debord_tete(longueur, demi_largeur, beta)
                 - debord_tete(longueur, demi_largeur, 0.0))
    return cx + marge, cy + marge, cz


def inverse(args):
    """Quel cadre faut-il pour imprimer CETTE piece, selon l'architecture ?"""
    x, y, h = args.cible
    taille = max(x, y) / 2.0
    forme = args.forme_piece
    ref = x * y * h if forme == "carre" else np.pi * taille ** 2 * h

    print(f"=== piece visee : {x:.0f} x {y:.0f} x {h:.0f} mm "
          f"({forme}, {ref/1e6:.2f} L) ===\n")
    print(f"  {'incl.':>6s} {'architecture':<20s} {'cadre necessaire':>22s} "
          f"{'enveloppe':>10s} {'ratio':>7s}")
    for theta in (0, 15, 30, 45, 60, 90):
        for nom, c in (
            ("plateau basculant",
             courses_requises(forme, taille, h, theta)),
            ("tete inclinable",
             courses_requises_tete(x, y, h, args.tete[0], args.tete[1], theta)),
        ):
            if nom.startswith("plateau") and theta > 60:
                continue          # au-dela, la piece est retournee : bridage
            env = c[0] * c[1] * c[2]
            print(f"  {theta:5.0f}° {nom:<20s} "
                  f"{c[0]:6.0f} x{c[1]:5.0f} x{c[2]:5.0f} mm "
                  f"{env/1e6:8.1f} L {env/ref:6.1f}x")
        print()
    print("  « ratio » = volume de l'enveloppe machine rapporte a la piece.")
    print("  Au-dela de 60°, un plateau basculant retourne la piece :")
    print("  l'adherence ne la tient plus, il faut un bridage mecanique.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--course", type=float, nargs=3,
                    metavar=("X", "Y", "Z"))
    ap.add_argument("--cible", type=float, nargs=3, metavar=("X", "Y", "Z"),
                    help="calcul INVERSE : piece visee, on en deduit le "
                         "cadre necessaire pour chaque architecture")
    ap.add_argument("--plateau", type=float, default=None,
                    help="cote si carre, diametre si rond, mm "
                         "(inutile avec --cible)")
    ap.add_argument("--forme-plateau", choices=("rond", "carre"), default="carre")
    ap.add_argument("--forme-piece", choices=("rond", "carre"), default="carre")
    ap.add_argument("--inclinaison", type=float, default=45.0)
    ap.add_argument("--bascule", choices=("plat", "3points", "cardan", "tete"),
                    default="plat",
                    help="qui s'incline : personne (plat), le plateau "
                         "(3points, cardan), ou la tete")
    ap.add_argument("--axes", type=float, nargs=2, default=(45.0, 45.0),
                    metavar=("ALPHA", "BETA"),
                    help="courses des deux axes du cardan, degres")
    ap.add_argument("--appuis", choices=sorted(t3.DISPOSITIONS),
                    default="equilateral",
                    help="disposition des trois appuis")
    ap.add_argument("--course-diff", type=float, default=150.0,
                    help="course differentielle des trois actionneurs, mm")
    ap.add_argument("--pivot", type=float, default=0.0,
                    help="hauteur du centre de bascule par rapport au plan "
                         "du plateau (negatif = cardan dessous). N'agit que "
                         "sur la plongee")
    ap.add_argument("--tete", type=float, nargs=2, default=(70.0, 25.0),
                    metavar=("LONGUEUR", "DEMI_LARGEUR"),
                    help="encombrement de la tete au-dessus de la pointe, mm")
    ap.add_argument("--outils", type=int, default=1)
    ap.add_argument("--dock", type=float, nargs=2, default=(55.0, 60.0),
                    metavar=("LARGEUR", "PROFONDEUR"))
    ap.add_argument("--pas", type=float, default=2.0)
    args = ap.parse_args()

    if args.cible:
        return inverse(args)
    if not args.course or args.plateau is None:
        ap.error("donner --course X Y Z et --plateau, ou --cible X Y Z")

    cx, cy, cz = args.course
    cx, cy = cout_outils(args.outils, args.dock[0], args.dock[1], cx, cy)
    taille_max = taille_max_sur_plateau(args.forme_piece, args.forme_plateau,
                                        args.plateau)
    courses = (cx, cy, cz)

    print(f"=== plateau {args.forme_plateau} {args.plateau:.0f} mm, "
          f"piece {args.forme_piece} ===")
    print(f"  courses X{cx:.0f} Y{cy:.0f} Z{cz:.0f}"
          + (f"  ({args.outils} outils)" if args.outils > 1 else ""))
    if args.bascule == "3points":
        pts = t3.mise_a_echelle(t3.DISPOSITIONS[args.appuis], args.plateau / 2)
        pire, az = t3.pire_cas(pts, args.course_diff)
        print(f"  appuis « {args.appuis} », course differentielle "
              f"{args.course_diff:.0f} mm : {pire:.1f}° garantis "
              f"(azimut {az:.0f}°)")
    elif args.bascule == "cardan":
        pr = profil_inclinaison(args)
        print(f"  cardan {args.axes[0]:.0f}°+{args.axes[1]:.0f}° : "
              f"{min(pr.values()):.1f}° garantis, {max(pr.values()):.1f}° "
              f"en diagonale")
    if args.pivot:
        print(f"  pivot a {args.pivot:+.0f} mm du plan du plateau")

    if args.bascule == "tete":
        print(f"  tete L{args.tete[0]:.0f} w{args.tete[1]:.0f} : "
              f"la piece ne bouge pas, seul le corps de la tete se couche")

    profil = profil_inclinaison(args)
    plat = {a: 0.0 for a in profil}
    _, h0, v0 = meilleure_piece(args.forme_piece, taille_max, courses,
                                plat, args.pas)

    print(f"\n  {'incl.':>6s} {'empreinte':>11s} {'hauteur':>8s} "
          f"{'volume':>9s} {'perte':>7s} {'vide dessous':>13s}")
    for theta in (0, 10, 15, 20, 25, 30, 35, 40, 45, 60, 90):
        if theta > max(profil.values()):
            break
        if args.bascule == "tete":
            # la piece reste a plat ; c'est le cadre qui se retrecit
            p = {a: 0.0 for a in profil}
            c = courses_tete_inclinable(courses, args.tete[0], args.tete[1],
                                        theta)
        else:
            p = {a: min(theta, profil[a]) for a in profil}
            c = courses
        taille, h, v = meilleure_piece(args.forme_piece, taille_max, c,
                                       p, args.pas)
        emp = (f"Ø{2*taille:.0f}" if args.forme_piece == "rond"
               else f"{2*taille:.0f}x{2*taille:.0f}")
        perte = 100.0 * (1 - v / v0) if v0 else 0.0
        print(f"  {theta:5.0f}° {emp:>11s} {h:7.0f} {v/1e6:8.2f} L "
              f"{perte:6.1f}% "
              + ("        0 mm" if args.bascule == "tete" else
                 f"{plongee(args.forme_plateau, args.plateau, min(theta, max(profil.values())), 45.0, args.pivot):9.0f} mm"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
