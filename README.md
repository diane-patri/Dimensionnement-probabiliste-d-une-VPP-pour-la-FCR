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

Cette modélisation repose sur plusieurs hypothèses simplificatrices qui doivent être prises en compte lors de l’interprétation des résultats :

- **Disponibilité des batteries**  
  - Hypothèse : chaque batterie est disponible pour la FCR avec une probabilité fixe (70 %) indépendamment des autres et du temps.  
  - Limite : dans la réalité, la disponibilité peut présenter des **corrélations temporelles** (par exemple plusieurs batteries simultanément sur d’autres marchés) et une **saisonnalité** (variation selon la consommation, la production PV/éolienne ou les périodes de maintenance).  
  - Impact : le facteur de surdimensionnement nécessaire pourrait être sous-estimé si des périodes prolongées de non-disponibilité se produisent.

- **État de charge (SOC)**  
  - Hypothèse : SOC initial et évolution sont simplifiés, avec une décharge constante sur la FCR et une recharge calibrée sur les autres marchés.  
  - Limite : le modèle **ne prend pas en compte** :
    - le rendement de charge/décharge,
    - la dégradation cyclique ou thermique des batteries,
    - la variabilité de SOC due aux cycles réels sur d’autres marchés.  
  - Impact : cela peut conduire à une **surestimation de la capacité réellement utilisable** sur l’année.

- **Modélisation de la FCR**  
  - Hypothèse : la FCR est assimilée à une décharge continue pendant 4 heures à puissance nominale.  
  - Limite : le signal FCR réel est variable et réagit aux fluctuations de fréquence, donc la consommation réelle peut être inférieure ou supérieure à cette approximation.  
  - Impact : le modèle fournit une estimation **conservative** de la sollicitation énergétique.

- **Interactions multi-marchés**  
  - Hypothèse : les 30 % de disponibilité restante sont affectés à d’autres marchés, sans modéliser la stratégie de maximisation de revenu ou les contraintes réseau.  
  - Limite : cela ignore les **interactions dynamiques** entre FCR, aFRR et arbitrage, ainsi que les priorités économiques réelles.  
  - Impact : la probabilité de succès réelle peut différer selon la stratégie opérationnelle adoptée.

- **Approche probabiliste et Monte Carlo**  
  - Hypothèse : les simulations sont basées sur des tirages stochastiques indépendants sur 2190 slots.  
  - Limite : le nombre limité de simulations et l’indépendance des tirages peuvent ne pas capturer certains **événements rares extrêmes** (périodes consécutives de forte indisponibilité).  
  - Impact : le **facteur de surdimensionnement 1.4–1.6** observé doit être considéré comme un ordre de grandeur robuste plutôt qu’une valeur exacte.

En résumé, le modèle fournit un cadre **robuste pour le dimensionnement probabiliste**, mais ne remplace pas une analyse opérationnelle complète tenant compte de la dynamique multi-marchés, des rendements, de la dégradation et de la saisonnalité.

