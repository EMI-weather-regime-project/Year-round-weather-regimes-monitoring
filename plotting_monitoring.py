import xarray as xr
import numpy as np
import json
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.colors import ListedColormap
import pandas as pd
import matplotlib.dates as mdates
import os
import calendar

save_path = Path("donnees_sauvegardees")

indices = xr.open_dataarray(save_path / 'indices.nc')
max_regime =  xr.open_dataarray(save_path / 'max_regime.nc')
active_regimes =  xr.open_dataarray(save_path / 'active_regimes.nc')

with open(save_path / "cluster_regime_names.json", "r", encoding="utf-8") as f:
    cluster_regime_names = json.load(f)

with open(save_path / "cluster_colors.json", "r", encoding="utf-8") as f:
    cluster_colors = json.load(f)

regime_meta = {k: {'nom': cluster_regime_names[k], 'couleur': cluster_colors[k]} for k in cluster_regime_names.keys()}

label_indice = list(pd.read_csv(save_path / 'label_indice.csv', index_col=0).squeeze("columns").index)

regime_names = list(cluster_regime_names.values())
print("Toutes les variables ont été restaurées avec succès !")

cluster_ids = sorted(cluster_regime_names.keys())   # [1..8]

regime_labels = [cluster_regime_names[r] for r in cluster_ids]

def plot_ultimate_regimes_masked_save(indices, active_regimes, max_regime, start_date, end_date, dictionnaire_regimes, save_path=None):
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
        
        # A. Ligne de fond (>0 mais fine)
        ax1.plot(data.time, data.values, label=regime_name, color=color, linewidth=1, alpha=0.3)
        
        # B. Ligne active (épaisse)
        data_active = data.where(mask_act)
        ax1.plot(data_active.time, data_active.values, color=color, linewidth=3.5, alpha=0.9)
        
        # C. Points pour le vainqueur
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
    # GRAPHIQUE 2 : Le Chronogramme à Bulles (NOUVEAU)
    # ==========================================
    scale_factor = 150
    dates = sub_idx.time.values
    
    for y_pos, regime_name in enumerate(regimes_valides):
        if regime_name in sub_idx.regime.values:
            # Extraction des données et masques en numpy array
            data_bubble = sub_idx.sel(regime=regime_name).values
            mask_act = sub_act.sel(regime=regime_name).values
            mask_max = sub_max.sel(regime=regime_name).values
            color = color_mapping.get(regime_name, 'black')
            
            # La taille de base (proportionnelle au carré de l'indice)
            base_sizes = (data_bubble ** 2) * scale_factor
            
            # --- Condition 1 : MAX REGIME (Opaque, Bord épais) ---
            # On vérifie data_bubble >= 0.9 par sécurité mathématique
            m_max = mask_max & (data_bubble >= 0.9)
            if np.any(m_max):
                ax2.scatter(dates[m_max], np.full(m_max.sum(), y_pos), s=base_sizes[m_max], 
                            color=color, alpha=1.0, edgecolors='black', linewidth=2.5, zorder=3)
                            
            # --- Condition 2 : ACTIF mais pas max (Semi-transparent, Bord fin) ---
            m_act = mask_act & ~mask_max & (data_bubble >= 0.9)
            if np.any(m_act):
                ax2.scatter(dates[m_act], np.full(m_act.sum(), y_pos), s=base_sizes[m_act], 
                            color=color, alpha=0.6, edgecolors='black', linewidth=1.0, zorder=2)
                            
            # --- Condition 3 : TENTATIVE (Seuil > 0.9 dépassé mais pas actif/persistant) ---
            m_base = (data_bubble >= 0.9) & ~mask_act
            if np.any(m_base):
                ax2.scatter(dates[m_base], np.full(m_base.sum(), y_pos), s=base_sizes[m_base], 
                            color=color, alpha=0.2, edgecolors='none', zorder=1)
                            
            # Note : Les valeurs < 0.9 ne sont délibérément pas tracées.

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
    
    for date, regime_name in frieze_series.items():
        color = color_mapping.get(str(regime_name).strip(), '#e0e0e0')
        start_rect = date - pd.Timedelta(hours=12)
        end_rect = date + pd.Timedelta(hours=12)
        ax3.axvspan(start_rect, end_rect, color=color, linewidth=0, alpha=1)

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
    ax1.set_xlim(start_dt, end_dt)
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
    ax1.set_xlim(start_dt, end_dt)
    plt.subplots_adjust(hspace=0.1) 
    plt.tight_layout(rect=[0, 0, 1, 0.5]) 
    if save_path:
        plt.savefig(save_path, dpi = 150, bbox_inches = 'tight', facecolor='white')
        plt.close(fig)
    else : 
        print("ça n'a pas enregistré (entrer chemin)")


# 1. Création d'un dossier spécifique pour les années
output_folder = Path("../archives/images_monitoring/ERA5")
output_folder.mkdir(parents=True, exist_ok=True)

# 2. On récupère la toute dernière année de vos données
max_year = pd.to_datetime(indices.time.values[-1]).year
start_year = 1960

print(f"Début de la génération des images (de {start_year} à {max_year})...")

# 3. La boucle par année
for year in range(start_year, max_year + 1):
    
    # On fixe les dates du début à la fin de l'année
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    
    # Nom du fichier (vous pouvez changer .png en .pdf si besoin)
    filename = output_folder / f"{year}_tous.png"
    
    # Appel de la fonction
    plot_ultimate_regimes_masked2_save(
        indices=indices,               
        active_regimes=active_regimes, 
        max_regime=max_regime,         
        start_date=start_date,
        end_date=end_date,
        dictionnaire_regimes=regime_meta, # N'oubliez pas le nom de votre dico !
        save_path=filename
    )
    
    print(f"✅ Enregistré : {filename}")

print("Génération terminée ! Toutes les images sont dans le dossier 'images_monitoring_annuel'.")


# 1. Création du dossier cible s'il n'existe pas
output_folder = Path("../archives/images_monitoring/ERA5")
output_folder.mkdir(parents=True, exist_ok=True)

# 2. On récupère la toute dernière année de vos données (pour savoir quand arrêter la boucle)
# max_date = pd.to_datetime(indices.time.max().values) # Si format xarray standard
# ou de manière sécurisée :
max_year = pd.to_datetime(indices.time.values[-1]).year
max_month = pd.to_datetime(indices.time.values[-1]).month

start_year = 1960

print(f"Début de la génération des images (de {start_year} à {max_year})...")

# 3. La boucle
for year in range(start_year, max_year + 1):
    for month in range(1, 13):
        
        # On s'arrête si on dépasse le dernier mois disponible dans les données
        if year == max_year and month > max_month:
            break
            
        # Trouver le dernier jour du mois (28, 29, 30 ou 31)
        last_day = calendar.monthrange(year, month)[1]
        
        # Formatage des dates pour la fonction (ex: '2015-01-01' et '2015-01-31')
        # Le :02d permet d'avoir 01, 02... au lieu de 1, 2
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-{last_day}"
        
        # Nom du fichier (ex: monitoring_2015_01.png)
        filename = output_folder / f"{year}_{month:02d}.png"
        
        # Appel de la fonction magique
        plot_ultimate_regimes_masked_save(
            indices=indices,               
            active_regimes=active_regimes, 
            max_regime=max_regime,         
            start_date=start_date,
            end_date=end_date,
            dictionnaire_regimes=regime_meta, # N'oubliez pas le nom de votre dico ici !
            save_path=filename
        )
        
        print(f"Enregistré : {filename}")

print("✅ Génération terminée ! Toutes les images sont dans le dossier 'images_monitoring'.")


