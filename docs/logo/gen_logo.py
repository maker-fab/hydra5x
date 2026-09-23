#!/usr/bin/env python3
"""Genere le logo HYDRA5X : un ruban qui se vrille en montant.

La piece se reoriente couche apres couche — c'est ce que fait une TRT.
La vrille passe de -90 deg (ruban de chant) a +90 deg en traversant le
plan de face : la largeur apparente suit |cos|, d'ou le pincement en
haut et en bas.
"""
import math
from pathlib import Path

N     = 34       # lames
W     = 88.0     # demi-largeur a plat
H     = 262.0    # hauteur
TWIST = 330.0    # vrille totale, deg
SLOPE = 0.26     # inclinaison apparente des lames
TH    = 8.4      # epaisseur d'une lame
CX, CY0 = 160.0, 296.0

# Palette MAKERFAB, degrade entierement dans l'accent : le logo doit rester
# lisible sur fond clair ET sur fond sombre, donc aucune extremite ne tombe
# dans le noir ni dans le blanc.
C0, C1, C2 = (232, 176, 120), (240, 130, 40), (250, 200, 145)


def lerp(a, b, t):
    return a + (b - a) * t


def colour(t, c0=C0):
    if t < 0.58:
        u, a, b = t / 0.58, c0, C1
    else:
        u, a, b = (t - 0.58) / 0.42, C1, C2
    return tuple(round(lerp(a[i], b[i], u)) for i in range(3))


def build(c0=C0):
    out = []
    for i in range(N):
        t = i / (N - 1)
        y = CY0 - t * H
        ang = math.radians(lerp(-TWIST / 2, TWIST / 2, t))
        # cos SIGNE : quand il change de signe les extremites s'echangent,
        # et le ruban se croise — c'est ce croisement qui fait lire la vrille.
        c = math.cos(ang)
        w = W * c
        dy = abs(w) * math.sin(ang) * SLOPE
        r, g, b = colour(t, c0)
        out.append(
            f'    <path d="M{CX - w:.1f} {y + dy:.1f} L{CX + w:.1f} {y - dy:.1f}" '
            f'stroke="rgb({r},{g},{b})" stroke-width="{TH:.1f}"/>'
        )
    return out


if __name__ == "__main__":
    def emit(lames, name):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 320" '
            'width="320" height="320">\n'
            '  <title>HYDRA5X</title>\n'
            f'  <!-- Genere par gen_logo.py : {N} lames, vrille {TWIST:.0f} deg. -->\n'
            '  <g fill="none" stroke-linecap="round">\n'
            + "\n".join(lames)
            + "\n  </g>\n</svg>\n"
        )
        Path(name).write_text(svg)

    emit(build(), "hydra5x.svg")
    print(f"  hydra5x.svg : {N} lames, vrille {TWIST:.0f} deg")
