# Gestionnaire de sauvegardes Primitier

Ce projet fournit une petite interface graphique pour ranger les sauvegardes de Primitier par monde, au lieu de se limiter aux slots du jeu.

## Ce que fait le programme

- Il affiche les slots du jeu (`save1.dat` à `save8.dat`) avec, pour chacun, le nom du monde, la seed, le mode (Créatif ou Survie), la date et la taille.
- Il permet de donner un nom à un monde : un dossier `Worlds/<nom>/` est créé, avec un fichier `seed.txt` qui contient la seed du monde.
- Il déplace une save d'un slot vers le dossier de son monde, ce qui libère le slot.
- Il recopie une save rangée vers un slot pour y rejouer.
- Il supprime une save, en l'envoyant à la corbeille Windows.
- Il propose un mode VR, avec une interface grossie pour être utilisable dans le casque.

## Lancer le programme

```
py save_manager.py
```

Il faut Python 3.6 ou plus récent, sous Windows. Aucune bibliothèque à installer : le programme n'utilise que la bibliothèque standard (dont `tkinter`).

Le script peut être rangé et lancé depuis n'importe quel dossier : il retrouve tout seul le dossier `Documents\Primitier\Saves` de l'utilisateur Windows courant.

Évite de déplacer, copier ou supprimer des saves pendant que le jeu tourne.

## Comment s'en servir

La fenêtre a deux panneaux : les slots du jeu à gauche, tes mondes à droite.

### Slots du jeu (à gauche)

- **Nommer ce monde** : donne un nom au monde de la save sélectionnée et crée son dossier. Si le monde a déjà un nom, ça le renomme.
- **Déplacer dans son monde →** : range la save dans le dossier de son monde. Si le monde n'a pas encore de nom, le programme le demande à ce moment-là. Un double-clic sur un slot fait la même chose.
- **Supprimer** : envoie la save du slot à la corbeille, après confirmation.
- **Actualiser** : relit les slots et les mondes, par exemple après avoir sauvegardé dans le jeu.

### Mes mondes (à droite)

Chaque monde s'affiche avec sa seed, et se déplie pour montrer les saves rangées dedans.

- **← Copier vers un slot** : copie la save sélectionnée dans le slot de ton choix. La save rangée reste dans le monde. Si le slot est déjà occupé, le programme demande confirmation avant de l'écraser.
- **Renommer** : renomme le monde (et son dossier).
- **Supprimer** : envoie la save rangée sélectionnée à la corbeille, après confirmation. Le dossier du monde et son `seed.txt` restent en place.
- **Ouvrir le dossier** : ouvre le dossier du monde dans l'explorateur Windows.

### Mode VR

Le bouton **Mode VR**, en haut à droite, active ou désactive une interface pensée pour le casque :

- le texte et les boutons sont grossis ;
- une barre de défilement large apparaît à côté de chaque liste ;
- la fenêtre passe en plein écran.

Le mode n'est pas mémorisé : le programme s'ouvre toujours en mode normal.

Les fenêtres de confirmation (Oui / Non) sont celles de Windows et gardent leur taille normale. Pour taper le nom d'un monde ou un numéro de slot, il faut un clavier.

## Comment les saves sont rangées

Un monde est reconnu par sa seed. Une save va toujours dans le dossier du monde qui a la même seed : impossible de la ranger dans le mauvais monde.

```
Saves/
├── save1.dat ... save8.dat      slots du jeu
└── Mondes/
    └── <nom du monde>/
        ├── seed.txt             seed du monde
        └── save_2026-07-06_04h47.dat
```

- Une save rangée est renommée d'après sa date de dernière modification. Si deux saves ont la même date, un numéro est ajouté (`_2`, `_3`...).
- Pour ajouter un monde à la main, il suffit de créer un dossier dans `Mondes/` avec un `seed.txt` contenant la seed.
- Un dossier sans `seed.txt` valide est ignoré par le programme.

## Format des saves

Les fichiers `.dat` sont du JSON compressé en gzip. Le programme ne lit que le début du fichier, où se trouvent la seed (`"seed"`) et le mode (`"isCreativeMode"`). Il ne modifie jamais le contenu d'une save.

## Réglages

Quelques constantes en haut de `save_manager.py` :

| Constante | Rôle | Valeur |
|---|---|---|
| `NOMBRE_SLOTS` | Nombre de slots affichés | `8` |
| `DOSSIER_SAVES` | Dossier des saves du jeu | `Documents\Primitier\Saves` |
| `DOSSIER_MONDES` | Dossier où sont rangés les mondes | `Saves\Mondes` |
| `ECHELLE_VR` | Grossissement du mode VR | `1.75` |
| `LARGEUR_DEFILEMENT_VR` | Largeur des barres de défilement en VR (pixels) | `40` |
