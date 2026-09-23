#!/usr/bin/env python3
"""
3e reference : interroge le VRAI firmware rep5x-marlin (build linux_native)
via M114 D, et confronte ses chiffres a nos deux implementations.

M114 D expose trois lignes utiles :
  DeltaK:  -> sortie de inverse_kinematics() = native_to_joint()
  FromStp: -> sortie de forward_kinematics() = joint_to_native() (la fonction buggee)
  Diff:    -> ecart aller-retour calcule par le firmware sur lui-meme

Le firmware est donc son propre temoin : si Diff est non-nul, il contredit
sa propre cinematique, independamment de toute analyse exterieure.
"""
import os
import re
import subprocess
import sys
from math import cos, radians, sin
from pathlib import Path

# Binaire Marlin compile en natif. A obtenir par :
#   git clone --depth 1 https://github.com/dennisklappe/rep5x-marlin
#   cd rep5x-marlin
#   # Configuration.h : MOTHERBOARD BOARD_SIMULATED, drivers A4988,
#   # SDSUPPORT / BTT_MINI_12864 / NEOPIXEL_LED / ADVANCED_PAUSE_FEATURE /
#   # CUSTOM_MENU_MAIN desactives, SERIAL_PORT 0
#   # Configuration_adv.h : #define M114_DETAIL
#   pio run -e linux_native
FIRMWARE = Path(
    os.environ.get("REP5X_MARLIN",
                   Path.home() / "rep5x-marlin")
) / ".pio" / "build" / "linux_native" / "program"

# Valeurs du Configuration.h racine du depot
LC, LB = 1.6, 54.67

CAS = [
    (10.0, 20.0, 30.0, 0.0, 0.0),
    (10.0, 20.0, 30.0, 90.0, 0.0),
    (10.0, 20.0, 30.0, 45.0, 30.0),
    (0.0, 0.0, 0.0, 0.0, 90.0),
    (79.4004, 42.1126, -25.8850, 310.1097, 67.5757),
]


def native_to_joint(x, y, z, c, b, lc, lb):
    """Notre reference C++ transcrite (identique a rep5x_ik.cpp)."""
    cr, br = radians(c), radians(b)
    sb, cb, sc, cc = sin(br), cos(br), sin(cr), cos(cr)
    return (x - sc * lc + cc * sb * lb,
            y + (cc - 1) * lc + sc * sb * lb,
            z + (cb - 1) * lb)


def joint_to_native_firmware(x, y, z, c, b, lc, lb):
    """joint_to_native du firmware, transcription fidele (bug inclus)."""
    cr = radians(c)
    sc, cc = sin(cr), cos(cr)
    rx = lb * sin(radians(180.0 - b)) * cc
    ry = lb * sin(radians(180.0 - b)) * sc
    rz = -lb * cos(radians(180.0 - b))
    return (x + rx, y + ry, z + lb + rz)


def interroge_firmware(cas):
    """Envoie G92 + M114 D pour chaque cas, recupere la sortie brute."""
    lignes = ["G43.4", "M211 S0"]
    for x, y, z, c, b in cas:
        lignes.append(f"G92 X{x} Y{y} Z{z} C{c} B{b}")
        lignes.append("M114 D")
    gcode = "\n".join(lignes) + "\n"

    proc = subprocess.run(
        [str(FIRMWARE)], input=gcode, capture_output=True,
        text=True, timeout=30,
    )
    return proc.stdout


def parse_bloc(texte):
    """Extrait les lignes DeltaK/FromStp/Diff de chaque rapport M114 D."""
    blocs, courant = [], {}
    for ligne in texte.splitlines():
        for cle, motif in (("deltak", "DeltaK:"), ("fromstp", "FromStp:"),
                           ("diff", "Diff:")):
            if ligne.startswith(motif):
                vals = [float(v) for v in re.findall(r"[XYZCBE]:(-?\d+\.?\d*)", ligne)]
                courant[cle] = vals
                if cle == "diff":
                    blocs.append(courant)
                    courant = {}
    return blocs


def main():
    if not FIRMWARE.exists():
        print(f"BLOQUE: firmware absent -> {FIRMWARE}")
        return 1

    brut = interroge_firmware(CAS)
    blocs = parse_bloc(brut)

    if not blocs:
        print("BLOQUE: aucune sortie M114 D exploitable. Sortie brute :")
        print(brut[:3000])
        return 1

    print(f"Firmware interroge : {len(blocs)} rapports pour {len(CAS)} cas")
    print(f"LC={LC} LB={LB} (Configuration.h racine du depot)\n")

    ecart_max = 0.0
    for (x, y, z, c, b), bloc in zip(CAS, blocs):
        attendu = native_to_joint(x, y, z, c, b, LC, LB)
        fw_ik = bloc.get("deltak", [])
        fw_diff = bloc.get("diff", [])

        print(f"C={c:8.3f}  B={b:7.3f}  (X={x} Y={y} Z={z})")
        if fw_ik:
            print(f"  firmware DeltaK  : {fw_ik[:3]}")
            print(f"  notre reference  : [{attendu[0]:.3f}, {attendu[1]:.3f}, {attendu[2]:.3f}]")
            d = max(abs(a - f) for a, f in zip(attendu, fw_ik[:3]))
            ecart_max = max(ecart_max, d)
            print(f"  -> ecart         : {d:.4f} mm")
        if fw_diff:
            print(f"  firmware Diff    : {fw_diff[:3]}  <- erreur aller-retour auto-constatee")
        print()

    print(f"Ecart max notre reference vs firmware (inverse kinematics) : {ecart_max:.6f} mm")
    return 0 if ecart_max < 0.01 else 1


if __name__ == "__main__":
    sys.exit(main())
