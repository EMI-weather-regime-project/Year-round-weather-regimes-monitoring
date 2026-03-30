import numpy as np
import xarray as xr
import pandas as pd

import matplotlib.pyplot as plt
import matplotlib.path as mpath
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.colors import TwoSlopeNorm

import regionmask
import json
import seaborn as sns
import warnings

# À modifier : traitement des concat dans la fonction composite pour les terciles -> notre version initiale ne marche plus (fonction composite terciles)
# Essayer de voir si mettre drop_feb29 à True permet de renvoyer des choses ou pas -> devrait être bon, fonctionne pour les terciles 

###########################################################
# ------------ Choix des paramètres et autres ------------
###########################################################

# On enlève tous les prints warning inutiles qui apparaissent dans le terminal
warnings.filterwarnings('ignore')

# Choix des paramètres de début et de fin
tstart = "1960-01-01"    
tend   = "2025-12-31"       

# Traitement du 29 février
drop_feb29 = True # True: retire 29/02 pour avoir DOY strict 1..365 (sinon on garde 29/02)


###########################################################
# --------------- Récupération des données ---------------
###########################################################

# On récupère l'ordre des régimes obtenus à partir des kmeans (produit par data_maker.py)
with open("donnees_sauvegardees/cluster_regime_names.json", "r", encoding="utf-8") as f:
    cluster_regime_names = json.load(f)

# On ne prend que les noms de régimes avec le .values()
cluster_regime_names = list(cluster_regime_names.values())

# On récupère la liste des attributions du régime actif par jour 
data_label = pd.read_csv("donnees_sauvegardees/label_indice.csv")  #On parcourt le fichier .csv    
label_indice = data_label.iloc[:,0].tolist() # On transforme les données en une liste
# Exemple : 
    # - position 0 : 1er jour de la période considérée
    # - numéro à la position 0 : indice du régime actif le premier jour de la période considérée


###########################################################
# --------- Paramètres pour produire les figures ---------
###########################################################

Saison = ["hiver","printemps","été","automne"]
Domaine = ["Global","Europe","France"]
Parametre = ["pr","tas"]
Regime = cluster_regime_names #["Atlantic Trough","Atlantic Ridge","Scandinavian Blocking","Zonal","Scandinavian Trough","Greenland Blocking", "European Blocking","No Regime"]


###########################################################
# ------- Paramètres pour la sauvegarde des figures -------
###########################################################

cluster_regime_names_false = ["European Blocking","Scandinavian Blocking","Greenland Blocking","Atlantic Ridge","Zonal","Scandinavian Trough","Atlantic Trough","No Regime"]
nom_mois=["Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Aout","Septembre","Octobre","Novembre","Décembre"]
dict_abreviation_regime = {"European Blocking":"EB","Scandinavian Blocking" : "SB","Atlantic Ridge": "AR", "Greenland Blocking" : "GB","Zonal": "ZO", "Scandinavian Trough" : "ST", "Atlantic Trough" : "AT", "No Regime" : "NR"}


###########################################################
# ---------- Fonction de formatation des données ----------
###########################################################

def open_dataset(path):
    """Ouvre le dataset et renomme les dimensions lat/lon
    """
    ds = xr.open_dataset(path)
    if "latitude" in ds.coords:
        ds = ds.rename({"latitude": "lat"})
    if "longitude" in ds.coords:
        ds = ds.rename({"longitude": "lon"})
    return ds

def remove_feb29(da):
    """Optionnel : retirer 29 février (utilisé si drop_feb29=True)."""
    if ((da.time.dt.month == 2) & (da.time.dt.day == 29)).any():
        return da.sel(time=~((da.time.dt.month == 2) & (da.time.dt.day == 29)))
    else:
        return da
    

###########################################################
# ---- Fonctions de sélection des paramètres d'intérêt ----
###########################################################

def choix_domaine(domaine):
    """
    Renvoie les latitudes et longitudes limites du domaine choisi 
    ATTENTION : les latitudes sont décroissantes dans dimension lat
    Pour domaine, entrez "France" pour la France (ou un des paramètres suivants : "Europe", "Global")
    """
    if domaine=="Global":
        return((90, 30),(-80, 40))
    if domaine=="Europe":
        return((72, 30),(-25, 40))
    if domaine=="France":
        return((52, 40),(-6, 11))
    if domaine == "Corse":
        return((44, 40),(7, 11))

def mois_saison(saison):
    """
    Renvoie les indices des mois relatifs à la saison sélectionnée
    Pour saison, entrez "hiver" pour hiver (ou un des paramètres suivants : "printemps", "été", "automne")
    """
    if saison == "hiver":
        return([12,1,2])
    if saison == "printemps":
        return([3,4,5])
    if saison == "été":
        return([6,7,8])
    if saison == "automne":
        return([9,10,11])
    if saison == "Vivaldi":
        return([12,1,2],[3,4,5],[6,7,8],[9,10,11])

def mois_saison_alphabet(saison):
    """
    Pour une saison selectionnée : renvoie les premières lettres des mois relatifs à la saison sélectionnée
    Pour une année entière selectionnée : renvoie une liste des premières lettres des mois pour toutes les saisons
    Pour saison, entrez "hiver" pour hiver (ou un des paramètres suivants : "printemps", "été", "automne")
    """
    if saison == "hiver":
        return("DJF")
    if saison == "printemps":
        return("MAM")
    if saison == "été":
        return("JJA")
    if saison == "automne":
        return("SON")
    if saison == "Vivaldi":
        return(["DJF","MAM","JJA","SON"])

def abreviation_domaine(domaine):
    """
    Renvoie l'abréviation du nom du domaine pour un domaine selectionné
    Nécessaire dans la sauvegarde des fichiers 
    Pour domaine, entrez "France" pour la France (ou un des paramètres suivants : "Europe", "Global")
    """
    if domaine == "Global":
        return("Gl")
    if domaine == "Europe":
        return("Eu")  
    if domaine == "France":
        return("Fr")
    if domaine == "Corse":
        return("Co")
    

###########################################################
# ---------- Fonctions de traitement des données ----------
###########################################################

def repartition_jour_regime(label_indice_slice): 
    """
    Répartit les indices des jours selon le numéro du régime auquel ils sont associés.
    Exemple : si le dataset va du 1960-01-01 au 2025-12-31, alors le jour 1 correspond au premier jour du dataset, le 1960-01-01
    """
    repartition = [[] for i in range(8)] 
    for k, regime in enumerate(label_indice_slice):
        repartition[regime].append(k)

    # Renvoie une liste, de listes des indices des jours relatif à chaque régime
    return repartition 

def fonction_composite(label_indice,drop_feb29,parameter,liste_mois,domaine,mask_on=False): 
    """
    Renvoie les données pour l'affichage des composites selon le(s) paramètre(s) demandé(s) et la saison demandée
    Nécessaire pour l'affichage de tous les composites
    Avec les options : 
        - drop_feb29 : enlever les 29 février (drop_feb = True)
        - mask_on : pour ne faire que les calculs sur la France (mask_on = True)
    Exemple :
    - pour liste_mois : pour l'hiver, entrez liste_mois = [12,1,2]"
    - pour parameter, entrez "tas" pour la temperature au sol ou "pr" pour les precipitations
    - pour domaine, entrez "France" pour la France (ou un des paramètres suivants : "Europe", "Global")
    """

    # -----------------------------
    # Ouverture des données
    # -----------------------------
    # Choix du dataset selon le paramètre sélectionné
    if parameter == "pr":
        data_path =   "../data/climatologie/precip_era5_1940_2025.nc"
    
    elif parameter == "tas":
        data_path = "../data/climatologie/tas_era5_day_raw_1940-2025.nc"
    
    # Définition du domaine
    tuple_latitude,tuple_longitude=choix_domaine(domaine)
    domain = dict(lat=slice(tuple_latitude[0],tuple_latitude[1]), lon=slice(tuple_longitude[0],tuple_longitude[1]))
    dataset = open_dataset(data_path)
    
    # Extraction du paramètre considéré dans le dataset
    ds = dataset[parameter]
    ds=ds.sortby("lat", ascending = False) # On ordonne les latitudes dans le bon sens (sens décroissant)
    ds = ds.sel(time=slice(tstart, tend))
    ds = ds.sel(**domain).squeeze()

    # Option : retirer 29/02 si on veut DOY strict
    if drop_feb29:
        ds = remove_feb29(ds)
    
    # Calcul des anomalies quotidiennes (groupees par dayofyear puis soustraction de la climatologie du jour)
    anom=ds.groupby("time.dayofyear") - ds.groupby("time.dayofyear").mean("time")

    # -----------------------------
    # Paramètres
    # -----------------------------
    # On récupère la liste des numéros de régimes pour chaque jour, en considérant la dernière date dans le dataset
    date_end = len(anom.time)
    print(date_end)
    label_indice_slice = label_indice[0:date_end]

    # -----------------------------
    # Répartition des jours selon les régimes
    # -----------------------------
    repartition = repartition_jour_regime(label_indice_slice)
    nb_regimes = len(repartition)

    # -----------------------------
    # Application du masque si nécessaire (masque sur la France, pour ne traiter que les données sur la France)
    # -----------------------------
    if mask_on :
        mask = regionmask.defined_regions.natural_earth_v5_0_0.countries_110.mask_3D(anom) # Création du masque général
        mask_FR = mask.sel({'region' :43}) # Selection du masque sur la France : masque numéro 43
        stacked = anom.where(mask_FR,drop=True)
        ds = ds.where(mask_FR, drop = True)
            
    # -----------------------------
    # Calcul des composites
    # -----------------------------
    moyenne_par_point_mois = [] # Moyenne par point sur l'ensemble des mois de liste_mois pour chaque régime 
    liste_stacked_mois = [] # Stocke les anomalies relatives à un régime pour les mois selectionné

    # On traite les données régime par régime
    for i in range (nb_regimes):
        stacked = anom.isel(time=repartition[i]) # Concaténation des anomalies relatives au régime i
        stacked_mois = stacked.where(stacked['time.month'].isin(liste_mois),drop=True) # Récupèration des données des mois sélectionnés
        moyenne_par_point_mois.append(stacked_mois.mean(dim="time")) # Moyenne par point sur la période de mois choisis
        liste_stacked_mois.append(stacked_mois) 
    
    # -----------------------------
    # Fréquence des régimes
    # -----------------------------
    nb_jour_tot=len(label_indice_slice)
    RdT_nb, nb_jour = np.unique(label_indice_slice, return_counts=True)    
    pourcentage_RdT=100*nb_jour/nb_jour_tot

    # Renvoie :
    # - Moyenne par point sur l'ensemble des mois de liste_mois pour chaque régime 
    # - Le dataset 
    # - Les pourcentages d'occurrences des régimes de temps
    # - La liste liste_stacked_mois (longueur = 8 pour les 7 régimes + No Regime): stocke les anomalies relatives aux régimes pour les mois selectionné
        # Exemple : liste_stacke_mois[0] = anomalies concaténées du régime 0 pour les mois selectionnés

    return moyenne_par_point_mois,ds,pourcentage_RdT,liste_stacked_mois

def fonction_composite_psl_ou_zg500(liste_mois,parameter2,domaine):
    """
    Renvoie les données pour l'affichage de la Pmer (psl) ou de la zg500 (zg500) le(s) paramètre(s) demandé(s) et la saison demandée
    Nécessaire pour l'affichage des composites pour laquelle on l'affiche
    Exemple :
    - pour liste_mois : pour l'hiver, entrez liste_mois = [12,1,2]"
    - pour parameter2, entrez "psl" pour la Pmer ou "zg500" pour la zg500
    - pour domaine, entrez "France" pour la France (ou un des paramètres suivants : "Europe", "Global")
    """

    # -----------------------------
    # Ouverture des données
    # -----------------------------
    # Choix du dataset selon le paramètre sélectionné
    if parameter2 == "psl":
        data_path_psl_ou_zg500 = "../data/climatologie/psl_era5_day_raw_1940-2025.nc"
    
    elif parameter2 == "zg500":
        data_path_psl_ou_zg500 = "../data/climatologie/zg500_era5_day_raw_1940-2025.nc"

    # Définition du domaine
    dataset = open_dataset(data_path_psl_ou_zg500)
    tuple_latitude,tuple_longitude=choix_domaine(domaine)
    domain = dict(lat=slice(tuple_latitude[0],tuple_latitude[1]), lon=slice(tuple_longitude[0],tuple_longitude[1]))

    # Extraction du paramètre considéré dans le dataset
    ds = dataset[parameter2]
    ds = ds.sel(time=slice(tstart, tend))
    ds = ds.sel(**domain).squeeze()

    # Option : retirer 29/02 si on veut DOY strict
    if drop_feb29:
        ds = remove_feb29(ds)
            
    # -----------------------------
    # Paramètres
    # -----------------------------
    # On récupère la liste des numéros de régimes pour chaque jour, en considérant la dernière date dans le dataset
    date_end = len(ds.time)
    print(date_end)
    label_indice_slice = label_indice[:date_end]

    # -----------------------------
    # Répartition des jours selon les régimes
    # -----------------------------
    repartition = repartition_jour_regime(label_indice_slice)    #repartition pour l'année
    nb_regimes = len(repartition)

    #------------------------------
    # Calcul du champ
    # -----------------------------
    moyenne_par_point_mois = [] # Moyenne par point sur l'ensemble des mois de liste_mois pour chaque régime 

    # On traite les données régime par régime
    for i in range (nb_regimes):
        stacked = ds.isel(time=repartition[i]) # Concaténation des données relatives au régime i
        stacked_mois = stacked.where(stacked['time.month'].isin(liste_mois),drop=True) # Récupèration des données des mois sélectionnés
        moyenne_par_point_mois.append(stacked_mois.mean(dim="time")) # Moyenne par point sur la période de mois choisis

    # Renvoie :
        # - Moyenne par point sur l'ensemble des mois de liste_mois pour chaque régime 
        # - Le dataset 

    return ds,moyenne_par_point_mois

def fonction_composite_psl_ou_zg500_tercile(date_33_ou_66,parameter2,domaine):
    """
    Renvoie les données pour l'affichage de la Pmer (psl) ou de la zg500 (zg500) selon le(s) paramètre(s) demandé(s)
    Nécessaire pour l'affichage des terciles
    Exemple :
    - pour parameter2, entrez "psl" pour la Pmer ou "zg500" pour la zg500
    - pour domaine, entrez "France" pour la France (ou un des paramètres suivants : "Europe", "Global")

    """

    # -----------------------------
    # Ouverture des données
    # -----------------------------
    # Choix du dataset selon le paramètre sélectionné
    if parameter2 == "psl":
        data_path_psl_ou_zg500 = "../data/climatologie/psl_era5_day_raw_1940-2025.nc"
    
    elif parameter2 == "zg500":
        data_path_psl_ou_zg500 = "../data/climatologie/zg500_era5_day_raw_1940-2025.nc"

    # Définition du domaine
    dataset = open_dataset(data_path_psl_ou_zg500)
    tuple_latitude,tuple_longitude=choix_domaine(domaine)
    domain = dict(lat=slice(tuple_latitude[0],tuple_latitude[1]), lon=slice(tuple_longitude[0],tuple_longitude[1]))

    # Extraction du paramètre considéré dans le dataset
    ds = dataset[parameter2]
    ds = ds.sel(time=slice(tstart, tend))
    ds = ds.sel(**domain).squeeze()

    # Option : retirer 29/02 si on veut DOY strict
    if drop_feb29:
        ds = remove_feb29(ds)
    
    #------------------------------
    # Calcul du champ
    # -----------------------------
    moyenne_par_point_mois_33_ou_66 = [] # Moyenne par point pour le tercile considéré pour chaque régime (tercile inférieur ou supérieur)
    nb_regimes = len(date_33_ou_66) # Nombre de régimes (7 régimes + No Regime)

    # On traite les données régime par régime
    for i in range (nb_regimes):
        dates = pd.to_datetime(date_33_ou_66[i]).floor("D")
        mask_dates = ds.time.dt.floor("D").isin(dates)
        stacked = ds.sel(time=mask_dates)
        moyenne_par_point_mois_33_ou_66.append(stacked.mean(dim="time"))

        # Notre version initiale, qui fonctionne si les données de précipitations n'ont pas les latitudes inversées
        #stacked = ds.sel(time=date_33_ou_66[i])
        #moyenne_par_point_mois_33_ou_66.append(stacked.mean(dim="time"))

     # Renvoie :
        # - Moyenne par point pour le tercile considéré pour chaque régime (tercile inférieur ou supérieur)        
    return moyenne_par_point_mois_33_ou_66

def bootstrap(stacked_DJF, n_iterations): 
    """
    Renvoie un masque de significativité des données   
    Le bootstrap est utilisé dans tous les composites sauf le composite tous les régimes/toutes les saisons (Vivaldi) et les terciles
    Pour n_iterations, entrez le nombre d'itérations souhaité
    """

    # Data : array (time, ...)
    data = np.asarray(stacked_DJF)
    n_time = data.shape[0]

    # Tirages bootstrap (indices)
    idx = np.random.randint(0,n_time, size = (n_iterations,n_time))

    # rRsampling vectorisé
    samples = data[idx]
    # shape : (n_iter, n_time, ...)

    # Moyenne sur le temps (time)
    means = samples.mean(axis = 1)

    # Quantiles
    q0025 = np.quantile(means,0.025, axis = 0)
    q0925 = np.quantile(means,0.975, axis = 0)

    # Les données dans le quantile 0.025 (2,5%) et au-dessus du quantile 0.0975 (97,5%) sont décrétées non significatives
    masque = ((0 >= q0025) & (0 <= q0925)).astype(int)

    return(masque)

    # Avec xskillscore 
    """
    pr_resampled = xs.resampling.resample_iterations_idx(stacked_DJF, n_iterations, dim='time',replace=True).mean(dim = 'time')
        
    q0025 = pr_resampled.quantile(q=0.025,dim='iteration',skipna=True)
    q0975 = pr_resampled.quantile(q=0.975,dim='iteration',skipna=True)
    masque = ((0 >= q0025) & (0 <= q0975)).astype(int)
    
    return masque
    """


###########################################################
# ---------- Fonction pour créer un chemin fermé ----------
###########################################################

def make_boundary_path(latS, latN, lonW, lonE, n=100):
    """
    Traitement des latitudes et longitudes nécessaire à l'affichage des composites
    """

    verts = []
    verts += list(zip(np.linspace(lonW, lonE, n), np.full(n, latN)))  # haut
    verts += list(zip(np.full(n, lonE), np.linspace(latN, latS, n)))  # droite
    verts += list(zip(np.linspace(lonE, lonW, n), np.full(n, latS)))  # bas
    verts += list(zip(np.full(n, lonW), np.linspace(latS, latN, n)))  # gauche
    verts.append(verts[0])
    codes = [mpath.Path.LINETO] * len(verts)
    codes[0] = mpath.Path.MOVETO

    return mpath.Path(verts, codes)


###########################################################
# ------------------ Affichage des plots ------------------
###########################################################

def affichage_affichage_psl_ou_zg500psl_ou_zg500(liste_mois,parameter2,domaine):
    """
    Permet de tester l'affichage du champ de Pmer (psl) ou zg500 (zg500)
    Exemple :
    - pour liste_mois : pour l'hiver, entrez liste_mois = [12,1,2]"
    - pour parameter2, entrez "psl" pour la Pmer ou "zg500" pour la zg500
    """

    # On traite les données avec fonction_composite_psl_ou_zg500
    ds, moyenne_par_point_mois = fonction_composite_psl_ou_zg500(liste_mois,parameter2,domaine)

    # ---------- Limites du domaine ----------
    lonW, lonE = ds.lon[0].values, ds.lon[-1].values
    latS, latN = ds.lat[0].values, ds.lat[-1].values

    boundary_path = make_boundary_path(latS, latN, lonW, lonE)

    # ---------- Projection ----------
    proj = ccrs.Orthographic(central_longitude=(lonW + lonE)/2, central_latitude=(latS + latN)/2)

    # ---------- Min / Max pour info ----------
    all_data = xr.concat(moyenne_par_point_mois,dim='regime')

    # Traitement du paramètre 2 : Pmer (psl) ou zg500 (zg500)
    if parameter2 == "psl" : 
        coeff_pour_bonne_valeur = 100
        min_anom = float(all_data.min())/coeff_pour_bonne_valeur
        max_anom = float(all_data.max())/coeff_pour_bonne_valeur
        print(f"Min anomaly = {min_anom:.3f} hPa")
        print(f"Max anomaly = {max_anom:.3f} hPa")

    elif parameter2 =="zg500":
        coeff_pour_bonne_valeur = 10
        min_anom = float(all_data.min())/coeff_pour_bonne_valeur
        max_anom = float(all_data.max())/coeff_pour_bonne_valeur
        print(f"Min anomaly = {min_anom:.3f} damgp")
        print(f"Max anomaly = {max_anom:.3f} damgp")

    # ---------- Figure ----------
    fig, axes = plt.subplots(2, 4, figsize=(18, 8), subplot_kw=dict(projection=proj))
    axes = axes.flatten()

    for k,ax in enumerate(axes):

        # Isolignes
        c = ax.contour(ds.lon, ds.lat, moyenne_par_point_mois[k]/coeff_pour_bonne_valeur, colors="brown", linewidths=0.7, transform=ccrs.PlateCarree())  #ISOLIGNES
        ax.clabel(c, fmt="%d", fontsize=7) #COTES

        # Cartographie
        ax.coastlines()
        ax.add_feature(cfeature.BORDERS, linewidth=0.3)
        ax.set_extent([lonW, lonE, latS, latN], crs=ccrs.PlateCarree())
        ax.set_boundary(boundary_path, transform=ccrs.PlateCarree())

        # Titre par régime
        ax.set_title(f"{cluster_regime_names[k]}", fontsize=11) 
        
    # ---------- Ajustement des espaces ----------
    fig.subplots_adjust(hspace=0.05, wspace=0.02)
    plt.suptitle(
        "K-means clustering in EOF space (7 regimes + no-regime)\n psl mean",
        fontsize=15, y=0.94
    )

    plt.show()

def affichage_composite_une_saison(label_indice,drop_feb29,parameter,parameter2,saison,domaine,pression,bootstrap_ok):
    """
    Produit et enregistre le composite tous les régimes/1saison
    Avec les options :
        - drop_feb29 : enlever les 29 février (drop_feb = True) 
        - Bootstrap (bootstrap_ok = True)
        - Pression (pression = True)
    Exemple :
    - pour parameter, entrez "tas" pour la temperature au sol ou "pr" pour les precipitations
    - pour parameter2, entrez "psl" pour la Pmer ou "zg500" pour la zg500
    - pour saison, entrez "hiver" pour hiver (ou un des paramètres suivants : "printemps", "été", "automne")
    - pour domaine, entrez "France" pour la France (ou un des paramètres suivants : "Europe", "Global")
    """

    # Initialisation
    liste_mois=mois_saison(saison)
    levels_psl = np.arange(940,1041,5)
    levels_psl= levels_psl.tolist()
    levels_psl.remove(1015)

    # ---------- Calcul des composites ----------
    # On traite les données avec fonction_composite et fonction_composite_psl_ou_zg500
    moyenne_par_point_mois,ds,pourcentage_RdT,liste_stacked_mois = fonction_composite(label_indice, drop_feb29,parameter,liste_mois,domaine)
    ds, moyenne_par_point_mois_psl = fonction_composite_psl_ou_zg500(liste_mois,parameter2,domaine)

    # ---------- Limites du domaine ----------
    lonW, lonE = ds.lon[0].values, ds.lon[-1].values
    latS, latN = ds.lat[0].values, ds.lat[-1].values
    boundary_path = make_boundary_path(latS, latN, lonW, lonE)

    # ---------- Projection ----------
    proj = ccrs.Orthographic(central_longitude=(lonW + lonE)/2, central_latitude=(latS + latN)/2)

    # ---------- Formatage de l'image selon le paramètre considéré ----------
    if parameter == "pr":
        levels_anom = np.arange(-6,6.2,0.25)
        levels_anom_bis = np.arange(-6,6.2,0.5)
        cmap = plt.get_cmap("BrBG")
        norm = TwoSlopeNorm(vmin=-6, vcenter=0, vmax=6) 
        unit_label = 'mm/jour'
        parameter_name = "précipitations"

    elif parameter == "tas":
        levels_anom = np.arange(-5,5.2,0.25)
        levels_anom_bis = np.arange(-5,5.2,0.5)
        cmap = plt.get_cmap("RdBu_r")
        norm = TwoSlopeNorm(vmin=-5, vcenter=0, vmax=5)
        unit_label = '°C'
        parameter_name = "température à 2m"

    # ---------- Min / Max pour info ----------
    all_data = xr.concat(moyenne_par_point_mois,dim="regime")
    print(f"Min anomaly = {float(all_data.min()):.3f} {unit_label}")
    print(f"Max anomaly = {float(all_data.max()):.3f} {unit_label}")

    # ---------- Figure ----------
    fig, axes = plt.subplots(2, 4, figsize=(18, 8), subplot_kw=dict(projection=proj))
    axes = axes.flatten()

    # Trace les vignettes régime par régime (8 vignettes au total)
    for k, ax in enumerate(axes):
        # Récupère dans les données les indices des régimes obtenus à partir des kmeans
        regime_position = cluster_regime_names_false[k]
        indice_regime = cluster_regime_names.index(regime_position)
        data_plot = moyenne_par_point_mois[indice_regime]

        # ---------- Isolignes ----------
        cf = ax.contourf(data_plot.lon, data_plot.lat, data_plot, levels=levels_anom, cmap=cmap, norm=norm, extend="both", transform=ccrs.PlateCarree())

        # ---------- Bootstrap ----------
        if bootstrap_ok :
            masque = (bootstrap(liste_stacked_mois[indice_regime], n_iterations = 50))
            ax.contourf(data_plot.lon, data_plot.lat, masque, hatches=[None,'...'], colors='none', levels=[-1, 0.5,1.5], transform=ccrs.PlateCarree(),add_colorbar = False)

        # ---------- Pression ----------
        if pression :
            c = ax.contour(ds.lon, ds.lat, moyenne_par_point_mois_psl[indice_regime]/100,levels=levels_psl, colors="brown", linewidths=0.7, transform=ccrs.PlateCarree())  #ISOLIGNES
            ax.clabel(c, fmt="%d", fontsize=7) #COTES
            c1015 = ax.contour(ds.lon, ds.lat, moyenne_par_point_mois_psl[indice_regime]/100,levels=[1015], colors="brown",linewidths=2.1,transform=ccrs.PlateCarree())
            ax.clabel(c1015, fmt="%d", fontsize=9)

        # ---------- Cartographie ----------
        ax.coastlines()
        ax.add_feature(cfeature.BORDERS, linewidth=0.3)
        ax.set_extent([lonW, lonE, latS, latN], crs=ccrs.PlateCarree())
        ax.set_boundary(boundary_path, transform=ccrs.PlateCarree())

        # ---------- Titre de la vignette ----------
        ax.set_title(f"{cluster_regime_names_false[k]}", fontsize=11)
    
    # ---------- Colorbar horizontale centrée ----------
    cbar_ax = fig.add_axes([0.15, 0.06, 0.7, 0.02])  # [left, bottom, width, height]    
    cbar = plt.colorbar(cf, cax=cbar_ax, orientation="horizontal",location = 'bottom', shrink = 1,aspect=5,ticks=levels_anom_bis, label=f"Anomalies de {parameter} en {unit_label}")
    cbar.set_label(label = f"{parameter_name} en {unit_label}", size=10, weight='bold',loc="center")

    # ---------- Ajustement des espaces ----------
    fig.subplots_adjust(hspace=0.15, wspace=0.04)

    # ---------- Titre du composite ----------
    plt.suptitle(
        f"Anomalies moyennes de {parameter_name} pour {saison} ",
        fontsize=15, y=0.97
    )

    # Paramètres de sauvegarde (pour le nom du fichier)
    saison_alphabet = mois_saison_alphabet(saison)
    abv_domaine = abreviation_domaine(domaine)

    # Sauvegarde du fichier
    plt.savefig(f"../archives/images_composites/{saison_alphabet}_All_{parameter}_{abv_domaine}.png",bbox_inches="tight", pad_inches = 0.3)

def affichage_composite_un_regime(label_indice,drop_feb29,parameter,parameter2,saison,domaine,regime,pression,bootstrap_ok):
    """
    Produit et enregistre le composite 1 régime/toutes les saisons
    Avec les options : 
        - drop_feb29 : enlever les 29 février (drop_feb = True)
        - Choix du paramètre 2 : Pmer ("psl") ou zg500 ("zg500")
        - Bootstrap (bootstrap_ok = True)
        - Pression (pression = True)
    Exemple :
    - pour parameter, entrez "tas" pour la temperature au sol ou "pr" pour les precipitations
    - pour parameter2, entrez "psl" pour la Pmer ou "zg500" pour la zg500
    - pour saison, entrez "hiver" pour hiver (ou un des paramètres suivants : "printemps", "été", "automne")
    - pour domaine, entrez "France" pour la France (ou un des paramètres suivants : "Europe", "Global")
    - pour regime, entrez "European Blocking" pour European Blocking (ou un des paramètres suivants : "Scandinavian Blocking", "Greenland Blocking", 
            "Atlantic Ridge", "Zonal", "Scandinavian Trough",c"Atlantic Trough", "No Regime")
    """

    # ---------- Initialisation ----------
    levels_psl = np.arange(940,1041,5) # On choisi le pas du champ que l'on va afficher (5 ici)
    levels_psl= levels_psl.tolist()
    levels_psl.remove(1015)
    liste_saison = [[12,1,2],[3,4,5],[6,7,8],[9,10,11]] # Liste des mois correspondants aux saisons
    raw_titles = mois_saison_alphabet(saison)

    # On traite les données avec fonction_composite_psl_ou_zg500
    ds,moyenne_par_point_mois_psl = fonction_composite_psl_ou_zg500(label_indice,parameter2,domaine)
    
    # ---------- Limites du domaine ----------
    lonW, lonE = ds.lon[0].values, ds.lon[-1].values
    latS, latN = ds.lat[0].values, ds.lat[-1].values

    boundary_path = make_boundary_path(latS, latN, lonW, lonE)

    # ---------- Projection ----------
    proj = ccrs.Orthographic(central_longitude=(lonW + lonE)/2, central_latitude=(latS + latN)/2)

    # ---------- Figure ----------
    fig, axes = plt.subplots(1, 4,figsize=(18, 8),subplot_kw=dict(projection=proj),tight_layout=True)
    axes = axes.flatten()

    # Stockage des masques de significativité pour les quatre saisons
    masque = [[],[],[],[]] 

    # Paramètres de sauvegarde (pour le nom du fichier)
    nb_regime = cluster_regime_names.index(regime)
    save_regime=dict_abreviation_regime[regime]

    # On traite les données saison par saison
    for i in range (4): 
        ax = axes[i]

        # On traite les données avec fonction_composite et fonction_composite_psl_ou_zg500
        moyenne_par_point_mois,ds,pourcentage_RdT,liste_stacked_mois= fonction_composite(label_indice, drop_feb29,parameter,liste_saison[i],domaine)
        moyenne_par_point_mois_psl_ou_zg500 = fonction_composite_psl_ou_zg500(liste_saison[i],parameter2,domaine)[1]

        # ---------- Calcul des anomalies minimales et maximales ----------
        min_anom = float(np.min(moyenne_par_point_mois))
        max_anom = float(np.max(moyenne_par_point_mois))

        # ---------- Paramètre considéré ----------
        if parameter == "pr":
            print(f"Min anomaly = {min_anom:.3f} mm")
            print(f"Max anomaly = {max_anom:.3f} mm")
            levels_anom = np.arange(-6,6.2,0.25)
            levels_anom_bis = np.arange(-6,6.2,0.5)
            norm = TwoSlopeNorm(vmin=-6, vcenter=0, vmax=6) 
            cmap = plt.get_cmap("BrBG")

        elif parameter == "tas":
            print(f"Min anomaly = {min_anom:.3f} °C")
            print(f"Max anomaly = {max_anom:.3f} °C")
            levels_anom = np.arange(-5,5.2,0.25)
            levels_anom_bis = np.arange(-5,5.2,0.5)
            norm = TwoSlopeNorm(vmin=-5, vcenter=0, vmax=5)
            cmap = plt.get_cmap("RdBu_r")

        # ---------- Isolignes ----------
        cf = ax.contourf(moyenne_par_point_mois[nb_regime].lon, moyenne_par_point_mois[nb_regime].lat, moyenne_par_point_mois[nb_regime], levels=levels_anom, cmap=cmap, norm=norm, extend="both", transform=ccrs.PlateCarree())

        # ---------- Formatage de l'image selon le paramètre considéré ----------
        if parameter == "pr":
            unity="mm/jour"
            parameter_name="précipitations"

        elif parameter == "tas":
            unity="°C"
            parameter_name="température à 2m"

        # ---------- Bootstrap ----------
        if bootstrap_ok :
            masque[i].append(bootstrap(liste_stacked_mois[nb_regime], n_iterations = 50))
            ax.contourf(moyenne_par_point_mois[nb_regime].lon, moyenne_par_point_mois[nb_regime].lat, masque[i][0],hatches=[None,'...'], colors='none', levels=[-1, 0.5,1.5], transform=ccrs.PlateCarree(),add_colorbar = False)

        # ---------- Pression ----------
        if pression :
            c = ax.contour(ds.lon, ds.lat, moyenne_par_point_mois_psl_ou_zg500[nb_regime]/100,levels=levels_psl, colors="brown", linewidths=0.7, transform=ccrs.PlateCarree())  #ISOLIGNES
            ax.clabel(c, fmt="%d", fontsize=7) #COTES
            c1015 = ax.contour(ds.lon, ds.lat, moyenne_par_point_mois_psl_ou_zg500[nb_regime]/100,levels=[1015], colors="brown",linewidths=2.1,transform=ccrs.PlateCarree())
            ax.clabel(c1015, fmt="%d", fontsize=9)

        # ---------- Cartographie ----------
        ax.coastlines()
        ax.add_feature(cfeature.BORDERS, linewidth=0.3)
        ax.set_extent([lonW, lonE, latS, latN], crs=ccrs.PlateCarree())
        ax.set_boundary(boundary_path, transform=ccrs.PlateCarree())
    
        # ---------- Titre de la vignette ----------
        ax.set_title(f"{raw_titles[i]}", fontsize=11,pad=6)

    # ---------- Colorbar horizontal centré ----------
    cbar_ax = fig.add_axes([0.15, 0.20, 0.7, 0.03])  # [left, bottom, width, height]
    cbar=plt.colorbar(cf, cax=cbar_ax, orientation="horizontal", location = 'bottom', shrink = 1,aspect=5,ticks=levels_anom_bis)
    cbar.set_label(label = f"{parameter_name} en {unity}", size=10, weight='bold',loc="center")

    # Titre du composite
    plt.suptitle(f"Anomalies moyennes de {parameter_name} pour le régime : {regime}", fontsize=14, y = 0.78)
    
    # Ajustement des espaces
    fig.subplots_adjust(hspace=0.09, wspace=0.04)
    
    # Formatage du nom du fichier
    abv_domaine = abreviation_domaine(domaine)

    # Sauvegarde du fichier
    plt.savefig(f"../archives/images_composites/All_{save_regime}_{parameter}_{abv_domaine}.png",bbox_inches="tight", pad_inches = 0.3)

def affichage_composite_vivaldi(label_indice,drop_feb29,parameter,domaine,pression=False, zg500=False,bootstrap_ok=False):
    """
    Affichage du composite tous les régimes/toutes les saisons
    Options :
        - drop_feb29 : enlever les 29 février (drop_feb = True)
        - Bootstrap (bootstrap_ok = True)
        - Pression (pression = True)
        - zg500 (zg500 = True)
    Exemple :
    - pour parameter, entrez "tas" pour la temperature au sol ou "pr" pour les precipitations
    - pour domaine, entrez "France" pour la France (ou un des paramètres suivants : "Europe", "Global")
    """
    
    # ---------- Initialisation ----------
    liste_saison = [[12,1,2],[3,4,5],[6,7,8],[9,10,11]] #Liste des mois correspondants aux saisons
    row_titles = ["DJF","MAM","JJA","SON"]
    levels_psl = np.arange(940,1041,5)
    levels_psl= levels_psl.tolist()
    levels_psl.remove(1015)

    # ---------- Domaine ----------
    ds = fonction_composite(label_indice, drop_feb29,parameter,liste_saison[0],domaine)[1]
    lonW, lonE = ds.lon[0].values, ds.lon[-1].values
    latS, latN = ds.lat[0].values, ds.lat[-1].values
    boundary_path = make_boundary_path(latS, latN, lonW, lonE)

    # ---------- Projection ----------
    proj = ccrs.Orthographic(central_longitude=(lonW + lonE)/2, central_latitude=(latS + latN)/2)

    # ---------- Formatage de l'image selon le paramètre considéré ----------
    if parameter == "pr":
        levels_anom = np.arange(-6,6.6,0.25)
        levels_anom_bis = np.arange(-6,6.2,0.5)
        cmap = plt.get_cmap("BrBG")
        norm = TwoSlopeNorm(vmin=-6, vcenter=0, vmax=6) 
        unit_label = "mm/jour"
        parameter_name = "précipitations"

    elif parameter == "tas":
        levels_anom = np.arange(-5,5.2,0.25)
        levels_anom_bis = np.arange(-5,5.2,0.5)
        cmap = plt.get_cmap("RdBu_r")
        norm = TwoSlopeNorm(vmin=-5, vcenter=0, vmax=5) 
        unit_label = "°C"
        parameter_name = "température à 2m"
       
    # ---------- Figure ----------
    fig, axes = plt.subplots(4, 8, figsize=(18, 8), subplot_kw=dict(projection=proj))
    axes = axes.flatten()

    # Stockage des masques de significativité pour les quatre saisons
    masque = [[] for i in range(4)]

    # On traite les données saison par saison
    for i,saison in enumerate(liste_saison): 

        # ---------- Label de saison ----------
        pos=axes[i*8].get_position()
        y_center = pos.y0 + pos.height/2
        fig.text(0.02,y_center, row_titles[i],ha = 'left',va='center',rotation=90,fontsize=16,fontweight='bold')
        
        # ---------- Composites ----------
        # On traite les données avec fonction_composite
        moyenne_par_point_mois,ds,pourcentage_RdT,liste_stacked_mois= fonction_composite(label_indice, drop_feb29,parameter,liste_saison[i],domaine)
        
        # Traitement du paramètre 2 : Pmer (psl) ou zg500 (zg500)
        if pression or zg500:
            if pression :
                parameter2 = "psl"
                unit_factor2 = 100
            elif zg500:
                parameter2 = "zg500"
                unit_factor2 = 10

            # On traite les données avec fonction_composite_psl_ou_zg500
            moyenne_par_point_mois_psl_ou_zg500 = fonction_composite_psl_ou_zg500(liste_saison[i],parameter2,domaine)[1]

        # ---------- Boucle sur les régimes ----------
        for k, data in enumerate(moyenne_par_point_mois): #Pour les 7 régimes et No Regime
            ax = axes[i*8+k] #On parcourt les composites en lignes
            data_plot = data
            
            # ---------- Isolignes ----------
            cf = ax.contourf(data_plot.lon, data_plot.lat, data_plot, levels=levels_anom, cmap=cmap, norm=norm, extend="both", transform=ccrs.PlateCarree())

            # ---------- Bootstrap ----------
            if bootstrap_ok :
                masque[i].append(bootstrap(liste_stacked_mois[k], n_iterations = 50))
                ax.contourf(data_plot.lon, data_plot.lat,  masque[i][k],hatches=[None,'...'], colors='none', levels=[-1, 0.5,1.5], transform=ccrs.PlateCarree(), add_colorbar = False)
                
            # ---------- Isolignes psl ou zg500 ----------
            if pression :
                c = ax.contour(ds.lon, ds.lat, moyenne_par_point_mois_psl_ou_zg500[k]/unit_factor2,levels=levels_psl, colors="brown", linewidths=0.7, transform=ccrs.PlateCarree())  #ISOLIGNES
                ax.clabel(c, fmt="%d", fontsize=7) #COTES
                c1015 = ax.contour(ds.lon, ds.lat, moyenne_par_point_mois_psl_ou_zg500[k]/unit_factor2,levels=[1015], colors="brown",linewidths=1.5,transform=ccrs.PlateCarree())
                ax.clabel(c1015, fmt="%d", fontsize=9)
            elif zg500 :
                c = ax.contour(ds.lon, ds.lat, moyenne_par_point_mois_psl_ou_zg500[k]/unit_factor2, colors="brown", linewidths=0.7, transform=ccrs.PlateCarree())  #ISOLIGNES
                ax.clabel(c, fmt="%d", fontsize=7) #COTES
                

            # ---------- Cartographie ----------
            ax.coastlines()
            ax.add_feature(cfeature.BORDERS, linewidth=0.3)
            ax.set_extent([lonW, lonE, latS, latN], crs=ccrs.PlateCarree())
            ax.set_boundary(boundary_path, transform=ccrs.PlateCarree())

    # ---------- Titre des régimes ----------
    for j in range(8): 
        axes[j].set_title(cluster_regime_names[j],fontsize=10,fontweight='bold',pad=5)      
   
    # ---------- Colorbar horizontale centrée ----------
    cbar_ax = fig.add_axes([0.15, 0.05, 0.7, 0.03])  # [left, bottom, width, height]    
    cbar = plt.colorbar(cf, cax=cbar_ax, orientation="horizontal",location = 'bottom', shrink = 1,aspect=5,ticks=levels_anom_bis, label=f"Anomalies de {parameter} en {unit_label}")
    cbar.set_label(label = f"{parameter_name} en {unit_label}", size=10, weight='bold',loc="center")

    # ---------- Ajustement des espaces ----------
    fig.subplots_adjust(left = 0.045,hspace=0.05, wspace=0.2)

    # ---------- Titre du composite ----------
    plt.suptitle(
        f"Panel des anomalies moyennes de {parameter_name} ",
        fontsize=15, y=0.95
    )

    # Formatage du nom du fichier
    abv_domaine = abreviation_domaine(domaine)

    # Sauvegarde  du fichier
    plt.savefig(f"../archives/images_composites/All_All_{parameter}_{abv_domaine}.png",bbox_inches="tight", pad_inches = 0.3)

def distribution_moyenne_ponderee(label_indice,drop_feb29,parameter,liste_mois,domaine,mask_on,violin=False):
    """
    Affiche les violinplots de la distribution de T2m (ou autre paramètre psl) pondérée par la latitude
    Utilisée pour les violinplots (violin = True) et les terciles (violin = False)
    Avec les options : 
        - drop_feb29 : enlever les 29 février (drop_feb = True)
        - mask_on : pour ne faire que les calculs sur la France (mask_on = True)
    Exemple :
    - pour parameter, entrez "tas" pour la temperature au sol ou "pr" pour les precipitations
    - pour liste_mois : pour l'hiver, entrez liste_mois = [12,1,2]"
    - pour domaine, entrez "France" pour la France (ou un des paramètres suivants : "Europe", "Global")
    Renvoie :
        - liste_stacked_mois_ordre : liste des DataArray par régime ordonnés selon l'ordre dans #ORDRE si violin = True
        - ds : dataset filtré selon mask
        - moyenne_ano_par_regime_sur_domaine_mask_valeurs : liste de DataFrame par régime pour violinplots
    """

    # Paramètres pour le formatage de l'image
    abreviation_regime = ["AT","ZO","ScBl","ScTr","EuBl","AR","GL","no"]

    # On traite les données avec fonction_composite
    moyenne_par_point_mois,ds,pourcentage_RdT,liste_stacked_mois = fonction_composite(label_indice, drop_feb29,parameter,liste_mois,domaine,mask_on)
    moyenne_ano_par_regime_sur_domaine_mask_valeurs = [] # Liste des valeurs des moyennes des anomalies par régime sur le domaine obtenu par le mask

    #ORDRE
    #ordre_violin_regime = ["Atlantic Trough","Zonal","Scandinavian Blocking","Scandinavian Trough","European Blocking","Atlantic Ridge","Greenland Blocking","No Regime"]
    if violin : # pour les violinplots
        liste_stacked_mois_ordre = [liste_stacked_mois[1],liste_stacked_mois[3],liste_stacked_mois[5],liste_stacked_mois[0],liste_stacked_mois[2],liste_stacked_mois[4],liste_stacked_mois[6],liste_stacked_mois[7]]
    else : # pour les terciles
        liste_stacked_mois_ordre = liste_stacked_mois

    # On réalise la moyenne pondérée en fonction de lat et lon sur le domaine considéré
    for i, stacked_list in enumerate(liste_stacked_mois_ordre):
        # Concaténation pour vectoriser la moyenne pondérée
        stacked_i = xr.concat(stacked_list, dim="time")
        weights = np.cos(np.deg2rad(ds.lat))
        mean_vals = stacked_i.weighted(weights).mean(("lat","lon")).values # array 1D (time)

        # Création du DataFrame pour les violinplots
        df_regime = pd.DataFrame({"regime":[abreviation_regime[i] for k in mean_vals],"anom_tas": mean_vals})
        moyenne_ano_par_regime_sur_domaine_mask_valeurs.append(df_regime)
        print(f"Régime {cluster_regime_names[i]} : {len(mean_vals)} jours, moyenne = {mean_vals.mean():.2f}")

    return liste_stacked_mois_ordre,ds,moyenne_ano_par_regime_sur_domaine_mask_valeurs

def affichage_violin_plots_distribution(label_indice, drop_feb29, parameter, saison, domaine, mask_on):
    """
    Affiche un violinplot des anomalies du paramètre (tas ou pr) par régime sur la France.
    Avec les options : 
        - drop_feb29 : enlever les 29 février (drop_feb = True)
        - mask_on : pour ne faire que les calculs sur la France (mask_on = True)
    Exemple :
    - pour parameter, entrez "tas" pour la temperature au sol ou "pr" pour les precipitations
    - pour saison, entrez "hiver" pour hiver (ou un des paramètres suivants : "printemps", "été", "automne")
    - pour domaine, entrez "France" pour la France (ou un des paramètres suivants : "Europe", "Global")
    """   

    # ---------- Initialisation ----------
    liste_mois = mois_saison(saison)
    saison_alphabet = mois_saison_alphabet(saison)

    # ---------- Récupérer les DataFrames par régime ----------
    _, _, df_par_regime = distribution_moyenne_ponderee(label_indice, drop_feb29, parameter, liste_mois, domaine,  mask_on, violin=True)

    # ---------- Concaténer tous les régimes en un seul DataFrame ----------
    df_all = pd.concat(df_par_regime, ignore_index=True)

    # ---------- Formatage de l'image selon le paramètre considéré ----------
    if parameter == "pr":
        parameter_name = "précipitations"
    elif parameter == "tas":
        parameter_name = "température à 2m"

    # ---------- Création du violinplot ----------
    #liste_color = ["#6a0dad","#ff0000","#ff8c00","#f2c300","#8cc63f","#006400","#0000ff","#7f7f7f"] Ancienne liste de couleur utilisée par Grams
    liste_color = ["#6a0dad","#ff0000","#ff8c00","#43CEF8","#8B4513","#0000ff","#228B22","#7f7f7f"]
    plt.figure(figsize=(10,5))
    sns.violinplot(data=df_all, x="regime", y="anom_tas",palette = liste_color )
    plt.axhline(0, linewidth=1, linestyle='--', color='black')
    plt.xlabel("Régime de temps")
    plt.ylabel(f"Anomalies de {parameter_name}")
    plt.title(f"Distribution des anomalies de {parameter_name} selon le régime sur la France en {saison_alphabet}")
    plt.xticks(rotation=45)
    plt.tight_layout()
    abv_domaine = abreviation_domaine(domaine)

    # Sauvegarde de la figure
    plt.savefig(f"../archives/images_composites/Violin_{saison_alphabet}_All_{parameter}_{abv_domaine}.png",bbox_inches="tight", pad_inches = 0.3)

def terciles(label_indice,drop_feb29,parameter,liste_mois,domaine,mask_on=False):
    """
    Les paramètres attendus sont les précipitations ("pr") ou la température ("tas")
    Pour chaque régime, trie les jours relatifsen fonction de leur appartenance au tercile inférieur ou supérieur
    Avec les options : 
        - drop_feb29 : enlever les 29 février (drop_feb = True)
        - mask_on : pour ne faire que les calculs sur la France (mask_on = True)
    Exemple :
    - pour parameter, entrez "tas" pour la temperature au sol ou "pr" pour les precipitations
    - pour saison, entrez "hiver" pour hiver (ou un des paramètres suivants : "printemps", "été", "automne")
    - pour domaine, entrez "France" pour la France (ou un des paramètres suivants : "Europe", "Global")
    Renvoie :
        - date_33, date_66 : listes des dates des jours du tercile inférieur et supérieur par régime
        - ds : dataset filtré
        - moyenne_par_point_33, moyenne_par_point_66 : moyenne globale par point
        - moyenne_par_point_mois_33, moyenne_par_point_mois_66 : moyenne par point sur les mois choisis
    """


    # Récupération des anomalies pondérées sur la France UNIQUEMENT
    moyenne_ano_par_regime_sur_domaine_mask_valeurs = distribution_moyenne_ponderee(label_indice,drop_feb29,parameter,liste_mois,domaine,mask_on=True)[2]
    
    # Récupération DataArrays complets
    liste_stacked_mois,ds,moyenne_ano_par_regime_France_valeurs_quon_ne_recupere_pas = distribution_moyenne_ponderee(label_indice,drop_feb29,parameter,liste_mois,domaine,mask_on)

    # Création des listes nécessaires
    date_33, date_66 = [[] for i in range (8)], [[] for i in range (8)] # Listes des jours appartenant au tercile inférieur (resp. supérieur) 
    moyenne_par_point_33, moyenne_par_point_66 = [], [] # Liste des moyennes par point pour les tercile inférieur/supérieur sur TOUTE l'année
    moyenne_par_point_mois_33,moyenne_par_point_mois_66 = [],[] # Liste des moyennes par point pour les tercile inférieur/supérieur sur les MOIS CONSIDÉRÉS
    
    # Boucle sur les 8 régimes
    for i in range (8) :
        # Récupèration des valeurs des anomalies pour le régime i
        values = moyenne_ano_par_regime_sur_domaine_mask_valeurs[i]['anom_tas'].values

        # Calcul des percentiles
        q33 = np.quantile(values, 0.333)
        q66 = np.quantile(values, 0.667)

        # Indices des jours pour chaque tercile
        indices_33 = np.where(values <= q33)[0] # Indices des jours appartenant au tercile INFÉRIEUR
        indices_66 = np.where(values >= q66)[0] # Indices des jours appartenant au tercile SUPÉRIEUR

        # Dates correspondates
        date_33[i] = liste_stacked_mois[i].time[indices_33] # Dates des jours appartenant au tercile INFÉRIEUR
        date_66[i] = liste_stacked_mois[i].time[indices_66] # Dates des jours appartenant au tercile SUPÉRIEUR
    
        # DataArrays concaténés pour chaque tercile
        stacked_33 = xr.concat([liste_stacked_mois[i][k] for k in indices_33], dim="time")
        stacked_66 = xr.concat([liste_stacked_mois[i][k] for k in indices_66], dim="time")

        # Moyenne globale par point
        moyenne_par_point_33.append(stacked_33.mean(dim="time")) # Utile si on veut la moyenne par point pour le tercile INFÉRIEUR sur toute l'année
        moyenne_par_point_66.append(stacked_66.mean(dim="time")) # Utile si on veut la moyenne par point pour le tercile SUPÉRIEUR sur toute l'année

        # Moyenne par point sur les mois choisis
        stacked_mois_33 = stacked_33.sel(time=stacked_33['time.month'].isin(liste_mois))
        stacked_mois_66 = stacked_66.sel(time=stacked_33['time.month'].isin(liste_mois))

        # Stockage des moyennes par point sur les mois choisis
        moyenne_par_point_mois_33.append(stacked_mois_33.mean(dim="time"))
        moyenne_par_point_mois_66.append(stacked_mois_66.mean(dim="time")) 

    # Renvoie les différentes listes de stockage des données crées
    return date_33,date_66,ds,moyenne_par_point_33,moyenne_par_point_66,moyenne_par_point_mois_33,moyenne_par_point_mois_66

def affichage_terciles(label_indice,drop_feb29,parameter,saison,domaine,regime,mask_on,pression = False,zg500 = False) :
    """
    Affiche les terciles des anomalies du paramètre (tas ou pr) du régime considéré, sur la France.
    Avec les options : 
        - drop_feb29 : enlever les 29 février (drop_feb = True)
        - mask_on : pour ne faire que les calculs sur la France (mask_on = True)
        - Pression (pression = True)
        - zg500 (zg500 = True)
    Exemple :
    - pour parameter, entrez "tas" pour la temperature au sol ou "pr" pour les precipitations
    - pour saison, entrez "hiver" pour hiver (ou un des paramètres suivants : "printemps", "été", "automne")
    - pour domaine, entrez "France" pour la France (ou un des paramètres suivants : "Europe", "Global")
    - pour regime, entrez "European Blocking" pour European Blocking (ou un des paramètres suivants : "Scandinavian Blocking", "Greenland Blocking", 
            "Atlantic Ridge", "Zonal", "Scandinavian Trough",c"Atlantic Trough", "No Regime")
    """   

    # ---------- Initialisation ----------
    liste_mois = mois_saison(saison)
    levels_psl = np.arange(940,1041,5)
    levels_psl = levels_psl.tolist()
    levels_psl.remove(1015)
    nb_regime = cluster_regime_names.index(regime) # Nombre de régime
    
    # Paramètre nécessaire pour le nom du fichier
    save_regime=dict_abreviation_regime[regime]

    # Moyenne générale
    moyenne_par_point_par_mois = fonction_composite(label_indice,drop_feb29,parameter,liste_mois,domaine,mask_on)[0]
    
    # Calcul des terciles
    indice_jour_33,indice_jour_66,ds,moyenne_par_point_33,moyenne_par_point_66,moyenne_par_point_mois_33,moyenne_par_point_mois_66 = terciles(label_indice,drop_feb29,parameter,liste_mois,domaine,mask_on=False)
    
    donnees_a_plot = [moyenne_par_point_mois_33,moyenne_par_point_par_mois,moyenne_par_point_mois_66]

    # ---------- Traitement du paramètre 2 ----------
    liste_moyenne_psl_ou_zg500 = [None,None,None] # On va ranger les données dans l'ordre : tercile inférieur, moyenne, tercile supérieur
    if pression :
        parameter2 = "psl"
        liste_moyenne_psl_ou_zg500[0] = fonction_composite_psl_ou_zg500_tercile(indice_jour_33,parameter2,domaine) # Traitement du tercile inférieur
        liste_moyenne_psl_ou_zg500[2] = fonction_composite_psl_ou_zg500_tercile(indice_jour_66,parameter2,domaine) # Traitement du tercile supérieur
        liste_moyenne_psl_ou_zg500[1] = fonction_composite_psl_ou_zg500(liste_mois,parameter2,domaine)[1] # Traitement de la moyenne
    elif zg500 : 
        parameter2 = "zg500"
        liste_moyenne_psl_ou_zg500[0] = fonction_composite_psl_ou_zg500_tercile(indice_jour_33,parameter2,domaine) # Traitement du tercile inférieur
        liste_moyenne_psl_ou_zg500[2] = fonction_composite_psl_ou_zg500_tercile(indice_jour_66,parameter2,domaine) # Traitement du tercile supérieur
        liste_moyenne_psl_ou_zg500[1] = fonction_composite_psl_ou_zg500(liste_mois,parameter2,domaine)[1] # Traitement de la moyenne

    # ---------- Limites du domaine ----------
    lonW, lonE = ds.lon[0].values, ds.lon[-1].values
    latS, latN = ds.lat[0].values, ds.lat[-1].values

    boundary_path = make_boundary_path(latS, latN, lonW, lonE)

    # ---------- Projection ----------
    proj = ccrs.Orthographic(central_longitude=(lonW + lonE)/2, central_latitude=(latS + latN)/2)

    # ---------- Formatage de l'image selon le paramètre considéré ----------
    if parameter == "pr":
        levels_anom = np.arange(-6,6.2,0.25)
        levels_anom_bis = np.arange(-6,6.2,0.5)
        norm = TwoSlopeNorm(vmin=-6, vcenter=0, vmax=6)
        cmap = plt.get_cmap("BrBG")
        parameter_name = "précipitations"
        unit = "mm/jour"
    elif parameter == "tas":
        levels_anom = np.arange(-5,5.2,0.25)
        levels_anom_bis = np.arange(-5,5.2,0.5)
        norm = TwoSlopeNorm(vmin=-5, vcenter=0, vmax=5)
        cmap = plt.get_cmap("RdBu_r")
        parameter_name = "température à 2m"
        unit = "°C"

    # ---------- Figures ----------
    fig, axes = plt.subplots(1, 3, figsize=(18, 8), subplot_kw=dict(projection=proj))
    axes = axes.flatten()
    titres_plot = ["tercile bas", "Moyenne", "tercile haut"]

    # On traite les données dans l'ordre des images : tercile inférieur, moyenne, tercile supérieur
    for k in range(3):
        ax = axes[k]
        data_to_plot = donnees_a_plot[k][nb_regime]

        # ---------- Isolignes ----------
        cf = ax.contourf(ds.lon, ds.lat, data_to_plot, levels=levels_anom, cmap=cmap, norm=norm, extend="both", transform=ccrs.PlateCarree())
    
        # ---------- Traitement du paramètre 2 ----------
        if liste_moyenne_psl_ou_zg500[k] is not None :
            if parameter2 == "psl":
                c = ax.contour(ds.lon, ds.lat, liste_moyenne_psl_ou_zg500[k][nb_regime]/100,levels=levels_psl, colors="brown", linewidths=0.7, transform=ccrs.PlateCarree())  #ISOLIGNES
                ax.clabel(c, fmt="%d", fontsize=7) #COTES
                c1015 = ax.contour(ds.lon, ds.lat, liste_moyenne_psl_ou_zg500[k][nb_regime]/100,levels=[1015], colors="brown",linewidths=2.1,transform=ccrs.PlateCarree())
                ax.clabel(c1015, fmt="%d", fontsize=9)
            elif parameter2 == "zg500":
                c = ax.contour(ds.lon, ds.lat, liste_moyenne_psl_ou_zg500[k][nb_regime]/10, colors="brown", linewidths=0.7, transform=ccrs.PlateCarree())  #ISOLIGNES
            ax.clabel(c, fmt="%d", fontsize=7) #COTES

        # ---------- Cartographie ----------
        ax.coastlines()
        ax.add_feature(cfeature.BORDERS, linewidth=0.3)
        ax.set_extent([lonW, lonE, latS, latN], crs=ccrs.PlateCarree())
        ax.set_boundary(boundary_path, transform=ccrs.PlateCarree())
        ax.set_title(f"{titres_plot[k]} du régime {regime}", fontsize=11, pad = 5)
    
        
    # ---------- Colorbar horizontale centrée ----------
    cbar_ax = fig.add_axes([0.15, 0.16, 0.7, 0.03])  # [left, bottom, width, height]
    cbar = plt.colorbar(cf, cax=cbar_ax, orientation="horizontal", location = "bottom", shrink = 1, aspect = 5, ticks = levels_anom_bis)
    cbar.set_label(label = f"{parameter_name} en {unit}", size=15, weight="bold", loc="center")
   
    # ---------- Ajustement des espaces ----------
    fig.subplots_adjust(hspace=0.05, wspace=0.02)
    month_plot = mois_saison_alphabet(saison)

    # ---------- Titre du composite ----------
    plt.suptitle(
        f"{regime} en {month_plot} ({len(indice_jour_33[nb_regime])} jours)\n Anomalies moyennes de {parameter_name} ",
        fontsize=15, y=0.85
    )

    # Paramètre nécessaire pour le nom du fichier
    abv_domaine = abreviation_domaine(domaine)

    # Sauvegarde de la figure
    plt.savefig(f"../archives/images_composites/{month_plot}_{save_regime}_{parameter}_{abv_domaine}.png",bbox_inches="tight", pad_inches = 0.3)


###########################################################
# ---------------- Production des figures ----------------
###########################################################

def sauvegarde_1_regime_1_saison_terciles(label_indice,drop_feb29,Parametre,Saison,Domaine,Regime):
    """
    Sauvegarde tous les composites terciles
    """

    for R in Regime:
        for P in Parametre : 
            for D in Domaine:
                for S in Saison:
                    if D == "Europe" or D == "Global":
                        affichage_terciles(label_indice,drop_feb29,P,S,D,R,mask_on=False,pression=True,zg500 = False)
                    elif D == "France":
                        affichage_terciles(label_indice,drop_feb29,P,S,D,R,mask_on=True,pression=False,zg500 = False)

def sauvegarde_1_regime_4_saisons(label_indice,drop_feb29,Parametre,Domaine):
    """
    Sauvegarde tous les composites 1 régimes/4 saisons
    """
    for R in Regime:
        for D in Domaine:
            for P in Parametre:
                if D == "Europe" or D == "Global" :
                    affichage_composite_un_regime(label_indice,drop_feb29,P,"psl","Vivaldi",D,R,pression=True,bootstrap_ok=True)
                elif D == "France":
                    affichage_composite_un_regime(label_indice,drop_feb29,P,"psl","Vivaldi",D,R,pression=False,bootstrap_ok=True)

def sauvegarde_8_regimes_1_saison(label_indice,drop_feb29,Parametre,parameter2,Saison,Domaine):
    """
    Sauvegarde tous les composites 8 régimes/1 saison
    """
    
    for S in Saison:
        for D in Domaine:
            for P in Parametre:
                if D == "Europe" or D == "Global" :
                    affichage_composite_une_saison(label_indice,drop_feb29,P,parameter2,S,D,pression=True,bootstrap_ok=True)
                elif D == "France":
                    affichage_composite_une_saison(label_indice,drop_feb29,P,parameter2,S,D,pression=False,bootstrap_ok=True)

def sauvegarde_8_regimes_4_saisons(label_indice,drop_feb29,Parametre,Domaine):
    """
    Sauvegarde tous les composites 8 régimes/4 saisons
    """

    for D in Domaine:
        for P in Parametre:
            if D == "Europe" or D == "Global" :
                affichage_composite_vivaldi(label_indice,drop_feb29,P,D,pression=True,zg500=False,bootstrap_ok=False)
            elif D == "France":
                affichage_composite_vivaldi(label_indice,drop_feb29,P,D,pression=False,zg500=False,bootstrap_ok=False)

def sauvegarde_violin_plots(label_indice,drop_feb29,Parametre,Saison):
    """
    Sauvegarde de tous les violinplots
    """

    for P in Parametre:
        for S in Saison:
            affichage_violin_plots_distribution(label_indice,drop_feb29,P,S,"France",mask_on=True)


###########################################################
# -- Pour essayer les fonctions de manière individuelle --
###########################################################

#affichage_composite_un_regime(label_indice,drop_feb29,"tas","psl","Vivaldi","Europe","Scandinavian Trough",pression=True,bootstrap_ok=True)
#affichage_composite_une_saison(label_indice,drop_feb29,"tas","psl","hiver","Global",pression=True,bootstrap_ok=True)
#affichage_composite_vivaldi(label_indice,drop_feb29,"tas","Global",pression=True,zg500=False,bootstrap_ok=True)
#affichage_terciles(label_indice,drop_feb29,"pr","hiver","Global","Scandinavian Blocking",mask_on=False,pression=True,zg500 = False)
#affichage_violin_plots_distribution(label_indice,drop_feb29,"tas","hiver","France",mask_on=True)


###########################################################
# -- Application des fonctions de production des figures --
###########################################################

sauvegarde_1_regime_1_saison_terciles(label_indice,drop_feb29,Parametre,Saison,Domaine,Regime)
sauvegarde_1_regime_4_saisons(label_indice,drop_feb29,Parametre,Domaine)
sauvegarde_8_regimes_1_saison(label_indice,drop_feb29,Parametre,"psl",Saison,Domaine)
sauvegarde_8_regimes_4_saisons(label_indice,drop_feb29,Parametre,Domaine)
sauvegarde_violin_plots(label_indice,drop_feb29,Parametre,Saison)
