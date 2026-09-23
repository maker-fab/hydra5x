#!/usr/bin/env python3
"""Compare la tenue en flexion d'un coude selon l'orientation des couches.

L'argument restant en faveur du multidirectionnel n'est pas la matiere
(17 %, voir decisions.md D11) mais l'orientation des couches : en 3 axes
elles sont toutes horizontales et le coude delamine en flexion, alors
qu'en multidirectionnel elles suivent la courbe.

Methode. Une piece imprimee casse presque toujours *entre* les couches,
pas dans le plan d'une couche. Le critere retenu est donc la **contrainte
normale au plan des couches**, `sigma_n = n . sigma . n`, ou `n` est la
normale de couche locale. Le champ de contraintes est calcule une seule
fois en elastique isotrope, puis projete sur deux champs d'orientation :

- 3 axes          : n = (0,0,1) partout
- multidirectionnel : n = direction d'impression du chunk local

Approximation assumee : le champ de contraintes est suppose independant de
l'anisotropie. C'est faux au second ordre -- une piece orthotrope redirige
un peu les efforts -- mais l'ecart de module entre les deux orientations
reste modeste devant l'ecart de resistance, et la comparaison porte sur la
geometrie du chargement, pas sur la rigidite.

Le solveur est ecrit ici plutot qu'importe, pour pouvoir le valider : voir
`valider_poutre()`, qui compare la fleche d'une poutre encastree a la
theorie d'Euler-Bernoulli.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve

sys.path.insert(0, str(Path(__file__).parent))

E_MODULE = 2300.0     # MPa, PLA imprime, dans le plan des couches
NU = 0.35


# --------------------------------------------------------------------------
# Maillage structure : section en anneau balayee le long d'un chemin
# --------------------------------------------------------------------------
def chemin_coude(rayon_courbure, angle_total, base, n_long):
    """Points et tangentes le long de l'axe du coude."""
    n_droit = max(2, n_long // 4)
    n_virage = n_long - n_droit + 1
    pts = [np.array([0.0, 0.0, z]) for z in np.linspace(0.0, base, n_droit)]
    tan = [np.array([0.0, 0.0, 1.0])] * n_droit
    centre = np.array([rayon_courbure, 0.0, base])
    for a in np.linspace(0.0, np.radians(angle_total), n_virage)[1:]:
        pts.append(centre + np.array([-rayon_courbure * np.cos(a), 0.0,
                                      rayon_courbure * np.sin(a)]))
        tan.append(np.array([np.sin(a), 0.0, np.cos(a)]))
    return np.array(pts), np.array(tan)


def mailler_tube(r_int, r_ext, pts, tan, n_theta, n_r):
    """Maillage hexaedrique structure, decoupe en tetraedres.

    Le coude etant un balayage, un maillage structure sort exact sans
    mailleur : a chaque station on pose un anneau de noeuds dans le plan
    normal a la tangente.
    """
    noeuds = []
    for p, t in zip(pts, tan):
        # repere local : t, plus deux vecteurs du plan de section
        u = np.cross(t, [0.0, 1.0, 0.0])
        u = u / np.linalg.norm(u) if np.linalg.norm(u) > 1e-9 else np.array([1.0, 0, 0])
        v = np.cross(t, u)
        for i in range(n_r + 1):
            r = r_int + (r_ext - r_int) * i / n_r
            for j in range(n_theta):
                a = 2 * np.pi * j / n_theta
                noeuds.append(p + r * (np.cos(a) * u + np.sin(a) * v))
    noeuds = np.array(noeuds)

    par_station = (n_r + 1) * n_theta
    def idx(s, i, j):
        return s * par_station + i * n_theta + (j % n_theta)

    tets, station_de = [], []
    # decoupe d'un hexaedre en 6 tetraedres (Freudenthal, conforme)
    motif = [(0, 1, 3, 7), (0, 1, 7, 5), (0, 5, 7, 4),
             (0, 3, 2, 7), (0, 2, 6, 7), (0, 6, 4, 7)]
    for s in range(len(pts) - 1):
        for i in range(n_r):
            for j in range(n_theta):
                h = [idx(s, i, j), idx(s, i, j + 1), idx(s, i + 1, j + 1), idx(s, i + 1, j),
                     idx(s + 1, i, j), idx(s + 1, i, j + 1), idx(s + 1, i + 1, j + 1),
                     idx(s + 1, i + 1, j)]
                for m in motif:
                    tets.append([h[k] for k in m])
                    station_de.append(s)
    return noeuds, np.array(tets), np.array(station_de)


# --------------------------------------------------------------------------
# Elasticite lineaire, tetraedres a 4 noeuds
# --------------------------------------------------------------------------
def matrice_hooke(e, nu):
    lam = e * nu / ((1 + nu) * (1 - 2 * nu))
    mu = e / (2 * (1 + nu))
    d = np.zeros((6, 6))
    d[:3, :3] = lam
    d[0, 0] = d[1, 1] = d[2, 2] = lam + 2 * mu
    d[3, 3] = d[4, 4] = d[5, 5] = mu
    return d


def gradients_tet(sommets):
    """Gradients des fonctions de forme et volume du tetraedre."""
    m = np.vstack([np.ones(4), sommets.T])          # 4x4
    detm = np.linalg.det(m)
    volume = detm / 6.0
    if abs(volume) < 1e-12:
        return None, 0.0
    inv = np.linalg.inv(m)
    return inv[:, 1:].T, volume                      # 3x4


def matrice_b(grad):
    b = np.zeros((6, 12))
    for k in range(4):
        gx, gy, gz = grad[:, k]
        b[0, 3 * k] = gx
        b[1, 3 * k + 1] = gy
        b[2, 3 * k + 2] = gz
        b[3, 3 * k] = gy; b[3, 3 * k + 1] = gx
        b[4, 3 * k + 1] = gz; b[4, 3 * k + 2] = gy
        b[5, 3 * k] = gz; b[5, 3 * k + 2] = gx
    return b


def resoudre(noeuds, tets, bloques, forces, e=E_MODULE, nu=NU):
    """Assemble et resout K u = f. Retourne deplacements et contraintes."""
    d = matrice_hooke(e, nu)
    n_ddl = 3 * len(noeuds)
    lignes, colonnes, valeurs = [], [], []
    bs, vols = [], []
    for tet in tets:
        grad, vol = gradients_tet(noeuds[tet])
        if grad is None:
            bs.append(None); vols.append(0.0); continue
        b = matrice_b(grad)
        ke = abs(vol) * (b.T @ d @ b)
        ddl = np.array([3 * n + c for n in tet for c in range(3)])
        lignes.append(np.repeat(ddl, 12)); colonnes.append(np.tile(ddl, 12))
        valeurs.append(ke.ravel())
        bs.append(b); vols.append(vol)
    k = coo_matrix((np.concatenate(valeurs),
                    (np.concatenate(lignes), np.concatenate(colonnes))),
                   shape=(n_ddl, n_ddl)).tocsr()

    libres = np.ones(n_ddl, dtype=bool)
    libres[np.array([3 * n + c for n in bloques for c in range(3)])] = False
    u = np.zeros(n_ddl)
    u[libres] = spsolve(k[libres][:, libres], forces[libres])

    sigma = np.zeros((len(tets), 6))
    for t, (tet, b) in enumerate(zip(tets, bs)):
        if b is None:
            continue
        ue = np.array([u[3 * n + c] for n in tet for c in range(3)])
        sigma[t] = d @ (b @ ue)
    return u.reshape(-1, 3), sigma


def tenseur(v):
    """Vecteur de Voigt -> tenseur 3x3."""
    sx, sy, sz, txy, tyz, txz = v
    return np.array([[sx, txy, txz], [txy, sy, tyz], [txz, tyz, sz]])


def contrainte_normale(sigma, normales):
    """n . sigma . n pour chaque element."""
    out = np.empty(len(sigma))
    for i, (s, n) in enumerate(zip(sigma, normales)):
        out[i] = n @ tenseur(s) @ n
    return out


# --------------------------------------------------------------------------
# Validation : poutre encastree contre Euler-Bernoulli
# --------------------------------------------------------------------------
def valider_poutre(n_long=24, n_theta=12, n_r=2):
    """Poutre tubulaire droite, charge en bout. Compare a la theorie."""
    longueur, r_int, r_ext, charge = 100.0, 4.0, 6.0, 10.0
    pts = np.array([[0.0, 0.0, z] for z in np.linspace(0, longueur, n_long + 1)])
    tan = np.tile([0.0, 0.0, 1.0], (len(pts), 1))
    noeuds, tets, _ = mailler_tube(r_int, r_ext, pts, tan, n_theta, n_r)

    bloques = np.where(noeuds[:, 2] < 1e-6)[0]
    bout = np.where(noeuds[:, 2] > longueur - 1e-6)[0]
    forces = np.zeros(3 * len(noeuds))
    for n in bout:
        forces[3 * n] = charge / len(bout)          # effort selon +X

    u, _ = resoudre(noeuds, tets, bloques, forces)
    fleche = float(np.abs(u[bout, 0]).mean())
    inertie = np.pi * (r_ext ** 4 - r_int ** 4) / 4.0
    theorie = charge * longueur ** 3 / (3 * E_MODULE * inertie)
    ecart = abs(fleche - theorie) / theorie * 100
    print(f"  Validation poutre encastree ({len(tets)} tetraedres)")
    print(f"    fleche calculee {fleche:.4f} mm   theorie {theorie:.4f} mm"
          f"   ecart {ecart:.1f} %")
    return ecart


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--valider", action="store_true",
                    help="ne lancer que la validation du solveur")
    ap.add_argument("--chunks", type=int, default=6)
    ap.add_argument("--n-long", type=int, default=48)
    ap.add_argument("--n-theta", type=int, default=16)
    ap.add_argument("--n-r", type=int, default=2)
    args = ap.parse_args()

    ecart = valider_poutre()
    if args.valider:
        return 0 if ecart < 15.0 else 1

    r_int, r_ext, r_courbure, angle, base = 4.0, 6.0, 30.0, 90.0, 12.0
    pts, tan = chemin_coude(r_courbure, angle, base, args.n_long)
    noeuds, tets, station = mailler_tube(r_int, r_ext, pts, tan,
                                         args.n_theta, args.n_r)
    print(f"\n  Coude creux : {len(noeuds)} noeuds, {len(tets)} tetraedres")

    bloques = np.where(noeuds[:, 2] < 1e-6)[0]
    bout = np.argsort(-noeuds[:, 0])[:args.n_theta * (args.n_r + 1)]
    forces = np.zeros(3 * len(noeuds))
    for n in bout:
        forces[3 * n + 2] = -10.0 / len(bout)       # charge verticale en bout
    u, sigma = resoudre(noeuds, tets, bloques, forces)
    print(f"  fleche en bout : {np.abs(u[bout, 2]).mean():.3f} mm")

    # champs d'orientation : normale de couche par element
    n_3axes = np.tile([0.0, 0.0, 1.0], (len(tets), 1))
    bornes = np.linspace(0, len(pts) - 1, args.chunks + 1)
    n_multi = np.empty((len(tets), 3))
    for t, s in enumerate(station):
        k = int(np.searchsorted(bornes, s, side="right") - 1)
        n_multi[t] = tan[min(int(bornes[min(k + 1, args.chunks)]), len(tan) - 1)]

    for nom, normales in (("3 axes", n_3axes), ("multidirectionnel", n_multi)):
        sn = contrainte_normale(sigma, normales)
        print(f"  {nom:18s} contrainte inter-couches : "
              f"max {sn.max():8.3f} MPa   p99 {np.percentile(sn, 99):8.3f} MPa")
    sn3 = contrainte_normale(sigma, n_3axes)
    snm = contrainte_normale(sigma, n_multi)
    print(f"\n  gain sur le pic  : {(sn3.max()-snm.max())/sn3.max()*100:+6.1f} %")
    print(f"  gain sur le p99  : "
          f"{(np.percentile(sn3,99)-np.percentile(snm,99))/np.percentile(sn3,99)*100:+6.1f} %")
    return 0


if __name__ == "__main__":
    sys.exit(main())
