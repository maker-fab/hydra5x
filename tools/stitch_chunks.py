#!/usr/bin/env python3
"""Coud les chunks tranches par un slicer mature en un G-code 5 axes.

Chaque chunk est pose a plat, tranche par PrusaSlicer comme une piece
3 axes ordinaire, puis recousu avec le protocole machine de Fractal Cortex
-- memes commandes MANUAL_STEPPER, meme convention d'angles, meme
degagement avant rotation. Le contrat cote machine ne change pas : seule
la generation des trajets est deleguee.

Le point delicat n'est pas la rotation, c'est ce qui l'entoure :

1. A partir du chunk 1 la "premiere couche" se pose sur du plastique, pas
   sur le plateau. Vitesse reduite, surepaisseur, compensation de pied
   d'elephant et temperature de premiere couche deviennent des erreurs.
   Elles sont neutralisees chunk par chunk.
2. Chaque G-code de chunk porte son propre prologue et epilogue. Un seul
   prologue et un seul epilogue doivent subsister.
3. L'axe E repart de zero a chaque chunk : un G92 E0 est emis a chaque
   frontiere.
4. La buse doit etre degagee pendant le basculement du plateau.

Convention d'angles, relevee dans slicing_functions.py et verifiee contre
le G-code de reference : A = 90 - phi, B = theta, chunk 0 force a l'origine.
"""
import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).parent))
from export_chunks import decouper, poser_a_plat, spherical_to_normal  # noqa: E402

AB_FEEDRATE = 25.0          # deg/s, comme Cortex
DEGAGEMENT_Z = 10.0         # mm au-dessus de la buse avant rotation
PARKING = (0.0, -175.0)     # position de degagement de la tete
HAUTEUR_REPRISE = 30.0      # mm de garde en arrivant sur un nouveau chunk


def angles_ab(directions):
    """Angles A et B par chunk, convention Cortex.

    Un retour a l'origine est ajoute en queue : sans lui, la vitesse du
    dernier mouvement se calcule sur un deplacement nul et sort a zero,
    ce que Klipper refuse.
    """
    a = [0.0] + [90.0 - phi for _, phi in directions[1:]] + [0.0]
    b = [0.0] + [theta for theta, _ in directions[1:]] + [0.0]
    return a, b


def vitesses_ab(a, b):
    """Vitesses decomposees sur le mouvement relatif, comme Cortex."""
    va, vb = [AB_FEEDRATE], [AB_FEEDRATE]
    for k in range(1, len(a)):
        angle = np.arctan2(b[k] - b[k - 1], a[k] - a[k - 1])
        va.append(abs(AB_FEEDRATE * np.cos(angle)))
        vb.append(abs(AB_FEEDRATE * np.sin(angle)))
    return va, vb


def non_nulle(v):
    """Une vitesse nulle est refusee par Klipper : replier sur la consigne."""
    return v if round(v, 5) != 0 else AB_FEEDRATE


def options_prusa(couche, premier_chunk):
    """Reglages communs, plus la neutralisation de la premiere couche.

    Sur un chunk pose sur du plastique, tout ce qui distingue la premiere
    couche est nuisible : elle n'a ni adherence a gagner, ni ecrasement a
    compenser.
    """
    opts = [
        "--layer-height", str(couche),
        "--first-layer-height", str(couche),
        "--fill-density", "20%",
        "--perimeters", "2",
        "--nozzle-diameter", "0.4",
        "--retract-length", "5",
        "--retract-speed", "40",
        "--support-material=0",
        "--brim-width", "0",
        "--skirts", "0",
        "--start-gcode", "",
        "--end-gcode", "",
    ]
    if premier_chunk:
        opts += ["--temperature", "210", "--first-layer-temperature", "215"]
    else:
        opts += [
            "--temperature", "210",
            "--first-layer-temperature", "210",     # plus de surchauffe d'accroche
            "--first-layer-speed", "100%",          # plus de ralentissement
            "--first-layer-extrusion-width", "0",   # 0 = largeur normale
            "--elefant-foot-compensation", "0",     # aucun ecrasement a corriger
        ]
    return opts


def trancher(prusa, stl, sortie, couche, premier_chunk):
    cmd = ([str(prusa), "--export-gcode", "--output", str(sortie)]
           + options_prusa(couche, premier_chunk) + [str(stl)])
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if not Path(sortie).exists():
        raise RuntimeError(
            f"PrusaSlicer n'a produit aucun G-code pour {Path(stl).name}.\n"
            f"  code   : {proc.returncode}\n  stderr : {proc.stderr[-600:]}"
        )
    return Path(sortie)


def corps_utile(chemin):
    """Retire les commentaires de configuration et les lignes de thermique.

    La thermique est geree une fois pour toutes dans le prologue : la
    laisser par chunk ferait attendre la machine a chaque frontiere.
    """
    garde = []
    for ligne in chemin.read_text().splitlines():
        nu = ligne.strip()
        if not nu or nu.startswith(";"):
            continue
        if re.match(r"^(M10[49]|M14[01]|M190|G2[018]|G91|M8[23])\b", nu):
            continue
        garde.append(nu)
    return garde


def premier_xy(corps):
    """Premier point XY vise par le chunk, pour l'atteindre en altitude."""
    for ligne in corps:
        x = re.search(r"\bX(-?\d*\.?\d+)", ligne)
        y = re.search(r"\bY(-?\d*\.?\d+)", ligne)
        if x and y:
            return float(x.group(1)), float(y.group(1))
    return None


def approche(corps, hauteur):
    """Amene la buse au-dessus du premier point AVANT de descendre.

    Sans ca le corps du chunk descend a la hauteur de couche depuis la
    position de degagement, puis traverse tout le plateau a 0,2 mm du
    plan de travail -- la buse laboure ce qui est deja imprime.
    """
    p = premier_xy(corps)
    if p is None:
        return []
    return [f"G0 F7800 X{p[0]:.3f} Y{p[1]:.3f} ; se placer avant de descendre",
            f"G0 F1800 Z{hauteur:.3f}"]


def prologue(couche, temp, temp_lit):
    return [
        "; HYDRA5X -- chunks tranches par PrusaSlicer, cousus ici",
        "; convention machine identique a Fractal Cortex",
        f"M140 S{temp_lit}",
        f"M104 S{temp}",
        "G28",
        f"M190 S{temp_lit}",
        f"M109 S{temp}",
        "G90",
        "M82",
        "G92 E0",
        f"G0 F1800 Z{couche}",
    ]


def bloc_rotation(k, a, b, va, vb, z_courant):
    """Degagement puis rotation, protocole Cortex a l'identique."""
    if k == 0:
        return []
    lignes = [f"; ---- chunk {k} : reorientation ----",
              f"G0 F1800 Z{z_courant + DEGAGEMENT_Z:.3f} ; degager Z avant rotation",
              f"G0 X{PARKING[0]} Y{PARKING[1]} ; ecarter la tete"]
    bouge_a = round(va[k], 5) != 0
    bouge_b = round(vb[k], 5) != 0
    if bouge_a:
        lignes.append(f"MANUAL_STEPPER STEPPER=stepper_a MOVE={a[k]:.5f} "
                      f"SPEED={va[k]:.5f} SYNC={0 if bouge_b else 1}")
    if bouge_b:
        lignes.append(f"MANUAL_STEPPER STEPPER=stepper_b MOVE={b[k]:.5f} "
                      f"SPEED={vb[k]:.5f} SYNC=1 STOP_ON_ENDSTOP=2")
    if not (bouge_a or bouge_b):
        lignes.append("; aucun mouvement A/B requis")
    lignes += [
        "; rotation terminee",
        "G92 E0 ; l'axe E repart de zero pour ce chunk",
        f"G0 F1800 Z{HAUTEUR_REPRISE:.3f} ; garde avant approche",
    ]
    return lignes


def epilogue(va, vb):
    return [
        "; ---- fin ----",
        "G1 F2400 E-5 ; retraction finale",
        "G0 F1800 Z60",
        f"MANUAL_STEPPER STEPPER=stepper_a MOVE=0.0 "
        f"SPEED={non_nulle(va[-1]):.5f} SYNC=0",
        f"MANUAL_STEPPER STEPPER=stepper_b MOVE=0.0 "
        f"SPEED={non_nulle(vb[-1]):.5f} SYNC=1 STOP_ON_ENDSTOP=2",
        "M104 S0",
        "M140 S0",
        "M84",
    ]


def z_max(lignes):
    zs = [float(m.group(1)) for l in lignes
          for m in [re.search(r"\bZ(-?\d*\.?\d+)", l)] if m]
    return max(zs) if zs else 0.0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prusa", type=Path, default=Path("/usr/bin/prusa-slicer"))
    ap.add_argument("--out", type=Path, default=Path("results/gcode/y_cousu.gcode"))
    ap.add_argument("--couche", type=float, default=0.2)
    ap.add_argument("--angle", type=float, default=30.0)
    args = ap.parse_args()

    from test_slice import make_y_part
    piece = make_y_part(angle=args.angle)
    directions = [(0.0, 0.0), (30.0, 0.0), (30.0, 180.0)]
    departs = [[0.0, 0.0, 0.0], [0.0, 0.0, 28.0], [0.0, 0.0, 28.0]]

    chunks = decouper(piece, directions, departs)
    a, b = angles_ab(directions)
    va, vb = vitesses_ab(a, b)
    print(f"Piece en Y : {len(piece.faces)} faces, {piece.volume:.1f} mm3")
    for k in range(len(directions)):
        print(f"  chunk {k} : A={a[k]:7.1f} deg  B={b[k]:6.1f} deg"
              f"   vitesses {va[k]:6.2f} / {vb[k]:6.2f}")

    sortie = [l for l in prologue(args.couche, 210, 60)]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for k, morceau in enumerate(chunks):
            if morceau is None:
                print(f"  chunk {k} : vide, ignore")
                continue
            normale = spherical_to_normal(*directions[k])
            pose = poser_a_plat(morceau, normale)
            stl = Path(tmp) / f"c{k}.stl"
            pose.export(stl)
            g = trancher(args.prusa, stl, Path(tmp) / f"c{k}.gcode",
                         args.couche, premier_chunk=(k == 0))
            corps = corps_utile(g)
            sortie += bloc_rotation(k, a, b, va, vb, z_max(sortie))
            sortie.append(f"; ---- chunk {k} : {len(corps)} lignes ----")
            if k > 0:
                sortie += approche(corps, HAUTEUR_REPRISE)
            sortie += corps
            print(f"  chunk {k} : {len(corps)} lignes de trajets, "
                  f"Z max {z_max(corps):.2f} mm")

    sortie += epilogue(va, vb)
    args.out.write_text("\n".join(sortie) + "\n")
    print(f"\n  {args.out}  {len(sortie)} lignes, "
          f"{args.out.stat().st_size/1024:.1f} Ko")
    return 0


if __name__ == "__main__":
    sys.exit(main())
