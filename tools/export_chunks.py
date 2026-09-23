#!/usr/bin/env python3
"""Exporte les chunks d'une decoupe multidirectionnelle en STL poses a plat.

Interet : un chunk aligne sur XY est une piece 3 axes ordinaire. N'importe
quel slicer mature (OrcaSlicer, PrusaSlicer) sait la trancher, avec ses
perimetres, ses supports et ses profils machine. Cet outil est le pont
entre la decomposition multidirectionnelle et ces slicers.

La decomposition reproduit exactement celle de `create_chunkList()` dans
slicing_functions.py : intersection avec un demi-espace, puis soustraction
de tous les chunks ulterieurs. Le controle de coherence en fin de course
verifie que la somme des volumes retombe sur le volume d'origine -- si la
reproduction divergeait, la comparaison de G-code qui suit n'aurait aucun
sens.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import trimesh

TOLERANCE_VOLUME = 0.01  # 1 %


def spherical_to_normal(theta, phi):
    """Copie conforme de slicing_functions.py:800.

    La fonction y est imbriquee dans all_5_axis_calculations(), donc non
    importable, et elle est deja dupliquee dans widget_functions.py:541.
    La remonter au niveau module dans le fork supprimerait la triplication
    -- a faire, mais pas dans ce test, qui doit rester a diff minimal.
    """
    theta = theta * (np.pi / 180.0)
    phi = phi * (np.pi / 180.0)
    return np.array([np.sin(theta) * np.cos(phi),
                     np.sin(theta) * np.sin(phi),
                     np.cos(theta)])


def demi_espace(maillage, point, normale):
    """Partie du maillage situee du cote +normale du plan."""
    cote = float(np.linalg.norm(maillage.extents)) * 3.0
    boite = trimesh.creation.box(extents=(cote, cote, cote))
    boite.apply_translation((0.0, 0.0, cote / 2.0))      # face -Z sur le plan
    boite.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], normale))
    boite.apply_translation(point)
    return maillage.intersection(boite)


def decouper(maillage, directions, departs):
    """Reproduit create_chunkList() de Cortex."""
    chunks = []
    for depart, direction in zip(departs, directions):
        normale = np.asarray(spherical_to_normal(*direction), dtype=float)
        morceau = demi_espace(maillage, np.asarray(depart, dtype=float), normale)
        if morceau.is_empty or len(morceau.faces) == 0:
            raise RuntimeError(
                f"intersection vide pour la direction {direction} au depart {depart}"
            )
        chunks.append(morceau)

    # Chaque chunk perd ce que les chunks ulterieurs occupent deja.
    for k in range(len(chunks)):
        reste = chunks[k]
        for r in range(len(chunks) - 1, k, -1):
            if chunks[r] is not None:
                reste = reste.difference(chunks[r], check_volume=False)
        chunks[k] = None if reste.is_empty else reste
    return chunks


def transform_a_plat(morceau, normale):
    """Matrice qui pose le chunk comme il sera imprime.

    Rendue separement de `poser_a_plat` parce que le test de collision doit
    appliquer la MEME transformation aux chunks precedents : c'est ce qui
    les remet en position relative correcte dans le repere du chunk courant.
    """
    rot = trimesh.geometry.align_vectors(normale, [0, 0, 1])
    sonde = morceau.copy()
    sonde.apply_transform(rot)
    centre = sonde.bounds.mean(axis=0)
    dep = trimesh.transformations.translation_matrix(
        (-centre[0], -centre[1], -sonde.bounds[0][2]))
    return dep @ rot


def poser_a_plat(morceau, normale):
    """Oriente le chunk comme il sera imprime : plan de coupe sur le plateau."""
    pose = morceau.copy()
    pose.apply_transform(transform_a_plat(morceau, normale))
    return pose


def controler(maillage, chunks):
    """La somme des chunks doit rendre le volume d'origine."""
    total = sum(c.volume for c in chunks if c is not None)
    ecart = abs(total - maillage.volume) / maillage.volume
    etat = "OK" if ecart < TOLERANCE_VOLUME else "ECART"
    print(f"  volume piece   : {maillage.volume:10.1f} mm3")
    print(f"  somme chunks   : {total:10.1f} mm3   ecart {ecart*100:.2f} %  [{etat}]")
    if ecart >= TOLERANCE_VOLUME:
        raise RuntimeError(
            f"la decomposition perd {ecart*100:.1f} % du volume -- "
            "elle ne reproduit pas celle de Cortex, comparaison invalide"
        )


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=Path("results/chunks"),
                    help="dossier de sortie des STL")
    ap.add_argument("--angle", type=float, default=30.0,
                    help="inclinaison des bras du Y, en degres")
    args = ap.parse_args()

    sys.path.insert(0, str(Path(__file__).parent))
    from test_slice import make_y_part

    piece = make_y_part(angle=args.angle)
    directions = [(0.0, 0.0), (30.0, 0.0), (30.0, 180.0)]
    departs = [[0.0, 0.0, 0.0], [0.0, 0.0, 28.0], [0.0, 0.0, 28.0]]

    print(f"Piece en Y, bras a {args.angle} deg : {len(piece.faces)} faces")
    chunks = decouper(piece, directions, departs)
    controler(piece, chunks)

    args.out.mkdir(parents=True, exist_ok=True)
    print()
    for k, (morceau, direction) in enumerate(zip(chunks, directions)):
        if morceau is None:
            print(f"  chunk {k} : vide, ignore")
            continue
        normale = np.asarray(spherical_to_normal(*direction), dtype=float)
        pose = poser_a_plat(morceau, normale)
        chemin = args.out / f"chunk_{k}_theta{direction[0]:.0f}_phi{direction[1]:.0f}.stl"
        pose.export(chemin)
        l, p, h = pose.extents
        print(f"  {chemin.name}")
        print(f"      {len(pose.faces):5d} faces  {pose.volume:8.1f} mm3  "
              f"encombrement {l:.1f} x {p:.1f} x {h:.1f} mm  "
              f"etanche={pose.is_watertight}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
