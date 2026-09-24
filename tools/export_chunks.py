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


VOLUME_ECLAT = 1e-6   # fraction du volume du chunk sous laquelle une
                      # composante est un artefact booleen


def nettoyer(morceau, seuil=VOLUME_ECLAT):
    """Retire les fragments de volume nul laisses par les differences.

    Les operations booleennes de manifold3d deposent des eclats de volume
    nul -- quelques facettes, disperses n'importe ou dans la piece. Ils ne
    changent pas le volume du chunk mais ils etendent sa boite englobante
    a toute la piece, et surtout ils apparaissent dans toute carte de
    hauteurs ou tout lancer de rayons. Un test de collision qui les voit
    mesure des artefacts.
    """
    if morceau is None or morceau.is_empty:
        return morceau
    composantes = morceau.split(only_watertight=False)
    if len(composantes) <= 1:
        return morceau
    total = abs(morceau.volume)
    gardees = [c for c in composantes if abs(c.volume) > seuil * max(total, 1e-9)]
    if not gardees:
        return morceau
    return trimesh.util.concatenate(gardees) if len(gardees) > 1 else gardees[0]


def decouper(maillage, directions, departs, mode="cortex"):
    """Decompose le maillage en chunks.

    `mode="cortex"` reproduit create_chunkList() : chunk k = demi-espace k
    moins TOUS les demi-espaces ulterieurs. Quand les plans ne sont pas
    emboites -- des qu'ils s'inclinent le long d'une courbe -- la matiere
    qu'aucun plan ulterieur ne reclame retombe dans le chunk 0. Sur une
    piece massive celui-ci herite des coins hauts et se dresse ensuite a
    cote de tous les suivants (voir decisions.md D13).

    `mode="tranches"` -- chunk k = demi-espace k moins demi-espace k+1 --
    EST INVALIDE des que les plans s'inclinent : un plan incline passe sous
    le precedent, donc les chunks se recouvrent et de la matiere serait
    deposee deux fois. Mesure sur le bloc a canal : 56 720 mm3 pour une
    piece de 53 340. Conserve uniquement pour documenter l'impasse ; le
    mode "cortex" est la seule partition correcte.
    """
    chunks = []
    for depart, direction in zip(departs, directions):
        normale = np.asarray(spherical_to_normal(*direction), dtype=float)
        morceau = demi_espace(maillage, np.asarray(depart, dtype=float), normale)
        if morceau.is_empty or len(morceau.faces) == 0:
            raise RuntimeError(
                f"intersection vide pour la direction {direction} au depart {depart}"
            )
        chunks.append(morceau)

    bruts = list(chunks)
    for k in range(len(chunks)):
        reste = bruts[k]
        ulterieurs = ([bruts[k + 1]] if mode == "tranches" and k + 1 < len(bruts)
                      else list(reversed(bruts[k + 1:])))
        for suivant in ulterieurs:
            if suivant is not None and not suivant.is_empty:
                reste = reste.difference(suivant, check_volume=False)
        chunks[k] = None if reste.is_empty else nettoyer(reste)
    return chunks


def decalage_a_plat(morceau, normale):
    """Translation que `transform_a_plat` retire au chunk, en mm.

    Poser un chunk a plat le recentre en XY et pose son plan de coupe a
    z=0. **Chaque chunk subit donc une translation differente**, et les
    G-code qui en sortent ne sont plus dans un repere commun.

    Sur la machine, incliner le plateau est l'operation inverse de poser a
    plat : les coordonnees du G-code sont donc les bonnes, **a cette
    translation pres**. La rendre permet de la remettre, au lieu de
    decouvrir le decalage apres coup.
    """
    rot = trimesh.geometry.align_vectors(normale, [0, 0, 1])
    sonde = morceau.copy()
    sonde.apply_transform(rot)
    centre = sonde.bounds.mean(axis=0)
    return np.array([centre[0], centre[1], sonde.bounds[0][2]])


def transform_a_plat(morceau, normale):
    """Matrice qui pose le chunk comme il sera imprime.

    Rendue separement de `poser_a_plat` parce que le test de collision doit
    appliquer la MEME transformation aux chunks precedents : c'est ce qui
    les remet en position relative correcte dans le repere du chunk courant.
    """
    rot = trimesh.geometry.align_vectors(normale, [0, 0, 1])
    d = decalage_a_plat(morceau, normale)
    return trimesh.transformations.translation_matrix(-d) @ rot


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
