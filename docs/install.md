# Parcours d'installation — de zéro au premier G-code

Ce parcours installe la **chaîne logicielle**. Il ne demande aucune
machine : tout se vérifie par le calcul et le G-code produit. Compter
15 minutes.

## Plateformes

| | Linux | macOS | Windows |
|---|---|---|---|
| Cœur de slicing (headless) | **vérifié** | attendu | attendu |
| Cinématique C++ | **vérifié** | attendu | attendu |
| Export DXF | **vérifié** | attendu | attendu |
| GUI Cortex (préparation/visu) | **vérifié** | à risque | attendu |
| `tools/gui_shot.sh` | X11 seulement | — | — |

**vérifié** = exécuté et mesuré sur Debian/Ubuntu, Python 3.12.
**attendu** = toutes les dépendances publient des wheels pour cette
plateforme et le code n'a rien de spécifique à l'OS, mais ce dépôt ne l'a
pas exécuté. **à risque** = `pyglet 1.5` pilote Cocoa en `ctypes` et OpenGL
est déprécié sous macOS ; le GUI y est le seul élément dont l'échec est
plausible. Le slicing, lui, ne dépend pas du GUI.

**Le slicing headless est obligatoire sur les trois OS** — pas seulement
sous Linux. Le figeage du GUI (`decisions.md` D4) vient de la
ré-initialisation du module principal dans les workers ; sous Windows et
macOS la méthode de démarrage par défaut est déjà `spawn`, donc le même
mur, atteint plus tôt.

Toutes les commandes ci-dessous s'écrivent identiquement sur les trois OS,
**sauf l'activation du venv** :

```bash
source .venv/bin/activate      # Linux / macOS
```
```powershell
.venv\Scripts\Activate.ps1     # Windows PowerShell
```

---

## 0. Prérequis système

```bash
sudo apt install -y python3-venv python3-dev build-essential git   # Debian / Ubuntu
```
```bash
xcode-select --install                                              # macOS
```
```powershell
winget install Python.Python.3.12 Git.Git                           # Windows
```

Sous Windows, aucun compilateur C++ n'est nécessaire pour le slicing.
Pour la cinématique, il faut **Visual Studio Build Tools** (charge de
travail « Développement Desktop en C++ »).

Pour le GUI de Cortex uniquement, sous Linux :

```bash
sudo apt install -y libgl1 libglu1-mesa
```

---

## 1. Récupérer le slicer

```bash
git clone https://github.com/maker-fab/hydra5x-slicer.git cortex
```

C'est tout — les correctifs sont dans le dépôt, il n'y a plus rien à
patcher.

[HYDRA5X Slicer](https://github.com/maker-fab/hydra5x-slicer) est un fork
maintenu de [Fractal Cortex](https://github.com/fractalrobotics/Fractal-Cortex),
créé par Fractal Robotics. L'amont est inactif depuis juillet 2025 et son
code **ne démarre pas sous Linux** en l'état : quatre chemins de
ressources sont écrits avec une casse qui ne correspond pas aux fichiers
réels. Sans effet sur un système de fichiers insensible à la casse
(Windows, macOS par défaut), bloquant sous Linux.

Le fork corrige aussi le masquage d'erreurs, les caps dégénérés et les
refus de collision opaques. Détail dans
[`cortex-notes.md`](cortex-notes.md), et les correctifs restent proposés
en amont via la [PR #4](https://github.com/fractalrobotics/Fractal-Cortex/pull/4).

Le dossier s'appelle toujours `cortex` : les scripts de ce dépôt l'y
cherchent.

---

## 2. Environnement Python

```bash
python3 -m venv cortex/.venv
source cortex/.venv/bin/activate          # Windows : cortex\.venv\Scripts\Activate.ps1
pip install -r tools/requirements-cortex-headless.txt
```

**Ne pas installer depuis le README de Cortex** : il omet cinq dépendances
(`scipy`, `manifold3d`, `networkx`, `rtree`, `mapbox_earcut`) et
l'installation échoue immédiatement.

Les versions sont épinglées pour une raison : `scipy` récent tire
`numpy>=2`, or `trimesh 4.3.1` utilise `ndarray.ptp()`, supprimé dans
NumPy 2.

Vérifier :

```bash
python3 -c "import numpy, scipy, trimesh, shapely, manifold3d; print(numpy.__version__, trimesh.__version__)"
```

Attendu : `1.26.4 4.3.1`.

---

## 3. Premier slicing

```bash
python3 tools/test_slice.py
```

Produit deux G-code dans `results/gcode/` : un cube en 1 direction
(3 axes), puis une pièce en Y en 3 directions — le cas qui justifie le
multidirectionnel.

Sortie attendue :

```
cube 1 direction  ->  7 818 lignes, 2 rotations
Y 3 directions    ->  100 499 lignes, 5 rotations
Resultat : 2/2 slicings aboutis
```

Valeurs exactes, vérifiées sur dépôt vierge. Un écart signale un problème
d'environnement — vérifier les versions à l'étape 2.

Les lignes `MANUAL_STEPPER` dans le G-code sont les réorientations entre
chunks.

**« Slicing abouti » ne veut pas dire « imprimable ».** Ce G-code est
produit sans erreur, mais la buse y percute la pièce déjà déposée : voir
l'étape 5. Cortex ne teste que la garde plateau-buse, jamais la collision
avec la matière. C'est une limite du slicer, pas de l'installation.

---

## 4. Régression complète

```bash
python3 tools/test_limits.py
```

Six cas, du cube à un Y en cylindres. **Score attendu : 3/6.** Les trois
échecs sont normaux et nommés — ils butent tous sur la garde plateau-buse
de 12 mm. Voir [`envelope.md`](envelope.md).

Un échec qui ne nomme ni son plan de coupe ni sa cause est un bug des
correctifs, pas une fatalité.

---

## 5. Collision buse-pièce

```bash
python3 tools/stitch_chunks.py --prusa /usr/bin/prusa-slicer
python3 tools/check_collision.py results/gcode/y_cousu.gcode
```

**Sortie attendue : 2 chunks en collision.** C'est le résultat correct, pas
une panne — il démontre que la pièce de démonstration n'est pas imprimable
telle qu'elle est découpée, et que l'outil le détecte.

```
chunk 1 : penetration max 4.632 mm   [COLLISION]
chunk 2 : penetration max 4.333 mm   [COLLISION]
```

Un dépistage par carte de hauteurs parcourt tous les points du trajet, puis
un lancer de rayons sur le maillage réel confirme le pire. Raisonnement,
modèle de buse et résultats du balayage dans
[`decisions.md`](decisions.md) D9.

`tools/sweep_decomposition.py` balaie inclinaison et hauteur de coupe :
**aucune découpe non dégénérée du Y ne passe**. La parade n'est pas dans
les paramètres.

---

## 6. Cinématique — vérification indépendante

Le build passe par CMake : c'est la seule voie qui marche sur les trois OS
(Windows n'a pas de `g++`). CMake s'installe par pip, sans droits admin.

```bash
pip install cmake
cd kinematics
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release
./sanity_test                             # Windows : .\sanity_test.exe
```

Attendu : `OK: 4/4 cas passent`.

Les binaires sont déposés à côté des sources quel que soit le générateur,
donc `compare.py` les trouve sans configuration :

```bash
python3 compare.py
```

Attendu : `OK: reference et implementation independante concordent, auto-coherente.`

C'est l'extraction corrigée de la cinématique `PENTA_AXIS_HH` de Marlin.
Le firmware amont contient deux bugs que ce harnais a permis de trouver
([Marlin2ForPipetBot #76](https://github.com/DerAndere1/Marlin2ForPipetBot/issues/76)).

`test_firmware.py` compare en plus au firmware compilé. Il s'appuie sur
l'environnement PlatformIO `linux_native`, donc **Linux et macOS
seulement** ; le reste de la vérification ne l'exige pas.

Sous Linux et macOS, un appel direct au compilateur reste possible :

```bash
g++ -O2 -std=c++17 rep5x_ik.cpp sanity.cpp -o sanity_test
```

---

## 7. Interface graphique — optionnelle

```bash
cd cortex/fractal-cortex && python3 slicer_main.py
```

L'interface sert à **préparer et visualiser** : charger un STL, placer les
plans de coupe, contrôler le résultat.

**Ne pas slicer depuis le GUI**, sur aucun OS. Le calcul se fige — voir
[`decisions.md`](decisions.md) D4. Utiliser les scripts headless.

---

## 8. DXF pour devis de découpe

Si tu construis la machine, il faut les profils plats pour consulter un
découpeur laser. La CAO de Fractal est un assemblage STEP 3D.

**Environnement séparé obligatoire.** `cadquery` tire `numpy>=2`, or
`trimesh 4.3.1` utilise `ndarray.ptp()`, supprimé dans NumPy 2. Les deux
chaînes ne cohabitent pas dans le même venv.

```bash
deactivate
python3 -m venv .venv-dxf
source .venv-dxf/bin/activate             # Windows : .venv-dxf\Scripts\Activate.ps1
pip install -r tools/requirements-dxf.txt
```

Récupérer la CAO — en Python plutôt qu'en `curl`/`unzip`, qui ne sont pas
présents partout :

```bash
python3 -c "
import urllib.request, zipfile, io, pathlib
url = 'https://github.com/fractalrobotics/Fractal-5-Pro/raw/main/CAD/Fractal_5_Pro_Assembly.zip'
pathlib.Path('build').mkdir(exist_ok=True)
with urllib.request.urlopen(url, timeout=120) as r:
    zipfile.ZipFile(io.BytesIO(r.read())).extractall('build')
print('CAO extraite dans build/')"
```

```bash
# Pieces en tole alu 1/8" — ~15 min au premier passage
python3 tools/export_dxf.py --step build/Fractal_5_Pro_Assembly.stp \
    --out fabrication/dxf-alu --thickness 3.175

# Panneaux de caisson
python3 tools/export_dxf.py --step build/Fractal_5_Pro_Assembly.stp \
    --out fabrication/dxf-caisson --thickness 3.0 --tol 0.05
```

Attendu : **11 profils alu (0,233 m²)** et **16 panneaux (2,301 m²)**.

Les DXF déjà extraits sont fournis dans `fabrication/` — ces commandes
servent à les régénérer ou à traiter une autre CAO.

---

## Ce qui ne marchera pas

À savoir **avant** d'investir dans le matériel :

- **le slicing depuis le GUI se fige** — headless obligatoire, sur les
  trois OS
- **aucun test de collision buse-pièce** dans Cortex : sur géométrie dense
  (réseau d'aubes, canaux), rien ne vérifie que la buse peut atteindre la
  zone sans toucher la matière déjà déposée
- **les pièces larges et plates sont hors enveloppe** : une roue radiale
  ouverte plafonne à 5° d'inclinaison — mesuré, voir
  [`envelope.md`](envelope.md)
- **la garde de 12 mm est codée en dur** et borne tout : à mesurer sur ta
  machine et à ajuster

---

## Provenance

| Composant | Origine | Licence |
|---|---|---|
| Slicer Cortex | [fractalrobotics/Fractal-Cortex](https://github.com/fractalrobotics/Fractal-Cortex) | GPL-3.0 |
| Machine, CAO, BOM | [fractalrobotics/Fractal-5-Pro](https://github.com/fractalrobotics/Fractal-5-Pro) | GPL-3.0 |
| Cinématique de référence | dérivée de [DerAndere1/Marlin](https://github.com/DerAndere1/Marlin), branche `Marlin2ForPipetBot` | GPL-3.0 |
| Correctifs, outillage, mesures | ce dépôt | GPL-3.0 |

Le guide d'assemblage mécanique est celui de Fractal. Ce dépôt ne le
duplique pas — il fournit ce qui manquait autour.
