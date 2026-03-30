# Régimes de temps toute saison

## Description
Le but du projet est de faire un site web de suivi quotidien des régimes de temps toute saison. Le code est à disposition sur le git et voici le [lien du site](http://sotrtm38-sidev/~voisinl/menu.html) (disponible uniquement en interne pour l'instant).

## Visuals
Depending on what you are making, it can be a good idea to include screenshots or even a video (you'll frequently see GIFs rather than actual videos). Tools like ttygif can help, but check out Asciinema for a more sophisticated method.

## Installation
### Mise en place pour récupérer le git :

Nous utilisons **python 3.12.3** (utiliser pyenv pour changer de version si besoin)

1) Se placer dans un dossier racine sur votre machine et ouvrir un terminal (par exemple : Projet EMI)
2) Cloner le dépot git :

```
git clone https://git.meteo.fr/voisinl/regimes-de-temps-toutes-saisons.git
cd regimes-de-temps-toutes-saisons
```

3) Créer un environnement virtuel compatible (dans le dossier : regimes-de-temps-toutes-saisons)

Sous linux :

```
python3 -m venv .venv #créer l'environnement
source .venv/bin/activate #activer l'environnement
pip install -r requirements.txt #installer les librairies necessaires
```

## Arborescence
Après avoir cloné le dépot git, vous devriez avoir cette arborescence là : 
```

📁 regimes-de-temps-toutes-saisons/
├── 📄 README.md
├── 📄 requirements.txt
├── 📄 .gitignore
├── 📁 scripts/
│   ├── 📄 data_maker.py
│   ├── 📄 plotting_from_data.py
│   ├── 📄 plotting_composite.py
│   ├── 📄 suivi_climatique.py
│   └── 📁 donnees_sauvegardees/
├── 📁 data/
└── 📁 archives/
    ├── 📁 composites/
    ├── 📁 images_suivi_climatique/
    └── 📁 images_suivi_quotidien/
```

Pour récupérer les data qui doivent être placées dans le dossier data, il faut aller sur le Climate Data Store et prendre les fichiers suivants.



## Usage
Pour obtenir les images, voici les étapes à suivre : 
- récupérer les données et les mettre dans le dossier data
- lancer le fichier data_maker.py -> stock toutes les données utiles aux plots pour la suite dans le dossier donnees_sauvegardees
- lancer le fichier plotting_from_data.py (long) -> permet de sauvegarder les graphiques mensuels et annuels des indices de régimes dans le dossier images_suivi_quotidien
- lancer le fichier plotting_composite.py (long) -> permet de sauvegarder l'ensemble des composites dans le dossier composites
- lancer le fichier suivi_climatique.py -> permet de sauvegarder les graphiques de suivi dans le dossier images_suivi_climatique

Si seulement la détermination des clusters et des indices vous interesse, le script qui vous est utile est data_maker.py

## Support
Si vous avez des questions, voici les personnes à contacter
- oscar.lorans@meteo.fr
- killian.mounier@meteo.fr
- louis.voisin@meteo.fr
- margaux.verly@meteo.fr

## Roadmap
On a également intégré un suivi quotitien des régimes toutes saisons interne à Météo-France sur un site web.

## Contributing
Pour le moment le projet est fini et nous n'allons pas explorer plus loin.

## Authors and acknowledgment
Nos encadrants qui nous ont bien aidé sur le projet :
- Frédéric Ferry
- Onaïa Savary
- Frédéric Gayrard
- Alexis Querin
- Julien Cattiaux
- Roland Amat-Boucq

## License
Vous êtes libre de reprendre notre code en nous mentionnant.

## Project status
Preque terminé
