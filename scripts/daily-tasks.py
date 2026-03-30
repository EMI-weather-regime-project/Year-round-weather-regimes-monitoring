import numpy as np
import xarray as xr
import pandas as pd
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


from matplotlib.patches import Patch
from dateutil.relativedelta import relativedelta
from datetime import date, datetime, timedelta
from pathlib import Path

import os
import calendar
import warnings
import glob
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--datatype', type=str, default='ERA5', help='entrez le type de données (ERA5 ou AnaCEP), par défaut ERA5')
args = parser.parse_args()

warnings.filterwarnings("ignore")

"""
À quoi sert ce fichier ?
-> Il doit tourner chaque jour de façon à produire des images de monitoring (les deux derniers mois disponibles) ainsi que le suivi climatique.
Où sont stockées ces images ?
-> En sortie, les images monitoring sont stockées dans le dossier archives/images_monitoring, de plus il y a deux sous dossier (images crées avec ERA5 et l'analyse CEP) AnaCEP00 et ERA500
-> Pour les images des histogrammes, elles sont mises dans archives/suivi_climatique et ne sont tracées que avec les données ERA5
"""

####### Définition de variables utiles #######

save_path = Path('donnes_sauvegardees')
DATA_TYPE = args.datatype # soit 'AnaCEP ou ERA5
DATA_EXT = '.grib'
new_data_folder_path = Path(f"../../../../../utemp/mcbd/voisinl/data_daily/{DATA_TYPE}")

if DATA_TYPE != 'AnaCEP' and DATA_TYPE != 'ERA5':
    raise ValueError("Erreur dans le nom des données que vous avez mises (bien verifier ERA5 ou AnaCEP)")


if DATA_TYPE == 'ERA5':
    date_actuelle = datetime.now() - relativedelta(days=30)
else :
    date_actuelle = datetime.now()


print(f'Utilisation de données {DATA_TYPE}')
annee_actuelle = date_actuelle.strftime('%Y')
mois_actuel = date_actuelle.strftime('%m')
jour_actuel = date_actuelle.strftime('%d')

domain = dict(lat=slice(90, 30), lon=slice(-80,40))

####### Définition de fonctions utiles #######

def rolling_filter(anoms):
    """
    Fait un lissage des anomalies sur 10 jours glissants.
    
    Paramètres :
    - indices : DataArray des indices standardisés.
    - threshold : Le seuil à dépasser (ex: sigma_seuil = 0.9).
    - min_duration : La durée minimale de persistance (ex: min_length = 5).
    - max_gap : Nombre de jours consécutifs autorisés sous le seuil (ex: 1).
    - min_max_duration : Nombre de jours pour valider un takeover (ex: N_dominant = 3).
    """
    anoms = anoms.pad(time=(0, 5), mode='edge')
    anoms = anoms.rolling(time=11, center=True).mean()
    anoms = anoms.isel(time=slice(5, -5))
    return anoms


def find_index(reference_date, current_date):
    delta = current_date - reference_date
    return delta.days


def open_dataset(path):
    """Ouvre le dataset et renomme les dimensions lat/lon
    """
    ds = xr.open_dataset(path)
    if "latitude" in ds.coords:
        ds = ds.rename({"latitude": "lat"})
    if "longitude" in ds.coords:
        ds = ds.rename({"longitude": "lon"})
    return ds


def decouper_domaine_ecmwf_ds(ds):
    """
    Prend un dataset xarray ECMWF, convertit les longitudes,
    et extrait uniquement les degrés entiers sur le domaine ciblé.
    """
    
    # 1. Conversion des longitudes [0, 360] vers [-180, 180]
    ds = ds.assign_coords(longitude=(((ds.longitude + 180) % 360) - 180))
    ds = ds.sortby('longitude')
    
    # 2. Définition stricte des degrés entiers que l'on veut garder
    # Latitudes : de 90 à 30 (décroissant car les lats ECMWF vont du Nord au Sud)
    lats_entieres = np.arange(90, 29, -1) 
    
    # Longitudes : de -80 à 40 (croissant)
    lons_entieres = np.arange(-80, 41, 1)
    
    # 3. La sélection (Crop + Filtre de résolution)
    # L'astuce method='nearest' est une sécurité vitale : parfois dans les GRIB,
    # 90.0 est encodé comme 89.999999. Cela évite que le script plante.
    ds_domaine = ds.sel(
        latitude=lats_entieres, 
        longitude=lons_entieres,
        method='nearest' 
    )
    
    return ds_domaine


def rename(ds):
    if "latitude" in ds.coords:
        ds = ds.rename({"latitude": "lat"})
    if "longitude" in ds.coords:
        ds = ds.rename({"longitude": "lon"})
    return ds
####### Extraction des données de Z500 les plus récentes pour tracer les graphiques #######

if DATA_TYPE == 'ERA5':
    pathlist = glob.glob(f"{str(new_data_folder_path)}/Z500*.grib")
    pathlist.sort()
    print(pathlist)
    new_data = xr.open_mfdataset(pathlist, coords='minimal', combine='nested', concat_dim='time')
    new_data = rename(new_data['z'])/10 #########A VERIFIER
    new_data = new_data.drop_duplicates('time') #permet d'enlever les doubles temps s'il y en a 
    new_data = new_data.resample(time="1D").asfreq()
    new_data = new_data.sel(time = slice(None, date_actuelle))
    print(len(new_data['time']))
    if len(new_data['time']) < 11:
        print('ATTENTION !!!! pas assez de données consécutives CEP')
        quit()
else:
    pathlist = glob.glob(f"{str(new_data_folder_path)}/Z500*.grib")
    pathlist.sort()
    print(pathlist)
    new_data = xr.open_mfdataset(pathlist, coords='minimal', combine='nested', concat_dim='time', compat='override')
    new_data = decouper_domaine_ecmwf_ds(new_data)
    new_data = new_data.drop_duplicates('time') #permet d'enlever les doubles dans le temps s'il y en a 
    new_data = new_data.resample(time="1D").asfreq()
    new_data = rename(new_data['gh'])
    if len(new_data['time']) < 11:
        print('ATTENTION !!!! pas assez de données consécutives CEP')
        quit()



####### Importation de données pour la projection, le calcul des indices et les plots #######

cluster_mean_z500_anom_norm = open_dataset(save_path/'cluster_mean_z500_anom_norm.nc')
with open(save_path / "cluster_regime_names.json", "r", encoding="utf-8") as f:
    cluster_regime_names = json.load(f)
with open(save_path / "cluster_colors.json", "r", encoding="utf-8") as f:
    cluster_colors = json.load(f)
regime_names = list(cluster_regime_names.values())
clim60 = open_dataset(save_path/'clim60.nc')['zg500'] 
std_daily_smooth = open_dataset(save_path/'std_daily_smooth.nc')

if isinstance(std_daily_smooth, xr.Dataset):
    std_daily_smooth = std_daily_smooth.to_dataarray().squeeze().drop_vars('variable', errors='ignore')


res_slope = np.load(save_path/"res_area_slope.npy")
res_intercept = np.load(save_path/"res_area_intercept.npy")
t_days_mean = np.load(save_path/"t_days_mean.npy")
mean_P_hist = np.load(save_path/"mean_P.npy")
std_P_hist = np.load(save_path/"std_P.npy")

climatologie = np.load(save_path/'climatologie.npy')
print("Toutes les données ont été chargées !")

####### Pipline de traitiement des données de Z500 (cf documentation) #######

# ETAPE 1 : Retirer l'anomalie et filtrage avec une moyenne glissante sur 10 jours
new_anoms = new_data.groupby("time.dayofyear") - clim60
new_anoms = rolling_filter(new_anoms)
# --- ETAPE 2 : Retirer la tendance climatique ---
reference_date = np.datetime64('1960-01-01')
t_days_new = (new_anoms['time'] - reference_date).dt.days.astype('float64').values

y_values_new = res_intercept + res_slope * (t_days_new - t_days_mean)
fit_xr = xr.DataArray(y_values_new, coords={"time": new_anoms.time}, dims=["time"])

new_anoms_resid = new_anoms - fit_xr

# --- ETAPE 3 : Normaliser par un scalaire correspondant à l'écart-type dépendant du jour de l'année ---
std_full = std_daily_smooth.sel(dayofyear=new_anoms_resid["time.dayofyear"])
new_anoms_norm = new_anoms_resid / std_full

# --- ETAPE 4 : Pondération par la latitude ---
weights_1d = np.cos(np.deg2rad(new_anoms_norm.lat.values))
weights_2d_pixel = xr.DataArray(
    np.outer(weights_1d, np.ones(len(new_anoms_norm.lon))),
    coords={"lat": new_anoms_norm.lat, "lon": new_anoms_norm.lon}, 
    dims=["lat", "lon"]
)
weights = np.sqrt(weights_2d_pixel.broadcast_like(new_anoms_norm))

new_anoms_w = new_anoms_norm * weights

####### Traitement et reformulation de la variable avec les centroïdes #######

cluster_mean_z500_anom_norm = cluster_mean_z500_anom_norm.to_dataarray()
cluster_mean_z500_anom_norm = cluster_mean_z500_anom_norm.squeeze('variable')
list_cluster_mean_z500_anom_norm = [cluster_mean_z500_anom_norm.isel(regime=i) for i in range(cluster_mean_z500_anom_norm.sizes['regime'])]

####### Fonctions de projection et de calcul de l'indice #######

def calculate_projection_chunked(anomalies, cluster_regimes_anomaly, cluster_regime_names, lat_dim='lat', lon_dim='lon', chunk_size=2000):
    """
    Calcule la projection en découpant le temps pour éviter les MemoryErrors 
    (credits gemini et donc tout les vrais gens qui ont posté leurs méthode auparavant sur internet).
    
    Args:
        anomalies (xr.DataArray): (Time, Lat, Lon)
        cluster_regimes_anomaly (list): Liste des DataArrays de régimes contenant les annomalies de géopotentiel.
        chunk_size (int): Nombre de jours à traiter à la fois (2000 jours ~= 100 Mo de RAM).
        cluster_regime_names
        
    """
    
    # 1. Optimisation immédiate : passer en float32 (divise la mémoire par 2)
    if anomalies.dtype == np.float64:
        anomalies = anomalies.astype(np.float32)
    
    # 2. Préparation des poids (inchangé)
    weights = np.cos(np.deg2rad(anomalies[lat_dim])).astype(np.float32)
    weights_2d = weights.broadcast_like(anomalies.isel(time=0, drop=True))
    
    # Dénominateur (constante spatiale)
    denom = weights_2d.sum(dim=[lat_dim, lon_dim])
    
    # Liste pour stocker les résultats finaux de chaque régime
    all_regimes_projections = []
    
    total_days = anomalies.sizes['time']
    

    # --- BOUCLE 1 : Sur les Régimes ---
    for i, pattern in enumerate(cluster_regimes_anomaly):
        pattern = pattern.astype(np.float32) # On allège aussi le pattern
        
        # Liste temporaire pour stocker les morceaux de temps de ce régime
        regime_time_chunks = []
        
        # --- BOUCLE 2 : Sur le Temps (Chunking) ---
        # On avance de 'chunk_size' à chaque fois (ex: 0->2000, 2000->4000...)
        for start_idx in range(0, total_days, chunk_size):
            end_idx = min(start_idx + chunk_size, total_days)
            
            # On sélectionne une petite tranche temporelle
            # Mémoire utilisée : infime (~100 Mo)
            anom_chunk = anomalies.isel(time=slice(start_idx, end_idx))
            
            # Calcul sur ce petit morceau uniquement
            product = anom_chunk * pattern
            numerator = (product * weights_2d).sum(dim=[lat_dim, lon_dim])
            proj_chunk = numerator / denom
            
            regime_time_chunks.append(proj_chunk)
        
        # On recolle les morceaux temporels pour ce régime
        full_regime_series = xr.concat(regime_time_chunks, dim='time')
        full_regime_series = full_regime_series.assign_coords(regime=cluster_regime_names[i])
        
        all_regimes_projections.append(full_regime_series)

    # 3. Assemblage final (Regime, Time)
    final_P_wr = xr.concat(all_regimes_projections, dim='regime')
    
    return final_P_wr

def calculate_regime_index_new(P_wr, mean_P_hist, std_P_hist):
    """
    Calcule l'Indice de Régime Standardisé I_wr(t) selon l'Équation 2 de l'article.
    
    Args:
        P_wr (xr.DataArray): La projection brute calculée précédemment (Time, Regime).
        
    Returns:
        xr.DataArray: L'indice de régime I_wr (Time, Regime).
    """
    # Calcul de l'indice
    mean_vals = mean_P_hist[:,None]
    std_vals = std_P_hist[:,None]
    I_wr = (P_wr - mean_vals) / std_vals
    return I_wr

####### calcul effectif de la projection et de l'indice sur les nouvelles données #######

new_Pwr = calculate_projection_chunked(new_anoms_norm, list_cluster_mean_z500_anom_norm, regime_names, lat_dim='lat', lon_dim='lon')
new_indices = calculate_regime_index_new(new_Pwr, mean_P_hist, std_P_hist)
####### Fonction de calcul des cyles de régimes et du dominant #######

def calculate_regime_states_takeover(indices, threshold=0.9, min_duration=5, max_gap=1, min_max_duration=3):
    """
    Calcule les régimes actifs et le régime max (Takeover).
    Basé sur l'approche itérative avec tolérance de trous (max_gap) 
    et coup d'état conditionné (N_dominant).
    
    Paramètres :
    - indices : DataArray des indices standardisés.
    - threshold : Le seuil à dépasser (ex: sigma_seuil = 0.9).
    - min_duration : La durée minimale de persistance (ex: min_length = 5).
    - max_gap : Nombre de jours consécutifs autorisés sous le seuil (ex: 1).
    - min_max_duration : Nombre de jours pour valider un takeover (ex: N_dominant = 3).
    """
    cond = indices >= threshold
    n_regimes = indices.sizes["regime"]
    times = indices.time
    values = indices.values

    # ===============================
    # 1. Détection des séquences persistantes (Active Regimes)
    # ===============================
    active_mask = np.zeros((n_regimes, len(times)), dtype=bool)

    for r in range(n_regimes):
        # On utilise isel au lieu de sel pour garantir l'accès par position numérique
        series = cond.isel(regime=r).values 
        start = None
        gap = 0
        for i, val in enumerate(series):
            if start is None:
                if val:
                    start = i
                    gap = 0
            else:
                if not val:
                    gap += 1
                else:
                    gap = 0
                if gap > max_gap:
                    end = i - gap
                    total_length = end - start + 1
                    if total_length >= min_duration:
                        active_mask[r, start:end+1] = True
                    start = None
                    gap = 0
                    
        if start is not None:
            end = len(series) - 1
            while end >= start and not series[end]:
                end -= 1
            total_length = end - start + 1
            if total_length >= min_duration:
                active_mask[r, start:end+1] = True

    # ===============================
    # 2. Assignation du régime dominant avec Takeover
    # ===============================
    # On utilise -1 pour "No Regime" au lieu de 7 (plus sûr mathématiquement)
    regime_sequence = np.full(len(times), -1, dtype=int) 

    t = 0
    while t < len(times):
        # Trouver les régimes actifs à l'instant t
        active_regs_t = np.where(active_mask[:, t])[0]
        
        if len(active_regs_t) == 0:
            t += 1
            continue

        # Début d’une nouvelle séquence
        left = t
        # Régime courant : le plus fort à t
        r_current = active_regs_t[np.argmax(values[active_regs_t, t])]

        # Tant que l'on avance et que le régime courant est toujours dans les "actifs"
        while t < len(times) and active_mask[r_current, t]:
            active_t = np.where(active_mask[:, t])[0]
            takeover = None

            # Vérifier si un autre régime tente un takeover
            for r_candidate in active_t:
                if r_candidate == r_current:
                    continue

                t_end = min(t + min_max_duration, len(times))
                dominant = True
                
                # Le candidat doit rester supérieur aux autres sur N jours
                for t_check in range(t, t_end):
                    active_check = np.where(active_mask[:, t_check])[0]
                    if len(active_check) == 0:
                        dominant = False
                        break
                    if values[r_candidate, t_check] < np.max(values[active_check, t_check]):
                        dominant = False
                        break

                if dominant:
                    takeover = (r_candidate, t_end)
                    break

            if takeover is not None:
                r_new, t_new_end = takeover
                regime_sequence[left:t] = r_current
                regime_sequence[t:t_new_end] = r_new
                t = t_new_end
                r_current = r_new
                left = t  # début de la nouvelle séquence
                continue

            t += 1

        # Assigner le régime courant pour toute sa séquence restante
        regime_sequence[left:t] = r_current

    # ===============================
    # 3. Conversion en masques booléens Xarray (Pour les graphiques)
    # ===============================
    
    # Masque 1 : active_regimes
    active_regimes = xr.DataArray(
        active_mask,
        dims=["regime", "time"],
        coords={"regime": indices.regime, "time": times},
        name="active_regimes"
    )
    
    # Masque 2 : max_regime (Créé de manière 100% sécurisée en Numpy)
    # On prépare une matrice remplie de "False" de la bonne taille (7 régimes x N jours)
    max_mask = np.zeros((n_regimes, len(times)), dtype=bool)
    
    # On identifie les jours où il y a un vrai gagnant (différent de -1 "No Regime")
    jours_valides = np.where(regime_sequence != -1)[0]
    regimes_gagnants = regime_sequence[jours_valides]
    
    # On allume en "True" la case exacte du régime vainqueur pour chaque jour valide
    max_mask[regimes_gagnants, jours_valides] = True
    
    # On transforme ça proprement en objet Xarray
    max_regime = xr.DataArray(
        max_mask,
        dims=["regime", "time"],
        coords={"regime": indices.regime, "time": times},
        name="max_regime"
    )

    return active_regimes, max_regime

####### Stockage dans une variable des régimes actifs et dominants #######

new_active_regimes, new_max_regime = calculate_regime_states_takeover(new_indices, threshold=0.9, min_duration=5, max_gap=1, min_max_duration=3)

################################ FIN DU TRAITEMENT/CALCUL ##############################

################################ DEBUT DU PLOTIING #####################################

####### Définitions de variables pour le plot ensuite #######

regime_meta = {k: {'nom': cluster_regime_names[k], 'couleur': cluster_colors[k]} for k in cluster_regime_names.keys()}

regime_names = list(cluster_regime_names.values())

cluster_ids = sorted(cluster_regime_names.keys())   # [1..8]

regime_labels = [cluster_regime_names[r] for r in cluster_ids]

output_folder = Path(f"../archives/images_monitoring/{DATA_TYPE}")

derniere_date = pd.to_datetime(new_indices.time.values[-1])
end_date_str = derniere_date.strftime('%Y-%m-%d')

print(f'Dernière date détectée dans les données : {end_date_str}')

start_annee = f"{derniere_date.year}-01-01"
end_annee = f"{derniere_date.year}-12-31"

start_mois_actuel = derniere_date.replace(day=1)
if derniere_date.month == 12:
    end_mois_actuel = derniere_date.replace(31)
else:
    end_mois_actuel = derniere_date.replace(month=derniere_date.month+1, day=1) - pd.Timedelta(days=1)

nom_mois_actuel = derniere_date.strftime('%Y_%m')

end_mois_prec = start_mois_actuel - pd.Timedelta(days=1)
start_mois_prec = end_mois_prec.replace(day=1)
nom_mois_prec = end_mois_prec.strftime('%Y_%m')

####### Définitions des fonctions pour faire les plots du monitoring (au mois et à l'année) #######

def plot_ultimate_regimes_masked_save(indices, active_regimes, max_regime, start_date, end_date, dictionnaire_regimes, save_path=None):
    """
    Trace 3 graphiques synchronisés :
    1. Courbes avec épaisseur dynamique (Actif) et points (Max).
    2. Chronogramme à bulles stylisé (Translucide=Tentative, Bord fin=Actif, Opaque/Gras=Max).
    3. Frise chronologique.
    Réalisée en très étroite collaboration avec une IA
    """
    # ==========================================
    # 1. PRÉPARATION
    # ==========================================
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    
    # --- NOUVEAU : Identification des limites globales du jeu de données ---
    temps_globaux = indices.time
    if len(temps_globaux) > 10:
        date_coupure_debut = temps_globaux[4].values  # Le 5ème jour
        date_coupure_fin = temps_globaux[-5].values   # Le 5ème jour avant la fin
    else:
        # Sécurité si le jeu de données total est minuscule
        date_coupure_debut = temps_globaux[-1].values
        date_coupure_fin = temps_globaux[0].values
    # ----------------------------------------------------------------------

    
    color_mapping = {info['nom']: info['couleur'] for info in dictionnaire_regimes.values()}
    ordre_haut_en_bas = ['European Blocking','Scandinavian Blocking','Greenland Blocking','Atlantic Ridge','Zonal','Scandinavian Trough','Atlantic Trough']
    regimes_valides = ordre_haut_en_bas[::-1]
    
    # Découpage temporel
    sub_idx = indices.sel(time=slice(start_dt, end_dt))
    sub_act = active_regimes.sel(time=slice(start_dt, end_dt))
    sub_max = max_regime.sel(time=slice(start_dt, end_dt))

    fig, (ax1, ax2, ax3) = plt.subplots(nrows=3, ncols=1, figsize=(15, 12), 
                                        sharex=True, gridspec_kw={'height_ratios': [3, 2.5, 0.8]})
    
    # ==========================================
    # GRAPHIQUE 1 : Lignes Dynamiques
    # ==========================================
    for regime_name in sub_idx.regime.values:
        data = sub_idx.sel(regime=regime_name)
        mask_act = sub_act.sel(regime=regime_name)
        mask_max = sub_max.sel(regime=regime_name)
        
        color = color_mapping.get(str(regime_name), 'black')
        
        # Astuce : On trace une ligne vide juste pour enregistrer la légende une seule fois.
        # Cela évite les doublons ou l'absence de légende si la zone du milieu n'est pas tracée.
        ax1.plot([], [], label=regime_name, color=color, linewidth=1, alpha=0.3, linestyle='-')
        
        if len(temps_globaux) > 10:
            # Découpage par DATES temporelles exactes. 
            # Les limites étant incluses, les morceaux s'accrocheront parfaitement sans trous !
            d_start = data.sel(time=slice(None, date_coupure_debut))
            d_mid = data.sel(time=slice(date_coupure_debut, date_coupure_fin))
            d_end = data.sel(time=slice(date_coupure_fin, None))
            
            # --- A. Ligne de fond ---
            # On ne trace que si le morceau n'est pas vide pour la période affichée
            if len(d_start) > 0: ax1.plot(d_start.time, d_start.values, color=color, lw=1.3, alpha=0.3, ls='--')
            if len(d_mid) > 0:   ax1.plot(d_mid.time, d_mid.values, color=color, lw=1.3, alpha=0.3, ls='-')
            if len(d_end) > 0:   ax1.plot(d_end.time, d_end.values, color=color, lw=1.3, alpha=0.3, ls='--')
            
            # --- B. Ligne active (épaisse) ---
            act_start = data.where(mask_act).sel(time=slice(None, date_coupure_debut))
            act_mid = data.where(mask_act).sel(time=slice(date_coupure_debut, date_coupure_fin))
            act_end = data.where(mask_act).sel(time=slice(date_coupure_fin, None))
            
            if len(act_start) > 0: ax1.plot(act_start.time, act_start.values, color=color, lw=1.5, alpha=0.9, ls='--')
            if len(act_mid) > 0:   ax1.plot(act_mid.time, act_mid.values, color=color, lw=3.5, alpha=0.9, ls='-')
            if len(act_end) > 0:   ax1.plot(act_end.time, act_end.values, color=color, lw=1.5, alpha=0.9, ls='--')
            
        else:
            # Cas extrême où la base de données entière fait moins de 10 jours
            ax1.plot(data.time, data.values, color=color, lw=1, alpha=0.3, ls='--')
            ax1.plot(data.where(mask_act).time, data.where(mask_act).values, color=color, lw=3.5, alpha=0.9, ls='--')
            
        # --- C. Points pour le vainqueur (Inchangé) ---
        data_max = data.where(mask_max)
        ax1.plot(data_max.time, data_max.values, marker='o', linestyle='none', color=color, 
                 markersize=8, markeredgecolor='black', zorder=5)


    ax1.axhline(0, color='black', linestyle='-', linewidth=0.8, alpha=0.5)
    ax1.axhline(0.9, color='red', linestyle='--', linewidth=0.8, alpha=0.5)
    ax1.grid(True, linestyle='--', alpha=0.6)
    ax1.set_title(f"Dynamique complète des Régimes de Temps ({start_date} au {end_date})", fontsize=16, pad=15)
    ax1.set_ylabel("Indice Standardisé ($I_{wr}$)")
    legende = ax1.legend(bbox_to_anchor=(0.5, 0), loc='lower center', ncol=4)
    for ligne in legende.get_lines():
        ligne.set_linewidth(4.0)
        ligne.set_alpha(1.0)

    # ==========================================
    # GRAPHIQUE 2 : Le Chronogramme à Bulles
    # ==========================================
    scale_factor = 150
    dates = sub_idx.time.values
    
    # --- NOUVEAU : Masques temporels pour les bords de la base de données ---
    if len(temps_globaux) > 10:
        m_incertain = (dates <= date_coupure_debut) | (dates >= date_coupure_fin)
    else:
        # Si la base est minuscule, tout est incertain
        m_incertain = np.ones(len(dates), dtype=bool) 
        
    m_certain = ~m_incertain
    # ------------------------------------------------------------------------

    for y_pos, regime_name in enumerate(regimes_valides):
        if regime_name in sub_idx.regime.values:
            data_bubble = sub_idx.sel(regime=regime_name).values
            mask_act = sub_act.sel(regime=regime_name).values
            mask_max = sub_max.sel(regime=regime_name).values
            color = color_mapping.get(regime_name, 'black')
            
            base_sizes = (data_bubble ** 2) * scale_factor
            
            # --- Condition 1 : MAX REGIME ---
            m_max = mask_max & (data_bubble >= 0.9)
            
            # 1A. Sûr (Contour plein)
            m_max_c = m_max & m_certain
            if np.any(m_max_c):
                ax2.scatter(dates[m_max_c], np.full(m_max_c.sum(), y_pos), s=base_sizes[m_max_c], 
                            color=color, alpha=1.0, edgecolors='black', linewidth=2.5, linestyle='-', zorder=3)
            # 1B. Incertain (Contour pointillé)
            m_max_inc = m_max & m_incertain
            if np.any(m_max_inc):
                ax2.scatter(dates[m_max_inc], np.full(m_max_inc.sum(), y_pos), s=base_sizes[m_max_inc], 
                            color=color, alpha=1.0, edgecolors='grey', linewidth=2.5, linestyle='--', zorder=3)
                            
            # --- Condition 2 : ACTIF mais pas max ---
            m_act = mask_act & ~mask_max & (data_bubble >= 0.9)
            
            # 2A. Sûr (Contour plein)
            m_act_c = m_act & m_certain
            if np.any(m_act_c):
                ax2.scatter(dates[m_act_c], np.full(m_act_c.sum(), y_pos), s=base_sizes[m_act_c], 
                            color=color, alpha=0.6, edgecolors='black', linewidth=1.0, linestyle='-', zorder=2)
            # 2B. Incertain (Contour pointillé)
            m_act_inc = m_act & m_incertain
            if np.any(m_act_inc):
                ax2.scatter(dates[m_act_inc], np.full(m_act_inc.sum(), y_pos), s=base_sizes[m_act_inc], 
                            color=color, alpha=0.6, edgecolors='grey', linewidth=1.5, linestyle='--', zorder=2)
                            
            # --- Condition 3 : TENTATIVE ---
            m_base = (data_bubble >= 0.9) & ~mask_act
            
            # 3A. Sûr (Pas de contour)
            m_base_c = m_base & m_certain
            if np.any(m_base_c):
                ax2.scatter(dates[m_base_c], np.full(m_base_c.sum(), y_pos), s=base_sizes[m_base_c], 
                            color=color, alpha=0.2, edgecolors='none', zorder=1)
            # 3B. Incertain (Contour pointillé gris très fin pour montrer qu'elle existe)
            m_base_inc = m_base & m_incertain
            if np.any(m_base_inc):
                ax2.scatter(dates[m_base_inc], np.full(m_base_inc.sum(), y_pos), s=base_sizes[m_base_inc], 
                            color=color, alpha=0.2, edgecolors=color, linewidth=1.0, linestyle='--', zorder=1)

    # ... (La cosmétique des axes ax2 reste inchangée) ...

    # Cosmétique des bulles
    ax2.set_yticks(range(len(regimes_valides)))
    ax2.set_yticklabels(regimes_valides)
    ax2.set_ylim(-0.5,len(regimes_valides)-0.5)
    ax2.margins(y=0.2)
    ax2.set_clip_on(False)
    
    for tick_label, regime_name in zip(ax2.get_yticklabels(), regimes_valides):
        tick_label.set_color(color_mapping.get(regime_name, 'black'))
        tick_label.set_fontweight('bold')
    
    ax2.grid(True, linestyle=':', alpha=0.7)
    for spine in ax2.spines.values():
        spine.set_visible(False)

    # ==========================================
    # GRAPHIQUE 3 : Frise Chronologique
    # ==========================================
    df_max = sub_max.to_pandas().T 
    frieze_series = df_max.idxmax(axis=1) 
    frieze_series = frieze_series.where(df_max.any(axis=1), 'No Regime')

    # --- NOUVEAU : Conversion des dates de coupure pour Pandas ---
    if len(temps_globaux) > 10:
        dt_coupure_debut = pd.to_datetime(date_coupure_debut)
        dt_coupure_fin = pd.to_datetime(date_coupure_fin)
    else:
        # Si la base est très petite, on met des dates factices pour tout hachurer
        dt_coupure_debut = pd.to_datetime('2100-01-01') 
        dt_coupure_fin = pd.to_datetime('1900-01-01')
    # -------------------------------------------------------------

    for date, regime_name in frieze_series.items():
        color = color_mapping.get(str(regime_name).strip(), '#e0e0e0')
        start_rect = date - pd.Timedelta(hours=12)
        end_rect = date + pd.Timedelta(hours=12)
        
        # On vérifie si ce jour précis est dans les 5 premiers ou 5 derniers jours
        est_incertain = (date <= dt_coupure_debut) or (date >= dt_coupure_fin)
        
        if est_incertain:
            # ZONE INCERTAINE : Hachures
            # hatch='//' crée des diagonales. On utilise facecolor pour le fond 
            # et edgecolor (ex: blanc ou gris clair) pour la couleur de la hachure
            ax3.axvspan(
                start_rect, end_rect, 
                facecolor=color, 
                edgecolor='white', 
                hatch='//', 
                linewidth=0, 
                alpha=0.8
            )
        else:
            # ZONE SÛRE : Remplissage classique
            ax3.axvspan(
                start_rect, end_rect, 
                facecolor=color, 
                linewidth=0, 
                alpha=1.0
            )

# ... (La suite avec les labels de l'axe ax3 reste inchangée) ...


    # ... (vos axvspan pour les couleurs de la frise) ...
    ax3.set_yticks([]) 
    ax3.set_ylabel("Actif", rotation=0, labelpad=20, va='center', fontweight='bold') 
    
    # On change "Date" par "Jour" (ou "Jour du mois") pour être plus précis
    ax3.set_xlabel("Jour du mois", fontsize=14)
    
    # --- LA MAGIE DU FORMATTAGE DES DATES ---
    # 1. On force Matplotlib à mettre une graduation tous les 2 jours
    ax3.xaxis.set_major_locator(mdates.DayLocator(interval=2))
    
    # 2. On lui dit de n'afficher QUE le jour sous format numérique (ex: 01, 05, 14...)
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%d'))
    
    # 3. Plus besoin de rotation car "14" prend très peu de place ! (labelrotation=0)
    ax3.tick_params(axis='x', labelsize=15, labelrotation=0)
    # ----------------------------------------

    
    # ==========================================
    # ALIGNEMENT FINAL
    # ==========================================
    limite_debut = pd.to_datetime(start_date)
    limite_fin = pd.to_datetime(end_date)

    ax1.set_xlim(limite_debut, limite_fin)
    ax2.set_xlim(limite_debut, limite_fin)
    ax3.set_xlim(limite_debut, limite_fin)

    plt.subplots_adjust(hspace=0.1) 
    plt.tight_layout(rect=[0, 0, 0.9, 1]) 
    if save_path:
        plt.savefig(save_path, dpi = 150, bbox_inches = 'tight', facecolor='white')
        plt.close(fig)
    else : 
        print("ça n'a pas enregistré (entrer chemin)")


def plot_ultimate_regimes_masked2_save(indices, active_regimes, max_regime, start_date, end_date, dictionnaire_regimes, save_path=None):
    """
    Trace 3 graphiques synchronisés :
    1. Courbes avec épaisseur dynamique (Actif) et points (Max).
    2. Chronogramme à bulles stylisé (Translucide=Tentative, Bord fin=Actif, Opaque/Gras=Max).
    3. Frise chronologique.
    """
    # ==========================================
    # 1. PRÉPARATION
    # ==========================================
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    
    color_mapping = {info['nom']: info['couleur'] for info in dictionnaire_regimes.values()}
    regimes_valides = [info['nom'] for info in dictionnaire_regimes.values() if info['nom'] != 'No Regime']
    
    # Découpage temporel
    sub_idx = indices.sel(time=slice(start_dt, end_dt))
    sub_act = active_regimes.sel(time=slice(start_dt, end_dt))
    sub_max = max_regime.sel(time=slice(start_dt, end_dt))

    fig, (ax1, ax3) = plt.subplots(nrows=2, ncols=1, figsize=(15, 12), 
                                        sharex=True, gridspec_kw={'height_ratios': [2, 0.8]})
    
    # ==========================================
    # GRAPHIQUE 1 : Lignes Dynamiques
    # ==========================================
    for regime_name in sub_idx.regime.values:
        data = sub_idx.sel(regime=regime_name)
        mask_act = sub_act.sel(regime=regime_name)
        mask_max = sub_max.sel(regime=regime_name)
        
        color = color_mapping.get(str(regime_name), 'black') 
        
        # A. Ligne de fond (>0 mais fine)
        ax1.plot(data.time, data.values, label=regime_name, color=color, linewidth=1, alpha=0.3)
        
        # B. Ligne active (épaisse)
        data_active = data.where(mask_act)
        ax1.plot(data_active.time, data_active.values, color=color, linewidth=3.5, alpha=0.9)
        

    ax1.axhline(0, color='black', linestyle='-', linewidth=0.8, alpha=0.5)
    ax1.axhline(0.9, color='red', linestyle='--', linewidth=0.8, alpha=0.5)
    ax1.grid(True, linestyle='--', alpha=0.6)
    ax1.set_ylim(bottom=-2)
    ax1.set_title(f"Dynamique complète des Régimes de Temps ({start_date} au {end_date})", fontsize=16, pad=15)
    ax1.set_ylabel("Indice Standardisé ($I_{wr}$)")
    legende = ax1.legend(bbox_to_anchor=(0.5, 0), loc='lower center', ncol=4)
    for ligne in legende.get_lines():
        ligne.set_linewidth(4.0)
        ligne.set_alpha(1.0)


    # ==========================================
    # GRAPHIQUE 3 : Frise Chronologique
    # ==========================================
    df_max = sub_max.to_pandas().T 
    frieze_series = df_max.idxmax(axis=1) 
    frieze_series = frieze_series.where(df_max.any(axis=1), 'No Regime')
    
    for date, regime_name in frieze_series.items():
        color = color_mapping.get(str(regime_name).strip(), '#e0e0e0')
        start_rect = date - pd.Timedelta(hours=12)
        end_rect = date + pd.Timedelta(hours=12)
        ax3.axvspan(start_rect, end_rect, color=color, linewidth=0, alpha=1)

    ax3.set_yticks([]) 
    ax3.set_ylabel("Actif", rotation=0, labelpad=20, va='center', fontweight='bold') 
    ax3.set_xlabel("Date", fontsize=14)
    ax3.tick_params(axis='x',labelsize=15, labelrotation=45)
    
    # ==========================================
    # ALIGNEMENT FINAL
    # ==========================================
    ax1.set_xlim(pd.to_datetime(start_dt), pd.to_datetime(end_dt))
    plt.subplots_adjust(hspace=0.1) 
    plt.tight_layout(rect=[0, 0, 1, 0.5]) 
    if save_path:
        plt.savefig(save_path, dpi = 150, bbox_inches = 'tight', facecolor='white')
        plt.close(fig)
    else : 
        print("ça n'a pas enregistré (entrer chemin)")

####### Appel des fonctions de plot #######

filename = output_folder / f"{derniere_date.year}_tous.png"

plot_ultimate_regimes_masked2_save(
    indices=new_indices,               
    active_regimes=new_active_regimes, 
    max_regime=new_max_regime,         
    start_date=start_annee,
    end_date=end_annee,
    dictionnaire_regimes=regime_meta,
    save_path=filename
)
    
print(f"Enregistré : {filename}")

filename = output_folder / f"{nom_mois_actuel}.png"

plot_ultimate_regimes_masked_save(
    indices=new_indices,               
    active_regimes=new_active_regimes, 
    max_regime=new_max_regime,         
    start_date=start_mois_actuel.strftime('%Y-%m-%d'),
    end_date=end_mois_actuel.strftime('%Y-%m-%d'),
    dictionnaire_regimes=regime_meta, # N'oubliez pas le nom de votre dico ici !
    save_path=filename
)

print(f"Enregistré : {filename}")

filename = output_folder / f"{nom_mois_prec}.png"

plot_ultimate_regimes_masked_save(
    indices=new_indices,               
    active_regimes=new_active_regimes, 
    max_regime=new_max_regime,         
    start_date=start_mois_prec.strftime('%Y-%m-%d'),
    end_date=end_mois_prec.strftime('%Y-%m-%d'),
    dictionnaire_regimes=regime_meta, # N'oubliez pas le nom de votre dico ici !
    save_path=filename
)

print(f"Enregistré : {filename}")

print(f"Génération terminée ! Toutes les images sont dans le dossier 'images_monitoring/{DATA_TYPE}'.")

################################ FIN DU PLOT POUR LE MONITORING ##############################

################################ HISTOGRAMMES ################################################

####### Définition de variables utiles #######

annee_debut_climatologie = 1991 #attention il faudra modifier dans le script suivi climatique si l'on veut enregistrer une nouvelle climatologie

cluster_regime_names=list(cluster_regime_names.values())

position_regime =[]
labels_regimes = ['European Blocking', 'Scandinavian Blocking', 'Greenland Blocking','Atlantic Ridge', 'Zonal', 'Scandinavian Trough', 'Atlantic Trough', 'No Regime']
mois_noms = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
mois = ['01','02','03','04','05','06','07','08','09','10','11','12']

####### Réorganisation pour avoir un plot dans le bon ordre #######

for i in labels_regimes:
    position_regime.append(cluster_regime_names.index(i))
position_regime.pop()

max_regime = new_max_regime.isel(regime=position_regime) #On réordonne le dataarray selon l'ordre souhaité

####### Définiton des fonctions de plot #######

def mois_selectionne(mois_actuel,annee_fin):
    annee_debut = int(annee_fin) - 1
    if mois_actuel == '01':
        liste_mois = [f'{annee_debut}-11',f'{annee_debut}-12',f'{annee_fin}-01']
        liste = [10,11,0]
    elif mois_actuel == '02':
        liste_mois = [f'{annee_debut}-12',f'{annee_fin}-01',f'{annee_fin}-02']
        liste = [11,0,1]
    elif mois_actuel == '03':
        liste_mois = [f'{annee_fin}-01',f'{annee_fin}-02',f'{annee_fin}-03']
        liste = [0,1,2]
    elif mois_actuel == '04':
        liste_mois = [f'{annee_fin}-02',f'{annee_fin}-03',f'{annee_fin}-04']
        liste = [1,2,3]
    elif mois_actuel == '05':
        liste_mois = [f'{annee_fin}-03',f'{annee_fin}-04',f'{annee_fin}-05']
        liste = [2,3,4]
    elif mois_actuel == '06':
        liste_mois = [f'{annee_fin}-04',f'{annee_fin}-05',f'{annee_fin}-06']
        liste = [3,4,5]
    elif mois_actuel == '07':
        liste_mois = [f'{annee_fin}-05',f'{annee_fin}-06',f'{annee_fin}-07']
        liste = [4,5,6]
    elif mois_actuel == '08':
        liste_mois = [f'{annee_fin}-06',f'{annee_fin}-07',f'{annee_fin}-08']
        liste = [5,6,7]
    elif mois_actuel == '09':
        liste_mois = [f'{annee_fin}-07',f'{annee_fin}-08',f'{annee_fin}-09']
        liste = [6,7,8]
    elif mois_actuel == '10':
        liste_mois = [f'{annee_fin}-08',f'{annee_fin}-09',f'{annee_fin}-10']
        liste = [7,8,9]
    elif mois_actuel == '11':
        liste_mois = [f'{annee_fin}-09',f'{annee_fin}-10',f'{annee_fin}-11']
        liste = [8,9,10]
    elif mois_actuel == '12':
        liste_mois = [f'{annee_fin}-10',f'{annee_fin}-11',f'{annee_fin}-12']
        liste = [9,10,11]

    return liste_mois, liste

def nombre_jours_par_regime(mois_actuel,annee_actuelle):

    repartition =[]
    pourcentage = [[],[],[]]
    repartition_trimestrielle = []
    pourcentage_par_jour = []

    liste_mois = mois_selectionne(mois_actuel,annee_actuelle)[0]
    for i, mois_cible in enumerate(liste_mois):
        data_mois = max_regime.sel(time=mois_cible)
        repartition.append((data_mois.sum(dim='time')).values.tolist()) #Compte le nombre de jours par régimes
        repartition[i].append((data_mois.sum(dim='regime')==0).sum(dim='time').item())

    for i in range(len(repartition)):
        somme_liste = sum(repartition[i])
        for el in repartition[i]:
            pct = (el/somme_liste)*100
            pourcentage[i].append(round(pct,2))
    
    for k in range (len(repartition[0])):
        repartition_trimestrielle.append(repartition[0][k] + repartition[1][k] + repartition[2][k])
    
    somme_liste = sum(repartition_trimestrielle)
    for el in repartition_trimestrielle:
        pct = (el/somme_liste)*100
        pourcentage_par_jour.append(round(pct,2))

    return repartition, pourcentage, repartition_trimestrielle, pourcentage_par_jour

def save_histogrammes(mois_actuel,annee_actuelle,climatologie):

    repartition, pourcentage, repartition_trimestrielle, pourcentage_par_jour = nombre_jours_par_regime(mois_actuel,annee_actuelle)
    climatologie_simple, stockage = climatologie
    liste = mois_selectionne(mois_actuel,annee_debut_climatologie)[1]

# Extraction des mois d'hiver (Dec, Jan, Fev)
    titres_mois = [mois_noms[liste[0]],mois_noms[liste[1]],mois_noms[liste[2]] ]
    #couleurs = ["#8cc63f", "#ff8c00", "#0000ff", "#006400", "#6a0dad","#f2c300", "#ff0000", "#7f7f7f"]   Ancienne couleur de régime
    couleurs = ["#8B4513","#6a0dad","#0000ff","#F4A460","#ff0000","#43CEF8","#228B22","#7f7f7f"]

    labels_regimes = ['European Blocking', 'Scandinavian Blocking', 'Greenland Blocking','Atlantic Ridge', 'Zonal', 'Scandinavian Trough', 'Atlantic Trough', 'No Regime']
    #couleur = ["#6a0dad","#ff0000","#ff8c00","#f2c300","#8cc63f","#006400","#0000ff","#7f7f7f"]
    #["AT","ZO","ScBl","BrTr","EuBl","AR","GL","no"]

    # ==========================================
    # 2. CONFIGURATION DE LA FIGURE
    # ==========================================
    # On utilise GridSpec pour séparer les 3 mois du cumul (car les échelles Y sont différentes)
    fig = plt.figure(figsize=(14, 8))
    fig.suptitle(f"ERA5 : Regimes de temps de {titres_mois[0]} à {titres_mois[2]} {annee_actuelle}\n(période de référence de la climatologie ERA5 : {annee_debut_climatologie}-{annee_debut_climatologie+29})", fontsize=14, fontweight='bold')

    gs = fig.add_gridspec(1, 2, width_ratios=[4, 1.6], wspace=0.3)
    ax1 = fig.add_subplot(gs[0]) # Pour Dec, Jan, Fev
    ax2 = fig.add_subplot(gs[1]) # Pour le Cumul

    # ==========================================
    # 3. FONCTION DE TRACÉ
    # ==========================================
    def tracer_barres(ax, repartition, climatologie_simple, titres, is_cumul=False):
        x_pos = 0
        xticks_pos = []
        xticks_labels = []
        
        for i in range(len(repartition)):
            # Affichage du titre du mois en haut
            centre_mois = x_pos + 3.5
            ax.text(centre_mois, ax.get_ylim()[1] if is_cumul else 30, titres[i], 
                    ha='center', va='bottom', fontsize=14, fontweight='bold', color='#A020F0') # Violet
            
            for j in range(8): # 8 régimes
                val_reelle = repartition[i][j]
                val_clim = climatologie_simple[i][j]
                
                # Barre de climatologie (Hachurée, plus large)
                ax.bar(x_pos, val_clim, width=0.85, color='white', edgecolor=couleurs[j], 
                    hatch='//////', linewidth=0.5, alpha=0.5)
                
                # Barre des données réelles (Pleine, plus fine, centrée par-dessus)
                ax.bar(x_pos, val_reelle, width=0.65, color=couleurs[j], edgecolor='black')
                
                # Texte dans la barre pleine (Nombre de jours)
                if val_reelle > 0:
                    ax.text(x_pos +0.07, val_reelle - 0.2, str(int(val_reelle)), 
                            ha='center', va='top', fontweight='bold', rotation=90,
                            color='black' if couleurs[j] in ['#00FF00', '#FFA500'] else 'white')
                
                # Texte au-dessus (Pourcentage par rapport à la clim)
                if val_clim > 0:
                    pourcentage = int((val_reelle / val_clim) * 100)
                    hauteur_texte = max(val_reelle, val_clim) + 0.5
                    ax.text(x_pos, hauteur_texte, f"{pourcentage}%", 
                            ha='center', va='bottom', color=couleurs[j], rotation=90)
                
                # Préparation des labels de l'axe X (valeurs de climatologie)
                xticks_pos.append(x_pos)
                xticks_labels.append(str(round(val_clim, 1)))
                
                x_pos += 1 # Espacement entre les régimes d'un même mois
            x_pos += 1 # Espacement entre les mois

        # Formatage de l'axe X
        ax.set_xticks(xticks_pos)
        ax.set_xticklabels(xticks_labels, rotation=0, fontsize = 7, fontweight='bold')
        ax.tick_params(axis='x', length=0) # Cache les petits traits de l'axe X
        
        # Grille horizontale
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Esthétique des bordures
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)

    # ==========================================
    # 4. TRACÉ DES MOIS INDIVIDUELS (Graphique Gauche)
    # ==========================================
    reelles_hiver = [repartition[i] for i in range(len(liste))]
    clim_hiver = [climatologie_simple[i] for i in liste]

    ax1.set_ylim(0, 31)
    ax1.set_ylabel("Nombre de jours")
    tracer_barres(ax1, reelles_hiver, clim_hiver, titres_mois)

    # ==========================================
    # 5. TRACÉ DU CUMUL (Graphique Droit)
    # ==========================================
    cumul_reelles = [sum(x) for x in zip(*reelles_hiver)]
    # Estimation de la clim du cumul (somme des clims des 3 mois)
    cumul_clim = [sum(x) for x in zip(*clim_hiver)]

    # On déplace l'axe Y à droite pour le cumul (comme sur ton image)
    ax2.yaxis.tick_right()
    ax2.set_ylim(0, 66)
    tracer_barres(ax2, [cumul_reelles], [cumul_clim], [f"De {titres_mois[0]} à {titres_mois[2]}"], is_cumul=True)

    # Ajout de la légende manuellement
    legend_elements = [Patch(facecolor=couleurs[i], edgecolor='none', label=labels_regimes[i]) for i in range(8)]
    ax1.legend(handles=legend_elements, loc='lower left', bbox_to_anchor=(0.0, -0.15), 
            framealpha=1, edgecolor='black', ncol=4)

    plt.tight_layout()
    plt.savefig(f"../archives/images_climatiques/{annee_actuelle}_{mois_actuel}_histogrammes_suivi_climatique.png",bbox_inches="tight", pad_inches = 0.3)


####### Appel de la fontion pour plot on est sur ERA5 #######

if DATA_TYPE == 'ERA5':
    save_histogrammes(mois_actuel,int(annee_actuelle),climatologie)
    print('Génération des histogrammes réussie')