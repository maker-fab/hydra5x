#!/usr/bin/env python3
"""Teste la reorientation progressive des bras du Y.

Le balayage a un seul plan par bras (`sweep_decomposition.py`) ne trouve
aucune decoupe imprimable : le tronc se dresse a moins d'un millimetre de
la base du bras. Multiplier les tranches sans changer l'angle ne servirait
a rien -- la premiere tranche contiendrait toujours la jonction, donc la
meme collision.

L'hypothese testee ici est differente : **monter l'angle par paliers**. Au
lieu d'un saut unique de 0 a theta, passer par theta/N, 2*theta/N, ...,
theta. Chaque tranche se depose sur la precedente, dont l'orientation est
proche, et le tronc ne surplombe que d'un palier au lieu de l'angle total.

Ordre des chunks : tronc, puis les tranches du bras +, puis celles du
bras -. Le ciselage de Cortex soustrait les chunks ulterieurs, donc cet
ordre determine qui perd le recouvrement.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).parent))
from export_chunks import decouper, spherical_to_normal, transform_a_plat  # noqa: E402
from sweep_decomposition import penetration_max, VOLUME_MINI  # noqa: E402


def pivot_du_y(piece):
    """Point d'articulation des bras, dans le repere de la piece posee.

    `make_y_part` fait tourner les bras autour de (0, 0, 30) puis translate
    la piece pour la poser sur le plateau ; le pivot suit cette translation.
    """
    return np.array([0.0, 0.0, 30.0 + piece.bounds[0][2]])


def plan_progressif(theta, n_paliers, t_debut, t_fin, pivot):
    """Directions et origines pour une montee en angle par paliers.

    Chaque plan est PERPENDICULAIRE a sa direction d'impression et pose le
    long du bras, a `pivot - n * t` : les bras descendent depuis le pivot,
    donc t se mesure vers le bas.

    Garder les origines sur l'axe Z -- l'erreur du premier jet -- produisait
    des eclats de quelques mm3 au lieu de tranches : la normale s'inclinait
    mais pas le point de passage.
    """
    directions = [(0.0, 0.0)]
    departs = [[0.0, 0.0, 0.0]]
    ts = np.linspace(t_debut, t_fin, n_paliers)
    for phi in (0.0, 180.0):
        for i in range(n_paliers):
            angle = theta * (i + 1) / n_paliers
            n = spherical_to_normal(angle, phi)
            directions.append((angle, phi))
            departs.append(list(np.asarray(pivot, dtype=float) - n * ts[i]))
    return directions, departs


def evaluer(theta, n_paliers, t_debut, t_fin, alpha, rayon):
    from test_slice import make_y_part
    piece = make_y_part(angle=theta)
    directions, departs = plan_progressif(theta, n_paliers, t_debut, t_fin,
                                          pivot_du_y(piece))
    try:
        chunks = decouper(piece, directions, departs)
    except Exception as e:
        return None, f"decoupe impossible : {e}"

    utiles = [c.volume for c in chunks[1:] if c is not None]
    if not utiles or max(utiles) < VOLUME_MINI * piece.volume:
        return None, "degeneree"

    pire, ou = 0.0, None
    for k in range(1, len(chunks)):
        if chunks[k] is None:
            continue
        precedents = [c for j, c in enumerate(chunks) if j < k and c is not None]
        if not precedents:
            continue
        T = transform_a_plat(chunks[k], spherical_to_normal(*directions[k]))
        poses = []
        for m in precedents:
            c = m.copy()
            c.apply_transform(T)
            poses.append(c)
        courant = chunks[k].copy()
        courant.apply_transform(T)
        p, o = penetration_max(trimesh.util.concatenate(poses), courant,
                               alpha, rayon)
        if p > pire:
            pire, ou = p, o
    return pire, ou


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--theta", type=float, default=30.0)
    ap.add_argument("--paliers", type=int, nargs="+", default=[1, 2, 3, 4])
    ap.add_argument("--t-debut", type=float, nargs="+", default=[1.0, 3.0, 5.0],
                    help="distance du premier plan sous le pivot, mm")
    ap.add_argument("--t-fin", type=float, default=0.5,
                    help="distance du dernier plan sous le pivot, mm")
    ap.add_argument("--alpha", type=float, default=45.0)
    ap.add_argument("--rayon", type=float, default=15.0)
    args = ap.parse_args()

    print(f"Bras a {args.theta:.0f} deg, cone {args.alpha:.0f} deg, "
          f"dernier plan a {args.t_fin:.1f} mm sous le pivot")
    print(f"  {'paliers':>8s}" + "".join(f"{t:>10.1f}" for t in args.t_debut)
          + "   <- premier plan, mm sous le pivot")
    bons = []
    for n in args.paliers:
        ligne = f"  {n:8d}"
        for z0 in args.t_debut:
            pire, info = evaluer(args.theta, n, z0, args.t_fin,
                                 args.alpha, args.rayon)
            if pire is None:
                ligne += f"{info[:9]:>10s}"
            else:
                ligne += f"{pire:10.2f}"
                if pire <= 0.0:
                    bons.append((n, z0))
        print(ligne)
    print("\n  penetration max en mm ; 0.00 = aucune collision")
    print(f"  sans collision : {bons if bons else 'aucune'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
