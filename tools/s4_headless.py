#!/usr/bin/env python3
"""Fait tourner la deformation de S4 Slicer sans affichage.

[S4 Slicer](https://github.com/jyjblrd/S4_Slicer) (GPL-3.0, Joshua Bird)
est le seul slicer non-planaire libre reellement utilisable : un notebook
Python, sans CUDA, Qt ni MKL. Mais il vise Google Colab et une pile de
2023, donc il ne tourne pas tel quel sur une machine a jour.

Ce script neutralise ce qui bloque, sans modifier le code d'origine -- pour
rester au plus pres de l'amont et pouvoir suivre ses mises a jour.

**Trois obstacles rencontres**, tous mesures :

1. **17 appels graphiques** (`.plot()`, `.show()`, `open_gif`) bloquent en
   headless. Neutralises par monkey-patch.
2. **`pv.start_xvfb()` n'existe plus** depuis pyvista 0.49. Stub.
3. **`np.cross` avec un vecteur 2D a disparu dans NumPy 2.0.** S4 en
   depend, donc il exige `numpy<2` -- le meme clivage que trimesh, et la
   raison pour laquelle il lui faut son propre environnement.

Environnement coherent :

    python3 -m venv .venv-s4
    .venv-s4/bin/pip install numpy==1.26.4 scipy==1.13.1 "contourpy<1.4" \\
        "matplotlib<3.10" networkx open3d pyvista tetgen pygcode

Duree mesuree sur leur exemple `pi 3mm` : **61 s**, cout d'optimisation de
28 836 a 181,7. Sortie : le STL deforme et le champ de deformation en
pickle.

**Suite de la chaine**, a faire ensuite : trancher le STL deforme avec un
slicer 3 axes ordinaire -- le notebook dit « go and slice in Cura », mais
PrusaSlicer fait l'affaire -- puis appliquer la deformation inverse au
G-code, ce qui courbe les couches et fait apparaitre les axes rotatifs.

C'est la meme architecture que `stitch_chunks.py` : deformer, deleguer,
recomposer. Voir `docs/decisions.md` D17.
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path


def neutraliser_affichage():
    """Rend pyvista silencieux : aucun rendu, aucune fenetre."""
    import pyvista as pv
    pv.OFF_SCREEN = True
    pv.start_xvfb = lambda *a, **k: None          # retire en 0.49
    pv.DataSet.plot = lambda self, *a, **k: None
    pv.Plotter.show = lambda self, *a, **k: None
    pv.Plotter.open_gif = lambda self, *a, **k: None
    pv.Plotter.write_frame = lambda self, *a, **k: None


def extraire_cellules(notebook, debut=2, fin=12):
    """Cellules de code du notebook, dans l'ordre.

    2 a 12 = la deformation. 0 et 1 sont le `git clone` et le `pip install`
    de Colab ; au-dela de 13 c'est le post-traitement du G-code, qui exige
    d'avoir tranche entre-temps.
    """
    import json
    nb = json.loads(Path(notebook).read_text())
    bouts = []
    for i, c in enumerate(nb["cells"]):
        if c["cell_type"] != "code" or not (debut <= i <= fin):
            continue
        # les magies Jupyter (%matplotlib) et les commandes shell (!pip)
        # sont des erreurs de syntaxe en Python pur
        lignes = [l for l in "".join(c["source"]).split("\n")
                  if not l.lstrip().startswith(("%", "!"))]
        bouts.append(f"# ===== cellule {i} =====\n" + "\n".join(lignes))
    return "\n\n".join(bouts)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("depot", type=Path,
                    help="racine du clone de S4_Slicer")
    ap.add_argument("--modele", default=None,
                    help="nom du modele dans input_models/, sans .stl")
    ap.add_argument("--fin", type=int, default=12,
                    help="derniere cellule executee")
    args = ap.parse_args()

    notebook = args.depot / "main.ipynb"
    if not notebook.exists():
        raise SystemExit(f"{notebook} introuvable -- cloner d'abord "
                         "https://github.com/jyjblrd/S4_Slicer")

    neutraliser_affichage()
    src = extraire_cellules(notebook, fin=args.fin)
    src = src.replace("SAVE_GIF = True", "SAVE_GIF = False")
    if args.modele:
        import re
        src = re.sub(r'model_name\s*=\s*"[^"]*"',
                     f'model_name = "{args.modele}"', src, count=1)

    import os
    os.chdir(args.depot)          # les chemins du notebook sont relatifs
    t0 = time.time()
    exec(compile(src, "S4_main.ipynb", "exec"), {"__name__": "__main__"})
    print(f"\n  deformation terminee en {time.time() - t0:.1f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
