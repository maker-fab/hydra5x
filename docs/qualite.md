# Exigence de qualité — aspect et technique

Ce fichier n'est pas une intention, c'est un **critère de réception**.
Chaque ligne dit ce qui est exigé et **comment on le vérifie**. Ce qui ne
se mesure pas ne figure pas ici.

La règle de fond : *maker* qualifie la façon de construire, pas le niveau
de finition.

---

## 1. Tout imprimer — et que ça se voie

**Correction d'une version précédente de ce fichier.** Elle exigeait de
l'acier rectifié sur les portées de contact et présentait l'impression
intégrale comme un plafond. C'était faux sur les deux plans :

- **les 71 pièces de DAKSH sont imprimées et ça tourne** — 2000
  changements d'outil sur leurs propres essais. Ce n'est pas une
  hypothèse ;
- une machine qui fabrique des machines **doit être faite par elle-même**.
  C'est l'argument le plus fort qu'un projet FDM puisse tenir, et le
  saboter avec des pièces tournées, c'est se priver de sa démonstration.

Le bon raisonnement n'est pas *plastique ou métal*, c'est **quel polymère
pour quelle sollicitation**. Les polymères techniques sont des matériaux
de palier depuis cinquante ans ; le problème n'a jamais été le plastique,
mais le mauvais plastique.

### Les trois propriétés qui décident, et qui ne sont pas sur une fiche de traction

| | pourquoi ça décide |
|---|---|
| **reprise d'humidité** | un PA6 qui gonfle de 1 % fait **1 mm sur 100**. Aucune répétabilité n'y survit. C'est le défaut des polyamides, et il est invisible sur un essai de traction |
| **fluage** | une pièce sous précharge permanente — ressort de verrouillage, bossage d'insert — se déforme lentement à charge constante. L'ASA flue notablement dès 60 °C |
| **usure** | au contact répété. Les polyamides et le PPS sont autolubrifiants |

`tools/filaments.py` les porte désormais toutes les trois.

### Ce que le croisement donne

Un seul matériau figure dans **toutes** les listes de candidats :

| poste | candidats |
|---|---|
| Gantry / Dock — portent les offsets | ASA-GF, PC-GF, **PPS-GF** |
| ToolLock, corps — chocs et inserts | ASA-GF, PA12-GF, PC-GF, **PPS-GF** |
| ToolLock, **contacts** — l'usure fait la référence | PA12-GF, **PPS-GF** |
| Bossages sous précharge — fluage | PC-GF, **PPS-GF** |
| Toolhead — isolant, près du bloc | ASA-GF, PC-GF, **PPS-GF** |

**Le PPS-GF passe partout** : 0,03 % de reprise d'eau, fluage 0,12,
usure 0,35, isolant, 200 °C de service, mat, teinte naturelle claire.
C'est la réponse techniquement irréprochable, et elle est entièrement
imprimée.

Son prix : **320-340 °C de buse et un caisson à 90-120 °C**. Il faut une
machine capable de l'imprimer.

Le **PC-GF** est la version atteignable : il passe partout sauf sur
l'usure (0,75). 290-310 °C, caisson à 60-70 °C, isolant, colorable, mat.

### Le plan qui résout l'amorçage

On ne peut pas imprimer du PPS avant d'avoir la machine qui l'imprime.
D'où une construction en deux temps, qui **est** la démonstration :

1. **Première monte en ASA-GF**, sur la Trident. Tout fonctionne, la
   machine est juste née d'un matériau ordinaire.
2. **Seconde monte en PPS-GF ou PC-GF**, imprimée **par la machine
   elle-même** une fois qu'elle tourne en caisson chaud. On remplace les
   pièces par poste, en mesurant à chaque fois les critères du §3.

Une machine qui se réimprime dans un matériau meilleur que celui qui l'a
vue naître : c'est exactement ce qu'une 5 axes FDM doit montrer, et aucune
pièce tournée ne le dirait à sa place.

**L'acier garde une seule place** : la visserie, les goupilles et les
rails, qui sont des composants du commerce et non des pièces du projet.

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
