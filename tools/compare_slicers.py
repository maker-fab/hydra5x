#!/usr/bin/env python3
"""Compare le tranchage d'un meme chunk par Cortex et par un slicer mature.

Question posee : que gagne-t-on a deleguer le tranchage de chaque chunk a
OrcaSlicer plutot qu'a Cortex ? Le chunk est deja pose a plat par
export_chunks.py, donc c'est une piece 3 axes ordinaire -- les deux
slicers font le meme travail sur la meme entree, et l'ecart est mesurable.

Les metriques sont tirees du G-code lui-meme, pas des annonces des
slicers : longueur extrudee, longueur parcourue a vide, nombre de couches,
retractions. La longueur de filament est le seul chiffre qui se compare
sans ambiguite entre deux generateurs differents.
"""
import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import trimesh

CORTEX = Path(__file__).parent.parent / "cortex" / "fractal-cortex"
sys.path.insert(0, str(CORTEX))
sys.path.insert(0, str(Path(__file__).parent))


def mesurer_gcode(chemin):
    """Parcourt le G-code et cumule les deplacements. Marche pour tout
    generateur : on ne lit que G0/G1 et les axes, aucun commentaire."""
    pos = {"X": 0.0, "Y": 0.0, "Z": 0.0}
    e_total = 0.0
    e_retract = 0.0
    extrude = 0.0
    vide = 0.0
    couches = set()
    n_retractions = 0
    e_dernier = 0.0
    absolu_e = True

    for ligne in Path(chemin).read_text(errors="ignore").splitlines():
        ligne = ligne.split(";")[0].strip()
        if not ligne:
            continue
        if ligne.startswith("M83"):
            absolu_e = False
        elif ligne.startswith("M82"):
            absolu_e = True
        elif ligne.startswith("G92"):
            if " E" in ligne:
                e_dernier = 0.0
            continue
        if not re.match(r"^G[01]\b", ligne):
            continue

        mots = dict(re.findall(r"([XYZEF])(-?\d*\.?\d+)", ligne))
        cible = {a: float(mots[a]) for a in "XYZ" if a in mots}
        d = np.linalg.norm([cible.get(a, pos[a]) - pos[a] for a in "XYZ"])

        de = None
        if "E" in mots:
            e = float(mots["E"])
            de = (e - e_dernier) if absolu_e else e
            e_dernier = e if absolu_e else e_dernier + e

        # Un mouvement d'extrudeur SANS deplacement XYZ n'est pas de
        # l'extrusion : c'est une retraction, une reprise ou une amorce.
        # Les compter faussait le filament de la valeur totale des reprises
        # -- +2 495 mm sur Prusa, +14 727 mm sur Cortex.
        if de is None or abs(d) < 1e-9:
            if de is not None and de < 0:
                e_retract += -de
                n_retractions += 1
            vide += d
        elif de > 0:
            extrude += d
            e_total += de
        else:
            vide += d

        pos.update(cible)
        if "Z" in cible:
            couches.add(round(cible["Z"], 3))

    return {
        "extrusion_mm": extrude,
        "vide_mm": vide,
        "filament_mm": e_total,
        "retractions": n_retractions,
        "retract_mm": e_retract,
        "couches": len(couches),
        "lignes": len(Path(chemin).read_text(errors="ignore").splitlines()),
        "taille_ko": Path(chemin).stat().st_size / 1024,
    }


def trancher_cortex(stl, sortie, hauteur_couche=0.2):
    """Tranche en une seule direction : le chunk est deja a plat."""
    import slicing_functions as sf
    from test_slice import print_settings

    reglages = print_settings()
    reglages[6] = hauteur_couche
    maillage = trimesh.load(stl, force="mesh")
    maillage.apply_translation((0.0, 0.0, -maillage.bounds[0][2]))

    resultat = sf.slice_in_5_axes(
        reglages, (["chunk"], {"chunk": maillage}),
        (1, [[0.0, 0.0, 0.0]], [(0.0, 0.0)]),
    )
    sf.write_5_axis_gcode(str(sortie), "chunk", reglages,
                          [[0.0, 0.0, 0.0]], [(0.0, 0.0)], *resultat)
    return sortie


def trancher_prusa(binaire, stl, sortie, hauteur_couche=0.2, profil=None):
    """PrusaSlicer en CLI. Les reglages passent en options directes, ce qui
    evite toute la machinerie de prereglages."""
    cmd = [
        str(binaire), "--export-gcode", "--output", str(sortie),
        "--layer-height", str(hauteur_couche),
        "--first-layer-height", str(hauteur_couche),
        "--fill-density", "20%",
        "--perimeters", "2",
        "--temperature", "210",
        "--first-layer-temperature", "215",
        "--bed-temperature", "60",
        "--first-layer-bed-temperature", "60",
        "--retract-length", "5",
        "--retract-speed", "40",
        "--support-material=0",
        "--brim-width", "0",
        "--skirts", "0",
        "--nozzle-diameter", "0.4",
    ]
    if profil:
        cmd += ["--load", str(profil)]
    cmd.append(str(stl))
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if not Path(sortie).exists():
        raise RuntimeError(
            "PrusaSlicer n'a produit aucun G-code.\n"
            f"  commande : {' '.join(cmd)}\n"
            f"  code     : {proc.returncode}\n"
            f"  stdout   : {proc.stdout[-800:]}\n"
            f"  stderr   : {proc.stderr[-800:]}"
        )
    return sortie


def trancher_orca(binaire, stl, sortie, hauteur_couche=0.2, profil=None):
    """OrcaSlicer en CLI.

    ATTENTION : bloque sur la 2.4.2 et anterieures. Le controle de
    compatibilite process/machine de la CLI compare des noms litteraux la ou
    l'interface evalue `compatible_printers_condition` ; toute paire de
    prereglages chargee par --load-settings sort en CLI_PROCESS_NOT_COMPATIBLE
    (-17), avant meme la moindre action. Le correctif est sur `main` en amont,
    dans aucune version publiee. Voir docs/decisions.md D8.

    Sans --profil, Orca echoue plus tot encore (-51) : son profil par defaut
    combine E relatif et layer_gcode vide, combinaison qu'il refuse lui-meme.
    """
    if not profil:
        raise RuntimeError(
            "OrcaSlicer exige un couple de prereglages machine+process "
            "(--profil). Sans lui il refuse son propre profil par defaut."
        )
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [str(binaire), str(stl), "--load-settings", str(profil),
               "--slice", "0", "--outputdir", tmp]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        produits = list(Path(tmp).glob("*.gcode"))
        if not produits:
            raise RuntimeError(
                "OrcaSlicer n'a produit aucun G-code.\n"
                f"  commande : {' '.join(cmd)}\n"
                f"  code     : {proc.returncode}\n"
                f"  stdout   : {proc.stdout[-500:]}\n"
                f"  stderr   : {proc.stderr[-500:]}"
            )
        Path(sortie).write_bytes(produits[0].read_bytes())
    return sortie


def afficher(titre, m):
    print(f"\n  {titre}")
    print(f"    couches          : {m['couches']}")
    print(f"    filament         : {m['filament_mm']:10.1f} mm")
    print(f"    trajet extrude   : {m['extrusion_mm']:10.1f} mm")
    print(f"    trajet a vide    : {m['vide_mm']:10.1f} mm"
          f"   ({m['vide_mm']/max(m['extrusion_mm'],1e-9)*100:.1f} % du trajet extrude)")
    print(f"    retractions      : {m['retractions']}  ({m['retract_mm']:.1f} mm)")
    print(f"    G-code           : {m['lignes']} lignes, {m['taille_ko']:.1f} Ko")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stl", type=Path, help="chunk STL pose a plat")
    ap.add_argument("--orca", type=Path, default=None,
                    help="binaire OrcaSlicer (bloque en 2.4.2, voir decisions.md D8)")
    ap.add_argument("--prusa", type=Path, default=None,
                    help="binaire PrusaSlicer, p.ex. /usr/bin/prusa-slicer")
    ap.add_argument("--profil", type=Path, default=None,
                    help="fichier de reglages a charger dans le slicer externe")
    ap.add_argument("--out", type=Path, default=Path("results/comparaison"))
    ap.add_argument("--couche", type=float, default=0.2)
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    maillage = trimesh.load(args.stl, force="mesh")
    print(f"Chunk : {args.stl.name}")
    print(f"  {len(maillage.faces)} faces, {maillage.volume:.1f} mm3, "
          f"etanche={maillage.is_watertight}")

    g_cortex = trancher_cortex(args.stl, args.out / "cortex.gcode", args.couche)
    m_cortex = mesurer_gcode(g_cortex)
    afficher("Cortex", m_cortex)

    if args.prusa:
        nom, g_ext = "PrusaSlicer", trancher_prusa(
            args.prusa, args.stl, args.out / "prusa.gcode", args.couche, args.profil)
    elif args.orca:
        nom, g_ext = "OrcaSlicer", trancher_orca(
            args.orca, args.stl, args.out / "orca.gcode", args.couche, args.profil)
    else:
        print("\n  Aucun slicer externe fourni (--prusa / --orca) : "
              "comparaison partielle.")
        return 0

    m_orca = mesurer_gcode(g_ext)
    afficher(nom, m_orca)

    print(f"\n  Ecarts ({nom} par rapport a Cortex)")
    for cle, libelle in (("filament_mm", "filament"),
                         ("extrusion_mm", "trajet extrude"),
                         ("vide_mm", "trajet a vide"),
                         ("couches", "couches")):
        a, b = m_cortex[cle], m_orca[cle]
        if a:
            print(f"    {libelle:16s} {(b-a)/a*100:+7.1f} %")
    return 0


if __name__ == "__main__":
    sys.exit(main())
