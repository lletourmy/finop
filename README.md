# SQL Query Optimizer for Snowflake

Application Streamlit pour analyser et optimiser automatiquement les requêtes SQL les plus coûteuses dans Snowflake, en utilisant Snowflake Cortex AI (Claude Sonnet) pour générer des recommandations d'optimisation.

## 📋 Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Architecture](#architecture)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Utilisation](#utilisation)
6. [Dépannage](#dépannage)

---

## Vue d'ensemble

### Fonctionnalités

- ✅ Identification des 20 requêtes les plus coûteuses (30 derniers jours)
- ✅ Affichage des métriques d'exécution et de performance
- ✅ Analyse automatique des schémas et statistiques des tables
- ✅ Génération de recommandations d'optimisation par IA (Claude Sonnet)
- ✅ Support dual : Streamlit in Snowflake (SiS) et développement local

### Cas d'usage

- **Optimisation des coûts** : Identifier les requêtes qui consomment le plus de crédits
- **Amélioration des performances** : Réduire les temps d'exécution
- **Audit de performance** : Analyser l'utilisation des warehouses par utilisateur

---

## Architecture

```
┌─────────────────────────────────────┐
│   User Interface (Streamlit)        │
│            app.py                   │
└─────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────┐
│   Business Logic (QueryOptimizer)   │
│      query_optimizer.py             │
└─────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────┐
│   Data Access (SnowflakeConnector)  │
│     snowflake_connector.py          │
└─────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────┐
│        Snowflake Backend            │
│  - ACCOUNT_USAGE.QUERY_HISTORY      │
│  - INFORMATION_SCHEMA               │
│  - SNOWFLAKE.CORTEX.COMPLETE        │
└─────────────────────────────────────┘
```

### Structure du projet

```
├── app.py                      # Application Streamlit principale
├── snowflake_connector.py      # Connexion et accès aux données
├── query_optimizer.py          # Logique métier et optimisation
├── requirements.txt            # Dépendances Python
└── README.md                   # Documentation
```

### Technologies

- **Python** 3.8+
- **Streamlit** ≥1.28.0
- **Snowflake Connector** ≥3.0.0
- **Pandas** ≥2.0.0

---

## Installation

### Déploiement Streamlit in Snowflake

1. **Créer un stage et uploader les fichiers**
   ```sql
   CREATE STAGE IF NOT EXISTS streamlit_stage;
   PUT file://app.py @streamlit_stage AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
   PUT file://snowflake_connector.py @streamlit_stage AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
   PUT file://query_optimizer.py @streamlit_stage AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
   ```

2. **Créer l'application Streamlit**
   ```sql
   CREATE STREAMLIT sql_query_optimizer
     ROOT_LOCATION = '@streamlit_stage'
     MAIN_FILE = 'app.py'
     QUERY_WAREHOUSE = 'YOUR_WAREHOUSE';
   ```

3. **Accorder les permissions**
   ```sql
   GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE YOUR_ROLE;
   GRANT USAGE ON WAREHOUSE YOUR_WAREHOUSE TO ROLE YOUR_ROLE;
   ```

### Installation locale

1. **Cloner le repository**
   ```bash
   git clone https://github.com/lletourmy/finop.git
   cd finop
   ```

2. **Installer les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurer la connexion** (voir section Configuration)

4. **Lancer l'application**
   ```bash
   streamlit run app.py
   ```

---

## Configuration

### Fichier de configuration local

**Emplacement :** `~/.snowflake/config.toml`

**Format :**
```toml
[dev]
account = "your_account"
user = "your_username"
password = "your_password"
database = "your_database"
schema = "your_schema"
warehouse = "your_warehouse"
role = "your_role"
authenticator = "snowflake"
```

**Sécurité :**
```bash
chmod 600 ~/.snowflake/config.toml
```

### Permissions Snowflake requises

```sql
-- Accès à Account Usage
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE YOUR_ROLE;

-- Accès au warehouse
GRANT USAGE ON WAREHOUSE YOUR_WAREHOUSE TO ROLE YOUR_ROLE;

-- Accès aux bases de données à analyser
GRANT USAGE ON DATABASE YOUR_DATABASE TO ROLE YOUR_ROLE;
GRANT SELECT ON ALL TABLES IN DATABASE YOUR_DATABASE TO ROLE YOUR_ROLE;
```

---

## Utilisation

### Mode Streamlit in Snowflake (SiS)

1. L'application se connecte automatiquement via `st.connection("snowflake")`
2. Cliquez sur "🔄 Actualiser la liste des requêtes"
3. Sélectionnez une requête dans le tableau
4. Cliquez sur "🚀 Analyser cette requête avec l'IA"
5. Consultez les suggestions d'optimisation

### Mode développement local

1. Lancez l'application : `streamlit run app.py`
2. Dans la sidebar, sélectionnez une connexion depuis `config.toml`
3. Cliquez sur "Se connecter"
4. Utilisez l'application comme en mode SiS

---

## Dépannage

### Problèmes de connexion

- **"Connection not available" (SiS)** : Vérifier que vous êtes bien dans SiS et les permissions du rôle
- **"Config file not found" (Local)** : Vérifier `~/.snowflake/config.toml` existe et est bien formaté
- **"Connection failed"** : Vérifier les paramètres de connexion (account, user, password, warehouse)

### Problèmes de données

- **"Aucune requête trouvée"** : 
  - Vérifier les permissions Account Usage : `GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE YOUR_ROLE`
  - Vérifier qu'il y a des requêtes dans les 30 derniers jours
  - Attendre la propagation des données (délai de 45 min pour Account Usage)

- **"Cortex AI error"** : 
  - Vérifier que Cortex AI est activé
  - Vérifier les permissions : `GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE`
  - Essayer un modèle différent (ex: 'claude-3-haiku')

- **"Table metadata not found"** : 
  - Vérifier que la table existe et est accessible
  - Vérifier les permissions SELECT sur la table
  - Vérifier le format du nom (database.schema.table)

### Problèmes de performance

- **Application lente** : Utiliser un warehouse plus grand ou réduire la fenêtre temporelle
- **Timeout IA** : Réduire le nombre de tables analysées ou utiliser un modèle plus rapide

---

## Composants principaux

### SnowflakeConnector (`snowflake_connector.py`)

Gère toutes les interactions avec Snowflake.

**Méthodes principales :**
- `init_connection()` : Initialise la connexion (SiS ou local)
- `execute_query(query, params=None)` : Exécute une requête SQL
- `call_cortex_ai(prompt, model='claude-3-5-sonnet')` : Appelle Cortex AI

### QueryOptimizer (`query_optimizer.py`)

Contient la logique métier d'optimisation.

**Méthodes principales :**
- `get_expensive_queries()` : Récupère les 20 requêtes les plus coûteuses
- `get_query_details(query_id)` : Récupère les détails d'une requête
- `extract_tables_from_sql(sql_text)` : Extrait les tables depuis le SQL
- `get_table_metadata(table_name)` : Récupère les métadonnées d'une table
- `optimize_query(...)` : Génère les recommandations d'optimisation via IA

### Application Streamlit (`app.py`)

Interface utilisateur et orchestration des composants.

**Workflow :**
1. Chargement des requêtes coûteuses
2. Sélection d'une requête dans le tableau
3. Affichage du SQL et métriques
4. Analyse IA avec extraction des tables et génération de recommandations

---

## Sécurité

- **SQL Injection Prevention** : Requêtes paramétrées uniquement
- **Prompt Injection Prevention** : Échappement des apostrophes dans les prompts
- **Credential Management** : 
  - Mode SiS : Authentification native
  - Mode Local : Credentials dans `~/.snowflake/config.toml` (permissions restreintes)
- **Read-Only Operations** : L'application ne fait que des SELECT
- **Network Security** : Connexions HTTPS uniquement

---

## Roadmap

- [ ] Export des recommandations en PDF/CSV
- [ ] Historique des analyses
- [ ] Comparaison avant/après optimisation
- [ ] Dashboard de tendances de performance
- [ ] Alertes automatiques
- [ ] Tests unitaires et CI/CD

---

## Support

- **Repository GitHub** : https://github.com/lletourmy/finop
- **Issues** : https://github.com/lletourmy/finop/issues
- **Documentation Snowflake Cortex AI** : https://docs.snowflake.com/en/user-guide/snowflake-cortex/llm-functions

---

## Licence

Ce projet est sous licence MIT.

---

**Dernière mise à jour :** 2025-12-01  
**Auteur :** Laurent Le Tourmy
