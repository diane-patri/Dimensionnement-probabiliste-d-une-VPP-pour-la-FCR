# Dimensionnement probabiliste d’une VPP pour la FCR

## Objectif de l’étude
Ce projet vise à dimensionner un portefeuille de batteries au sein d’une centrale virtuelle (Virtual Power Plant, VPP) pour garantir, avec une probabilité annuelle de 95 %, la fourniture de **10 MW** sur le marché de la réserve primaire de fréquence (FCR).  

- Horizon : 1 an, découpé en **2190 slots de 4 heures**.  
- Critère contractuel : la puissance requise doit être disponible sur au moins 95 % des slots.  
- Justification : nécessité d’un **surdimensionnement** pour compenser les indisponibilités et variabilités stochastiques.

## Structure du portefeuille et hypothèses sur les actifs

Le portefeuille est constitué de batteries homogènes, caractérisées par les points suivants :

- **Puissance nominale** : chaque batterie a une puissance nominale tirée selon une **loi normale** de moyenne 100 kW et d’écart-type 20 kW.  
  - Cette approche reflète la **variabilité industrielle** des batteries et des systèmes de conversion : même pour des modèles identiques, les performances réelles peuvent varier.  
  - La loi normale permet d’introduire de manière simple cette hétérogénéité tout en garantissant qu’une majorité d’actifs se situe autour de la valeur nominale.  
  - Les valeurs extrêmes sont limitées par une borne minimale pour rester réalistes sur le plan technique.

- **État de charge initial (SOC)** : le SOC de chaque batterie est tiré selon une **loi normale centrée sur 600 kWh**, soit environ 6 heures d’autonomie à puissance nominale.  
  - Cette valeur est choisie pour que chaque batterie puisse couvrir un slot FCR complet de 4 heures sans tomber en dessous du minimum énergétique requis.  
  - L’écart-type introduit une **variabilité initiale naturelle** entre les batteries, reflétant des conditions opérationnelles hétérogènes au démarrage de l’année.

- **Disponibilité pour la FCR** : à chaque slot, une batterie a 70 % de chance d’être activée pour la FCR, et 30 % de chance d’être affectée à d’autres marchés tels que l’arbitrage journalier ou l’aFRR.  
  - Cette hypothèse reflète la **priorisation économique** : lorsque le SOC est suffisant, l’optimisation choisit parfois de réserver la batterie sur des marchés plus rémunérateurs.  
  - La disponibilité aléatoire est modélisée par un tirage de type Bernoulli indépendant pour chaque batterie et chaque slot, introduisant une **composante stochastique** réaliste dans la simulation.


## Dynamique du SOC
- Batteries utilisées pour la FCR : légère **décharge** proportionnelle au SOC moyen.  
- Batteries affectées à d’autres marchés : **recharge calibrée** pour maintenir un équilibre énergétique légèrement positif sur l’année.  
- Condition pour fournir la FCR : disponibilité + SOC suffisant.

## Méthodologie de simulation
- **Langage et outils** : Python, choisi pour sa flexibilité dans la modélisation stochastique, sa capacité à gérer de longues séries temporelles, et son efficacité pour des simulations Monte Carlo.  
- **Simulation Monte Carlo** : estimation de la probabilité annuelle de respecter le critère contractuel selon la taille du portefeuille.  
- **Résultats** : facteur de surdimensionnement nécessaire entre **1.4 et 1.6** pour garantir 95 % de confiance.  

## Graphiques et interprétation

### 1. Évolution du SOC (`soc_evolution.png`)
- Montre l’évolution de l’état de charge des batteries au fil des 2190 slots.  
- Permet de vérifier :
  - Les batteries ne tombent pas à zéro.  
  - Le SOC reste au-dessus du minimum requis (puissance × durée slot).  
  - L’équilibre charge/décharge fonctionne sur le long terme.  
- Lignes horizontales indiquent le SOC critique et le minimum nécessaire pour fournir un slot FCR.

### 2. Puissance FCR fournie et performance cumulée (`power_delivery.png`)
- Graphe principal pour évaluer la performance :
  - Ligne bleue : puissance réellement fournie par slot.  
  - Ligne rouge en pointillé : objectif contractuel de 10 MW.  
  - Zones vertes : succès (puissance ≥ objectif).  
  - Zones rouges : échec (puissance < objectif).  
- Graphique secondaire : taux de succès cumulatif (%) sur l’année, comparé à la cible de 95 %.

### 3. Contraintes limitantes (`limiting_factors.png`)
- Analyse pourquoi le portefeuille ne fournit pas toujours 10 MW :
  - **Disponibilité** : nombre d’actifs disponibles pour la FCR à chaque slot.  
  - **SOC suffisant** : nombre d’actifs capables de fournir la puissance requise.  
- Comparaison avec le nombre minimum d’actifs requis pour atteindre 10 MW.  
- Barres statistiques : moyenne annuelle et minimum observé pour les deux contraintes.

## Limites de la modélisation
- Disponibilité des batteries supposée **indépendante et stationnaire**, alors qu’elle peut présenter saisonnalité et corrélations dans la réalité.  
- SOC simplifié : **pas de rendement ni de dégradation électrochimique dépendante des cycles**.  
- FCR modélisée comme une **décharge continue sur 4 heures**, approximation conservative du signal réel.  
- Les résultats doivent être considérés comme **des ordres de grandeur robustes**, et non comme une prévision opérationnelle détaillée.
