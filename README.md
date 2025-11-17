# SQL Query Optimizer - Streamlit in Snowflake

Application Streamlit déployée dans Snowflake pour analyser et optimiser les requêtes SQL les plus coûteuses en utilisant Cortex AI (Claude Sonnet).

## 🎯 Fonctionnalités

- **Identification des requêtes coûteuses** : Récupère automatiquement les 20 requêtes SQL les plus coûteuses des 30 derniers jours
- **Analyse détaillée** : Pour chaque requête sélectionnée, affiche :
  - Le code SQL complet
  - Les métadonnées d'exécution (durée, bytes scannés, partitions, etc.)
  - Les métadonnées des tables utilisées (colonnes, types, statistiques)
- **Optimisation par IA** : Utilise Cortex AI (Claude Sonnet) pour générer des suggestions d'optimisation :
  - Optimisations SQL (réécriture, JOINs, WHERE clauses, etc.)
  - Optimisations liées au Warehouse (taille, multi-clustering, auto-suspend)
  - Meilleures pratiques Snowflake

## 📋 Prérequis

- Compte Snowflake avec accès à :
  - `SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY`
  - `INFORMATION_SCHEMA` pour les métadonnées des tables
  - Cortex AI activé (fonction `SNOWFLAKE.CORTEX.COMPLETE`)
- Streamlit in Snowflake activé dans votre compte

## 🚀 Déploiement

### Option 1 : Via Snowsight (Interface Web Snowflake)

1. Connectez-vous à Snowsight
2. Allez dans **Apps** > **Streamlit**
3. Cliquez sur **Create** > **From scratch**
4. Nommez votre application (ex: "SQL Query Optimizer")
5. Copiez le contenu de `app.py` dans l'éditeur
6. Cliquez sur **Run** pour tester
7. Cliquez sur **Share** pour déployer

### Option 2 : Via SnowSQL ou Snowflake CLI

```sql
-- Créer un stage pour stocker l'application
CREATE STAGE IF NOT EXISTS apps_stage;

-- Uploader le fichier app.py
PUT file:///path/to/app.py @apps_stage;

-- Créer l'application Streamlit
CREATE STREAMLIT sql_query_optimizer
  ROOT_LOCATION = '@apps_stage'
  MAIN_FILE = 'app.py'
  QUERY_WAREHOUSE = 'YOUR_WAREHOUSE';
```

## 📖 Utilisation

1. **Lancer l'application** : Ouvrez l'application Streamlit depuis Snowsight
2. **Actualiser la liste** : Cliquez sur le bouton "🔄 Actualiser la liste" pour charger les requêtes coûteuses
3. **Sélectionner une requête** : Choisissez une requête dans la liste déroulante
4. **Analyser** : Cliquez sur "🚀 Analyser cette requête"
5. **Consulter les suggestions** : Les suggestions d'optimisation apparaissent dans la section "✨ Suggestions d'optimisation"

## 🔍 Requête SQL utilisée

L'application utilise la requête suivante pour identifier les requêtes les plus coûteuses :

```sql
with recent_queries AS (
    SELECT
        warehouse_name,
        warehouse_size,
        user_name,
        sum(total_elapsed_time) as total_elapsed_time,
        count(*) as cnt,
        ROW_NUMBER() OVER (
            PARTITION BY warehouse_name
            ORDER BY sum(total_elapsed_time) DESC
        ) AS rank    
    FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
    WHERE
        warehouse_name IS NOT NULL
        AND execution_status = 'SUCCESS'
        AND START_TIME > DATEADD(DAY, -30, CURRENT_TIMESTAMP())
    group by 1, 2, 3
)
SELECT
    warehouse_name,
    warehouse_size,
    user_name,
    cnt,
    total_elapsed_time / 1000 AS duration_seconds,
    total_elapsed_time / 1000 / 60 / 24 AS duration_hours,
    total_elapsed_time / 1000 / 60 / 24 * 
        CASE 
            WHEN warehouse_size = 'X-Small' THEN 1 
            WHEN warehouse_size = 'Small' THEN 2 
            WHEN warehouse_size = 'Medium' THEN 4 
            WHEN warehouse_size = 'Large' THEN 8 
            WHEN warehouse_size = 'X-Large' THEN 16 
            WHEN warehouse_size = '2X-Large' THEN 32
            ELSE 1
        END AS cost_factor
FROM recent_queries
WHERE rank <= 20
ORDER BY duration_seconds DESC;
```

## 🛠️ Structure du code

- **`get_expensive_queries()`** : Retourne la requête SQL pour récupérer les requêtes coûteuses
- **`get_query_text_by_user_warehouse()`** : Récupère le texte SQL et les métadonnées d'une requête spécifique
- **`extract_tables_from_sql()`** : Extrait les noms de tables depuis le texte SQL
- **`get_table_metadata()`** : Récupère les métadonnées complètes d'une table (colonnes, statistiques, contraintes)
- **`call_cortex_ai()`** : Appelle Cortex AI avec le prompt complet pour obtenir des suggestions d'optimisation

## 📝 Notes importantes

- L'application nécessite des privilèges sur `SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY`
- Cortex AI doit être activé dans votre compte Snowflake
- Les métadonnées des tables sont récupérées depuis `INFORMATION_SCHEMA`
- L'extraction des tables depuis le SQL utilise des expressions régulières et peut nécessiter des ajustements selon vos conventions de nommage

## 🔒 Permissions requises

```sql
-- Accès à l'historique des requêtes
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE YOUR_ROLE;

-- Accès à INFORMATION_SCHEMA (généralement déjà disponible)
-- Accès à Cortex AI (vérifier avec votre administrateur Snowflake)
```

## 🐛 Dépannage

### Erreur : "Connexion Snowflake non disponible"
- Assurez-vous d'exécuter l'application dans Streamlit in Snowflake, pas en local
- Vérifiez que la connexion `st.connection("snowflake")` est configurée

### Erreur : "Cortex AI non disponible"
- Vérifiez que Cortex AI est activé dans votre compte Snowflake
- Contactez votre administrateur pour activer l'accès à `SNOWFLAKE.CORTEX.COMPLETE`

### Erreur : "Aucune table identifiée"
- L'extraction des tables utilise des regex qui peuvent ne pas couvrir tous les cas
- Vérifiez le format de vos requêtes SQL

## 📚 Ressources

- [Documentation Streamlit in Snowflake](https://docs.snowflake.com/en/developer-guide/streamlit/)
- [Documentation Cortex AI](https://docs.snowflake.com/en/developer-guide/snowflake-cortex/)
- [Snowflake Account Usage](https://docs.snowflake.com/en/sql-reference/account-usage.html)

## 📄 Licence

Ce projet est fourni tel quel pour usage interne.

