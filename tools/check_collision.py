#!/usr/bin/env python3
"""Detecte les collisions entre la buse et la matiere deja imprimee.

Ce test n'existe nulle part ailleurs : Cortex ne le fait pas, et aucun
slicer 3 axes ne peut le faire puisqu'il ignore que le plateau s'incline.

Ce qui rend le probleme tractable : pendant l'impression d'un chunk, le
plateau ne bouge pas. Dans le repere de ce chunk, tout ce qui est deja
imprime est un solide fixe. Le test redevient statique et purement
geometrique -- aucune cinematique n'intervient.

Modele de buse. La buse n'est pas un point : au-dessus de la pointe il y a
le cone puis le bloc chauffant, et c'est ce volume qui percute. On le
resume par une hauteur de garde requise en fonction de la distance
horizontale :

    h(r) = r / tan(alpha)      pour r <= rayon_max

La matiere situee a distance r de la pointe doit rester sous
`z_pointe + h(r)`. La garde de 12 mm codee en dur dans Cortex devient
ainsi une consequence du modele, au lieu d'une constante magique.

Approximation assumee : la matiere deja imprimee est ramenee a une carte
de hauteurs (max Z par cellule). C'est exact pour une surface vue d'en
haut, et pessimiste sous un surplomb -- ou la carte retient le point haut
alors que la buse pourrait passer dessous. Un faux positif est acceptable
ici, un faux negatif ne le serait pas.
"""
import argparse
import re
import sys
from pathlib import Path

import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).parent))
from export_chunks import decouper, spherical_to_normal, transform_a_plat  # noqa: E402

PAS_GRILLE = 0.5        # mm
N_ECHANTILLONS = 300_000


def carte_hauteurs(maillage, pas=PAS_GRILLE):
    """Carte des hauteurs max, echantillonnee en surface puis dilatee.

    La dilatation d'une cellule garantit qu'aucun sommet ne tombe entre
    deux mailles : mieux vaut surestimer la matiere que la manquer.
    """
    pts = np.vstack([maillage.vertices, maillage.sample(N_ECHANTILLONS)])
    x0, y0 = pts[:, 0].min() - pas, pts[:, 1].min() - pas
    ix = ((pts[:, 0] - x0) / pas).astype(int)
    iy = ((pts[:, 1] - y0) / pas).astype(int)
    grille = np.full((ix.max() + 2, iy.max() + 2), -np.inf)
    np.maximum.at(grille, (ix, iy), pts[:, 2])
    dilatee = grille.copy()
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        dilatee = np.maximum(dilatee, np.roll(np.roll(grille, dx, 0), dy, 1))
    return dilatee, x0, y0, pas


def disque(rayon, pas, alpha_deg):
    """Offsets de cellules, distance et garde requise a chaque offset.

    `alpha` et `rayon` ne sont pas independants : le rayon decrit jusqu'ou
    le corps de buse s'etend, et la garde qu'il impose a cette distance
    vaut rayon/tan(alpha). Un alpha proche de 90 deg avec un grand rayon
    decrit un disque plat au niveau de la pointe -- physiquement absurde.
    """
    n = int(np.ceil(rayon / pas))
    dx, dy = np.mgrid[-n:n + 1, -n:n + 1]
    d = np.hypot(dx, dy) * pas
    dedans = d <= rayon
    return dx[dedans], dy[dedans], d[dedans], d[dedans] / np.tan(np.radians(alpha_deg))


def trajets_par_chunk(gcode):
    """Points (X, Y, Z) par chunk, lus dans le G-code produit.

    Seul le marqueur de CORPS est retenu. Celui de reorientation porte le
    meme numero de chunk, et l'avaler ferait entrer la position de
    degagement (X0 Y-175) dans les trajets -- elle fausse ensuite le
    recalage de repere.
    """
    chunks, courant = {}, None
    pos = {"X": 0.0, "Y": 0.0, "Z": 0.0}
    e_precedent, absolu = 0.0, True
    for ligne in Path(gcode).read_text().splitlines():
        # Deux formats : celui de stitch_chunks.py et celui de Cortex
        # (";Chunk 0"). Sans ca le fichier de Cortex ne serait pas analyse
        # du tout, et l'absence de collision viendrait de l'absence de test.
        entete = (re.match(r";\s*-+\s*chunk (\d+)\s*:\s*\d+\s+lignes",
                           ligne.strip(), re.I)
                  or re.match(r";\s*chunk\s+(\d+)\s*$", ligne.strip(), re.I))
        if entete:
            k = int(entete.group(1))
            courant = chunks.setdefault(k, [])
            continue
        if re.match(r";\s*-+\s*chunk \d+\s*:\s*reorientation", ligne.strip(), re.I):
            courant = None
            continue
        nu = ligne.split(";")[0].strip()
        if nu.startswith("M83"):
            absolu = False
        elif nu.startswith("M82"):
            absolu = True
        elif re.match(r"^G92\b", nu) and " E" in f" {nu}":
            e_precedent = 0.0
        if not re.match(r"^G[01]\b", nu):
            continue
        for axe, val in re.findall(r"([XYZ])(-?\d*\.?\d+)", nu):
            pos[axe] = float(val)
        me = re.search(r"\bE(-?\d*\.?\d+)", nu)
        extrude = False
        if me:
            e = float(me.group(1))
            de = (e - e_precedent) if absolu else e
            e_precedent = e if absolu else e_precedent + e
            extrude = de > 0
        if courant is not None:
            courant.append((pos["X"], pos["Y"], pos["Z"], float(extrude)))
    return {k: np.array(v) for k, v in chunks.items() if len(v)}


def reperes_publies(gcode):
    """Centres XY publies par le producteur du G-code, s'il en publie."""
    out = {}
    for ligne in Path(gcode).read_text().splitlines():
        m = re.match(r";\s*HYDRA5X_REPERE\s+chunk=(\d+)\s+cx=(-?[\d.]+)\s+cy=(-?[\d.]+)",
                     ligne.strip())
        if m:
            out[int(m.group(1))] = (float(m.group(2)), float(m.group(3)))
    return out


def recaler(points, chunk_pose, centre_publie=None):
    """Ramene les trajets dans le repere du maillage.

    Le slicer externe centre la piece sur SON plateau -- PrusaSlicer la
    pose vers X100 Y100 -- alors que les chunks sont centres sur l'origine.
    Sans ce recalage le test compare deux regions disjointes et ne trouve
    jamais rien : un faux negatif silencieux, le pire resultat possible
    pour un detecteur de collision.
    """
    # Seuls les points d'EXTRUSION servent de reference : ils sont toujours
    # sur la piece. Les deplacements de degagement (parking a Y-175) et les
    # approches en altitude fausseraient le centre, et un mauvais recalage
    # rend le test aveugle sans rien signaler.
    sur_piece = points[points[:, 3] > 0][:, :2]
    if len(sur_piece) == 0:
        raise RuntimeError("aucun point d'extrusion : recalage impossible")
    c_gcode = (sur_piece.min(axis=0) + sur_piece.max(axis=0)) / 2.0
    if centre_publie is not None:
        c_mesh = np.asarray(centre_publie, dtype=float)
    else:
        b = chunk_pose.bounds
        c_mesh = (b[0][:2] + b[1][:2]) / 2.0
    decalage = c_mesh - c_gcode
    recales = points[:, :3].copy()
    recales[:, :2] += decalage
    return recales, decalage


def tester_chunk(deja_imprime, points, alpha, rayon):
    """Retourne la pire penetration, en mm, et ou elle se produit."""
    grille, x0, y0, pas = carte_hauteurs(deja_imprime)
    dx, dy, dist, garde = disque(rayon, pas, alpha)
    nx, ny = grille.shape
    pire, ou, contact = 0.0, None, None
    for x, y, z in points:
        cx = int((x - x0) / pas)
        cy = int((y - y0) / pas)
        ix, iy = cx + dx, cy + dy
        ok = (ix >= 0) & (ix < nx) & (iy >= 0) & (iy < ny)
        if not ok.any():
            continue
        hauteurs = grille[ix[ok], iy[ok]]
        depassement = hauteurs - (z + garde[ok])
        i = int(depassement.argmax())
        if depassement[i] > pire:
            pire = float(depassement[i])
            ou = (float(x), float(y), float(z))
            contact = (float(dist[ok][i]), float(hauteurs[i]))
    return pire, ou, contact


def confirmer(deja_imprime, point, alpha, rayon, n_rayons=72):
    """Recontrole le pire point par lancer de rayons sur le maillage reel.

    La carte de hauteurs depiste vite mais approxime : la dilatation
    deplace une valeur haute d'une cellule, ce qui fausse la distance
    rapportee. Le lancer de rayons n'approxime rien -- il interroge la
    geometrie. On l'emploie seulement sur le pire point, ou son cout est
    negligeable.
    """
    cx, cy, cz = point
    pire, detail = 0.0, None
    for r in np.linspace(0.25, rayon, int(rayon * 4)):
        angles = np.linspace(0, 2 * np.pi, n_rayons, endpoint=False)
        origines = np.column_stack([cx + r * np.cos(angles),
                                    cy + r * np.sin(angles),
                                    np.full(n_rayons, cz - 100.0)])
        directions = np.tile([0.0, 0.0, 1.0], (n_rayons, 1))
        loc, idx, _ = deja_imprime.ray.intersects_location(origines, directions)
        if not len(loc):
            continue
        h = float(loc[:, 2].max())
        depassement = h - (cz + r / np.tan(np.radians(alpha)))
        if depassement > pire:
            pire, detail = depassement, (float(r), h)
    return pire, detail


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("gcode", type=Path, help="G-code 5 axes a verifier")
    ap.add_argument("--alpha", type=float, default=45.0,
                    help="demi-angle du cone de buse, en degres")
    ap.add_argument("--rayon", type=float, default=15.0,
                    help="rayon au-dela duquel la buse ne peut plus toucher, mm")
    ap.add_argument("--angle", type=float, default=30.0,
                    help="inclinaison des bras du Y")
    ap.add_argument("--tolerance", type=float, default=0.0,
                    help="penetration toleree avant echec, mm")
    args = ap.parse_args()

    from test_slice import make_y_part
    piece = make_y_part(angle=args.angle)
    directions = [(0.0, 0.0), (30.0, 0.0), (30.0, 180.0)]
    departs = [[0.0, 0.0, 0.0], [0.0, 0.0, 28.0], [0.0, 0.0, 28.0]]
    chunks = decouper(piece, directions, departs)
    trajets = trajets_par_chunk(args.gcode)
    reperes = reperes_publies(args.gcode)
    if not reperes:
        print("  ATTENTION : ce G-code ne publie pas son repere "
              "(; HYDRA5X_REPERE). Le recalage est deduit de l'emprise des\n"
              "  trajets d'extrusion -- approximation non verifiable. Un\n"
              "  verdict 'pas de collision' obtenu ainsi n'engage a rien.\n")
    if not trajets:
        raise RuntimeError(
            f"aucun marqueur de chunk trouve dans {args.gcode.name} : rien "
            "n'a ete analyse. Un verdict 'pas de collision' obtenu sans "
            "rien tester serait un faux negatif."
        )

    print(f"Modele de buse : cone a {args.alpha:.0f} deg, rayon utile "
          f"{args.rayon:.0f} mm")
    print(f"  garde requise a 5 mm : {5/np.tan(np.radians(args.alpha)):.1f} mm"
          f"   a 12 mm : {12/np.tan(np.radians(args.alpha)):.1f} mm")
    print(f"G-code : {args.gcode.name}\n")

    echecs = 0
    for k in sorted(trajets):
        if k == 0:
            print(f"  chunk 0 : rien d'imprime avant, sans objet")
            continue
        precedents = [c for j, c in enumerate(chunks) if j < k and c is not None]
        if not precedents:
            continue
        # MEME transformation que celle qui pose le chunk courant : c'est
        # ce qui remet les chunks precedents a leur place relative reelle.
        T = transform_a_plat(chunks[k], spherical_to_normal(*directions[k]))
        poses = []
        for morceau in precedents:
            copie = morceau.copy()
            copie.apply_transform(T)
            poses.append(copie)
        deja = trimesh.util.concatenate(poses)
        courant = chunks[k].copy()
        courant.apply_transform(T)
        pts, decalage = recaler(trajets[k], courant, reperes.get(k))
        pire, ou, contact = tester_chunk(deja, pts, args.alpha, args.rayon)
        etat = "OK" if pire <= args.tolerance else "COLLISION"
        source = "publie" if k in reperes else "deduit"
        print(f"  chunk {k} : {len(pts)} points, recalage {source} "
              f"({decalage[0]:+.1f}, {decalage[1]:+.1f}) mm, "
              f"penetration max {pire:7.3f} mm   [{etat}]")
        if ou:
            print(f"      buse en X{ou[0]:.2f} Y{ou[1]:.2f} Z{ou[2]:.2f}")
            vrai, det = confirmer(deja, ou, args.alpha, args.rayon)
            if det:
                print(f"      confirme par lancer de rayons : matiere a "
                      f"{det[0]:.2f} mm, haute de {det[1]:.2f} mm, "
                      f"garde requise {det[0]/np.tan(np.radians(args.alpha)):.2f} mm")
                print(f"      penetration confirmee : {vrai:.3f} mm")
            else:
                print("      lancer de rayons : aucun contact -- "
                      "la carte de hauteurs a surestime")
        if pire > args.tolerance:
            echecs += 1

    print(f"\n  {echecs} chunk(s) en collision")
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main())
