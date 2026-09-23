#!/usr/bin/env python3
"""Pieces de test, et leurs decoupes multidirectionnelles.

Le Y de `test_slice.py` appartient a la famille que cette cinematique ne
sait pas faire : une branche part du milieu d'une forme plus haute, donc
le tronc depasse toujours le plan de base du bras (voir decisions.md D10).

Le coude est de l'autre famille. Son axe tourne de facon monotone : a
chaque reorientation, ce qui est deja imprime reste sous le plan de base
du chunk suivant. C'est la condition qui rend le multidirectionnel
possible -- restaurer l'invariant du 3 axes, buse au-dessus de tout.
"""
import numpy as np
import trimesh


def coude(rayon_tube=6.0, rayon_courbure=30.0, angle_total=90.0,
          base=12.0, segments=64, facettes=32):
    """Tube coude : montee droite, puis virage jusqu'a l'horizontale.

    En 3 axes la partie couchee est un surplomb franc et demande du
    support. En multidirectionnel elle s'imprime a plat, chunk par chunk.
    """
    chemin = [np.array([0.0, 0.0, z]) for z in np.linspace(0.0, base, 6)]
    centre = np.array([rayon_courbure, 0.0, base])
    for a in np.linspace(0.0, np.radians(angle_total), segments)[1:]:
        chemin.append(centre + np.array([-rayon_courbure * np.cos(a), 0.0,
                                         rayon_courbure * np.sin(a)]))
    chemin = np.array(chemin)

    cercle = trimesh.path.creation.circle(radius=rayon_tube,
                                          segments=facettes).polygons_full[0]
    maillage = trimesh.creation.sweep_polygon(cercle, chemin, cap=True)
    maillage.apply_translation((0.0, 0.0, -maillage.bounds[0][2]))
    return maillage


def bloc_a_canal(rayon_canal=5.0, rayon_courbure=25.0, angle_total=90.0,
                 base=10.0, marge=7.0, segments=48, facettes=28):
    """Bloc massif traverse d'un canal coude.

    Le cas ou le multidirectionnel n'est pas un gain marginal mais binaire :
    en 3 axes le toit du canal est en surplomb, le support se depose a
    l'interieur, et il n'y a aucun moyen de l'en sortir. La piece est donc
    irrecevable, pas juste plus chere.
    """
    chemin = [np.array([0.0, 0.0, z]) for z in np.linspace(-marge, base, 6)]
    centre = np.array([rayon_courbure, 0.0, base])
    for a in np.linspace(0.0, np.radians(angle_total), segments)[1:]:
        chemin.append(centre + np.array([-rayon_courbure * np.cos(a), 0.0,
                                         rayon_courbure * np.sin(a)]))
    # prolonge la sortie pour percer franchement la paroi
    sortie = chemin[-1] - chemin[-2]
    chemin.append(chemin[-1] + sortie / np.linalg.norm(sortie) * marge)
    chemin = np.array(chemin)

    cercle = trimesh.path.creation.circle(radius=rayon_canal,
                                          segments=facettes).polygons_full[0]
    canal = trimesh.creation.sweep_polygon(cercle, chemin, cap=True)

    bmin, bmax = canal.bounds
    bmin = bmin - marge
    bmax = bmax + marge
    bmin[2] = 0.0                      # le bloc repose sur le plateau
    bmax[2] = canal.bounds[1][2] + marge
    bloc = trimesh.creation.box(extents=(bmax - bmin))
    bloc.apply_translation((bmin + bmax) / 2.0)

    piece = bloc.difference(canal)
    piece.apply_translation((0.0, 0.0, -piece.bounds[0][2]))
    return piece


def axe_du_coude(rayon_courbure=30.0, angle_total=90.0, base=12.0, n=64):
    """Points et tangentes le long de l'axe, pour poser les plans de coupe."""
    centre = np.array([rayon_courbure, 0.0, base])
    pts, tangentes = [], []
    for a in np.linspace(0.0, np.radians(angle_total), n):
        pts.append(centre + np.array([-rayon_courbure * np.cos(a), 0.0,
                                      rayon_courbure * np.sin(a)]))
        # tangente : derivee du parametrage, orientee vers l'avant du tube
        tangentes.append(np.array([np.sin(a), 0.0, np.cos(a)]))
    return np.array(pts), np.array(tangentes)


def normal_to_spherical(n):
    """Inverse de spherical_to_normal : vecteur unitaire -> (theta, phi) en degres."""
    n = np.asarray(n, dtype=float)
    n = n / np.linalg.norm(n)
    theta = np.degrees(np.arccos(np.clip(n[2], -1.0, 1.0)))
    phi = np.degrees(np.arctan2(n[1], n[0]))
    return float(theta), float(phi)


def decoupe_coude(n_chunks, rayon_courbure=30.0, angle_total=90.0,
                  base=12.0, z_offset=0.0):
    """Directions et origines pour decouper le coude en n_chunks blocs.

    Les plans sont perpendiculaires a l'axe du tube, repartis le long du
    virage. Le premier chunk est la montee droite : direction verticale,
    plan au niveau du plateau.
    """
    pts, tangentes = axe_du_coude(rayon_courbure, angle_total, base,
                                  n=max(n_chunks, 2))
    directions = [(0.0, 0.0)]
    departs = [[0.0, 0.0, 0.0]]
    indices = np.linspace(0, len(pts) - 1, n_chunks + 1).astype(int)[1:]
    for i in indices:
        theta, phi = normal_to_spherical(tangentes[i])
        directions.append((theta, phi))
        origine = pts[i].copy()
        origine[2] -= z_offset
        departs.append(list(origine))
    return directions, departs


if __name__ == "__main__":
    m = coude()
    print(f"  coude : {len(m.faces)} faces, {m.volume:.1f} mm3, "
          f"etanche={m.is_watertight}")
    print(f"  encombrement : " +
          " x ".join(f"{v:.1f}" for v in m.extents) + " mm")
    d, dp = decoupe_coude(4)
    for i, (dd, pp) in enumerate(zip(d, dp)):
        print(f"    chunk {i} : theta={dd[0]:6.1f} phi={dd[1]:6.1f} "
              f"origine ({pp[0]:6.2f}, {pp[1]:5.2f}, {pp[2]:6.2f})")
