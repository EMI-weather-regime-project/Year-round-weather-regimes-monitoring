# Régimes de temps toute saison

## Description
L’objectif du projet est d’implémenter la méthode de calcul des régimes de temps « toutes saisons » sur l’Atlantique nord puis de faire un site web en temps réel de produits de suivi climatique et quotidien des régimes de temps toutes saisons. Le code est à disposition sur le git et voici le [lien du site](http://sotrtm38-sidev/~voisinl/menu.html) (disponible uniquement en interne pour l'instant).

## Visuals
Depending on what you are making, it can be a good idea to include screenshots or even a video (you'll frequently see GIFs rather than actual videos). Tools like ttygif can help, but check out Asciinema for a more sophisticated method.

## Installation
### Mise en place pour récupérer le git :

Nous utilisons **python 3.12.3** (utiliser pyenv pour changer de version si besoin)

1) Se placer dans un dossier racine sur votre machine et ouvrir un terminal (par exemple : Projet EMI)
2) Cloner le dépot git :

```
git clone https://github.com/EMI-weather-regime-project/Year-round-weather-regimes-monitoring.git
cd Year-round-weather-regimes-monitoring
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

📁 Year-round-weather-regimes-monitoring/
├── 📄 README.md
├── 📄 requirements.txt
├── 📄 .gitignore
├── 📁 scripts/
│   ├── 📄 data_maker.py
│   ├── 📄 daily-tasks.py
│   ├── 📄 plotting_monitoring.py
│   ├── 📄 plotting_composites.py
│   ├── 📄 plotting_suivi_climatique.py
│   ├── 📄 recuperer_donnees_manuellement.py
│   ├── 📄 recuperer_nouvelles_donnees.py
│   └── 📁 donnees_sauvegardees/
├── 📁 data/
│   ├── 📁 climatologie/
│   └── 📁 donnees_quotidiennes/
│   │   ├── 📁 AnaCEP/
│   │   └── 📁 ERA5/
├── 📁 html/
│   ├── 📄 cartes_composites.html
│   ├── 📄 menu.html
│   ├── 📄 style.css
│   ├── 📄 suivi_climatique.html
│   └── 📄 suivi_quotidien.html
└── 📁 archives/
    ├── 📁 images_composites/
    ├── 📁 images_documentation/
    ├── 📁 images_suivi_climatique/
    └── 📁 images_monitoring/
        ├── 📁 AnaCEP/
        └── 📁 ERA5/
```

Pour récupérer les data qui doivent être placées dans le dossier data, il faut aller sur le Climate Data Store et prendre les fichiers suivants.



## Usage
Pour obtenir les images, voici les étapes à suivre : 
1) Récupérer les données et les mettre dans le dossier data
2) Lancer le fichier data_maker.py -> stock toutes les données utiles aux plots pour la suite dans le dossier donnees_sauvegardees
```
cd scripts
python3 data_maker.py
```
3) Lancer le fichier plotting_monitoring.py (long) -> permet de sauvegarder les graphiques mensuels et annuels des indices de régimes dans le dossier images_monitoring
```
python3 plotting_monitoring.py
```
4) Lancer le fichier plotting_composites.py (long) -> permet de sauvegarder l'ensemble des composites dans le dossier images_composites
```
python3 plotting_composites.py
```
5) Lancer le fichier plotting_suivi_climatique.py -> permet de sauvegarder les graphiques de suivi dans le dossier images_suivi_climatique
```
python3 plotting_suivi_climatique.py
```

Si vous êtes uniquement intéressé par la détermination des clusters et des indices de régime, le script qui vous est utile est data_maker.py

## Support
Si vous avez des questions, voici les personnes à contacter :
- oscar.lorans@meteo.fr
- killian.mounier@meteo.fr
- louis.voisin@meteo.fr
- margaux.verly@meteo.fr

## Roadmap
On a également intégré un suivi quotitien des régimes toutes saisons interne à Météo-France sur un site web.

## Contributing
Pour le moment le projet est fini et nous n'allons pas explorer plus loin.

## Authors and acknowledgment
Nos encadrants qui nous ont apporté une grande aide sur le projet :
- Frédéric Ferry
- Onaïa Savary
- Frédéric Gayrard
- Alexis Querin
- Julien Cattiaux
- Roland Amat-Boucq

## License
Vous êtes libre de reprendre notre code en nous mentionnant.

## Project status
Presque terminé
