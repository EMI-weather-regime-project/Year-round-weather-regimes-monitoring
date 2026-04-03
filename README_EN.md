# Year-Round Weather Regimes

## Description
The objective of this project is to implement the calculation method for “year-round” weather regimes over the North Atlantic, and then to build a real-time website providing climate monitoring products and daily tracking of year-round weather regimes. The code is available on Git, and here is the website link (currently available internally only).
## Installation
### Setting up to clone the Git repository:

We use **python 3.12.3** (use pyenv to change versions if needed).

1) Go to a root directory on your machine and open a terminal (for example: Projet EMI)
2) Clone the Git repository:

```
git clone https://github.com/EMI-weather-regime-project/Year-round-weather-regimes-monitoring.git
cd Year-round-weather-regimes-monitoring
```

3) Create a compatible virtual environment (in the folder: Year-round-weather-regimes-monitoring)

On Linux:

```
python3 -m venv .venv  # create environment
source .venv/bin/activate # activate environment
pip install -r requirements.txt # install required libraries
```

## Project Structure
After cloning the repository, you should have the following structure:
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
    │   └── 📄 Recuperation_donnees_exemple.txt
    ├── 📁 images_suivi_climatique/
    └── 📁 images_monitoring/
        ├── 📁 AnaCEP/
        └── 📁 ERA5/
```
 

If you only want data for a few years, you can follow the methodology in the file "Récupération_donnees_exemple.txt", which explains the commands needed to download precipitation data from 2023 to 2025.
Otherwise, you can email us and we will send you the data 😉.



## Usage
To generate the images, follow these steps:
1) Retrieve the data and place it in the folder data/climatologie
2) Run the file data_maker.py -> stores all useful data for plotting in the donnees_sauvegardees folder. During execution, an image will be created in this folder showing cluster numbers, allowing you to guess quiz answers. Alternatively, you can find the solution in figure_cluster_init.png in the folder images_documentation in archives.
```
cd scripts
python3 data_maker.py
```
3) Run fichier plotting_monitoring.py (long) -> saves monthly and yearly regime index plots in the images_monitoring folder
```
python3 plotting_monitoring.py
```
4) Run plotting_composites.py (long) ->saves all composites in the images_composites folder
```
python3 plotting_composites.py
```
Since this script takes several hours to run, you can execute it in three parts:
```
gedit plotting_composites.py
```
Then, at the bottom of the file in the section “Application of figure generation functions”, uncomment (remove #) the lines corresponding to the figures you want to generate, and comment out the others.
For example, to generate terciles, leave the first three lines uncommented and comment the rest. Save your changes, then run:

```
python3 plotting_composites.py
```
Repeat as needed. Note: the last 9 lines can be executed in one go due to their faster execution.
5) Run plotting_suivi_climatique.py -> saves monitoring plots in the images_suivi_climatique folder
```
python3 plotting_suivi_climatique.py
```
Once finished, if you want histograms for the 1960–1990 period:
```
gedit plotting_suivi_climatique.py
```

At the bottom in the “Histogram generation” section, comment the line for 1991–2025 and uncomment the line for 1960–1990. Save and run again:
```
python3 plotting_suivi_climatique.py
```

If you are only interested in cluster determination and regime indices, use data_maker.py.

At this stage, you have generated all images for 1960–2025. To enable real-time website updates:

1) Make sure plotting_suivi_climatique.py has fully run and that all images are generated. You should have a climatologie.npy file in données_sauvegardées.


2) The easiest data to retrieve is ERA5. First, create a .cdsapirc file at the root of your system:
```
cd ~
touch .cdsapirc
```
Then create an account on the Climate Data Store, activate it, and add your API key to .cdsapirc:
```
gedit .cdsapirc
```

3) Run fichier recuperer_donnees_manuellement.py and choose missing dates (between 2025 and today). Due to filtering, the first 5 days will be removed, so choose a wider range.
```
cd scripts
python3 recuperer_donnees_manuellement.py
```

4) Then run:
```
python3 daily-tasks.py --datatype ERA5
```
This generates monitoring histograms for the last two months and the graphs of monitoring

5) If data is incomplete, modify relativedelta(days=5) in the script:
```
gedit daily-tasks.py
```

6) The script recuperer_nouvelles_donnees.py retrieves daily data. You can set up a cron job to automate it.
   
7) You can also run real-time monitoring with CEP analysis, but older data is harder to retrieve. Ideally, run the data retrieval script for 11 days before getting a curve (due to filtering):
```
python3 daily-tasks.py --datatype AnaCEP
```
8) Finally, open menu.html in your browser to explore the website.

## Support
If you have any questions, please contact:
- oscar.lorans@meteo.fr
- killian.mounier@meteo.fr
- louis.voisin@meteo.fr
- margaux.verly@meteo.fr

## Roadmap
We have also implemented internal daily monitoring of year-round regimes at Météo-France via a web interface.

## Contributing
The project is currently complete. Future work may include forecast integration.

## Authors and acknowledgment
Authors of the project :
- Oscar Lorans
- Killian Mounier
- Louis Voisin
- Margaux Verly

Acknowledgment : Thanks to our supervisors for their valuable help throughout the project.
- Frédéric Ferry
- Onaïa Savary
- Frédéric Gayrard
- Alexis Querin
- Julien Cattiaux
- Roland Amat-Boucq

## License
You are free to reuse our code as long as you credit us.

## Project status
Completed for now.

## Visuals

![Image locale](archives/images_documentation/figure_cluster_init.png)
&nbsp;
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
&nbsp;
![Image locale](archives/images_documentation/smooth2.png)
&nbsp;
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
&nbsp;
![Image locale](archives/images_documentation/figure_WRI_nouv.png)
&nbsp;
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
&nbsp;
![Image locale](archives/images_documentation/figure_courbesWRI.png)
&nbsp;
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
&nbsp;
![Image locale](archives/images_documentation/composite1.png)
&nbsp;
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
&nbsp;
![Image locale](archives/images_documentation/composite21.png)
&nbsp;
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
&nbsp;
![Image locale](archives/images_documentation/composite3.png)
&nbsp;
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
&nbsp;
![Image locale](archives/images_documentation/composite4.png)
&nbsp;
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
