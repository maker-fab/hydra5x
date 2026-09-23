#!/usr/bin/env python3
"""
Comparateur deterministe entre deux implementations de la cinematique.

Reference : rep5x_ik.cpp -- extraction fidele du firmware rep5x-marlin,
correctif du signe rz applique, exposee ici via un binaire C++ autonome.

Second avis : impl_independante.py -- ecrite depuis SPEC.md seul, sans
acces a la reference ni au firmware. C'est cet aveuglement qui donne sa
valeur a la concordance : deux chemins partant de la meme specification
ecrite, pas une relecture du meme code.

Ne juge rien par "vote majoritaire" : la reference tranche. Tout ecart
superieur a la tolerance bloque -- pas de PASS silencieux.
"""
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
TOL_MM = 0.01  # seuil d'alerte (precision mecanique visee)
LC, LB = 5.0, 47.9
N_POINTS = 5000
SEED = 20260920


def binaire(nom: str) -> Path:
    """Localise un binaire construit, avec ou sans .exe selon la plateforme."""
    for candidat in (HERE / nom, HERE / f"{nom}.exe"):
        if candidat.exists():
            return candidat
    raise FileNotFoundError(
        f"{nom} absent -- construire d'abord :\n"
        f"  cmake -S . -B build && cmake --build build --config Release"
    )


def reference_via_cpp(native: np.ndarray, direction: str) -> np.ndarray:
    """Appelle le binaire C++ de reference (rep5x_ik) point par point via stdin/stdout.
    direction: 'inverse' (native->joint) ou 'forward' (joint->native)."""
    exe = binaire("ref_cli")
    lines = "\n".join(f"{x} {y} {z} {c} {b}" for x, y, z, c, b in native)
    proc = subprocess.run(
        [str(exe), direction, str(LC), str(LB)],
        input=lines, capture_output=True, text=True, timeout=60, check=True,
    )
    out = np.array([[float(v) for v in row.split()]
                    for row in proc.stdout.strip().splitlines()])
    return out


def main() -> int:
    impl_path = HERE / "impl_independante.py"
    if not impl_path.exists():
        print(f"BLOQUE: {impl_path} absent -- implementation independante pas encore livree.")
        return 1

    sys.path.insert(0, str(HERE))
    import impl_independante  # noqa: E402

    rng = np.random.default_rng(SEED)
    x = rng.uniform(-100, 100, N_POINTS)
    y = rng.uniform(-100, 100, N_POINTS)
    z = rng.uniform(-100, 100, N_POINTS)
    c = rng.uniform(0, 360, N_POINTS)
    b = rng.uniform(0, 90, N_POINTS)
    native = np.column_stack([x, y, z, c, b])

    # Cas de reference exacts (B=0) ajoutes au jeu aleatoire
    fixed = np.array([
        [10, 20, 30, 0, 0],
        [1, 2, 3, 45, 0],
        [1, 2, 3, 200, 0],
    ])
    native = np.vstack([fixed, native])

    ref_joint = reference_via_cpp(native, "inverse")
    ds_joint = impl_independante.inverse(native.copy(), LC, LB)

    diff = np.linalg.norm(ref_joint[:, :3] - ds_joint[:, :3], axis=1)
    worst = int(np.argmax(diff))
    max_diff = float(diff[worst])

    print(f"Points testes: {len(native)}")
    print(f"Ecart max reference vs independante (inverse): {max_diff:.6f} mm"
          f" au point {worst}")
    print(f"  native={native[worst]}")
    print(f"  ref   ={ref_joint[worst]}")
    print(f"  independante={ds_joint[worst]}")

    # Aller-retour l'implementation independante seul (coherence interne)
    back = impl_independante.forward(ds_joint.copy(), LC, LB)
    rt_diff = np.linalg.norm(back[:, :3] - native[:, :3], axis=1)
    print(f"Aller-retour independante (coherence interne) max:"
          f" {float(np.max(rt_diff)):.9f} mm")

    if max_diff > TOL_MM:
        print(f"BLOQUE: ecart {max_diff:.4f} mm > tolerance {TOL_MM} mm -- divergence non resolue.")
        return 1
    if np.max(rt_diff) > 1e-6:
        print(f"BLOQUE: implementation independante non auto-coherente"
              f" (aller-retour {np.max(rt_diff):.6f} mm).")
        return 1

    print("OK: reference et implementation independante concordent, auto-coherente.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
