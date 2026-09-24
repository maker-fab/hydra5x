#!/usr/bin/env python3
"""Verifie la cinematique de la table basculante a trois verins.

Six controles, du plus fondamental au plus operationnel. Aucun n'admet de
tolerance genereuse : la cinematique est exacte en forme fermee, donc les
ecarts attendus sont au niveau du flottant.

Pas de pytest dans ce depot -- meme forme que `test_limits.py`, un script
qui s'execute et rend un compte.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import cinematique_3points as c3  # noqa: E402

RAYON = 150.0               # machine retenue en D24
COURSE_DIFF = 210.0
VISE = 35.0


def aller_retour():
    """(theta, phi, z) -> hauteurs -> (theta, phi, z) sur une grille dense."""
    pire = 0.0
    for theta in np.arange(0.0, 40.1, 0.5):
        for phi in np.arange(0.0, 360.0, 7.5):
            for z in (50.0, 200.0, 400.0):
                h = c3.hauteurs(theta, phi, z, RAYON)
                t2, p2, z2 = c3.pose(h, RAYON)
                pire = max(pire, abs(t2 - theta), abs(z2 - z))
                if theta > 1e-9:      # l'azimut n'a pas de sens a plat
                    d = abs((p2 - phi + 180.0) % 360.0 - 180.0)
                    pire = max(pire, d)
    return pire < 1e-9, f"ecart max {pire:.3e} (angles en deg, z en mm)"


def normale_vers_vertical():
    """La pose calculee amene-t-elle la normale du chunk sur +Z ?"""
    pire = 0.0
    for theta in np.arange(0.0, 40.1, 1.0):
        for phi in np.arange(0.0, 360.0, 15.0):
            m = c3.normale_plateau(theta, phi)
            # la normale du plateau doit faire l'angle theta avec +Z
            pire = max(pire, abs(np.degrees(np.arccos(
                np.clip(m[2], -1.0, 1.0))) - theta))
    return pire < 1e-9, f"ecart d'inclinaison max {pire:.3e} deg"


def centre_immobile():
    """Le centre du plateau reste a sa hauteur de consigne."""
    pire = 0.0
    for theta in np.arange(0.0, 40.1, 1.0):
        for phi in np.arange(0.0, 360.0, 15.0):
            h = c3.hauteurs(theta, phi, 200.0, RAYON)
            pire = max(pire, abs(float(np.mean(h)) - 200.0))
    return pire < 1e-9, f"derive du centre {pire:.3e} mm"


def anisotropie():
    """L'ecart entre verins varie entre 1,5 et V3 fois R.tan(theta)."""
    ecarts = []
    for phi in np.arange(0.0, 360.0, 0.5):
        h = c3.hauteurs(VISE, phi, 200.0, RAYON)
        ecarts.append(float(h.max() - h.min()))
    base = RAYON * np.tan(np.radians(VISE))
    lo, hi = min(ecarts) / base, max(ecarts) / base
    ok = abs(lo - c3.ETALEMENT_MEILLEUR) < 1e-6 and abs(hi - c3.ETALEMENT_PIRE) < 1e-6
    return ok, f"etalement mesure {lo:.4f} a {hi:.4f} (attendu 1.5000 a 1.7321)"


def budget_de_course():
    """L'angle vise tient-il dans la course, et les deux formules
    sont-elles bien reciproques ?"""
    besoin = c3.course_necessaire(VISE, RAYON)
    atteignable = c3.angle_max(RAYON, COURSE_DIFF)
    retour = c3.course_necessaire(atteignable, RAYON)
    ok = (besoin <= COURSE_DIFF and abs(retour - COURSE_DIFF) < 1e-9
          and atteignable > VISE)
    return ok, (f"{VISE:.0f}° demandent {besoin:.1f} mm sur {COURSE_DIFF:.0f} ; "
                f"butee a {atteignable:.2f}° ; reciprocite {abs(retour-COURSE_DIFF):.2e}")


def garde_de_course():
    """Depasser la course leve une erreur nommant le chunk, sans produire
    de G-code inexecutable."""
    import stitch_chunks as sc
    poses = [np.full(3, 200.0), c3.hauteurs(VISE, 0.0, 200.0, RAYON)]
    try:
        sc.bloc_rotation_3points(1, poses, 10.0, 50.0)
    except ValueError as e:
        return "chunk 1" in str(e), f"leve bien : {e}"
    return False, "aucune erreur levee alors que la course est insuffisante"


def forme_lineaire():
    """La forme en gradient donne exactement les memes hauteurs.

    C'est la parametrisation qui rendra un noyau de firmware court : une
    combinaison lineaire fixe de (z, gx, gy), sans trigonometrie ni
    singularite a plat.
    """
    pire = 0.0
    for theta in np.arange(0.0, 40.1, 0.5):
        for phi in np.arange(0.0, 360.0, 7.5):
            gx, gy = c3.gradient(theta, phi)
            pire = max(pire, float(np.abs(
                c3.hauteurs_gradient(gx, gy, 200.0, RAYON)
                - c3.hauteurs(theta, phi, 200.0, RAYON)).max()))
            t2, _ = c3.depuis_gradient(gx, gy)
            pire = max(pire, abs(t2 - theta))
    return pire < 1e-9, f"ecart lineaire / trigonometrique {pire:.3e}"


def butees():
    """Les trois refus attendus, et le cas qui passe."""
    cas = [
        (c3.hauteurs(VISE, 0.0, 300.0, RAYON), True, "pose nominale"),
        (c3.hauteurs(VISE, 0.0, 50.0, RAYON), False, "butee basse"),
        (c3.hauteurs(VISE, 0.0, 560.0, RAYON), False, "butee haute"),
        (c3.hauteurs(38.0, 0.0, 300.0, RAYON), True, "juste sous la butee"),
        (c3.hauteurs(39.0, 0.0, 300.0, RAYON), False, "course differentielle"),
    ]
    details = []
    for h, attendu, nom in cas:
        ok, _ = c3.dans_les_butees(h, 0.0, 610.0, 210.0)
        if ok != attendu:
            return False, f"« {nom} » : attendu {attendu}, obtenu {ok}"
        details.append(nom)
    return True, f"{len(details)} cas conformes"


CONTROLES = [
    ("aller-retour hauteurs <-> pose", aller_retour),
    ("normale du chunk ramenee sur +Z", normale_vers_vertical),
    ("centre du plateau immobile", centre_immobile),
    ("anisotropie 1,5 / racine de 3", anisotropie),
    ("budget de course et reciprocite", budget_de_course),
    ("forme lineaire en gradient", forme_lineaire),
    ("butees hautes, basses, differentielle", butees),
    ("garde sur course insuffisante", garde_de_course),
]


def main():
    print(f"Table a trois verins : R={RAYON:.0f} mm, "
          f"course differentielle {COURSE_DIFF:.0f} mm, vise {VISE:.0f}°\n")
    resultats = []
    for nom, f in CONTROLES:
        ok, detail = f()
        print(f"  {'OK ' if ok else 'ECHEC'}  {nom:<34s} {detail}")
        resultats.append(ok)
    print(f"\n  {sum(resultats)}/{len(resultats)} controles passes")
    return 0 if all(resultats) else 1


if __name__ == "__main__":
    sys.exit(main())
