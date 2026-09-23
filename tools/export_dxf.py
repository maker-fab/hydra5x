#!/usr/bin/env python3
"""
Extrait les profils DXF 2D des pieces en tole depuis un assemblage STEP.

Cible : obtenir des devis de decoupe laser. Les services en ligne exigent
des DXF plats ; la CAO du Fractal 5 Pro est un assemblage STEP 3D sans
historique parametrique.

Le chargement du STEP (103 Mo, 985 solides) prend ~7 min. Les solides en
tole sont donc mis en cache au format BREP des le premier passage, et les
executions suivantes sont immediates.

Usage :
    python3 export_dxf.py --step CAD/Fractal_5_Pro_Assembly.stp --out dxf/
    python3 export_dxf.py --out dxf/ --thickness 3.0     # panneaux caisson
"""
import argparse
import hashlib
import sys
from pathlib import Path

import cadquery as cq
from OCP.Bnd import Bnd_Box
from OCP.BRep import BRep_Builder
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepTools import BRepTools
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPControl import STEPControl_Reader
from OCP.TopAbs import TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS, TopoDS_Compound

TOL_DEFAULT = 0.06  # mm, tolerance sur l'epaisseur mesuree


def cache_path(step_file, thickness, cache_dir):
    """Chemin du cache BREP, indexe sur le STEP et l'epaisseur demandee."""
    key = f"{Path(step_file).resolve()}:{Path(step_file).stat().st_size}:{thickness}"
    digest = hashlib.sha1(key.encode()).hexdigest()[:12]
    return Path(cache_dir) / f"sheets_{thickness}_{digest}.brep"


def load_sheets_from_step(step_file, thickness, tol):
    """Charge le STEP et renvoie SEULEMENT les solides en tole.

    Le filtrage se fait en OCP brut (Bnd_Box) AVANT toute conversion
    cadquery. Envelopper les 985 solides dans cq.Solid() avant de filtrer
    fait exploser le temps de traitement : mesure a >17 h sans aboutir,
    contre ~15 min avec ce filtrage prealable.
    """
    print(f"  chargement de {step_file} (plusieurs minutes)...", flush=True)
    reader = STEPControl_Reader()
    if reader.ReadFile(str(step_file)) != IFSelect_RetDone:
        raise RuntimeError(f"lecture STEP impossible : {step_file}")
    reader.TransferRoots()
    shape = reader.OneShape()
    print("  transfert fait, parcours des solides...", flush=True)

    sheets = []
    total = 0
    explorer = TopExp_Explorer(shape, TopAbs_SOLID)
    while explorer.More():
        current = explorer.Current()
        total += 1
        box = Bnd_Box()
        BRepBndLib.Add_s(current, box)
        xm, ym, zm, xM, yM, zM = box.Get()
        if any(abs(d - thickness) < tol for d in (xM - xm, yM - ym, zM - zm)):
            sheets.append(cq.Solid(TopoDS.Solid_s(current)))
        explorer.Next()

    print(f"  {total} solides parcourus, {len(sheets)} en tole", flush=True)
    return sheets


def write_cache(solids, path):
    builder = BRep_Builder()
    compound = TopoDS_Compound()
    builder.MakeCompound(compound)
    for s in solids:
        builder.Add(compound, s.wrapped)
    path.parent.mkdir(parents=True, exist_ok=True)
    BRepTools.Write_s(compound, str(path))


def read_cache(path):
    builder = BRep_Builder()
    compound = TopoDS_Compound()
    BRepTools.Read_s(compound, str(path), builder)
    solids = []
    explorer = TopExp_Explorer(compound, TopAbs_SOLID)
    while explorer.More():
        solids.append(cq.Solid(TopoDS.Solid_s(explorer.Current())))
        explorer.Next()
    return solids


def find_cache(thickness, cache_dir):
    """Cache correspondant a cette epaisseur, sans connaitre le STEP.

    Le nom encode l'epaisseur ; on retient le plus recent s'il y en a
    plusieurs. Permet de relancer l'export sans repasser les ~15 min de
    chargement, et sans avoir le STEP sous la main.
    """
    found = sorted(Path(cache_dir).glob(f"sheets_{thickness}_*.brep"),
                   key=lambda f: f.stat().st_mtime, reverse=True)
    return found[0] if found else None


def get_sheets(step_file, thickness, tol, cache_dir):
    """Renvoie les solides en tole, depuis le cache si possible."""
    cache = cache_path(step_file, thickness, cache_dir) if step_file \
        else find_cache(thickness, cache_dir)
    if cache and cache.exists():
        print(f"  cache : {cache.name}", flush=True)
        return read_cache(cache)

    if not step_file:
        raise RuntimeError(
            f"aucun cache pour l'epaisseur {thickness} dans {cache_dir}/ "
            f"et pas de --step : rien a faire")

    sheets = load_sheets_from_step(step_file, thickness, tol)
    if cache:
        write_cache(sheets, cache)
        print(f"  cache ecrit : {cache.name}", flush=True)
    return sheets


def flatten_face(solid):
    """Renvoie la plus grande face plane du solide, ramenee dans le plan XY.

    `toLocalCoords` transforme du repere global VERS le repere du plan de
    la face, ce qui pose bien la face en Z=0. Une transformation dans
    l'autre sens laisse les pieces non paralleles a XY dans un plan
    vertical : leur DXF sort alors avec une dimension nulle.
    """
    planar = [f for f in solid.Faces() if f.geomType() == "PLANE"]
    if not planar:
        return None

    face = max(planar, key=lambda f: f.Area())
    plane = cq.Plane(origin=face.Center(), normal=face.normalAt())
    flat = plane.toLocalCoords(face)

    box = flat.BoundingBox()
    if min(box.xlen, box.ylen) < 1e-6:
        return None  # aplatissement rate : on refuse plutot que d'ecrire un DXF vide
    return flat, face.Area()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--step", help="assemblage STEP (omis si le cache existe)")
    ap.add_argument("--out", default="dxf", help="dossier de sortie")
    ap.add_argument("--thickness", type=float, default=3.175,
                    help="epaisseur visee en mm (defaut 3.175 = 1/8\")")
    ap.add_argument("--tol", type=float, default=TOL_DEFAULT)
    ap.add_argument("--cache-dir", default=".dxf_cache")
    ap.add_argument("--min-area", type=float, default=100.0,
                    help="ignorer les pieces sous cette aire en mm2")
    args = ap.parse_args()

    sheets = get_sheets(args.step, args.thickness, args.tol, args.cache_dir)
    print(f"  {len(sheets)} pieces a {args.thickness} mm\n")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    written, skipped = 0, 0
    total_area = 0.0
    for i, solid in enumerate(sorted(sheets, key=lambda s: -s.Area())):
        result = flatten_face(solid)
        if result is None:
            print(f"  [{i:02d}] IGNORE : aucune face plane")
            skipped += 1
            continue

        flat, area = result
        if area < args.min_area:
            skipped += 1
            continue

        bb = flat.BoundingBox()
        name = f"piece_{i:02d}_{bb.xlen:.0f}x{bb.ylen:.0f}mm.dxf"
        target = out_dir / name
        try:
            cq.exporters.export(flat, str(target), exportType="DXF")
        except Exception as exc:
            print(f"  [{i:02d}] ECHEC export : {type(exc).__name__}: {exc}")
            skipped += 1
            continue

        total_area += area
        written += 1
        print(f"  [{i:02d}] {name:<34} aire {area / 100:7.1f} cm2")

    print(f"\n  {written} DXF ecrits dans {out_dir}/ , {skipped} ignores")
    print(f"  aire totale : {total_area / 1e6:.3f} m2")
    return 0 if written else 1


if __name__ == "__main__":
    sys.exit(main())
