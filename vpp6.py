import numpy as np
import matplotlib.pyplot as plt

# =====================================================
# PARAMÈTRES GLOBAUX DU MODÈLE
# =====================================================

# Définition du marché FCR
ENERGY_HOURS = 4              # Durée d'un slot de marché (heures)
REQUIRED_POWER = 10_000       # Puissance FCR requise (kW)
N_SLOTS_YEAR = 2190           # Nombre de slots par an (365 jours × 6 slots/jour)

# Caractéristiques des actifs de stockage
POWER_MEAN = 100              # Puissance nominale moyenne (kW)
POWER_STD = 20                # Écart-type de la puissance (kW)

# État de charge initial des batteries
SOC_MEAN = 600                # SOC moyen initial (kWh) - dimensionné pour 6h d'autonomie
SOC_STD = 100                 # Écart-type du SOC initial (kWh)

# Modèle de disponibilité
P_AVAILABLE_FCR = 0.70        # Probabilité qu'un actif soit disponible pour FCR à chaque slot

# Dynamique du SOC : modèle auto-calibré pour maintenir l'équilibre long terme
SOC_DEGRADATION_PER_USE = 0.002    # Décharge relative quand l'actif est utilisé pour FCR
TARGET_NET_BALANCE = 0.0005         # Balance nette positive cible par slot

# Calcul automatique du taux de recharge pour équilibrer les cycles
# L'équation garantit que : recharge × (1-p) - décharge × p = balance positive
SOC_RECHARGE_RATE = (SOC_DEGRADATION_PER_USE * P_AVAILABLE_FCR + TARGET_NET_BALANCE) / (1 - P_AVAILABLE_FCR)

# Critère de succès annuel
MIN_SUCCESS_RATE = 0.95       # L'agrégateur doit fournir 10 MW pendant au moins 95% des slots


# =====================================================
# MISE À JOUR DU SOC
# =====================================================
def update_soc(socs, powers, available_for_fcr):
    """
    Met à jour l'état de charge des batteries selon leur utilisation.
    
    Les actifs utilisés pour FCR se déchargent légèrement, tandis que ceux
    réservés sur d'autres marchés (aFRR, arbitrage) se rechargent.
    Le taux de recharge est calibré automatiquement pour maintenir un équilibre
    positif sur le long terme en fonction de P_AVAILABLE_FCR.
    
    Args:
        socs: États de charge actuels (kWh)
        powers: Puissances nominales des actifs (kW)
        available_for_fcr: Masque booléen indiquant quels actifs sont utilisés pour FCR
        
    Returns:
        États de charge mis à jour, avec limite basse à 0
    """
    delta_soc = np.zeros_like(socs)
    
    # Décharge pour les actifs sollicités sur le marché FCR
    delta_soc[available_for_fcr] = -SOC_DEGRADATION_PER_USE * SOC_MEAN
    
    # Recharge pour les actifs utilisés sur d'autres marchés
    delta_soc[~available_for_fcr] = SOC_RECHARGE_RATE * SOC_MEAN
    
    # Application des variations avec contrainte de non-négativité
    socs = socs + delta_soc
    return np.clip(socs, 0, None)


# =====================================================
# SIMULATION D'UN SLOT DE MARCHÉ
# =====================================================
def simulate_fcr_slot(socs):
    """
    Simule un slot de 4 heures sur le marché FCR.
    
    À chaque slot, chaque actif a une probabilité P_AVAILABLE_FCR d'être disponible
    pour le marché FCR. Pour contribuer effectivement, un actif doit :
    1. Être disponible (tirage aléatoire selon P_AVAILABLE_FCR)
    2. Avoir suffisamment de SOC pour tenir pendant toute la durée du slot
    
    Args:
        socs: États de charge actuels de tous les actifs (kWh)
        
    Returns:
        success: Booléen indiquant si l'objectif de puissance est atteint
        can_provide_fcr: Masque des actifs pouvant effectivement fournir FCR
        available_for_fcr: Masque des actifs disponibles (avant contrainte SOC)
        powers: Puissances nominales tirées pour ce slot
    """
    n_assets = len(socs)

    # Tirage des puissances nominales avec variabilité
    powers = np.random.normal(POWER_MEAN, POWER_STD, n_assets)
    powers = np.clip(powers, 20, None)  # Limite basse technique

    # Disponibilité aléatoire : chaque actif peut être réservé sur un autre marché
    available_for_fcr = np.random.random(n_assets) < P_AVAILABLE_FCR
    
    # Contrainte énergétique : vérification que le SOC permet de tenir 4 heures
    has_enough_soc = socs >= powers * ENERGY_HOURS
    
    # Un actif contribue au FCR ssi disponible ET capacité énergétique suffisante
    can_provide_fcr = available_for_fcr & has_enough_soc
    
    # Agrégation de la puissance disponible
    available_fcr_power = np.sum(powers[can_provide_fcr])
    
    # Vérification de l'objectif de puissance
    success = available_fcr_power >= REQUIRED_POWER
    
    return success, can_provide_fcr, available_for_fcr, powers


# =====================================================
# SIMULATION D'UNE ANNÉE COMPLÈTE
# =====================================================
def simulate_year_with_tracking(n_assets):
    """
    Simule une année complète (2190 slots) avec suivi détaillé des métriques.
    
    Cette version enregistre l'historique complet pour permettre l'analyse
    et la visualisation de la dynamique du système.
    
    Args:
        n_assets: Nombre d'actifs dans le portefeuille
        
    Returns:
        Dictionnaire contenant les historiques et statistiques de la simulation
    """
    # Initialisation des SOC selon une distribution normale
    socs = np.clip(
        np.random.normal(SOC_MEAN, SOC_STD, n_assets),
        0, None
    )
    
    success_count = 0
    
    # Structures de stockage des historiques
    soc_history = [socs.copy()]
    fcr_power_history = []
    success_history = []
    available_history = []
    soc_ok_history = []

    # Simulation de tous les slots de l'année
    for _ in range(N_SLOTS_YEAR):
        success, can_provide, available, powers = simulate_fcr_slot(socs)
        
        if success:
            success_count += 1
        
        # Mise à jour du SOC pour le prochain slot
        socs = update_soc(socs, powers, can_provide)
        
        # Enregistrement des métriques
        soc_history.append(socs.copy())
        fcr_power_history.append(np.sum(powers[can_provide]))
        success_history.append(success)
        available_history.append(np.sum(available))
        soc_ok_history.append(np.sum(socs >= powers * ENERGY_HOURS))

    return {
        'soc_history': np.array(soc_history),
        'fcr_power_history': np.array(fcr_power_history),
        'success_history': np.array(success_history),
        'available_history': np.array(available_history),
        'soc_ok_history': np.array(soc_ok_history),
        'success_rate': success_count / N_SLOTS_YEAR
    }


def simulate_year(n_assets):
    """
    Version simplifiée de la simulation annuelle pour les calculs de probabilité.
    
    Ne stocke pas l'historique complet, uniquement le résultat final (succès/échec).
    """
    socs = np.clip(
        np.random.normal(SOC_MEAN, SOC_STD, n_assets),
        0, None
    )
    
    success_count = 0

    for _ in range(N_SLOTS_YEAR):
        success, can_provide, available, powers = simulate_fcr_slot(socs)
        
        if success:
            success_count += 1
        
        socs = update_soc(socs, powers, can_provide)

    return success_count / N_SLOTS_YEAR >= MIN_SUCCESS_RATE


# =====================================================
# CALCUL DE LA PROBABILITÉ DE SUCCÈS ANNUELLE
# =====================================================
def annual_success_probability(n_assets, n_trials=200):
    """
    Estime la probabilité qu'un portefeuille de n_assets respecte le critère
    de disponibilité annuelle via simulation Monte Carlo.
    
    Args:
        n_assets: Taille du portefeuille à évaluer
        n_trials: Nombre de simulations indépendantes pour l'estimation
        
    Returns:
        Proportion de simulations ayant atteint MIN_SUCCESS_RATE
    """
    successes = 0
    for _ in range(n_trials):
        if simulate_year(n_assets):
            successes += 1
    return successes / n_trials


def installed_capacity(n_assets):
    """Calcule la capacité installée totale en kW."""
    return n_assets * POWER_MEAN


# =====================================================
# FONCTIONS DE VISUALISATION
# =====================================================

def plot_soc_evolution(result, n_assets_sample=10):
    """
    Montre comment les batteries se chargent et déchargent au fil de l'année.
    
    Ce graphe permet de vérifier que :
    - Les batteries ne tombent pas à zéro (épuisement)
    - Le SOC reste au-dessus du minimum requis (400 kWh)
    - L'équilibre charge/décharge fonctionne sur le long terme
    """
    fig, ax = plt.subplots(figsize=(14, 6))
    
    soc_history = result['soc_history']
    n_show = min(n_assets_sample, soc_history.shape[1])
    
    for i in range(n_show):
        ax.plot(soc_history[:, i], alpha=0.6, linewidth=1, label=f'Actif {i+1}')
    
    ax.axhline(y=0, color='red', linestyle='--', linewidth=2, 
               label='Limite critique : batterie vide')
    ax.axhline(y=POWER_MEAN * ENERGY_HOURS, color='orange', linestyle=':', 
               linewidth=2, alpha=0.7, 
               label=f'Minimum pour 4h : {POWER_MEAN * ENERGY_HOURS} kWh')
    
    ax.set_xlabel('Slot temporel (1 slot = 4 heures)', fontsize=12)
    ax.set_ylabel('Charge de la batterie (kWh)', fontsize=12)
    ax.set_title('Évolution de la charge des batteries sur 1 an', fontsize=14, fontweight='bold')
    ax.legend(loc='best', fontsize=9)
    ax.grid(True, alpha=0.3)
    
    # Annotation explicative
    ax.text(0.02, 0.98, 
            'Les batteries se déchargent quand utilisées pour FCR (70% du temps)\n'
            'et se rechargent quand sur autre marché (30% du temps)',
            transform=ax.transAxes, fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    return fig


def plot_power_delivery(result):
    """
    Montre la puissance FCR fournie à chaque slot vs l'objectif de 10 MW.
    
    Ce graphe répond à la question : "Est-ce qu'on arrive à fournir 10 MW ?"
    - Zones vertes : on a assez de puissance (succès)
    - Zones rouges : on n'a pas assez (échec)
    
    Le taux de succès doit être >= 95% pour respecter le contrat.
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    
    fcr_power = result['fcr_power_history']
    success = result['success_history']
    
    # Graphe 1 : Puissance disponible slot par slot
    ax1.plot(fcr_power / 1000, color='steelblue', linewidth=1, alpha=0.8, label='Puissance FCR fournie')
    ax1.axhline(y=REQUIRED_POWER/1000, color='red', linestyle='--', linewidth=2, 
                label=f'Objectif contractuel : {REQUIRED_POWER/1000} MW')
    ax1.fill_between(range(len(fcr_power)), fcr_power/1000, REQUIRED_POWER/1000, 
                      where=(fcr_power >= REQUIRED_POWER), color='green', alpha=0.2, label='Succès')
    ax1.fill_between(range(len(fcr_power)), fcr_power/1000, REQUIRED_POWER/1000, 
                      where=(fcr_power < REQUIRED_POWER), color='red', alpha=0.2, label='Échec')
    
    ax1.set_ylabel('Puissance (MW)', fontsize=12)
    ax1.set_title('Puissance FCR fournie à chaque slot', fontsize=14, fontweight='bold')
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)
    
    # Graphe 2 : Performance cumulée
    cumul_success = np.cumsum(success) / np.arange(1, len(success) + 1)
    ax2.plot(cumul_success * 100, color='steelblue', linewidth=2, label='Performance réelle')
    ax2.axhline(y=MIN_SUCCESS_RATE*100, color='red', linestyle='--', linewidth=2, 
                label=f'Minimum contractuel : {MIN_SUCCESS_RATE*100}%')
    
    final_rate = cumul_success[-1] * 100
    color = 'green' if final_rate >= MIN_SUCCESS_RATE*100 else 'red'
    ax2.text(0.98, 0.02, f'Taux final : {final_rate:.2f}%',
             transform=ax2.transAxes, fontsize=14, fontweight='bold',
             horizontalalignment='right', color=color,
             bbox=dict(boxstyle='round', facecolor='white', edgecolor=color, linewidth=2))
    
    ax2.set_xlabel('Slot temporel (1 slot = 4 heures)', fontsize=12)
    ax2.set_ylabel('Taux de disponibilité (%)', fontsize=12)
    ax2.set_title('Performance cumulée sur l\'année', fontsize=14, fontweight='bold')
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim([90, 100])
    
    plt.tight_layout()
    return fig


def plot_limiting_factors(result, n_assets):
    """
    Diagnostique POURQUOI on n'arrive pas toujours à fournir 10 MW.
    
    Il y a deux raisons possibles pour qu'un actif ne contribue pas :
    1. Il n'est pas disponible (réservé sur un autre marché) - hasard
    2. Sa batterie est trop déchargée (SOC insuffisant) - gestion énergétique
    
    Ce graphe montre quelle contrainte est la plus limitante.
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    
    available = result['available_history']
    soc_ok = result['soc_ok_history']
    
    # Graphe 1 : Évolution temporelle des deux contraintes
    ax1.plot(available, label=f'Actifs disponibles (hasard, p={P_AVAILABLE_FCR})', 
             color='royalblue', linewidth=1.5, alpha=0.8)
    ax1.plot(soc_ok, label='Actifs avec batterie suffisamment chargée', 
             color='forestgreen', linewidth=1.5, alpha=0.8)
    ax1.axhline(y=REQUIRED_POWER/POWER_MEAN, color='red', linestyle='--', 
                linewidth=2, label=f'Nombre minimum d\'actifs requis : {REQUIRED_POWER/POWER_MEAN:.0f}')
    
    ax1.set_ylabel('Nombre d\'actifs', fontsize=12)
    ax1.set_xlabel('Slot temporel (1 slot = 4 heures)', fontsize=12)
    ax1.set_title('Évolution des contraintes au fil de l\'année', fontsize=14, fontweight='bold')
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)
    
    # Annotation explicative
    ax1.text(0.02, 0.98, 
            'Si les deux courbes sont au-dessus de la ligne rouge : succès\n'
            'Si l\'une des deux passe en dessous : échec',
            transform=ax1.transAxes, fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    
    # Graphe 2 : Statistiques comparatives
    avg_available = np.mean(available)
    avg_soc_ok = np.mean(soc_ok)
    min_available = np.min(available)
    min_soc_ok = np.min(soc_ok)
    
    categories = ['Moyenne sur l\'année', 'Minimum rencontré']
    available_values = [avg_available, min_available]
    soc_ok_values = [avg_soc_ok, min_soc_ok]
    
    x = np.arange(len(categories))
    width = 0.35
    
    bars1 = ax2.bar(x - width/2, available_values, width, label='Contrainte disponibilité',
                    color='royalblue', alpha=0.8)
    bars2 = ax2.bar(x + width/2, soc_ok_values, width, label='Contrainte SOC',
                    color='forestgreen', alpha=0.8)
    
    ax2.axhline(y=REQUIRED_POWER/POWER_MEAN, color='red', linestyle='--', 
                linewidth=2, label=f'Seuil minimum : {REQUIRED_POWER/POWER_MEAN:.0f}')
    
    ax2.set_ylabel('Nombre d\'actifs', fontsize=12)
    ax2.set_xticks(x)
    ax2.set_xticklabels(categories)
    ax2.set_title('Comparaison des contraintes limitantes', fontsize=14, fontweight='bold')
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3, axis='y')
    
    # Annotations sur les barres
    for bar in bars1:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}', ha='center', va='bottom', fontsize=10)
    for bar in bars2:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}', ha='center', va='bottom', fontsize=10)
    
    plt.tight_layout()
    return fig


def plot_oversizing_vs_probability():
    """
    Cette courbe est supprimée car elle nécessite trop de calculs.
    Utilisez find_min_assets_annual() pour trouver le dimensionnement optimal.
    """
    pass


# =====================================================
# DIAGNOSTIC ET ANALYSE
# =====================================================

def diagnostic_slot(n_assets=200):
    """
    Analyse détaillée d'un seul slot pour validation du modèle.
    
    Utile pour déboguer et comprendre le comportement instantané du système.
    """
    print(f"\n{'='*70}")
    print("DIAGNOSTIC D'UN SLOT")
    print(f"{'='*70}\n")
    
    socs = np.clip(
        np.random.normal(SOC_MEAN, SOC_STD, n_assets),
        0, None
    )
    
    powers = np.random.normal(POWER_MEAN, POWER_STD, n_assets)
    powers = np.clip(powers, 20, None)
    
    print(f"État initial :")
    print(f"  Nombre d'actifs : {n_assets}")
    print(f"  SOC moyen : {np.mean(socs):.1f} kWh (min: {np.min(socs):.1f}, max: {np.max(socs):.1f})")
    print(f"  Puissance moyenne : {np.mean(powers):.1f} kW")
    print(f"  Énergie requise par actif : {np.mean(powers) * ENERGY_HOURS:.1f} kWh")
    
    available_for_fcr = np.random.random(n_assets) < P_AVAILABLE_FCR
    has_enough_soc = socs >= powers * ENERGY_HOURS
    can_provide_fcr = available_for_fcr & has_enough_soc
    
    print(f"\nContraintes :")
    print(f"  Actifs disponibles (p={P_AVAILABLE_FCR}) : {np.sum(available_for_fcr)} / {n_assets} ({np.sum(available_for_fcr)/n_assets*100:.1f}%)")
    print(f"  Actifs avec SOC suffisant : {np.sum(has_enough_soc)} / {n_assets} ({np.sum(has_enough_soc)/n_assets*100:.1f}%)")
    print(f"  Actifs pouvant fournir FCR : {np.sum(can_provide_fcr)} / {n_assets} ({np.sum(can_provide_fcr)/n_assets*100:.1f}%)")
    
    available_fcr_power = np.sum(powers[can_provide_fcr])
    print(f"\nPuissance FCR :")
    print(f"  Puissance disponible : {available_fcr_power/1000:.2f} MW")
    print(f"  Puissance requise : {REQUIRED_POWER/1000:.1f} MW")
    print(f"  Statut : {'SUCCÈS' if available_fcr_power >= REQUIRED_POWER else 'ÉCHEC'}")


def analyze_one_year(n_assets):
    """
    Rapport complet d'analyse pour un portefeuille de taille donnée.
    
    Génère toutes les visualisations et statistiques nécessaires pour évaluer
    la performance d'une configuration.
    """
    print(f"\n{'='*70}")
    print(f"ANALYSE D'UNE ANNÉE AVEC {n_assets} ACTIFS")
    print(f"{'='*70}\n")
    
    print("Paramètres du modèle :")
    print(f"  Probabilité disponibilité FCR : {P_AVAILABLE_FCR*100:.0f}%")
    print(f"  Puissance moyenne par actif : {POWER_MEAN} kW")
    print(f"  SOC moyen initial : {SOC_MEAN} kWh")
    print(f"  SOC minimum requis : {POWER_MEAN * ENERGY_HOURS} kWh")
    print(f"  Décharge si FCR : {SOC_DEGRADATION_PER_USE*100:.2f}% du SOC moyen")
    print(f"  Recharge si autre marché : {SOC_RECHARGE_RATE*100:.3f}% du SOC moyen (auto-calibré)")
    
    expected_balance = (SOC_RECHARGE_RATE * (1 - P_AVAILABLE_FCR) - 
                       SOC_DEGRADATION_PER_USE * P_AVAILABLE_FCR) * 100
    print(f"  Balance nette attendue : {expected_balance:+.3f}% par slot")
    print(f"  Balance annuelle (2190 slots) : {expected_balance * N_SLOTS_YEAR:+.1f}%\n")
    
    result = simulate_year_with_tracking(n_assets)
    
    print(f"Résultats :")
    print(f"  Taux de disponibilité annuel : {result['success_rate']*100:.2f}%")
    print(f"  Slots réussis : {np.sum(result['success_history'])} / {N_SLOTS_YEAR}")
    print(f"  Capacité installée : {installed_capacity(n_assets)/1000:.1f} MW")
    print(f"  Surdimensionnement : x{installed_capacity(n_assets)/REQUIRED_POWER:.2f}")
    print(f"  Surdimensionnement théorique (1/p) : x{1.0/P_AVAILABLE_FCR:.2f}")
    
    avg_available = np.mean(result['available_history'])
    avg_soc_ok = np.mean(result['soc_ok_history'])
    print(f"\n  Actifs disponibles en moyenne : {avg_available:.1f} ({avg_available/n_assets*100:.1f}%)")
    print(f"  Actifs avec SOC suffisant en moyenne : {avg_soc_ok:.1f} ({avg_soc_ok/n_assets*100:.1f}%)")
    
    print("\nGénération des graphiques...")
    
    fig1 = plot_soc_evolution(result)
    plt.savefig(f'soc_evolution_{n_assets}assets.png', dpi=150, bbox_inches='tight')
    print("  Sauvegarde : soc_evolution.png")
    print("    -> Montre si les batteries tiennent la charge sur l'année")
    
    fig2 = plot_power_delivery(result)
    plt.savefig(f'power_delivery_{n_assets}assets.png', dpi=150, bbox_inches='tight')
    print("  Sauvegarde : power_delivery.png")
    print("    -> Montre si on arrive à fournir 10 MW à chaque slot")
    
    fig3 = plot_limiting_factors(result, n_assets)
    plt.savefig(f'limiting_factors_{n_assets}assets.png', dpi=150, bbox_inches='tight')
    print("  Sauvegarde : limiting_factors.png")
    print("    -> Diagnostique quelle contrainte limite les performances")
    
    plt.show()
    
    return result


# =====================================================
# RECHERCHE DU DIMENSIONNEMENT OPTIMAL
# =====================================================

def find_min_assets_annual(
    confidence_target=0.95,
    n_min=100,
    n_max=400,
    step=10
):
    """
    Recherche dichotomique du nombre minimal d'actifs pour atteindre l'objectif.
    
    Args:
        confidence_target: Taux de disponibilité annuel cible (ex: 0.95 pour 95%)
        n_min: Borne inférieure de la recherche
        n_max: Borne supérieure de la recherche
        step: Pas de la recherche
        
    Returns:
        Tuple (n_assets, capacity, oversizing, probability) ou None si non trouvé
    """
    print(f"\nRecherche du nombre minimal d'actifs (cible : {confidence_target*100:.0f}%)\n")
    
    # Diagnostic initial pour validation
    diagnostic_slot(n_min)
    
    for n_assets in range(n_min, n_max + 1, step):
        prob = annual_success_probability(n_assets, n_trials=100)
        capacity = installed_capacity(n_assets)
        oversizing = capacity / REQUIRED_POWER

        print(
            f"{n_assets:3d} actifs | "
            f"Capacité {capacity/1000:5.1f} MW | "
            f"Surdim x{oversizing:.2f} | "
            f"P = {prob:.3f}"
        )

        if prob >= confidence_target:
            print(f"\n{'='*70}")
            print("SEUIL ATTEINT")
            print(f"{'='*70}")
            print(f"  Nombre minimal d'actifs : {n_assets}")
            print(f"  Capacité installée : {capacity/1000:.1f} MW")
            print(f"  Facteur de surdimensionnement : x{oversizing:.2f}")
            print(f"  Probabilité de succès annuel : {prob:.1%}")
            print(f"  Surdimensionnement théorique (1/p) : x{1.0/P_AVAILABLE_FCR:.2f}")
            return n_assets, capacity, oversizing, prob

    print("\nSeuil non atteint dans la plage explorée")
    print(f"Augmentez n_max au-delà de {n_max} ou ajustez les paramètres du modèle")
    return None


# =====================================================
# PROGRAMME PRINCIPAL
# =====================================================

if __name__ == "__main__":
    print("="*70)
    print("MODÈLE DE DIMENSIONNEMENT BATTERIE POUR LE MARCHÉ FCR")
    print("="*70)
    print(f"\nHypothèse : Chaque actif a {P_AVAILABLE_FCR*100:.0f}% de chance d'être")
    print(f"disponible pour FCR à chaque slot (sinon réservé sur autre marché)")
    
    # Étape 1 : Recherche du dimensionnement optimal
    print("\n" + "="*70)
    print("RECHERCHE DU NOMBRE MINIMAL D'ACTIFS")
    print("="*70)
    result_search = find_min_assets_annual(
        confidence_target=0.95,
        n_min=100,
        n_max=400,
        step=10
    )
    
    if result_search:
        optimal_n_assets = result_search[0]
        
        # Étape 2 : Analyse détaillée avec le nombre optimal trouvé
        print("\n" + "="*70)
        print("ANALYSE DÉTAILLÉE AVEC LE NOMBRE OPTIMAL")
        print("="*70)
        analyze_one_year(n_assets=optimal_n_assets)
        
    else:
        print("\nImpossible de trouver une solution dans la plage explorée")
        print("Suggestions :")
        print("  - Augmenter n_max dans find_min_assets_annual()")
        print("  - Réduire MIN_SUCCESS_RATE")
        print("  - Augmenter P_AVAILABLE_FCR")