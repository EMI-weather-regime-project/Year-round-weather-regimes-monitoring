import numpy as np
import xarray as xr
import pandas as pd
from scipy import stats


import matplotlib.pyplot as plt
import matplotlib.path as mpath
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import json
from matplotlib.colors import TwoSlopeNorm

from sklearn.decomposition import PCA
from sklearn.cluster import KMeans

from pathlib import Path
"""
Ce script est à la base du projet, il permet de déterminer les 7 clusters des régimes sur une climatologie. On en détermine un certain nombre de constantes utiles 
au calcul en temps réel aussi qui sont exportés. Les données qui sont renvoyées sont : 
- les centroïdes des clusters en anomalies normalisées
- les noms des différents régimes pour les plots (ordre à définir)
- les couleurs qui correspondent aux régimes
- une liste de numéros coresspondant aux régime qui a été attribué à chaque jours sur la clim
- un fichier .nc avec les valeur des indices pour les 7 régimes sur la clim
- un fichier .nc avec les régimes actifs (True quand le régime est actif ce jour ci)
- un fichier .nc qui donne pour chaque jours le régime gagnant
- 5 fichiers de données utiles pour le calcul en temps réel sous forme .npy
- une moyenne glissante qui permet de normaliser selon la saison (pour le temps réel aussi)
- une clim à soustraire (encore pour le temps réel)
"""

########### Définition de fonctions utiles ###########

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

def smooth_doy_climatology(da, window=60):
    """
    Calcule la climatologie DOY lissée sur `window` jours (rolling centré).
    Méthode : groupby.dayofyear -> concat x3 -> rolling -> slice central.
    Retourne un DataArray indexed by dayofyear (1..n_doy).
    """
    clim_raw = da.groupby("time.dayofyear").mean("time", skipna=True)
    n_doy = clim_raw.sizes["dayofyear"]
    clim_cycle = xr.concat([clim_raw, clim_raw, clim_raw], dim="dayofyear")
    clim_cycle_smooth = clim_cycle.rolling(dayofyear=window, center=True, min_periods=1).mean()
    clim60 = clim_cycle_smooth.isel(dayofyear=slice(n_doy, 2*n_doy))
    # s'assurer que dayofyear est 1..n_doy
    clim60 = clim60.assign_coords(dayofyear=np.arange(1, n_doy+1))
    return clim60

def linregress_xarray(da):
    """
    Régression linéaire (pente, intercept, pval) pixel-wise le long de la dimension 'time'.
    - da : DataArray avec dim 'time','lat','lon' (ou plus dims spatiales).
    Retour :
      slope (per day), intercept, p_value, t_centered (numpy array days centered)
    Implémentation :
      t is days from first obs, centered -> mean(t_centered) == 0
      slope = sum((y-mean_y) * t_centered) / Sxx  (vectorisé via xarray)
      se & p-val calculés de façon classique (assume erreurs approx normales)
    Compatible dask/xarray (opérations lazy).
    """
    # convert time to numeric (days)
    t_days = (da.time - da.time[0]).dt.days.astype("float64").values  # shape (T,)
    t_centered = t_days - t_days.mean()                              # mean 0
    Sxx = np.sum(t_centered**2)

    # statistiques de base
    mean_y = da.mean(dim="time", skipna=True)
    # nombre d'observations valides par pixel
    n_obs = da.count(dim="time")

    # numerator = sum( (y - mean_y) * t_centered )
    # broadcasting: (time, lat, lon) * (time, 1, 1)
    num = ( (da - mean_y) * xr.DataArray(t_centered, coords={ "time": da.time }, dims=["time"]) ).sum(dim="time", skipna=True)

    slope = num / Sxx
    # intercept : since t_centered mean == 0, intercept = mean_y - slope*mean(t_centered) = mean_y
    intercept = mean_y

    # fitted values & residuals
    # y_fit = intercept + slope * t_centered[t]
    # Do it lazily via broadcasting
    y_fit = intercept + slope * xr.DataArray(t_centered, coords={ "time": da.time }, dims=["time"])
    residuals = da - y_fit

    rss = (residuals**2).sum(dim="time", skipna=True)  # residual sum of squares
    dof = n_obs - 2
    valid = dof > 0

    # standard error of slope
    # se_slope = sqrt( (rss / dof) / Sxx )
    se_slope = xr.full_like(slope, np.nan)
    se_slope = se_slope.where(~valid, ( (rss / dof) / Sxx )**0.5 )

    t_stat = slope / se_slope
    # two-sided p-value from Student's t
    # Note: scipy functions can't be applied lazily on xarray/dask arrays -> convert to numpy when needed
    def _pval_from_t(tarr, dof_arr):
        # works on numpy arrays
        with np.errstate(invalid="ignore"):
            p = 2 * stats.t.sf(np.abs(tarr), df=dof_arr)
        return p

    # if dask arrays present, compute pvals via xarray.apply_ufunc (vectorize)
    pval = xr.apply_ufunc(
        _pval_from_t, t_stat, dof,
        input_core_dims=[[], []],
        output_core_dims=[[]],
        vectorize=True,
        dask="parallelized",
        output_dtypes=[float],
    )

    # mask invalid
    slope = slope.where(valid)
    intercept = intercept.where(valid)
    pval = pval.where(valid)

    return slope, intercept, pval, t_centered

def rolling_filter(anoms):
    anoms = anoms.pad(time=(0, 5), mode='edge')
    anoms = anoms.rolling(time=11, center=True).mean()
    anoms = anoms.isel(time=slice(5, -5))
    return anoms

def lanczos_weights(window, cutoff):
    """
    window : taille du filtre (impair recommandé, ex: 21, 31, 61)
    cutoff : fréquence de coupure (en cycles/jour)
    ex: 1/10 pour 10 jours
    """
    n = (window - 1) // 2
    k = np.arange(-n, n+1)
    h = np.zeros_like(k, dtype=float)

    for i, ki in enumerate(k):
        if ki == 0:
            h[i] = 2 * cutoff
        else:
            h[i] = np.sin(2 * np.pi * cutoff * ki) / (np.pi * ki)


    # fenêtre de Lanczos (sigma factor)
    sigma = np.sinc(k / n)

    w = h * sigma
    w = w / w.sum()  # normalisation

    return w

def lanczos_filter(da, window=31, cutoff=1/10):
    w_da = xr.DataArray(
    weights,
    dims=["window"],
    coords={"window": np.arange(len(weights))}
    )

    # rolling + dot product
    da_rolled = da.rolling(time=window, center=True)

    filtered = da_rolled.construct("window").dot(w_da)

    return filtered

########### Définition de la date de clim ###########
tstart = "1960-01-01"
tend   = "2025-12-31"

########### Définition de constantes et de paramètres ###########
FILTER = 'rolling'
drop_feb29 = False       # True: retire 29/02 pour avoir DOY strict 1..365 (sinon on garde 29/02)

domain = dict(lat=slice(90, 30), lon=slice(-80, 40)) # latitudes décroissantes dans dimension lat

g = 9.81  # gravité

data_path = "../data/climatologie/zg500_era5_day_raw_1940-2025.nc" #chemin vers les données de Z500


########### Ouvrir les données ###########
ds = open_dataset(data_path)


# 2) extraire z500 en m (z in dataset is geopotential in m2/s2 -> geopotential/g gives geopotential height in m)
z = ds["zg500"]
z = z.sel(time=slice(tstart, tend))
z = z.sel(**domain).squeeze()


# option : retirer 29/02 si on veut DOY strict
if drop_feb29:
    z = remove_feb29(z)

########### Pipline (cf donc pour comprendre) ###########

# 3) climatologie DOY lissée (60 jours)
clim60 = smooth_doy_climatology(z, window=60)

# 4) anomalies quotidiennes (groupe par dayofyear puis soustraction de la climatologie lissée)
#    on utilise groupby subtraction qui est broadcast-safe avec xarray
anoms = z.groupby("time.dayofyear") - clim60

if FILTER == 'lanczos':
    anoms = lanczos_filter(anoms, window=31, cutoff=1/10)
    anoms = anoms.dropna("time")

if FILTER == 'rolling':
    anoms = rolling_filter(anoms)

# 5) pondération par latitude (2D)
weights_1d = np.cos(np.deg2rad(z.lat.values))
weights_2d_pixel = xr.DataArray(np.outer(weights_1d, np.ones(len(z.lon))),
                                coords={"lat": z.lat, "lon": z.lon}, dims=["lat", "lon"])

# 6) régression pixel-wise sur anomalies -> slope (per day), intercept, pval
z_day, intercept, pval = (None, None, None)
z_day, intercept, pval, t_centered = linregress_xarray(anoms)

# 7) conversion pente -> per decade (pratique pour rapports)
z_decade = z_day * 365.2422 * 10

# 8) moyenne de domaine pondérée (série temporelle) + régression 1D
weights_2d_time = weights_2d_pixel.broadcast_like(anoms)
area_mean_ts = (anoms * weights_2d_time).sum(("lat", "lon")) / weights_2d_time.sum(("lat", "lon"))

# pour la pente régionale on peut utiliser scipy.stats.linregress (1D numpy)
t_days = (anoms.time - anoms.time[0]).dt.days.astype("float64").values
res_area = stats.linregress(t_days - t_days.mean(), area_mean_ts.values)  # slope per day
slope_area_decade = res_area.slope * 365.2422 * 10
fit_ts = res_area.intercept + res_area.slope * (t_days - t_days.mean())
fit_xr = xr.DataArray(fit_ts, coords={"time": anoms.time}, dims=["time"])

# 9) anomalies résiduelles (on retire la tendance régionale)
anoms_resid = anoms - fit_xr

# 10) std DOY (pour normalisation Grams+2017)
std_daily_map = anoms_resid.groupby("time.dayofyear").std("time", skipna=True)

# moyenne pondérée (un scalaire par dayofyear)
std_daily_scalar = (std_daily_map * weights_2d_pixel).sum(("lat", "lon")) / weights_2d_pixel.sum(("lat", "lon"))

# lissage 60j sur le DOY et projection sur les dates
std_daily_smooth = std_daily_scalar.rolling(dayofyear=60, center=True, min_periods=1).mean()
n_doy = std_daily_scalar.sizes["dayofyear"]
std_daily_smooth = std_daily_smooth.assign_coords(dayofyear=np.arange(1, n_doy+1))
std_full = std_daily_smooth.sel(dayofyear=anoms_resid["time.dayofyear"])
# 11) normalisation finale (Grams+2017)
anoms_norm_all = anoms_resid / std_full  # lazy if dask chunks present
anoms_norm = anoms_norm_all.sel(time = slice(tstart, tend))
# --- Résultats utiles pour diagnostics / plotting ---
z_decade = z_decade  # pente par decade (DataArray lat x lon)
pval_map = pval
area_mean_ts = area_mean_ts
rolling365 = area_mean_ts.rolling(time=365, center=True).mean()
daily_std_area = std_daily_scalar
rolling60 = std_daily_smooth
doy = daily_std_area["dayofyear"].values

print("Pipeline construit. Variables clés : z_decade, pval_map, anoms_norm, area_mean_ts.")

########### Pipline fin, calcul d'anomalies pondérées ###########

weights = np.sqrt(weights_2d_pixel.broadcast_like(anoms_norm))
anoms_w = anoms_norm * weights

########### ACP et kmeans ###########
n_modes = 12

# --- Reshape comme le fait Eof ---
nt, ny, nx = anoms_w.shape
X = anoms_w.values.reshape(nt, ny*nx).astype('float32')

# --- PCA ---
pca = PCA(n_components=n_modes, svd_solver='randomized')

pcs = pca.fit_transform(X)                 # équivalent solver.pcs()
eofs = pca.components_.reshape(n_modes, ny, nx)   # équivalent solver.eofs()
variance_frac = pca.explained_variance_ratio_     # équivalent varianceFraction

variance_cum12 = float(variance_frac.sum() * 100)
print(f"Variance cumulée (12 premiers modes) : {variance_cum12:.2f} %")

n_modes = 12       # nombre d’EOFs utilisés
n_clusters = 7     # nombre de clusters
pcs12 = pcs[:, :n_modes]       # PC1..PC12, non standardisés

km = KMeans(n_clusters=n_clusters, n_init=500, random_state=None).fit(pcs12)
best_km = km
best_inertia = km.inertia_
labels_kmeans = km.labels_
centroids = km.cluster_centers_

print("Best inertia:", best_inertia)
print("Clusters trouvés :", np.unique(labels_kmeans))
print("Shape des centroids :", centroids.shape)

########### Sauvegarder dans des listes les clusters centroïdes ###########

cluster_mean_z500 = []
cluster_mean_z500_anom = []
cluster_mean_z500_anom_norm = []

for k in range(n_clusters):
    idx = np.where(labels_kmeans == k)[0]

    if len(idx) == 0:
        cluster_mean_z500.append(None)
        cluster_mean_z500_anom.append(None)
        cluster_mean_z500_anom_norm.append(None)
        continue

    mean_z = z.isel(time=idx).mean("time")
    mean_zanom = anoms.isel(time=idx).mean("time")
    mean_zanom_norm = anoms_norm.isel(time=idx).mean("time")

    cluster_mean_z500.append(mean_z)
    cluster_mean_z500_anom.append(mean_zanom)
    cluster_mean_z500_anom_norm.append(mean_zanom_norm)

min_anom = float(np.min(cluster_mean_z500_anom))
max_anom = float(np.max(cluster_mean_z500_anom))

min_anom_norm = float(np.min(cluster_mean_z500_anom_norm))
max_anom_norm = float(np.max(cluster_mean_z500_anom_norm))
print(f"Min anomaly = {min_anom:.3f} m")
print(f"Max anomaly = {max_anom:.3f} m")
print(f"Min anomaly = {min_anom_norm:.3f} m")
print(f"Max anomaly = {max_anom_norm:.3f} m")

########### Tracer les clusters pour les nommer par la suite (permet d'avoir l'ordre pour toutes les données) ###########

# ---------- Limites du domaine ----------
lonW, lonE = z.lon[0].values, z.lon[-1].values
latS, latN = z.lat[0].values, z.lat[-1].values

# ---------- Fonction pour créer un chemin fermé ----------
def make_boundary_path(latS, latN, lonW, lonE, n=100):
    verts = []
    verts += list(zip(np.linspace(lonW, lonE, n), np.full(n, latN)))  # haut
    verts += list(zip(np.full(n, lonE), np.linspace(latN, latS, n)))  # droite
    verts += list(zip(np.linspace(lonE, lonW, n), np.full(n, latS)))  # bas
    verts += list(zip(np.full(n, lonW), np.linspace(latS, latN, n)))  # gauche
    verts.append(verts[0])
    codes = [mpath.Path.LINETO] * len(verts)
    codes[0] = mpath.Path.MOVETO
    return mpath.Path(verts, codes)

boundary_path = make_boundary_path(latS, latN, lonW, lonE)

# ---------- Projection ----------
proj = ccrs.Orthographic(central_longitude=(lonW + lonE)/2, central_latitude=(latS + latN)/2)


cmap = plt.get_cmap("RdBu_r")
levels_anom = np.arange(-150, 160, 10)
norm = TwoSlopeNorm(vmin=-150, vcenter=0, vmax=150)
levels_z500 = np.arange(4800, 6050, 50)

fig, axes = plt.subplots(2, 4, figsize=(18, 8), subplot_kw=dict(projection=proj))
axes = axes.flatten()

for k in range(n_clusters):
    ax = axes[k]

    cf = ax.contourf(anoms.lon, anoms.lat, cluster_mean_z500_anom[k], levels=levels_anom, cmap=cmap, norm=norm, extend="both", transform=ccrs.PlateCarree())

    c = ax.contour(z.lon, z.lat, cluster_mean_z500[k], levels=levels_z500, colors="k", linewidths=0.7, transform=ccrs.PlateCarree())
    ax.clabel(c, fmt="%d", fontsize=7)

    ax.coastlines()
    ax.add_feature(cfeature.BORDERS, linewidth=0.3)
    ax.set_extent([lonW, lonE, latS, latN], crs=ccrs.PlateCarree())
    ax.set_boundary(boundary_path, transform=ccrs.PlateCarree())

    pct = 100 * np.sum(labels_kmeans == k) / len(labels_kmeans)
    ax.set_title(f"Cluster {k+1} ({pct:.1f}%)", fontsize=11)

# ---- Colorbar dans le panneau vide ----
cbar_ax = axes[-1]
cbar_ax.axis("off")
fig.colorbar(cf, ax=cbar_ax, orientation="horizontal", fraction=0.8, pad=0.05, label="Z500 anomaly (m)")

# ---- Resserrement maximal ----
fig.subplots_adjust(hspace=0.05, wspace=0.02)

plt.suptitle(
    "K-means clustering in EOF space (7 regimes)\nZ500 anomalies + mean fields",
    fontsize=15, y=0.94
)
plt.savefig("donnees_sauvegardees/clusters.png")

########### Quizz pour trouver les clusters (la figures est sauvagardee dans donnés_sauvegardees) ###########

regime_names_list = [
    "Atlantic Trough",
    "Scandinavian Blocking",
    "Atlantic Ridge",
    "Zonal",
    "European Blocking",
    "Scandinavian Trough",
    "Greenland Blocking"
]

print("\nVeuillez associer un numéro de régime à chaque cluster (0 à 6).")
print("Choisissez parmi les régimes suivants :\n")
for i, name in enumerate(regime_names_list, 0):
    print(f" {i}. {name}")

print("\nIndiquez pour chaque cluster quel numéro de régime correspond.\n")

cluster_regime_names = {}

for k in range(0, 7):  # Clusters 0..6
    while True:
        try:
            c = int(input(f"Régime pour le cluster {k+1} : "))
            if 0 <= c <= 6:
                cluster_regime_names[k] = regime_names_list[c]
                break
            else:
                print("Entrée invalide. Choisissez un nombre entre 0 et 6.")
        except ValueError:
            print("Veuillez entrer un nombre.")

print("\nAttribution finale :")
for k in range(0, 7):
    print(f"Cluster {k} → {cluster_regime_names[k]}")

########### Tracer les clusters avec les noms ###########

cmap = plt.get_cmap("RdBu_r")
levels_anom = np.arange(-150, 160, 10)
norm = TwoSlopeNorm(vmin=-150, vcenter=0, vmax=150)
levels_z500 = np.arange(4800, 6050, 50)

fig, axes = plt.subplots(2, 4, figsize=(18, 8), subplot_kw=dict(projection=proj))
axes = axes.flatten()

# --- 7 clusters ---
for k in range(n_clusters):
    ax = axes[k]

    cf = ax.contourf(anoms.lon, anoms.lat, cluster_mean_z500_anom[k], levels=levels_anom, cmap=cmap, norm=norm, extend="both", transform=ccrs.PlateCarree())
    c = ax.contour(z.lon, z.lat, cluster_mean_z500[k], levels=levels_z500, colors="k", linewidths=0.7, transform=ccrs.PlateCarree())
    ax.clabel(c, fmt="%d", fontsize=7)

    ax.coastlines()
    ax.add_feature(cfeature.BORDERS, linewidth=0.3)
    ax.set_extent([lonW, lonE, latS, latN], crs=ccrs.PlateCarree())
    ax.set_boundary(boundary_path, transform=ccrs.PlateCarree())

    pct = 100 * np.sum(labels_kmeans == k) / len(labels_kmeans)
    regime_name = cluster_regime_names[k]
    ax.set_title(f"{regime_name} ({pct:.1f}%)", fontsize=11)

# --- Colorbar dans l'emplacement vide ---
cbar_ax = axes[-1]
cbar_ax.axis("off")
cbar = fig.colorbar(cf, ax=cbar_ax, orientation="horizontal", fraction=0.8, pad=0.05, label="Z500 anomaly (m)")

# resserrage maximal
fig.subplots_adjust(hspace=0.05, wspace=0.02)
plt.suptitle(
    "K-means clustering in EOF space (7 regimes)\nZ500 anomalies + mean fields",
    fontsize=15, y=0.95
)

#plt.show()

########### Ajout du no régime ###########

pcs12_np = pcs12   # convert DataArray -> ndarray

# distance au climat
d_clim = np.linalg.norm(pcs12, axis=1)          # (time,)

# distance au centroïde le plus proche
dist_to_centroids = np.linalg.norm(
    pcs12_np[:, None, :] - centroids[None, :, :],
    axis=2
)                                                   # shape (time, n_clusters)

d_min = dist_to_centroids.min(axis=1)

# condition no-regime
mask_noregime = d_clim < d_min

# labels finaux
labels = labels_kmeans.copy()
labels[mask_noregime] = 7

print("Labels finaux :", np.unique(labels))

cluster_regime_names[7] = "No Regime"
print(cluster_regime_names)

cluster_mean_z500_no_regime = []
cluster_mean_z500_anom_no_regime = []
cluster_mean_z500_anom_norm_no_regime = []

for k in range(n_clusters + 1):    # inclut no-regime
    idx = np.where(labels == k)[0]

    if len(idx) == 0:
        cluster_mean_z500_no_regime.append(None)
        cluster_mean_z500_anom_no_regime.append(None)
        cluster_mean_z500_anom_norm_no_regime.append(None)
        continue

    mean_z = z.isel(time=idx).mean("time")
    mean_zanom = anoms.isel(time=idx).mean("time")
    mean_zanom_norm = anoms_norm.isel(time=idx).mean("time")

    cluster_mean_z500_no_regime.append(mean_z)
    cluster_mean_z500_anom_no_regime.append(mean_zanom)
    cluster_mean_z500_anom_norm_no_regime.append(mean_zanom_norm)

# ---------------------------------------
# 7. Min / max anomalies composites
# ---------------------------------------
valid_anoms = [c.values for c in cluster_mean_z500_anom_no_regime if c is not None]

min_anom = float(np.min(valid_anoms))
max_anom = float(np.max(valid_anoms))

print(f"Min anomaly = {min_anom:.3f} m")
print(f"Max anomaly = {max_anom:.3f} m")
print(len(cluster_mean_z500_anom_no_regime))

fig, axes = plt.subplots(2, 4, figsize=(18, 8), subplot_kw=dict(projection=proj))
axes = axes.flatten()

for k in range(n_clusters+1):
    ax = axes[k]

    cf = ax.contourf(anoms.lon, anoms.lat, cluster_mean_z500_anom_no_regime[k], levels=levels_anom, cmap=cmap, norm=norm, extend="both", transform=ccrs.PlateCarree())
    c = ax.contour(z.lon, z.lat, cluster_mean_z500_no_regime[k], levels=levels_z500, colors="k", linewidths=0.7, transform=ccrs.PlateCarree())
    ax.clabel(c, fmt="%d", fontsize=7)

    ax.coastlines()
    ax.add_feature(cfeature.BORDERS, linewidth=0.3)
    ax.set_extent([lonW, lonE, latS, latN], crs=ccrs.PlateCarree())
    ax.set_boundary(boundary_path, transform=ccrs.PlateCarree())

    pct = 100 * np.sum(labels == k) / len(labels)
    regime_name = cluster_regime_names[k]
    ax.set_title(f"{regime_name} ({pct:.1f}%)", fontsize=11)
    
# ---------- Colorbar horizontale centrée ----------
cbar_ax = fig.add_axes([0.15, 0.05, 0.7, 0.03])  # [left, bottom, width, height]
plt.colorbar(cf, cax=cbar_ax, orientation="horizontal", label="Z500 anomaly (m)")

# ---------- Ajustement des espaces ----------
fig.subplots_adjust(hspace=0.05, wspace=0.02)

plt.suptitle(
    "K-means clustering in EOF space (7 regimes + no-regime)\nZ500 anomalies + mean fields",
    fontsize=15, y=0.94
)

#plt.show()

########### définition des couleurs et diminutif pour les régimes ###########

REGIME_META = {
    "Atlantic Trough": {
        "abbr": "AT",
        "color": "#228B22" 
    },
    "Zonal": {
        "abbr": "ZO",
        "color": "#ff0000"  
    },
    "Scandinavian Trough": {
        "abbr": "ScTr",
        "color": "#43CEF8"  
    },
    "Atlantic Ridge": {
        "abbr": "AR",
        "color": "#F4A460"  
    },
    "European Blocking": {
        "abbr": "EuBL",
        "color": "#8B4513"  
    },
    "Scandinavian Blocking": {
        "abbr": "ScBL",
        "color": "#6a0dad"  
    },
    "Greenland Blocking": {
        "abbr": "GL",
        "color": "#0000ff"   
    },
    "No Regime": {
        "abbr": "NR",
        "color": "#7f7f7f" 
    }
}

cluster_colors = {
    k: REGIME_META[name]["color"]
    for k, name in cluster_regime_names.items()
}

########### Fonction de calcul des indices ###########

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
        print("Conversion en float32 pour économiser la mémoire...")
        anomalies = anomalies.astype(np.float32)
    
    # 2. Préparation des poids (inchangé)
    weights = np.cos(np.deg2rad(anomalies[lat_dim])).astype(np.float32)
    weights_2d = weights.broadcast_like(anomalies.isel(time=0, drop=True))
    
    # Dénominateur (constante spatiale)
    denom = weights_2d.sum(dim=[lat_dim, lon_dim])
    
    # Liste pour stocker les résultats finaux de chaque régime
    all_regimes_projections = []
    
    total_days = anomalies.sizes['time']
    
    print(f"Démarrage du calcul par lots (taille du lot : {chunk_size} jours)")

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
        print(f" - Régime {cluster_regime_names[i]} terminé.")

    # 3. Assemblage final (Regime, Time)
    final_P_wr = xr.concat(all_regimes_projections, dim='regime')
    
    return final_P_wr

def calculate_regime_index(P_wr):
    """
    Calcule l'Indice de Régime Standardisé I_wr(t) selon l'Équation 2 de l'article.
    
    Args:
        P_wr (xr.DataArray): La projection brute calculée précédemment (Time, Regime).
        
    Returns:
        xr.DataArray: L'indice de régime I_wr (Time, Regime).
    """
    mean_P = P_wr.mean(dim='time')#calcul de la moyenne de la projection sur la periode
    std_P = P_wr.std(dim='time') #calcul de l'écart type de la projction sur la periode # Note: xarray utilise ddof=0 par défaut (population), ajustez si nécessaire
    
    # Calcul de l'indice
    I_wr = (P_wr - mean_P) / std_P
    
    return I_wr

########### Calcul à partir des fonctions ###########

Pwr = calculate_projection_chunked(anoms_norm_all, cluster_mean_z500_anom_norm, cluster_regime_names, lat_dim='lat', lon_dim='lon')
indices = calculate_regime_index(Pwr)

########### Fonction pour déterminer les régimes actifs et dominants ###########

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

########### Fonction pour récuperer les régimes actifs et majoritaire  ###########
active_regimes, max_regime = calculate_regime_states_takeover(indices, threshold=0.9, min_duration=5, max_gap=1, min_max_duration=3)

########### Pour label indice qui sert aux composites ###########

# 1. On cherche la position (0 à 6) du régime qui est 'True'
indices_bruts = max_regime.argmax(dim='regime')

# 2. On regarde quels jours n'ont aucun régime actif (No Regime)
jours_sans_regime = ~max_regime.any(dim='regime')

# 3. On fusionne : si c'est un jour sans régime on met 7, sinon on garde l'index trouvé
label_indice_xr = xr.where(jours_sans_regime, 7, indices_bruts)

# 4. On extrait ça sous forme de liste Python classique (exactement comme votre ancien code)
label_indice = label_indice_xr.values.tolist()

########### récupération pour le temps réel ###########

mean_P = Pwr.mean(dim='time')#calcul de la moyenne de la projection sur la periode
std_P = Pwr.std(dim='time') #calcul de l'écart type de la projction sur la periode # Note: xarray utilise ddof=0 par défaut (population), ajustez si nécessaire

########### Si vous voulez voir certaines variable, décommenter ###########


# print('shape : ', np.shape(cluster_mean_z500), 'type : ', type(cluster_mean_z500), 'data : ', cluster_mean_z500) #liste de DataArray
# print('shape : ', np.shape(cluster_mean_z500_anom), 'type : ', type(cluster_mean_z500_anom), 'data : ', cluster_mean_z500_anom) #liste de DataArray
# print('shape : ', np.shape(cluster_mean_z500_anom_norm), 'type : ', type(cluster_mean_z500_anom_norm), 'data : ', cluster_mean_z500_anom_norm) #liste de DataArray

# print('shape : ', np.shape(cluster_mean_z500_no_regime), 'type : ', type(cluster_mean_z500_no_regime), 'data : ', cluster_mean_z500_no_regime) #liste de DataArray
# print('shape : ', np.shape(cluster_mean_z500_anom_no_regime), 'type : ', type(cluster_mean_z500_anom_no_regime), 'data : ', cluster_mean_z500_anom_no_regime) #liste de DataArray
# print('shape : ', np.shape(cluster_mean_z500_anom_norm_no_regime), 'type : ', type(cluster_mean_z500_anom_norm_no_regime), 'data : ', cluster_mean_z500_anom_norm_no_regime) #liste de DataArray

# print('taille: ', len(cluster_regime_names), 'type : ', type(cluster_regime_names), 'data : ', cluster_regime_names) #dico avec clé = chiffre et valeur = régime
# print('taille: ', len(cluster_colors), 'type : ', type(cluster_colors), 'data : ', cluster_colors) #dico avec clé = chiffre et valeur = couleur

# print('taille : ', len(labels_kmeans), 'type : ', type(labels_kmeans), 'data : ', labels_kmeans) #ndarray, liste des jours classés dans les clusters par kmeans
# print('taille : ', len(label_indice), 'type : ', type(label_indice), 'data : ', label_indice) #ndarray, liste des jours classés dans les clusters par kmeans
# print('taille : ', np.shape(life_cycle_series), 'type : ', type(life_cycle_series), 'data : ', life_cycle_series) #pd.series (date et régime en cours)


# print('shape : ', np.shape(slope_area_decade), 'type : ', type(slope_area_decade), 'data : ', slope_area_decade) #scalaire de la pente de tendence climatique m/10 ans
# print('shape : ', np.shape(std_daily_smooth), 'type : ', type(std_daily_smooth), 'data : ', std_daily_smooth) #les 366 scalaires par lesquels diviser pour normaliser selon la saison

#print('shape : ', np.shape(indices), 'type : ', type(indices), 'data : ', indices) #liste de DataArray avec les indices des 7 régimes

# print('taille : ', np.shape(z), 'type : ', type(z), 'data : ', z) #DataArray  avec toutes les z de chaques jours sur tout les points de grille
# print('taille : ', np.shape(anoms), 'type : ', type(anoms), 'data : ', anoms) #DataArray  avec toutes les anomalies de chaques jours sur tout les points de grille
# print('taille : ', np.shape(anoms_norm), 'type : ', type(anoms_norm), 'data : ', anoms_norm) #DataArray  avec toutes les anomalies normalisées de chaques jours sur tout les points de grille

########### Pour tout sauvegarder ###########

save_path = Path('donnees_sauvegardees') #chemin de sauvegarde

cluster_mean_z500_anom_norm = xr.concat(cluster_mean_z500_anom_norm, dim="regime")

cluster_mean_z500_anom_norm.to_netcdf(save_path/'cluster_mean_z500_anom_norm.nc')

with open(save_path/"cluster_regime_names.json", "w", encoding="utf-8") as f:
    json.dump(cluster_regime_names, f, indent=4, ensure_ascii=False)

with open(save_path/"cluster_colors.json", "w", encoding="utf-8") as f:
    json.dump(cluster_colors, f, indent=4, ensure_ascii=False)

label_indice = pd.DataFrame(label_indice)
label_indice.to_csv(save_path/"label_indice.csv", index = False)

indices.to_netcdf(save_path/'indices.nc')
active_regimes.to_netcdf(save_path/'active_regimes.nc')
max_regime.to_netcdf(save_path/'max_regime.nc')


np.save(save_path/'res_area_slope.npy', res_area.slope)
np.save(save_path/'res_area_intercept.npy', res_area.intercept)
np.save(save_path/'t_days_mean.npy', t_days.mean())
np.save(save_path/'mean_P.npy', mean_P)
np.save(save_path/'std_P.npy', std_P)

std_daily_smooth.to_netcdf(save_path/'std_daily_smooth.nc')
clim60.to_netcdf(save_path/'clim60.nc')