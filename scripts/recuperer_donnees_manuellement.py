import cdsapi
from pathlib import Path
import pandas as pd

"""
On cherche dans ce fichier à offrir la possibilité de récupérer des données qui manquerait !ATTENTION UNIQUEMENT ERA5!
Le fichier est stocké sous forme .grib dans le path défini dans le code.
Les données récupérées sont z500 et températures à 2 mètres
"""

######## Récupération de la ou les dates cibles ########

date_debut = str(input('Entrez la date de début des données que vous voulez sous le format YYYYMMDD : '))
date_fin = str(input('Entrez la date de fin des données que vous voulez sous le format YYYYMMDD : '))
######## Conversion de la date ########

date_debut_tirets = (pd.to_datetime(date_debut, format="%Y%m%d")).strftime('%Y-%m-%d')
date_fin_tirets = (pd.to_datetime(date_fin, format="%Y%m%d")).strftime('%Y-%m-%d')

print(f"la date de début est : {date_debut_tirets}")
print(f"la date de fin est : {date_fin_tirets}")

######## Définition des chemins de sauvegarde ########
dossier_de_sortie_ERA5 = Path('../data/donnees_quotidiennes/ERA5')


fichier_de_sortie_ERA5_z500 = dossier_de_sortie_ERA5 / f"Z500_ERA500_{date_debut}.grib"
fichier_de_sortie_ERA5_temperatures = dossier_de_sortie_ERA5 / f"tas_ERA500_{date_debut}.grib"

######## Téléchargement sur le CDS ########
c = cdsapi.Client()

#z500 ERA5
try:
    c.retrieve(
        'reanalysis-era5-pressure-levels',
        {
            'product_type': 'reanalysis',
            'format': 'grib',
            'variable': 'geopotential',
            'pressure_level': '500',
            'time': '00:00',
            'area': [90, -80, 30, 40],
            'grid': ['1.0', '1.0'], 
            'date': f'{date_debut_tirets}/{date_fin_tirets}',
        },
        fichier_de_sortie_ERA5_z500
    )
    print(f"Succès ! Fichier enregistré sous : {fichier_de_sortie_ERA5_z500}")
      
except Exception as e:
    print(f"Échec du téléchargement. Détails : {e}")

#températures ERA5
try:
    c.retrieve(
        'reanalysis-era5-single-levels',
        {
            'product_type': 'reanalysis',
            'format': 'grib',
            'variable': '2m_temperature',
            'pressure_level': '500',
            'time': '00:00',
            'area': [90, -80, 30, 40],
            'grid': ['1.0', '1.0'],
            'date': f'{date_debut_tirets}/{date_fin_tirets}', 
        },
        fichier_de_sortie_ERA5_temperatures
    )
    print(f"Succès ! Fichier enregistré sous : {fichier_de_sortie_ERA5_temperatures}")
    
except Exception as e:
    print(f"Échec du téléchargement. Détails : {e}")