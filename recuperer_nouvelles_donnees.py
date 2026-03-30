import cdsapi
from datetime import datetime, timedelta
import os
from ecmwf.opendata import Client
from pathlib import Path

"""
Le but de ce fichier est de récupérer les données CEP et ERA5 de aujourd'hui(CEP) et de il y a 5 jours(ERA5)
Les fichiers ERA5 et CEP sont stockés sous forme .grib
Les données récupérées sont z500 et températures à 2 mètres
"""

######## Récupération de la date d'aujourd'hui pour CEP########
date_actuelle = datetime.now()
date_actuelle_str = date_actuelle.strftime("%Y%m%d")

annee_actuelle = date_actuelle.strftime("%Y")
mois_actuel = date_actuelle.strftime("%m")
jour_actuel = date_actuelle.strftime("%d")

######## Récupération de la date de il y a 5 jours pour ERA5 ########
date_moins_5_jours = date_actuelle - timedelta(days=5)

annee_moins_5_jours = date_moins_5_jours.strftime("%Y")
mois_moins_5_jours = date_moins_5_jours.strftime("%m")
jour_moins_5_jours = date_moins_5_jours.strftime("%d")

######## Définition des chemins et fichiers de sortie ########
dossier_de_sortie_ERA5 = Path('../../../../../utemp/mcbd/voisinl/data_daily/ERA5')
dossier_de_sortie_CEP = Path('../../../../../utemp/mcbd/voisinl/data_daily/AnaCEP')


fichier_de_sortie_ERA5_z500 = dossier_de_sortie_ERA5 / f"Z500_ERA500_{annee_moins_5_jours}{mois_moins_5_jours}{jour_moins_5_jours}.grib"
fichier_de_sortie_ERA5_temperatures = dossier_de_sortie_ERA5 / f"tas_ERA500_{annee_moins_5_jours}{mois_moins_5_jours}{jour_moins_5_jours}.grib"

fichier_de_sortie_CEP_z500 = dossier_de_sortie_CEP / f"Z500_AnaCEP00_{annee_actuelle}{mois_actuel}{jour_actuel}.grib"
fichier_de_sortie_CEP_temperatures = dossier_de_sortie_CEP / f"tas_AnaCEP00_{annee_actuelle}{mois_actuel}{jour_actuel}.grib"

######## Exécution des requêtes vers les serveurs européens (CDS et ECMWF) ########
print(f"Tentative de téléchargement pour la date du {jour_moins_5_jours}/{mois_moins_5_jours}/{annee_moins_5_jours} à 00:00 UTC...")

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
            'year': annee_moins_5_jours,
            'month': mois_moins_5_jours,
            'day': jour_moins_5_jours,
            'time': '00:00',
            'area': [90, -80, 30, 40],
            'grid': ['1.0', '1.0'], 
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
            'year': annee_moins_5_jours,
            'month': mois_moins_5_jours,
            'day': jour_moins_5_jours,
            'time': '00:00',
            'area': [90, -80, 30, 40],
            'grid': ['1.0', '1.0'], 
        },
        fichier_de_sortie_ERA5_temperatures
    )
    print(f"Succès ! Fichier enregistré sous : {fichier_de_sortie_ERA5_temperatures}")
    
except Exception as e:
    print(f"Échec du téléchargement. Détails : {e}")


client = Client(source="ecmwf")

#z500 CEP
try:
    client.retrieve(
        date=date_actuelle_str,
        time=0,           # L'heure du run (06:00 UTC)
        step=0,           # Étape 0 = L'analyse (l'état initial du modèle)
        type="fc",        # Forecast (les données ouvertes classent l'analyse sous 'fc' step 0)
        levtype="pl",     # Pressure levels (niveaux de pression)
        levelist=500,     # 500 hPa
        param="gh",       # Geopotential Height (Géopotentiel)
        target=fichier_de_sortie_CEP_z500
    )
    print(f"Téléchargement réussi ! Fichier enregistré sous : {fichier_de_sortie_CEP_z500}")

except Exception as e:
    print(f"Échec du téléchargement. Le run de 00z n'est peut-être pas encore publié. Détails : {e}")

#températures CEP
try:
    client.retrieve(
        date=date_actuelle_str,
        time=0,           # L'heure du run (06:00 UTC)
        step=0,           # Étape 0 = L'analyse (l'état initial du modèle)
        type="fc",        # Forecast (les données ouvertes classent l'analyse sous 'fc' step 0)
        levtype="sfc",     # Pressure levels (niveaux de pression)
        param="2t",       # Geopotential Height (Géopotentiel)
        target=fichier_de_sortie_CEP_temperatures
    )
    print(f"Téléchargement réussi ! Fichier enregistré sous : {fichier_de_sortie_CEP_temperatures}")

except Exception as e:
    print(f"Échec du téléchargement. Le run de 00z n'est peut-être pas encore publié. Détails : {e}")