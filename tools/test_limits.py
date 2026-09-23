#!/usr/bin/env python3
"""
Caracterise ou Fractal Cortex casse : plusieurs geometries et nombres de
directions, du plus simple au plus complexe.

But : savoir si l'echec du Y vient de MA geometrie ou de la fragilite de
Cortex, et jusqu'ou on peut aller.
"""
import io
import sys
import contextlib
from pathlib import Path

import numpy as np
import trimesh

CORTEX = Path(__file__).parent.parent / "cortex" / "fractal-cortex"
sys.path.insert(0, str(CORTEX))
import slicing_functions as sf  # noqa: E402

SETTINGS = [210.0, 215.0, 60.0, 60.0, 20.0, 2, 0.2, 50.0, 25.0, 120.0, 120.0,
            False, True, 5.0, 40.0, False, False]


def box(sx, sy, sz, at=(0, 0, 0)):
    m = trimesh.creation.box(extents=(sx, sy, sz))
    m.apply_translation(at)
    return m


def on_bed(m):
    m.apply_translation((0, 0, -m.bounds[0][2]))
    return m


def g_cube():
    return on_bed(box(20, 20, 20))


def g_l_shape():
    """L : pied vertical + bras horizontal. Surplomb franc, faces planes."""
    base = box(15, 15, 30, at=(0, 0, 15))
    arm = box(30, 15, 12, at=(15, 0, 36))
    return on_bed(trimesh.boolean.union([base, arm]))


def g_y_cylinders():
    """Y en cylindres : ce qui a echoue au premier test."""
    stem = trimesh.creation.cylinder(radius=6.0, height=30.0)
    stem.apply_translation((0, 0, 15.0))
    arms = []
    for s in (+1, -1):
        a = trimesh.creation.cylinder(radius=5.0, height=30.0)
        a.apply_translation((0, 0, 15.0))
        a.apply_transform(trimesh.transformations.rotation_matrix(
            np.radians(45.0 * s), [0, 1, 0], point=[0, 0, 30.0]))
        arms.append(a)
    return on_bed(trimesh.boolean.union([stem] + arms))


def g_y_boxes():
    """Meme topologie en Y mais en boites : faces planes, pas de courbure."""
    stem = box(12, 12, 30, at=(0, 0, 15))
    arms = []
    for s in (+1, -1):
        a = box(12, 12, 28, at=(0, 0, 14))
        a.apply_transform(trimesh.transformations.rotation_matrix(
            np.radians(45.0 * s), [0, 1, 0], point=[0, 0, 28.0]))
        arms.append(a)
    return on_bed(trimesh.boolean.union([stem] + arms))


CASES = [
    ("cube / 1 direction", g_cube,
     [(0.0, 0.0)], [[0, 0, 0]]),
    ("cube / 2 directions", g_cube,
     [(0.0, 0.0), (30.0, 0.0)], [[0, 0, 0], [0, 0, 10.0]]),
    ("L boites / 1 direction", g_l_shape,
     [(0.0, 0.0)], [[0, 0, 0]]),
    ("L boites / 2 directions", g_l_shape,
     [(0.0, 0.0), (45.0, 0.0)], [[0, 0, 0], [0, 0, 28.0]]),
    ("Y boites / 3 directions", g_y_boxes,
     [(0.0, 0.0), (45.0, 0.0), (45.0, 180.0)], [[0, 0, 0], [0, 0, 26.0], [0, 0, 26.0]]),
    ("Y cylindres / 3 directions", g_y_cylinders,
     [(0.0, 0.0), (45.0, 0.0), (45.0, 180.0)], [[0, 0, 0], [0, 0, 28.0], [0, 0, 28.0]]),
]


def main():
    print(f"{'cas':<30} {'maillage':<12} {'resultat'}")
    print("-" * 78)
    results = []
    for name, geom_fn, directions, starts in CASES:
        try:
            mesh = geom_fn()
        except Exception as e:
            print(f"{name:<30} {'--':<12} maillage impossible: {type(e).__name__}")
            results.append(False)
            continue

        info = f"{len(mesh.faces)}f"
        buf = io.StringIO()
        try:
            # Cortex ecrit beaucoup sur stdout -- on le capture
            with contextlib.redirect_stdout(buf):
                res = sf.slice_in_5_axes(
                    SETTINGS, (["p"], {"p": mesh}),
                    (len(directions), starts, directions))
                out = Path(__file__).parent.parent / "results" / "gcode" / f"lim_{len(results)}.gcode"
                out.parent.mkdir(parents=True, exist_ok=True)
                sf.write_5_axis_gcode(str(out), name, SETTINGS, starts, directions, *res)
            n = len(out.read_text().splitlines())
            ext = sum(1 for l in out.read_text().splitlines()
                      if l.startswith("G1 ") and " E" in l)
            print(f"{name:<30} {info:<12} OK  ({n} lignes, {ext} extrusions)")
            results.append(True)
        except Exception as e:
            print(f"{name:<30} {info:<12} ECHEC  {type(e).__name__}: {e}")
            results.append(False)

    print("-" * 78)
    print(f"{sum(results)}/{len(results)} cas aboutis")
    return 0


if __name__ == "__main__":
    sys.exit(main())
