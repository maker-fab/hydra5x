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

        if de is not None and de > 0:
            extrude += d
            e_total += de
        elif de is not None and de < 0:
            e_retract += -de
            n_retractions += 1
            vide += d
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


def trancher_orca(binaire, stl, sortie, hauteur_couche=0.2, profil=None):
    """Appelle OrcaSlicer en ligne de commande.

    Orca ecrit dans un dossier de sortie, pas vers un fichier nomme : on
    passe par un dossier temporaire puis on recupere le seul .gcode produit.
    """
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [str(binaire), str(stl), "--slice", "0", "--outputdir", tmp]
        if profil:
            cmd += ["--load-settings", str(profil)]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        produits = list(Path(tmp).glob("*.gcode")) + list(Path(tmp).glob("*.gcode.3mf"))
        if not produits:
            raise RuntimeError(
                "OrcaSlicer n'a produit aucun G-code.\n"
                f"  commande : {' '.join(cmd)}\n"
                f"  code     : {proc.returncode}\n"
                f"  stdout   : {proc.stdout[-800:]}\n"
                f"  stderr   : {proc.stderr[-800:]}"
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
                    help="binaire OrcaSlicer ; absent, seul Cortex est mesure")
    ap.add_argument("--profil", type=Path, default=None,
                    help="profil de reglages Orca (.json)")
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

    if not args.orca:
        print("\n  OrcaSlicer non fourni (--orca) : comparaison partielle.")
        return 0

    g_orca = trancher_orca(args.orca, args.stl, args.out / "orca.gcode",
                           args.couche, args.profil)
    m_orca = mesurer_gcode(g_orca)
    afficher("OrcaSlicer", m_orca)

    print("\n  Ecarts (Orca par rapport a Cortex)")
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
