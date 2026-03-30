import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import json
from matplotlib.patches import Patch


###########################################################
# ---------- Récupération des données d'intérêt ----------
###########################################################

# ---------- Récupération des données indiquant si un régime est dominant ----------
# On récupère un DataArray contenant pour chaque jour une liste de 7 booléens : 
    # - Si le régime est dominant, il est inscrit True pour le régime correspondant (il n'y a qu'un régime dominant pour chaque jour).
    # - Si il n'y a pas de régime actif, il est inscrit False pour tous les régimes. Le "régime actif" est alors No Regime.
max_regime = xr.open_dataarray("donnees_sauvegardees/max_regime.nc") 

# ---------- Récupération de l'ordre des régime obtenu par kmeans ----------
# On récupère la liste des régimes de temps, dans l'ordre obtenu par les kmeans
with open("donnees_sauvegardees/cluster_regime_names.json", "r", encoding="utf-8") as f:
    cluster_regime_names = json.load(f)
cluster_regime_names=list(cluster_regime_names.values())

# ---------- On ordonne les régimes selon un ordre souhaité (et réfléchi !) ----------
labels_regimes = ['European Blocking', 'Scandinavian Blocking', 'Greenland Blocking','Atlantic Ridge','Zonal' , 'Scandinavian Trough', 'Atlantic Trough', 'No Regime']

# ---------- # Récupération des indices des régime pour s'adapter à l'ordre souhaité (et réfléchi !) ----------
# Liste de stockage
position_regime = []
# On traite les régimes selon l'ordre souhaité (et réfléchi !)
for i in labels_regimes:
    position_regime.append(cluster_regime_names.index(i))
position_regime.pop() # On enlève le No Regime, car il n'apparait pas dans les données issues spécifiquement du kmeans 

# ---------- On réordonne le dataarray selon l'ordre souhaité (et réfléchi !) ----------
max_regime = max_regime.isel(regime=position_regime) 


###########################################################
# ---- Formatage des couleurs et paramètres d'intérêt ----
###########################################################

#European Blocking, Scandinavian Blocking, Greenland Blocking, Atlantic Ridge, Zonal, Scandinavian Trough, Atlantic Trough, No Regime    

#couleurs = ["#8cc63f", "#ff8c00", "#0000ff", "#006400", "#6a0dad","#f2c300", "#ff0000", "#7f7f7f"] # Couleurs utilisées par Grams
couleurs = ["#8B4513","#6a0dad","#0000ff","#F4A460","#ff0000","#43CEF8","#228B22","#7f7f7f"]

mois_noms = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
mois = ['01','02','03','04','05','06','07','08','09','10','11','12']
annee_actuelle = [1991+i for i in range(35)] # Pour la sauvegarde des histogrammes allant de 1991 à 2025


###########################################################
# ---------- Fonctions de traitement des données ----------
###########################################################

def mois_selectionne(mois_actuel,annee_fin):
    """
    Nécessite d'entrer les derniers mois et l'année des trois mois glissants que l'on souhaite renvoyer : 
    - Entrez le mois_actuel sous la forme str : mois_actuel = "01" pour janvier par exemple, ou mois_actuel = "12" pour décembre 
    - Entrez l'année de fin sous la forme d'un entier : annee_fin = 2026 pour 2026
    Renvoie une liste du mois actuel et des deux mois précédents, chacun sous la forme "année-mois" 
    Par exemple : ["2023-12","2024-01","2024-02"], si on choisit de se placer en février 2024 (mois_actuel = "02" et annee_fin = 2024) 
    """

    annee_debut = annee_fin - 1 # Calcul de l'année précédente

    # Disjonction de cas selon le mois_actuel choisi
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

def nombre_jours_par_regime(mois_actuel,annee_fin):
    """
    Nécessite d'entrer les derniers mois et l'année des trois mois glissants que l'on souhaite renvoyer : 
    - Entrez le mois_actuel sous la forme str : mois_actuel = "01" pour janvier par exemple, ou mois_actuel = "12" pour décembre 
    - Entrez l'année de fin sous la forme d'un entier : annee_fin = 2026 pour 2026
    Renvoie :
    - repartition : liste de trois listes (une pour chaque mois considéré, ordonné dans les sens passé -> présent) des nombres d'occurrences des régimes
    - repartition_trimestrielle : liste des nombres d'occurences des régimes sur les trois mois considérés
    """

    # ---------- Listes de stockage ----------
    repartition = []
    repartition_trimestrielle = []

    # ---------- Récupération de la liste des mois considérés ----------
    liste_mois = mois_selectionne(mois_actuel,annee_fin)[0] 

    # ---------- Détermine le nombre d'occurences de chaque régime par mois ----------
    # Traite les données mois par mois, pour les mois sélectionnés
    for i, mois_cible in enumerate(liste_mois):
        data_mois = max_regime.sel(time=mois_cible) # Récupère les données du mois considéré uniquement
        repartition.append((data_mois.sum(dim='time')).values.tolist()) # Compte le nombre de jours par régimes
        repartition[i].append((data_mois.sum(dim='regime')==0).sum(dim='time').item()) # Ajoute le nombre d'occurrences de No Regime au mois considéré

    # ---------- Détermine le nombre d'occurences de chaque régime de sur les trois mois considérés ----------
    # Traite les données régime par régime
    for k in range (len(repartition[0])):
        repartition_trimestrielle.append(repartition[0][k] + repartition[1][k] + repartition[2][k])
    
    return repartition, repartition_trimestrielle

def pourcentages(mois_actuel,annee_fin):
    """
    Nécessite d'entrer les derniers mois et l'année des trois mois glissants que l'on souhaite renvoyer : 
    - Entrez le mois_actuel sous la forme str : mois_actuel = "01" pour janvier par exemple, ou mois_actuel = "12" pour décembre 
    - Entrez l'année de fin sous la forme d'un entier : annee_fin = 2026 pour 2026
    Renvoie :
    - pourcentage_par_rapport_climatologie_par_regime_par_mois : le pourcentage d'occurrences des régimes par rapport à la climatologie du mois pour chaque mois sélectionné
    - pourcentage_par_rapport_climatologie_par_regime_trimestriel : le pourcentage d'occurrences des régimes par rapport à la climatologie trimestrielle pour les trois mois sélectionnés
    Nécessite la répartition des jours entre chaque régime pour chaque mois sélectionné, et la répartition des jours entre chaque régime sur les
    trois mois sélectionnés (qui sont produites par la fonction nombre_jours_par_regime)
    """

    # ---------- Traitement des données avec nombre_jours_par_regime ----------
    repartition, repartition_trimestrielle = nombre_jours_par_regime(mois_actuel,annee_fin)

    # ---------- Listes de stockage ----------
    pourcentage_par_rapport_climatologie_par_regime_par_mois = [[],[],[]]
    pourcentage_par_rapport_climatologie_par_regime_trimestriel = []

    # ---------- Détermine le pourcentage d'occurences de chaque régime par mois ----------
    # Traite les données mois par mois, pour les mois sélectionnés    
    for i in range(len(repartition)):
        somme_liste = sum(repartition[i]) # Calcul du nombre de jours dans le mois 
        # Traite les données régime par régime    
        for el in repartition[i]:
            pct = (el/somme_liste)*100 # Calcul du pourcentage d'occurrences par régime
            pourcentage_par_rapport_climatologie_par_regime_par_mois[i].append(round(pct,2)) # Stockage en récupérant deux chiffres après la virgule

    # ---------- Détermine le pourcentage d'occurences de chaque régime sur l'ensemble des trois mois considérés ----------
    somme_liste = sum(repartition_trimestrielle) # Calcul du nombre de jours sur les trois mois considérés
    # Traite les données des trois mois régime par régime  
    for el in repartition_trimestrielle :
        pct = (el/somme_liste)*100 # Calcul du pourcentage d'occurrences par régime
        pourcentage_par_rapport_climatologie_par_regime_trimestriel.append(round(pct,2)) # Stockage en récupérant deux chiffres après la virgule

    return pourcentage_par_rapport_climatologie_par_regime_par_mois, pourcentage_par_rapport_climatologie_par_regime_trimestriel

def climatologie(annee_fin):
    """
    Nécessite d'entrer l'année de fin de la climatologie que l'on souhaite renvoyer : 
    - Entrez l'année de fin sous la forme d'un entier : annee_fin = 2026 pour 2026
    Renvoie :
    - climatologie_mois : nombre moyen climatologique d'occurrences de chaque régime sur le mois considéré
    - climatologie_trimestrielle_glissante : nombre moyen climatologique d'occurrences de chaque régime sur les trois mois considérés
    - annee_debut : année de début qu'on souhaite considérer
    """

    # ---------- Récupération des données d'intérêt pour établir la climatologie ----------
    annee_debut = annee_fin//10*10-29 # Calcul de l'année de début de la climatologie
    max_regime_30_ans = max_regime.sel(time=slice(f"{annee_debut}-01-01",f"{annee_fin}-12-31")) # Récupération des données des 30 ans considérés

    # ---------- Listes de stockage ----------
    donnees_climatologie = [] # Stockage des données des mois (pour chaque moi : liste des nombres d'occurrences de chaque régime)
    climatologie_mois = [[],[],[],[],[],[],[],[],[],[],[],[]] # Stockage des moyennes climatologiques d'occurrences de chaque régime pour chaque mois
    climatologie_trimestrielle_glissante = [] # Stockage des moyennes climatologiques d'occurrences de chaque régime pour chaque mois
    
    # ---------- Calcul des occurrences de chaque régime sur une durée de 30 ans pour chaque mois ----------
    # Traitement des données mois par mois (mais sur les 30 ans climatologiques en même temps)
    for i, mois_cible in enumerate(mois) : 
        data_mois = max_regime_30_ans.where(max_regime_30_ans['time'].dt.month == int(mois_cible), drop = True) # Transofrme les données en entier 0 (False) et 1 (True)
        donnees_mois = data_mois.sum(dim='time').values.tolist() # Somme les occurrences (1) des différents régimes -> Renvoie pour chaque mois une liste des nombres d'occurrences de chaque régime
        donnees_climatologie.append(donnees_mois) # Stocke les données du mois
        donnees_climatologie[i].append((data_mois.sum(dim='regime')==0).sum(dim='time').item()) # Calcul et stokage du nombre d'occurences de No Regime sur le mois traité
    
    # ---------- Calcul de la moyenne climatologique d'occurrences mensuelles pour chaque régime ----------
    nombre_annee = annee_fin-annee_debut+1 # 30 ans (normalement)
    # Traitement des données climatologique mois par mois
    for i in range(len(donnees_climatologie)):
        # Traitement des données climatologique régime par régime
        for k in range(len(donnees_climatologie[0])):
            climatologie_mois[i].append(round(donnees_climatologie[i][k]/nombre_annee,1)) # Calcul de la moyenne climatologique d'occurrences mensuelles pour chaque régime, arrondi au dixième près
    
    # ---------- Calcul de la moyenne climatologique d'occurrences trimestrielles pour chaque régime ----------
    # Traitement des données climatologique mois par mois
    for i in range (len(mois)) :
        liste = mois_selectionne(mois[i],annee_debut)[1] # On récupère les deux mois précédents le mois sélectionné dans la boucle, ainsi que le mois sélectionné dans la boucle
        # On somme sur les moyennes d'occurrences des régimes de chaque mois du trimestre considéré 
        sommme_par_element = [round(a+b+c,1) for a,b,c in zip(climatologie_mois[liste[0]],climatologie_mois[liste[1]],climatologie_mois[liste[2]])]
        climatologie_trimestrielle_glissante.append(sommme_par_element)# Stocke les données climatologique des trois mois 


    ''' #Pour vérifier qu'on a bien tous les jours
    somme = 0
    for i in range(len(mois)):
        somme += sum(donnees_climatologie[i])
    print(somme)
    '''

    return climatologie_mois, climatologie_trimestrielle_glissante, annee_debut


###########################################################
# ------------------ Fonctions de tracé ------------------
###########################################################

def tracer_barres(ax, repartition, clim_trois_mois, titres, is_cumul=False):
    """
    Trace les barres des histogrammes
    """

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
            val_clim = clim_trois_mois[i][j]
            
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

def affichage_histogrammes(mois_actuel,annee_fin):
    """
    Trace les histogrammes
    Nécessite d'entrer les derniers mois et l'année des trois mois glissants que l'on souhaite renvoyer : 
    - Entrez le mois_actuel sous la forme str : mois_actuel = "01" pour janvier par exemple, ou mois_actuel = "12" pour décembre 
    - Entrez l'année de fin sous la forme d'un entier : annee_fin = 2026 pour 2026
    """

    # ---------- Traitement des données ----------
    repartition, repartition_trimestrielle = nombre_jours_par_regime(mois_actuel,annee_fin) # Récupération des nombres d'occurrences des régimes
    climatologie_mois, climatologie_trimestrielle_glissante, annee_debut = climatologie(annee_fin) # Établissement de la climatologie
    liste = mois_selectionne(mois_actuel,annee_fin)[1] # Détermination des mois d'intérêt

    # ---------- Paramètre pour la présentation des histogrammes ----------
    # Extraction des noms des mois d'intérêt
    titres_mois = [mois_noms[liste[0]],mois_noms[liste[1]],mois_noms[liste[2]] ]

    # ---------- Configuration de la figure ----------
    fig = plt.figure(figsize=(14, 8)) # Taille de la figure
    # Nom de la figure
    fig.suptitle(f"ERA5 : Regimes de temps de {titres_mois[0]} à {titres_mois[2]} {annee_fin}\n(période de référence de la climatologie ERA5 : {annee_debut}-{annee_debut+29})", fontsize=14, fontweight='bold')

    gs = fig.add_gridspec(1, 2, width_ratios=[4, 1.6], wspace=0.3) # On utilise GridSpec pour séparer les 3 mois du cumul (car les échelles Y sont différentes)
    ax1 = fig.add_subplot(gs[0]) # Pour les trois mois d'intérêt
    ax2 = fig.add_subplot(gs[1]) # Pour le Cumul

    # ---------- Tracé des mois individuels (graphique de gauche) ----------
    climatologie_trois_mois_graphique = [climatologie_mois[i] for i in liste]
    # Formatage des axes
    ax1.set_ylim(0, 31)
    ax1.set_ylabel("Nombre de jours")
    tracer_barres(ax1, repartition, climatologie_trois_mois_graphique, titres_mois)

    # ---------- Tracé des trois mois glissants (graphique de droite) ----------
    cumul_trimestriel_graphique = repartition_trimestrielle
    # Estimation de la clim du cumul (somme des clims des 3 mois)
    climatologie_trimestrielle_graphique_ = climatologie_trimestrielle_glissante[int(mois_actuel)-1]
    # Formatage des axes
    ax2.yaxis.tick_right() # On déplace l'axe Y à droite pour le cumul
    ax2.set_ylim(0, 66)
    tracer_barres(ax2, [cumul_trimestriel_graphique], [climatologie_trimestrielle_graphique_], [f"De {titres_mois[0]} à {titres_mois[2]}"], is_cumul=True)

    # ---------- Ajout de la légende ----------
    legend_elements = [Patch(facecolor=couleurs[i], edgecolor='none', label=labels_regimes[i]) for i in range(8)]
    ax1.legend(handles=legend_elements, loc='lower left', bbox_to_anchor=(0.0, -0.15), 
            framealpha=1, edgecolor='black', ncol=4)

    # ---------- Sauvegarde ----------
    plt.tight_layout()
    plt.savefig(f"../archives/images_suivi_climatique/{annee_fin}_{mois_actuel}_histogrammes_suivi_climatique.png",bbox_inches="tight", pad_inches = 0.3)


###########################################################
# ---------------- Fonction de sauvegarde ----------------
###########################################################

def sauvegarde_tous_histogrammes(mois,annee_actuelle):
    """
    Sauvegarde tous les composites de l'année 1991 à 2025
    """

    # Traitement des données années par années
    for annee in annee_actuelle :
        # Traitement des données mois par mois
        for mois_actuel in mois : 
            affichage_histogrammes(mois_actuel,annee) # Génération des histogrammes (et sauvegarde comprise dans affichage_histogrammes)


###########################################################
# -------------- Génération des histogrammes --------------
###########################################################

sauvegarde_tous_histogrammes(mois,annee_actuelle)

###########################################################
# ------------- Génération de la climatologie -------------
###########################################################

np.save('donnees_sauvegardees/climatologie.npy', climatologie(2025)[:2])