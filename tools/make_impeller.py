#!/usr/bin/env python3
"""
Genere une roue radiale ouverte (open radial impeller) parametrique.

Geometrie typique de pompe centrifuge : moyeu central, disque de base, et
N aubes a courbure arriere rayonnant vers l'exterieur. Ouverte sur le
dessus (pas de flasque).

C'est le cas d'usage le plus exigeant identifie pour Cortex : la buse doit
imprimer entre des aubes deja posees, or Cortex ne teste QUE les collisions
buse-plateau, jamais buse-piece.
"""
import numpy as np
import trimesh
from shapely.geometry import Polygon


def blade_polygon(r_in, r_out, sweep_deg, thickness, phase_deg, n=40):
    """Aube a courbure arriere, vue en plan : bande le long d'une spirale."""
    t = np.linspace(0.0, 1.0, n)
    r = r_in + (r_out - r_in) * t
    # courbure arriere : l'angle recule quand le rayon augmente
    theta = np.radians(phase_deg) - np.radians(sweep_deg) * t

    cx, cy = r * np.cos(theta), r * np.sin(theta)

    # normale locale a la ligne moyenne, pour donner l'epaisseur
    dx, dy = np.gradient(cx), np.gradient(cy)
    norm = np.hypot(dx, dy)
    nx, ny = -dy / norm, dx / norm

    half = thickness / 2.0
    left = np.column_stack([cx + nx * half, cy + ny * half])
    right = np.column_stack([cx - nx * half, cy - ny * half])[::-1]
    return Polygon(np.vstack([left, right]))


def make_impeller(n_blades=6, r_hub=14.0, r_out=44.0, base_h=6.0,
                  hub_h=26.0, blade_h=22.0, blade_t=3.0, sweep_deg=38.0):
    """Assemble disque de base + moyeu + aubes."""
    base = trimesh.creation.cylinder(radius=r_out, height=base_h, sections=64)
    base.apply_translation((0, 0, base_h / 2.0))

    hub = trimesh.creation.cylinder(radius=r_hub, height=hub_h, sections=48)
    hub.apply_translation((0, 0, hub_h / 2.0))

    parts = [base, hub]
    for i in range(n_blades):
        poly = blade_polygon(r_hub - 1.0, r_out - 1.0, sweep_deg, blade_t,
                             phase_deg=i * 360.0 / n_blades)
        blade = trimesh.creation.extrude_polygon(poly, height=blade_h)
        blade.apply_translation((0, 0, base_h - 0.5))
        parts.append(blade)

    wheel = trimesh.boolean.union(parts)
    wheel.apply_translation((0, 0, -wheel.bounds[0][2]))
    return wheel


if __name__ == "__main__":
    w = make_impeller()
    w.export("impeller.stl")
    print(f"impeller.stl : {len(w.faces)} faces, watertight={w.is_watertight}")
    print(f"  dimensions : {w.extents[0]:.1f} x {w.extents[1]:.1f} x {w.extents[2]:.1f} mm")
    print(f"  volume     : {w.volume:.0f} mm3")

    # Espace libre entre aubes : ce que la buse doit traverser
    import math
    r_mid = 29.0
    gap = 2 * math.pi * r_mid / 6 - 3.0
    print(f"  entre-aubes a r={r_mid:.0f} mm : ~{gap:.1f} mm de passage")
