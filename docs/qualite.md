# Exigence de qualité — aspect et technique

Ce fichier n'est pas une intention, c'est un **critère de réception**.
Chaque ligne dit ce qui est exigé et **comment on le vérifie**. Ce qui ne
se mesure pas ne figure pas ici.

La règle de fond : *maker* qualifie la façon de construire, pas le niveau
de finition.

---

## 1. Le levier principal : ne pas imprimer ce qui doit être usiné

C'est ce qui sépare une machine d'un prototype, avant toute question de
couleur ou d'état de surface.

**Le plastique imprimé n'a pas sa place dans une liaison de référence.**
Il flue sous charge maintenue, il se dilate trois fois plus que
l'aluminium, et il s'use au contact répété.

| pièce | matière exigée | pourquoi |
|---|---|---|
| contacts de l'accouplement d'outil | **acier rectifié** | contact répété, c'est LA référence de position |
| goupilles et portées de goupille | acier | 2000 cycles |
| appuis du plateau basculant | acier ou alu usiné | ils portent la planéité |
| support de rail linéaire | alu usiné ou profilé | la rectitude ne s'imprime pas |
| structure, capots, guidage de câbles | **imprimé, sans réserve** | c'est là que l'impression excelle |

DAKSH revendique « no machined parts required ». C'est son argument, et
c'est aussi son plafond. **Remplacer les seules portées de contact par des
inserts acier** est le meilleur rapport qualité/effort de tout le projet.

---

## 2. Ce qui se voit, par ordre d'impact

Dans l'ordre où un regard extérieur juge une machine :

1. **Le câblage.** Le signal le plus fort, et de loin. Chaînes porte-câbles
   ou gaines tressées, **connecteurs sur tous les départs** — jamais de
   domino ni de gaine thermo sur un fil nu —, faisceau étiqueté aux deux
   bouts, baie électronique sur platine démontable.
2. **Les panneaux.** Polycarbonate fumé ou composite aluminium. **Pas de
   panneau imprimé.** Découpe laser ou CNC, arêtes ébavurées.
3. **La cohérence.** Une seule famille de couleur, une seule matière
   visible, une seule texture. Une machine bariolée de restes de bobines
   se voit immédiatement.
4. **L'état de surface des pièces imprimées.** Voir §4.
5. **Les fixations.** Une seule empreinte, une seule classe de vis, aucune
   tête dépassante non voulue.

### Le schéma retenu

| | |
|---|---|
| profilés | aluminium **anodisé noir** |
| panneaux | polycarbonate fumé ; fond en composite alu |
| pièces imprimées | **ASA-GF, un seul gris clair**, mat |
| pièces métalliques | acier bruni ou alu anodisé noir |
| visserie | **inox, six pans creux**, une seule classe |

Deux matières visibles, deux couleurs. Rien d'autre.

---

## 3. Les critères techniques, et leur mesure

Aucun n'est déclaratif.

| critère | seuil | comment on le vérifie |
|---|---|---|
| répétabilité d'un changement d'outil | **< 0,05 mm** | 20 changements, palpage d'une bille de référence |
| jeu inversé, chaque axe | **< 0,02 mm** | comparateur, aller-retour sur 50 mm |
| perpendicularité X/Y | **< 0,05 mm sur 300** | impression d'une équerre, mesure à la règle de contrôle |
| planéité du plateau | **< 0,10 mm** | palpage en 25 points |
| répétabilité de l'inclinaison | **< 0,05°** | palpage de trois points du plateau, 10 allers-retours |
| dérive thermique entre étalonnages | **< 0,05 mm** | `tools/filaments.py` en conception, palpage en recette |
| bruit | < 55 dB(A) à 1 m | sonomètre, impression nominale |

Les quatre premiers sont les critères d'une machine-outil. Ils ne sont pas
excessifs pour une imprimante — ils sont simplement rarement mesurés.

---

## 4. Les pièces imprimées : ce qui fait la différence

| | exigence |
|---|---|
| hauteur de couche | 0,15 mm sur les faces vues, 0,2 ailleurs |
| parois | 4, et 5 dessus/dessous |
| remplissage | 40 %, gyroïde |
| **orientation** | **aucune face vue en contact avec un support** |
| **couture** | alignée, et rejetée sur une face non vue |
| pied d'éléphant | compensé, ou **chanfrein de 0,4 mm** sur la première couche |
| ébavurage | systématique, y compris les trous d'insert |
| inserts | posés à la presse, jamais au fer libre |

Le chanfrein de première couche vaut mieux que la compensation logicielle :
il donne une arête nette sans dépendre d'un réglage.

---

## 5. Ce que ça coûte, pour ne pas le découvrir après

- **Les pièces métalliques.** Le chiffrage Fractal donnait 150 à 370 € de
  découpe laser pour 17 pièces. Ici il en faut beaucoup moins — seulement
  les portées de contact et les appuis.
- **Le temps de finition.** Ébavurage, pose d'inserts, faisceau : compter
  autant que l'assemblage lui-même.
- **Une bobine unique.** Acheter toute la matière visible d'un coup, même
  lot — les teintes varient d'un lot à l'autre, et ça se voit.

---

## 6. Ce qui est déjà outillé pour ça

Le dépôt contient déjà de quoi tenir plusieurs de ces critères :

- `tools/export_dxf.py` — profils DXF depuis un STEP, pour faire découper
  les panneaux et les pièces plates ;
- `tools/fea_bending.py` — raideur d'une pièce avant de la fabriquer ;
- `tools/filaments.py` — dérive thermique selon la matière ;
- `cad/machine.py` — modèle paramétrique, donc cotes régénérables ;
- `tools/check_collision.py` — ce qui touche, avant d'imprimer.

Ce qui manque : **la recette**. Les mesures du §3 sont à faire sur la
machine, une fois montée, et à consigner ici.
