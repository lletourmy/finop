# SQL Query Optimizer for Snowflake

## 📋 Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Architecture](#architecture)
3. [Structure du projet](#structure-du-projet)
4. [Technologies](#technologies)
5. [Composants principaux](#composants-principaux)
6. [Guide d'utilisation](#guide-dutilisation)
7. [Installation et déploiement](#installation-et-déploiement)
8. [Configuration](#configuration)
9. [Développement](#développement)
10. [Dépannage](#dépannage)

---

## Vue d'ensemble

### Description

**SQL Query Optimizer for Snowflake** est une application Streamlit qui permet d'analyser et d'optimiser automatiquement les requêtes SQL les plus coûteuses dans un environnement Snowflake. L'application utilise l'intelligence artificielle via Snowflake Cortex AI (Claude Sonnet) pour générer des recommandations d'optimisation personnalisées.

### Fonctionnalités principales

- ✅ Identification des 20 requêtes les plus coûteuses (30 derniers jours)
- ✅ Affichage détaillé des métriques d'exécution et de performance
- ✅ Analyse automatique des schémas et statistiques des tables
- ✅ Génération de recommandations d'optimisation par IA (Claude Sonnet)
- ✅ Support dual : Streamlit in Snowflake (SiS) et développement local
- ✅ Interface interactive avec sélection de requêtes
- ✅ Suggestions d'optimisation SQL et infrastructure (warehouse)

### Cas d'usage

- **Optimisation des coûts** : Identifier les requêtes qui consomment le plus de crédits
- **Amélioration des performances** : Réduire les temps d'exécution des requêtes lentes
- **Audit de performance** : Analyser l'utilisation des warehouses par utilisateur
- **Formation** : Apprendre les meilleures pratiques SQL sur Snowflake

---

## Architecture

### Architecture en couches

```
┌─────────────────────────────────────────────────────┐
│         User Interface Layer (Streamlit)            │
│                    app.py                           │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│      Business Logic Layer (QueryOptimizer)          │
│               query_optimizer.py                    │
│  - Récupération des requêtes coûteuses             │
│  - Extraction des tables depuis SQL                 │
│  - Construction des prompts IA                      │
│  - Orchestration de l'optimisation                  │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│     Data Access Layer (SnowflakeConnector)          │
│            snowflake_connector.py                   │
│  - Gestion de la connexion Snowflake               │
│  - Exécution de requêtes SQL                        │
│  - Appels à Cortex AI                               │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│              Snowflake Backend                      │
│  - ACCOUNT_USAGE.QUERY_HISTORY                      │
│  - INFORMATION_SCHEMA (COLUMNS, TABLES, etc.)       │
│  - SNOWFLAKE.CORTEX.COMPLETE (Claude Sonnet)        │
└─────────────────────────────────────────────────────┘
```

### Principes de conception

1. **Séparation des préoccupations** : Chaque classe a une responsabilité unique
2. **Injection de dépendances** : QueryOptimizer reçoit SnowflakeConnector
3. **Modularité** : Les classes peuvent être réutilisées indépendamment
4. **Testabilité** : Architecture facilitant les tests unitaires
5. **Maintenabilité** : Code organisé et documenté

---

## Structure du projet

```
finopt/
├── app.py                      # Application Streamlit principale
├── snowflake_connector.py      # Classe de connexion et accès aux données
├── query_optimizer.py          # Classe de logique métier et optimisation
├── requirements.txt            # Dépendances Python
├── CLAUDE.MD                   # Documentation technique (ce fichier)
├── README.md                   # Documentation utilisateur
└── .gitignore                  # Configuration Git
```

### Description des fichiers

| Fichier | Lignes | Description |
|---------|--------|-------------|
| `app.py` | ~200 | Interface utilisateur Streamlit, gestion de l'UI et des interactions |
| `snowflake_connector.py` | ~243 | Connexion Snowflake, exécution SQL, appels Cortex AI |
| `query_optimizer.py` | ~421 | Logique métier : récupération requêtes, métadonnées, prompts IA |
| `requirements.txt` | ~5 | Dépendances : streamlit, snowflake-connector-python, pandas, toml |

---

## Technologies

### Stack technique

| Technologie | Version | Usage |
|-------------|---------|-------|
| **Python** | 3.8+ | Langage principal |
| **Streamlit** | ≥1.28.0 | Framework UI web |
| **Snowflake Connector** | ≥3.0.0 | Connexion à Snowflake |
| **Snowpark Python** | ≥1.0.0 | API Python Snowflake |
| **Pandas** | ≥2.0.0 | Manipulation de données |
| **TOML** | ≥0.10.2 | Parsing fichiers config |

### APIs Snowflake utilisées

- `SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY` - Historique des requêtes
- `INFORMATION_SCHEMA.COLUMNS` - Définitions des colonnes
- `INFORMATION_SCHEMA.TABLES` - Statistiques des tables
- `INFORMATION_SCHEMA.TABLE_CONSTRAINTS` - Contraintes et clés
- `SNOWFLAKE.CORTEX.COMPLETE` - API Cortex AI (Claude Sonnet)

---

## Composants principaux

### 1. SnowflakeConnector (`snowflake_connector.py`)

Classe responsable de toutes les interactions avec Snowflake.

#### Méthodes principales

##### `__init__(connection=None)`
Initialise le connecteur avec une connexion optionnelle.

```python
connector = SnowflakeConnector()
```

##### `load_config_file()` - Static, Cached
Charge les configurations depuis `~/.snowflake/config.toml`.

**Retourne :** `Dict` - Dictionnaire des connexions disponibles

##### `create_connection(_conn_params)` - Static, Cached
Crée une connexion Snowflake avec les paramètres fournis.

**Paramètres :**
- `_conn_params` (Dict) : Paramètres de connexion (account, user, password, etc.)

**Retourne :** `SnowflakeConnectionWrapper` - Connexion encapsulée

##### `init_connection()`
Initialise la connexion en mode SiS ou local.

**Comportement :**
- **Mode SiS** : Utilise `st.connection("snowflake")`
- **Mode Local** : Affiche UI de sélection de connexion depuis config.toml

**Retourne :** Objet de connexion Snowflake

##### `get_connection()`
Retourne la connexion active courante.

##### `execute_query(query, params=None)`
Exécute une requête SQL et retourne un DataFrame pandas.

**Paramètres :**
- `query` (str) : Requête SQL à exécuter
- `params` (tuple, optional) : Paramètres pour requête paramétrée

**Retourne :** `pd.DataFrame` - Résultats de la requête

**Fonctionnalités :**
- Normalisation des noms de colonnes en minuscules
- Support des requêtes paramétrées (protection SQL injection)
- Gestion d'erreurs avec messages Streamlit

##### `call_cortex_ai(prompt, model='claude-3-5-sonnet')`
Appelle Snowflake Cortex AI avec un prompt.

**Paramètres :**
- `prompt` (str) : Texte du prompt pour l'IA
- `model` (str) : Nom du modèle Cortex AI

**Retourne :** `str` - Réponse générée par l'IA

---

### 2. QueryOptimizer (`query_optimizer.py`)

Classe contenant toute la logique métier d'optimisation de requêtes.

#### Méthodes principales

##### `__init__(connector: SnowflakeConnector)`
Initialise l'optimiseur avec une instance de SnowflakeConnector.

```python
optimizer = QueryOptimizer(connector)
```

##### `get_expensive_queries()`
Récupère les 20 requêtes les plus coûteuses des 30 derniers jours.

**Retourne :** `pd.DataFrame` avec les colonnes :
- `warehouse_name` : Nom du warehouse
- `warehouse_size` : Taille du warehouse
- `user_name` : Utilisateur ayant exécuté la requête
- `cnt` : Nombre d'exécutions
- `sample_query_id` : ID de la requête la plus longue
- `sample_query_text` : Texte SQL de la requête
- `min_start_time` : Première exécution
- `max_end_time` : Dernière exécution
- `duration_seconds` : Durée totale en secondes
- `duration_hours` : Durée totale en heures
- `cost_factor` : Facteur de coût (durée × taille warehouse)

**Logique SQL :**
- Partition par warehouse et utilisateur
- Ranking par temps d'exécution total
- Top 20 par warehouse
- Calcul du facteur de coût basé sur la taille du warehouse

##### `get_query_details(query_id)`
Récupère les détails complets d'une requête spécifique.

**Paramètres :**
- `query_id` (str) : ID de la requête

**Retourne :** `pd.DataFrame` avec métriques détaillées :
- Temps de compilation/exécution
- Bytes scannés/spillés
- Partitions scannées
- Lignes produites/insérées/mises à jour

##### `extract_tables_from_sql(sql_text)` - Static
Extrait les noms de tables depuis le texte SQL.

**Paramètres :**
- `sql_text` (str) : Code SQL à analyser

**Retourne :** `List[str]` - Liste des tables identifiées

**Patterns supportés :**
- `FROM table_name`
- `JOIN table_name`
- `INTO table_name`
- `UPDATE table_name`
- Support formats : `database.schema.table`, `schema.table`, `table`

##### `get_table_metadata(table_name)`
Récupère les métadonnées complètes d'une table.

**Paramètres :**
- `table_name` (str) : Nom de la table

**Retourne :** `Dict` avec :
- `columns` : Liste des colonnes (name, type, nullable, default, comment)
- `statistics` : Statistiques (row_count, bytes, retention_time, created, last_altered)
- `constraints` : Contraintes (primary keys, foreign keys, etc.)

##### `build_optimization_prompt(query_text, execution_metadata, tables_metadata)`
Construit le prompt structuré pour Cortex AI.

**Paramètres :**
- `query_text` (str) : Code SQL de la requête
- `execution_metadata` (Dict) : Métriques d'exécution
- `tables_metadata` (Dict) : Métadonnées des tables utilisées

**Retourne :** `str` - Prompt formaté pour l'IA

**Structure du prompt :**
1. Contexte : Expert en optimisation SQL Snowflake
2. Requête SQL à analyser
3. Métadonnées d'exécution (durée, warehouse, coût)
4. Métadonnées des tables (colonnes, stats, contraintes)
5. Instructions structurées :
   - Optimisations SQL (rewrites, JOINs, WHERE, clustering)
   - Optimisations warehouse (taille, multi-clustering, auto-suspend)
   - Optimisations générales (performance, coûts, best practices)

##### `optimize_query(query_text, execution_metadata, tables_metadata, model='claude-3-5-sonnet')`
Méthode principale d'orchestration de l'optimisation.

**Paramètres :**
- `query_text` (str) : SQL à optimiser
- `execution_metadata` (Dict) : Contexte d'exécution
- `tables_metadata` (Dict) : Informations sur les tables
- `model` (str) : Modèle IA à utiliser

**Retourne :** `str` - Suggestions d'optimisation générées par l'IA

**Workflow :**
1. Construction du prompt via `build_optimization_prompt()`
2. Appel à Cortex AI via `connector.call_cortex_ai()`
3. Retour des suggestions formatées

---

### 3. Application Streamlit (`app.py`)

Interface utilisateur et orchestration des composants.

#### Structure de l'application

##### Initialisation
```python
# Configuration de la page
st.set_page_config(
    page_title="SQL Query Optimizer",
    page_icon="🔍",
    layout="wide"
)

# Initialisation des composants
connector = SnowflakeConnector()
conn = connector.init_connection()
optimizer = QueryOptimizer(connector)
```

##### Interface principale

**1. Section de chargement des données**
- Bouton "🔄 Actualiser la liste des requêtes"
- Appel à `optimizer.get_expensive_queries()`
- Stockage dans `st.session_state['df_queries']`
- Conversion des types de données (numeric, datetime)

**2. Layout deux colonnes**

**Colonne gauche :**
- Dataframe interactif avec colonnes : `warehouse_name`, `warehouse_size`, `user_name`, `cnt`, `duration_seconds`
- Sélection de lignes via `on_select="rerun"`
- Affichage de toutes les lignes sans pagination

**Colonne droite :**
- Métriques : Facteur de coût, première/dernière exécution
- Code SQL avec coloration syntaxique
- Bouton "🚀 Analyser cette requête avec l'IA"

**3. Section d'analyse IA (pleine largeur sous les colonnes)**
- Tables identifiées
- Suggestions d'optimisation de Cortex AI
- Stockage dans `st.session_state['ai_analysis']`

#### Workflow d'analyse

1. Utilisateur clique sur une ligne du dataframe
2. Détails SQL affichés dans colonne droite
3. Utilisateur clique sur "Analyser cette requête avec l'IA"
4. Extraction des tables : `optimizer.extract_tables_from_sql()`
5. Récupération métadonnées : `optimizer.get_table_metadata()` pour chaque table
6. Construction des métadonnées d'exécution depuis la ligne sélectionnée
7. Optimisation : `optimizer.optimize_query()`
8. Affichage des résultats en-dessous des colonnes

---

## Guide d'utilisation

### Mode Streamlit in Snowflake (SiS)

1. **Connexion automatique**
   - L'application se connecte automatiquement via `st.connection("snowflake")`
   - Message de confirmation affiché : "✅ Connecté via Streamlit in Snowflake"

2. **Chargement des requêtes**
   - Cliquez sur "🔄 Actualiser la liste des requêtes"
   - Les 20 requêtes les plus coûteuses s'affichent

3. **Sélection et analyse**
   - Cliquez sur une ligne du tableau
   - Le code SQL apparaît dans la colonne droite
   - Cliquez sur "🚀 Analyser cette requête avec l'IA"
   - Les suggestions d'optimisation s'affichent en-dessous

### Mode développement local

1. **Configuration**
   - Créez le fichier `~/.snowflake/config.toml`
   - Ajoutez vos connexions (voir section Configuration)

2. **Lancement**
   - Exécutez : `streamlit run app.py`
   - Message : "📌 Mode développement local - Connexion depuis config.toml"

3. **Connexion**
   - Dans la sidebar, sélectionnez une connexion
   - Vérifiez les paramètres affichés
   - Cliquez sur "Se connecter"
   - Message de succès : "✅ Connecté avec succès"

4. **Utilisation**
   - Même workflow que le mode SiS

---

## Installation et déploiement

### Déploiement Streamlit in Snowflake

#### Prérequis
- Compte Snowflake avec accès à Account Usage
- Cortex AI activé
- Streamlit in Snowflake disponible
- Permissions appropriées (voir section Permissions)

#### Étapes de déploiement

1. **Uploader les fichiers**
   ```sql
   -- Créer un stage
   CREATE STAGE IF NOT EXISTS streamlit_stage;

   -- Uploader les fichiers Python
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

4. **Lancer l'application**
   - Interface Snowflake UI → Streamlit → Votre application

### Installation locale

#### Prérequis
- Python 3.8 ou supérieur
- pip installé

#### Étapes d'installation

1. **Cloner le repository**
   ```bash
   git clone https://github.com/lletourmy/finop.git
   cd finop
   ```

2. **Créer un environnement virtuel (recommandé)**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # ou
   venv\Scripts\activate  # Windows
   ```

3. **Installer les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurer la connexion** (voir section Configuration)

5. **Lancer l'application**
   ```bash
   streamlit run app.py
   ```

6. **Accéder à l'application**
   - Ouvrir le navigateur à l'adresse affichée (généralement `http://localhost:8501`)

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
client_session_keep_alive = true

[prod]
account = "prod_account"
user = "prod_username"
password = "prod_password"
database = "prod_database"
schema = "prod_schema"
warehouse = "prod_warehouse"
role = "prod_role"
```

**Paramètres :**
- `account` : Nom du compte Snowflake (sans `.snowflakecomputing.com`)
- `user` : Nom d'utilisateur
- `password` : Mot de passe ou token JWT
- `database` : Base de données par défaut
- `schema` : Schéma par défaut
- `warehouse` : Warehouse à utiliser
- `role` : Rôle à utiliser
- `authenticator` : Méthode d'authentification (défaut: "snowflake")
- `client_session_keep_alive` : Garder la session active (défaut: false)

**Sécurité :**
```bash
# Restreindre les permissions du fichier
chmod 600 ~/.snowflake/config.toml
```

### Permissions Snowflake requises

```sql
-- Accès à Account Usage pour l'historique des requêtes
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE YOUR_ROLE;

-- Accès à Information Schema (généralement déjà disponible)
-- GRANT USAGE ON SCHEMA INFORMATION_SCHEMA TO ROLE YOUR_ROLE;

-- Accès au warehouse
GRANT USAGE ON WAREHOUSE YOUR_WAREHOUSE TO ROLE YOUR_ROLE;

-- Accès aux bases de données à analyser
GRANT USAGE ON DATABASE YOUR_DATABASE TO ROLE YOUR_ROLE;
GRANT USAGE ON ALL SCHEMAS IN DATABASE YOUR_DATABASE TO ROLE YOUR_ROLE;

-- Lecture des tables (pour métadonnées)
GRANT SELECT ON ALL TABLES IN DATABASE YOUR_DATABASE TO ROLE YOUR_ROLE;
```

---

## Développement

### Design patterns utilisés

| Pattern | Usage | Exemple |
|---------|-------|---------|
| **Class-Based Architecture** | Séparation des préoccupations | SnowflakeConnector (data), QueryOptimizer (business) |
| **Dependency Injection** | Couplage faible | QueryOptimizer reçoit SnowflakeConnector |
| **Caching** | Optimisation performance | `@st.cache_resource`, `@st.cache_data` |
| **Lazy Loading** | Chargement à la demande | Métadonnées des tables chargées au clic |
| **Static Methods** | Fonctions utilitaires | `extract_tables_from_sql()` |

### Conventions de code

- **Type Hints** : Utilisés pour tous les paramètres et retours
- **Docstrings** : Format Google pour toutes les méthodes publiques
- **Nomenclature** :
  - Classes : PascalCase (`SnowflakeConnector`)
  - Méthodes/fonctions : snake_case (`get_expensive_queries`)
  - Constantes : UPPER_CASE (si nécessaire)
- **Langue** : UI en français, code et commentaires en anglais
- **Normalisation SQL** : Colonnes toujours en minuscules
- **Gestion d'erreurs** : Try-except avec messages Streamlit user-friendly

### Patterns SQL

- **Requêtes paramétrées** : `?` placeholders avec `execute(query, params)`
- **Window Functions** : `ROW_NUMBER() OVER (PARTITION BY ...)`
- **CTEs** : `WITH` pour requêtes complexes
- **Noms qualifiés** : Support `database.schema.table`

### Ajouter une nouvelle fonctionnalité

#### Exemple : Ajouter une nouvelle métrique

1. **Modifier QueryOptimizer**
   ```python
   # Dans query_optimizer.py
   def get_expensive_queries(self):
       query = """
       ...
       , NEW_METRIC_COLUMN
       FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
       ...
       """
   ```

2. **Mettre à jour l'UI**
   ```python
   # Dans app.py
   table_display_df = display_df[[
       'warehouse_name',
       'warehouse_size',
       'user_name',
       'cnt',
       'duration_seconds',
       'new_metric'  # Ajouter la nouvelle colonne
   ]].copy()
   ```

3. **Tester**
   - Tester en local
   - Tester en SiS
   - Vérifier les types de données

#### Exemple : Changer le modèle IA

```python
# Dans query_optimizer.py, méthode optimize_query()
def optimize_query(
    self,
    query_text: str,
    execution_metadata: Dict[str, Any],
    tables_metadata: Dict[str, Dict[str, Any]],
    model: str = 'claude-3-opus'  # Modifier ici
) -> Optional[str]:
```

#### Exemple : Ajouter une méthode au connecteur

```python
# Dans snowflake_connector.py
def execute_batch_queries(self, queries: List[str]) -> List[pd.DataFrame]:
    """
    Exécute plusieurs requêtes en batch

    Args:
        queries: Liste de requêtes SQL

    Returns:
        Liste de DataFrames avec les résultats
    """
    results = []
    for query in queries:
        df = self.execute_query(query)
        results.append(df)
    return results
```

### Tests

#### Structure de tests (recommandée)

```
tests/
├── test_snowflake_connector.py
├── test_query_optimizer.py
└── test_integration.py
```

#### Exemple de test unitaire

```python
import pytest
from snowflake_connector import SnowflakeConnector
from query_optimizer import QueryOptimizer

def test_extract_tables_from_sql():
    sql = "SELECT * FROM database.schema.table1 JOIN table2"
    tables = QueryOptimizer.extract_tables_from_sql(sql)
    assert 'database.schema.table1' in tables
    assert 'table2' in tables
```

---

## Dépannage

### Problèmes de connexion

#### "Connection not available" (Mode SiS)
**Cause :** L'application ne détecte pas l'environnement Streamlit in Snowflake

**Solutions :**
- Vérifier que vous êtes bien dans SiS (pas en local)
- Vérifier que `st.connection("snowflake")` est supporté dans votre version
- Vérifier les permissions du rôle

#### "Config file not found" (Mode Local)
**Cause :** Fichier `~/.snowflake/config.toml` absent ou mal placé

**Solutions :**
- Vérifier le chemin : `ls ~/.snowflake/config.toml`
- Créer le fichier si absent (voir section Configuration)
- Vérifier la syntaxe TOML

#### "Connection failed" (Mode Local)
**Cause :** Paramètres de connexion incorrects

**Solutions :**
- Vérifier le nom du compte (sans `.snowflakecomputing.com`)
- Vérifier username/password
- Vérifier que le warehouse existe et est accessible
- Tester la connexion avec SnowSQL : `snowsql -a account -u user`

#### "No connections available"
**Cause :** Fichier config.toml vide ou mal formaté

**Solutions :**
- Vérifier qu'il y a au moins une section `[connection_name]`
- Valider la syntaxe TOML : https://www.toml.io/en/

### Problèmes de données

#### "Aucune requête trouvée"
**Cause :** Pas de requêtes dans les 30 derniers jours ou pas d'accès à Account Usage

**Solutions :**
- Vérifier les permissions : `GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE YOUR_ROLE`
- Vérifier qu'il y a des requêtes dans Account Usage :
  ```sql
  SELECT COUNT(*)
  FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
  WHERE START_TIME > DATEADD(DAY, -30, CURRENT_TIMESTAMP());
  ```
- Attendre la propagation des données (Account Usage a un délai de 45 min)

#### "Cortex AI error"
**Cause :** Cortex AI non activé ou quota dépassé

**Solutions :**
- Vérifier que Cortex AI est activé : contacter votre administrateur Snowflake
- Vérifier le quota : `SHOW PARAMETERS LIKE 'CORTEX%'`
- Vérifier les permissions : `GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE`
- Essayer avec un modèle différent (ex: 'claude-3-haiku')

#### "Table metadata not found"
**Cause :** Table non accessible ou nom incorrect

**Solutions :**
- Vérifier que la table existe : `SHOW TABLES LIKE 'table_name'`
- Vérifier les permissions SELECT sur la table
- Vérifier le format du nom (database.schema.table)
- Le schema/database courant doit avoir accès à la table

### Problèmes de performance

#### "Application lente au chargement"
**Cause :** Requêtes lourdes ou grand nombre de données

**Solutions :**
- Utiliser un warehouse plus grand
- Réduire la fenêtre temporelle (modifier de 30 à 7 jours dans le SQL)
- Vérifier qu'il n'y a pas de spilling : regarder les métriques de la requête

#### "Timeout lors de l'appel IA"
**Cause :** Prompt trop long ou modèle surchargé

**Solutions :**
- Réduire le nombre de tables analysées
- Limiter les métadonnées incluses dans le prompt
- Essayer un modèle plus rapide (haiku au lieu de sonnet)

### Erreurs courantes

#### CachedWidgetWarning
**Cause :** Widgets Streamlit dans une fonction cachée

**Solution :** Ne pas utiliser `@st.cache_*` sur des fonctions contenant des widgets

#### KeyError sur colonnes DataFrame
**Cause :** Snowflake retourne des colonnes en majuscules

**Solution :** Toujours normaliser : `df.columns = df.columns.str.lower()`

#### TypeError sur types de données
**Cause :** Snowflake retourne des types non-pandas

**Solution :** Convertir avec `pd.to_numeric()`, `pd.to_datetime()`, etc.

---

## Sécurité

### Considérations de sécurité

1. **SQL Injection Prevention**
   - Toutes les requêtes utilisent des paramètres bindés : `execute(query, params)`
   - Pas de concatenation de strings pour construire le SQL

2. **Prompt Injection Prevention**
   - Les apostrophes sont échappées dans les prompts : `replace("'", "''")`
   - Le SQL utilisateur est encapsulé dans des blocs markdown

3. **Credential Management**
   - **Mode SiS** : Authentification native, pas de credentials stockés
   - **Mode Local** : Credentials dans `~/.snowflake/config.toml`
     - Fichier avec permissions restreintes (`chmod 600`)
     - Pas de stockage en clair dans le code
     - Passwords jamais affichés dans l'UI

4. **Read-Only Operations**
   - L'application ne fait que des SELECT
   - Pas de INSERT, UPDATE, DELETE, DROP
   - Pas de modification de données

5. **Network Security**
   - Connexions HTTPS uniquement vers Snowflake
   - Pas d'exposition de ports (sauf Streamlit en local)

### Bonnes pratiques

- Ne jamais commiter `config.toml` dans git
- Utiliser des tokens JWT au lieu de passwords en production
- Appliquer le principe du moindre privilège pour le rôle Snowflake
- Auditer régulièrement les accès avec Account Usage
- Utiliser des secrets managers pour stocker les credentials (AWS Secrets Manager, Azure Key Vault, etc.)

---

## Roadmap et améliorations futures

### Fonctionnalités envisagées

- [ ] Export des recommandations en PDF/CSV
- [ ] Historique des analyses (stockage persistent)
- [ ] Comparaison avant/après optimisation
- [ ] Support multi-langues (i18n)
- [ ] Dashboard de tendances de performance
- [ ] Alertes automatiques pour requêtes dégradées
- [ ] Intégration avec Slack/Teams pour notifications
- [ ] Tests unitaires et CI/CD
- [ ] Support de modèles IA alternatifs
- [ ] Analyse de requêtes en temps réel

### Limitations connues

- Extraction de tables basée sur regex (peut manquer CTEs complexes)
- Langue UI uniquement en français
- Pas de stockage persistent des analyses
- Dépendance à la disponibilité de Cortex AI
- Délai de 45 minutes pour Account Usage

---

## Contribuer

### Comment contribuer

1. Fork le repository
2. Créer une branche feature : `git checkout -b feature/ma-fonctionnalite`
3. Commiter les changements : `git commit -m "Ajout de ma fonctionnalité"`
4. Pusher vers la branche : `git push origin feature/ma-fonctionnalite`
5. Ouvrir une Pull Request

### Guidelines

- Respecter les conventions de code
- Ajouter des docstrings pour toutes les nouvelles méthodes
- Tester en mode SiS et local avant de soumettre
- Mettre à jour la documentation (CLAUDE.MD)

---

## Support et contact

### Resources

- **Repository GitHub** : https://github.com/lletourmy/finop
- **Issues** : https://github.com/lletourmy/finop/issues
- **Documentation Snowflake Cortex AI** : https://docs.snowflake.com/en/user-guide/snowflake-cortex/llm-functions
- **Documentation Streamlit** : https://docs.streamlit.io/

---

## Licence

Ce projet est sous licence MIT. Voir le fichier LICENSE pour plus de détails.

---

## Changelog

### Version 2.0.0 (2025-12-01)
- ✨ Refactoring complet en architecture classe-based
- ✨ Création de SnowflakeConnector et QueryOptimizer
- ✨ Amélioration de la modularité et testabilité
- ✨ Documentation complète réécrite
- 🐛 Correction du CachedWidgetWarning
- 🎨 Interface améliorée avec layout deux colonnes
- 🎨 Affichage des recommandations IA en pleine largeur

### Version 1.0.0 (2025-11-30)
- 🎉 Version initiale
- ✨ Support dual SiS et local
- ✨ Intégration Cortex AI
- ✨ Analyse des requêtes coûteuses
- ✨ Génération de recommandations

---

**Dernière mise à jour :** 2025-12-01
**Branche courante :** kind-euler
**Auteur :** Laurent Le Tourmy
