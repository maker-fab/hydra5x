#!/usr/bin/env python3
"""
Test headless de Fractal Cortex : appelle le coeur de slicing sans le GUI.

Objectif : verifier que la chaine logicielle produit du G-code 5 axes
exploitable, AVANT tout achat de materiel.

Le GUI (pyglet/glooey/OpenGL) n'est pas installe -- seul
`slicing_functions.py` est importe, qui ne depend que de
trimesh/shapely/numpy.
"""
import sys
import traceback
from pathlib import Path

import numpy as np
import trimesh

CORTEX = Path(__file__).parent.parent / "cortex" / "fractal-cortex"
sys.path.insert(0, str(CORTEX))
import slicing_functions as sf  # noqa: E402

OUT = Path(__file__).parent.parent / "results" / "gcode"
OUT.mkdir(parents=True, exist_ok=True)


def print_settings():
    """Les 17 reglages, dans l'ordre positionnel attendu par Cortex.

    ATTENTION : les index 11,12,15,16 passent par bool() -- il faut de vrais
    booleens, pas des chaines ("False" serait evalue a True).
    """
    return [
        210.0,   # 0  nozzleTemp
        215.0,   # 1  initialNozzleTemp
        60.0,    # 2  bedTemp
        60.0,    # 3  initialBedTemp
        20.0,    # 4  infillPercentage (%)
        2,       # 5  shellThickness
        0.2,     # 6  layerHeight
        50.0,    # 7  printSpeed
        25.0,    # 8  initialPrintSpeed
        120.0,   # 9  travelSpeed
        120.0,   # 10 initialTravelSpeed
        False,   # 11 enableZHop
        True,    # 12 enableRetraction
        5.0,     # 13 retractionDistance
        40.0,    # 14 retractionSpeed
        False,   # 15 enableSupports
        False,   # 16 enableBrim
    ]


def make_cube():
    """Cube simple -- smoke test du pipeline."""
    return trimesh.creation.box(extents=(20.0, 20.0, 20.0)).apply_translation((0, 0, 10.0))


def make_y_part(angle=30.0):
    """Piece en Y : tronc vertical + deux bras inclines.

    En 3 axes, les deux bras demandent des supports. C'est le cas qui
    justifie le multidirectionnel.
    """
    stem = trimesh.creation.cylinder(radius=6.0, height=30.0)
    stem.apply_translation((0, 0, 15.0))

    arms = []
    for sign in (+1, -1):
        arm = trimesh.creation.cylinder(radius=5.0, height=30.0)
        arm.apply_translation((0, 0, 15.0))
        rot = trimesh.transformations.rotation_matrix(
            np.radians(angle * sign), [0, 1, 0], point=[0, 0, 30.0]
        )
        arm.apply_transform(rot)
        arms.append(arm)

    part = trimesh.boolean.union([stem] + arms)
    part.apply_translation((0, 0, -part.bounds[0][2]))  # poser sur le plateau
    return part


def run(name, mesh, directions, starts):
    """Lance un slicing et ecrit le G-code. Retourne True si ca a abouti."""
    print(f"\n{'='*60}\n{name}\n{'='*60}")
    print(f"  maillage   : {len(mesh.faces)} faces, watertight={mesh.is_watertight}")
    print(f"  bornes Z   : {mesh.bounds[0][2]:.1f} -> {mesh.bounds[1][2]:.1f} mm")
    print(f"  directions : {len(directions)}  {directions}")

    mesh_data = (["piece"], {"piece": mesh})
    slicing_directions = (len(directions), starts, directions)

    try:
        result = sf.slice_in_5_axes(print_settings(), mesh_data, slicing_directions)
    except Exception:
        print("  ECHEC pendant le slicing :")
        traceback.print_exc()
        return False

    chunk_transforms, adhesion, shells, internal, solid = result
    n_chunks = len(chunk_transforms) if chunk_transforms else 0
    print(f"  chunks     : {n_chunks}")

    out = OUT / f"{name.replace(' ', '_').lower()}.gcode"
    try:
        sf.write_5_axis_gcode(str(out), name, print_settings(), starts, directions, *result)
    except Exception:
        print("  ECHEC pendant l'ecriture du G-code :")
        traceback.print_exc()
        return False

    if not out.exists():
        print("  ECHEC : aucun fichier produit")
        return False

    lines = out.read_text().splitlines()
    rot = [l for l in lines if "MANUAL_STEPPER" in l]
    moves = [l for l in lines if l.startswith("G1 ") and " E" in l]
    print(f"  G-code     : {out.name}  ({len(lines)} lignes, {out.stat().st_size/1024:.1f} Ko)")
    print(f"  extrusions : {len(moves)}")
    print(f"  rotations  : {len(rot)}")
    for l in rot[:4]:
        print(f"      {l}")
    return True


def main():
    ok = []

    # 1) Smoke test : cube, 1 seule direction (equivaut au 3 axes)
    ok.append(run("cube 1 direction", make_cube(),
                  directions=[(0.0, 0.0)],
                  starts=[[0.0, 0.0, 0.0]]))

    # 2) Le vrai test : Y, 3 directions (tronc + 2 bras a 45 deg)
    #    spherical_to_normal(theta, phi) : theta = angle depuis +Z, phi = azimut
    # ATTENTION : cette decoupe aboutit mais n'est PAS imprimable -- la buse
    # percute le tronc. Voir docs/decisions.md D9 et tools/check_collision.py.
    # On la garde comme cas de reference du pipeline, pas comme exemple sain.
    # 30 deg et non 45 : a 45 la garde plateau-buse de 12 mm est violee et
    # Cortex refuse — comportement correct, mais on veut ici une demo qui
    # aboutit. Voir docs/envelope.md pour l'enveloppe mesuree.
    ok.append(run("Y 3 directions", make_y_part(angle=30.0),
                  directions=[(0.0, 0.0), (30.0, 0.0), (30.0, 180.0)],
                  starts=[[0.0, 0.0, 0.0], [0.0, 0.0, 28.0], [0.0, 0.0, 28.0]]))

    print(f"\n{'='*60}")
    print(f"Resultat : {sum(ok)}/{len(ok)} slicings aboutis")
    return 0 if all(ok) else 1


if __name__ == "__main__":
    sys.exit(main())
