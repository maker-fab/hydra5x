# HYDRA5X — la machine, en un seul endroit

`decisions.md` est un journal : il garde les erreurs, les revirements et
les raisons. Ce fichier-ci ne garde que **l'état courant**. Chaque ligne
renvoie à la décision qui la porte.

---

## La ligne

> **La pièce ne bouge jamais. Ce qui s'oriente doit être le plus petit et
> le plus léger possible.**

Tout le reste en découle. Quand un choix hésite, c'est cette phrase qui
tranche.

---

## La machine

| | valeur | d'où ça vient |
|---|---|---|
| plateau | **fixe, plat, chauffant**, 400 mm | D30 |
| mouvement du plateau | Z seulement, jamais d'orientation | D30 |
| orientation | **platine inclinable sur la tête** | D30 |
| mécanisme de la platine | **pivot central + 3 biellettes** | tete-concepts |
| joint central | cardan à roulements préchargés — **pas un flexible** | tete-concepts |
| rayon des points d'attaque | 45 mm | tete-concepts |
| inclinaison visée | **35°** | D16, D24 |
| course des actionneurs | **54,6 mm** (`√3·R·tan θ`) | D25 |
| résolution exigée | **136 µm** pour 0,1° à la platine | D20 |
| bâti | CoreXY ordinaire, aucune pièce usinée | D23 |
| moteurs | X, Y, Z + 3 actionneurs = **6 pour 5 degrés** | D30 |
| firmware | Klipper en indexé ; RRF à réexaminer pour le continu | D3, emprunts |

### La taille, qui n'était pas encore arrêtée

La tête inclinée déborde de 112,7 mm de part et d'autre de la buse. Le
cadre doit donc contenir la pièce **plus deux fois ce débord** :

| inclinaison | débord | pièce 150 | pièce 200 | pièce 250 |
|---|---|---|---|---|
| 15° | 81,2 mm | 312 | 362 | 412 |
| 25° | 98,1 mm | 346 | 396 | 446 |
| **35°** | **112,7 mm** | 375 | **425** | 475 |

**Un bâti de 400 mm ne donne que ~175 mm de pièce à 35°.** Pour une pièce
de 200, il faut **425 mm**. C'est le vrai dimensionnement, et il n'avait
pas encore été posé.

---

## Les cinq choix, et la mesure qui les porte

**1. La pièce ne bascule pas.** La faire basculer coûte 60 à 77 % du
volume, 70 % de hauteur de bâti, et met 750 W de chauffage sur une
articulation mobile. En prime, l'inertie de l'organe orienté va de 1 à
198 selon qu'on bouge la tête ou le plateau — et seul un organe léger
pourra un jour suivre un tranchage continu. *(D19, D21, D29)*

**2. La gravité n'interdit rien.** L'argument qui avait fait retenir le
plateau basculant n'existe pas : nombre de Bond **0,011** à 45°, dérive du
cordon **0,01 µm**, robuste sur quatre matériaux, quatre décades de
viscosité, et une fois le plateau chauffant intégré par loi WLF. *(D29)*

**3. Le pivot est au centre, pas réparti.** Trois rotules rigides sur
trois verticales se bloqueraient — un plateau rigide garde ses distances
entre points. Un cardan central porteur libère le degré latéral par
construction, définit le pivot au lieu de le subir, et encaisse l'effort
de dépôt dans une seule pièce. *(D25, tete-concepts)*

**4. Le joint est mécanique, pas flexible.** Un col flexible atteignant
35° demande 102 à 305 mm de longueur libre selon le matériau ; il en reste
80 entre la platine et la pointe. Un col qui tient dans 40 mm plafonne à
14° (robuste) ou 28° (fragile). *(tete-concepts)*

**5. Les actionneurs sont irréversibles.** Vis sans fin ou vis
trapézoïdale. En indexé ils peuvent être très démultipliés, donc raides et
sans jeu sous charge, et ils tiennent la position moteur coupé. *(D30,
mouvements)*

---

## Ce qui est écrit, testé, et tourne

```
pièce → découpe multidirectionnelle → chunks posés à plat
      → PrusaSlicer (3 axes) → transposition dans le repère machine
      → couture 5 axes → contrôle de collision
```

- **12 contrôles sur 12**, écarts au niveau du flottant.
- La transposition vérifiée sur **32 054 points d'extrusion** : 100 %
  déposent dans la pièce.
- Trois machines cibles au choix (`--machine berceau|3points|platine`) —
  le contrat machine est un commutateur, pas une réécriture.
- Modèle CAO paramétrique qui **importe la même cinématique que le
  G-code** : aucune dérive possible entre le dessin et la commande.

---

## Ce qui reste ouvert, par ordre

1. **Dessiner la platine et son cardan central.** Le point dur est le
   passage du filament à travers un joint qui occupe l'axe.
2. **Choisir l'actionneur** — vis, courroie ou biellette poussée. Les
   136 µm sont atteignables par les trois ; le jeu, non.
3. **Vérifier la raideur** sous effort de dépôt et verrouillage d'outil.
   `fea_bending.py` existe. Tolérance dure : **0,1° = 0,12 mm à la
   pointe**.
4. **La chaîne continue** — S4 Slicer sur notre pièce, bloquée au plancher
   TetGen. *C'est là qu'est le gain de 2 à 3× en résistance, et la seule
   raison de préférer une tête légère.*
5. **Klipper ou RepRapFirmware**, avant d'acheter l'électronique.
6. Le matériel.

L'essai de dépôt incliné (pièce et protocole prêts, 1 h 30 de machine)
reste au catalogue en **confirmation**. Il ne bloque plus rien.

---

## Ce qui est écarté, pour ne pas y revenir

| écarté | pourquoi, en un chiffre |
|---|---|
| plateau basculant | 60 à 77 % du volume, inertie 39× |
| portique basculant | même dépôt incliné, inertie 55 à 198× |
| marier deux bascules | les encombrements s'**additionnent** ; le 50/50 est la posture la plus chère |
| colonnes de vérins sur la platine | 53 mm de course perdus pour aucun gain |
| cardan série (chape) | silhouette 33,7°, sous la cible de 35° — à reprendre si l'encombrement devient le point dur |
| pivot flexible à 35° | 102 à 305 mm de col, il en reste 80 |
| quatre points d'appui | hyperstatique ; un plan tient sur trois |
| ré-entrants au-delà de 90° | hors périmètre de la v1 |

---

## Ce que le projet apporte, et qui n'existe nulle part

- le **test de collision buse-pièce**, qu'aucun slicer ne fait ;
- la **couture inter-chunks** avec neutralisation de la première couche ;
- la **transposition du G-code** vers le repère machine d'une tête
  inclinable ;
- un **critère de faisabilité** d'une pièce sur cette classe de machine.

Partout ailleurs, il vaut mieux emprunter — c'est le rôle de
`emprunts.md`.
