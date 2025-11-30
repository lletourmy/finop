import streamlit as st
import pandas as pd
import json
from typing import Dict, List
import re
import toml
import os
from pathlib import Path
import snowflake.connector

# Configuration de la page
st.set_page_config(
    page_title="SQL Query Optimizer",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 SQL Query Optimizer")
st.markdown("Analysez et optimisez vos requêtes SQL les plus coûteuses avec l'IA")

# Initialisation de la session Snowflake
@st.cache_data
def load_snowflake_config():
    """Charge les connexions disponibles depuis ~/.snowflake/config.toml"""
    config_path = Path.home() / '.snowflake' / 'config.toml'
    if config_path.exists():
        try:
            config = toml.load(config_path)
            return config
        except Exception as e:
            return None
    return None

@st.cache_resource
def create_snowflake_connection(_conn_params):
    """Crée une connexion Snowflake avec les paramètres fournis"""
    conn = snowflake.connector.connect(
        account=_conn_params.get('account'),
        user=_conn_params.get('user'),
        password=_conn_params.get('password'),
        database=_conn_params.get('database'),
        schema=_conn_params.get('schema'),
        warehouse=_conn_params.get('warehouse'),
        role=_conn_params.get('role'),
        authenticator=_conn_params.get('authenticator', 'snowflake'),
        client_session_keep_alive=_conn_params.get('client_session_keep_alive', False)
    )

    # Wrapper pour compatibilité avec l'API Streamlit
    class SnowflakeConnectionWrapper:
        def __init__(self, conn):
            self._conn = conn

        def cursor(self):
            return self._conn.cursor()

        def close(self):
            return self._conn.close()

    return SnowflakeConnectionWrapper(conn)

def init_session():
    """Initialise la session Snowflake depuis Streamlit in Snowflake ou local"""

    # Vérifier si déjà connecté en mode local
    if 'snowflake_connection' in st.session_state:
        return st.session_state['snowflake_connection']

    # Tenter d'abord la connexion Streamlit in Snowflake
    try:
        conn = st.connection("snowflake")
        if 'sis_mode_confirmed' not in st.session_state:
            st.success("✅ Connecté via Streamlit in Snowflake")
            st.session_state['sis_mode_confirmed'] = True
        return conn
    except Exception as e:
        # Fallback pour développement local
        if 'local_mode_shown' not in st.session_state:
            st.info("📌 Mode développement local - Connexion depuis config.toml")
            st.session_state['local_mode_shown'] = True

        # Charger les connexions disponibles
        config = load_snowflake_config()
        if not config:
            st.error("❌ Fichier ~/.snowflake/config.toml non trouvé ou invalide")
            return None

        # Extraire les noms de connexion
        connection_names = list(config.keys())
        if not connection_names:
            st.error("❌ Aucune connexion trouvée dans config.toml")
            return None

        # Sélection de la connexion via Streamlit
        st.sidebar.header("🔌 Configuration de connexion")
        selected_connection = st.sidebar.selectbox(
            "Choisir une connexion:",
            connection_names,
            index=0,
            key="connection_selector"
        )

        if not selected_connection:
            return None

        # Récupérer les paramètres de connexion
        conn_params = config[selected_connection]

        # Afficher les détails de connexion (sans le mot de passe)
        st.sidebar.info(f"""
        **Connexion sélectionnée:** {selected_connection}
        - **Account:** {conn_params.get('account', 'N/A')}
        - **User:** {conn_params.get('user', 'N/A')}
        - **Database:** {conn_params.get('database', 'N/A')}
        - **Schema:** {conn_params.get('schema', 'N/A')}
        - **Warehouse:** {conn_params.get('warehouse', 'N/A')}
        - **Role:** {conn_params.get('role', 'N/A')}
        """)

        # Bouton pour se connecter
        if st.sidebar.button("🔗 Se connecter", key="connect_button"):
            try:
                # Créer la connexion Snowflake via fonction cachée
                wrapped_conn = create_snowflake_connection(conn_params)
                st.sidebar.success(f"✅ Connecté à {selected_connection}")
                st.session_state['snowflake_connection'] = wrapped_conn
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"❌ Erreur de connexion: {e}")
                return None

        st.warning("⚠️ Veuillez cliquer sur 'Se connecter' dans la barre latérale")
        return None

def get_expensive_queries():
    """Récupère les requêtes SQL les plus coûteuses"""
    query = """
    WITH query_details AS (
        SELECT
            warehouse_name,
            warehouse_size,
            user_name,
            query_id,
            query_text,
            total_elapsed_time,
            start_time,
            end_time,
            -- Identifier la requête la plus longue par combinaison warehouse/user
            ROW_NUMBER() OVER (
                PARTITION BY warehouse_name, user_name
                ORDER BY total_elapsed_time DESC
            ) AS query_rank
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE
            warehouse_name IS NOT NULL
            AND execution_status = 'SUCCESS'
            AND START_TIME > DATEADD(DAY, -30, CURRENT_TIMESTAMP())
    ),
    aggregated_queries AS (
        SELECT
            warehouse_name,
            warehouse_size,
            user_name,
            SUM(total_elapsed_time) as total_elapsed_time,
            COUNT(*) as cnt,
            -- Prendre le QUERY_ID et QUERY_TEXT de la requête la plus longue
            MAX(CASE WHEN query_rank = 1 THEN query_id END) as sample_query_id,
            MAX(CASE WHEN query_rank = 1 THEN query_text END) as sample_query_text,
            -- Min et Max des dates d'exécution
            MIN(start_time) as min_start_time,
            MAX(end_time) as max_end_time,
            ROW_NUMBER() OVER (
                PARTITION BY warehouse_name
                ORDER BY SUM(total_elapsed_time) DESC
            ) AS rank
        FROM query_details
        GROUP BY warehouse_name, warehouse_size, user_name
    )
    SELECT
        warehouse_name,
        warehouse_size,
        user_name,
        cnt,
        sample_query_id,
        sample_query_text,
        min_start_time,
        max_end_time,
        total_elapsed_time / 1000 AS duration_seconds,
        total_elapsed_time / 1000 / 60 / 60 AS duration_hours,
        total_elapsed_time / 1000 / 60 / 60 *
            CASE
                WHEN warehouse_size = 'X-Small' THEN 1
                WHEN warehouse_size = 'Small' THEN 2
                WHEN warehouse_size = 'Medium' THEN 4
                WHEN warehouse_size = 'Large' THEN 8
                WHEN warehouse_size = 'X-Large' THEN 16
                WHEN warehouse_size = '2X-Large' THEN 32
                ELSE 1
            END AS cost_factor
    FROM aggregated_queries
    WHERE rank <= 20
    ORDER BY duration_seconds DESC
    """
    return query

def get_query_details(query_id: str, conn):
    """Récupère les détails d'une requête spécifique"""
    query = """
    SELECT
        QUERY_ID,
        QUERY_TEXT,
        QUERY_TYPE,
        WAREHOUSE_NAME,
        WAREHOUSE_SIZE,
        USER_NAME,
        ROLE_NAME,
        DATABASE_NAME,
        SCHEMA_NAME,
        TOTAL_ELAPSED_TIME / 1000 AS duration_seconds,
        BYTES_SCANNED,
        BYTES_SPILLED_TO_LOCAL_STORAGE,
        BYTES_SPILLED_TO_REMOTE_STORAGE,
        PARTITIONS_SCANNED,
        PARTITIONS_TOTAL,
        ROWS_PRODUCED,
        ROWS_INSERTED,
        ROWS_UPDATED,
        ROWS_DELETED,
        COMPILATION_TIME / 1000 AS compilation_time_seconds,
        EXECUTION_TIME / 1000 AS execution_time_seconds,
        QUEUED_OVERLOAD_TIME / 1000 AS queued_time_seconds,
        TRANSACTION_BLOCKED_TIME / 1000 AS blocked_time_seconds,
        START_TIME,
        END_TIME,
        EXECUTION_STATUS
    FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
    WHERE QUERY_ID = ?
    """
    
    try:
        cursor = conn.cursor()
        cursor.execute(query, (query_id,))
        df = cursor.fetch_pandas_all()
        # Normaliser les noms de colonnes en minuscules
        df.columns = df.columns.str.lower()
        return df
    except Exception as e:
        st.error(f"Erreur lors de la récupération des détails de la requête: {str(e)}")
        return None

def get_query_text_by_user_warehouse(user_name: str, warehouse_name: str, conn):
    """Récupère le texte SQL d'une requête basée sur user et warehouse"""
    query = """
    SELECT
        QUERY_ID,
        QUERY_TEXT,
        QUERY_TYPE,
        WAREHOUSE_NAME,
        WAREHOUSE_SIZE,
        USER_NAME,
        ROLE_NAME,
        DATABASE_NAME,
        SCHEMA_NAME,
        TOTAL_ELAPSED_TIME / 1000 AS duration_seconds,
        BYTES_SCANNED,
        BYTES_SPILLED_TO_LOCAL_STORAGE,
        BYTES_SPILLED_TO_REMOTE_STORAGE,
        PARTITIONS_SCANNED,
        PARTITIONS_TOTAL,
        ROWS_PRODUCED,
        ROWS_INSERTED,
        ROWS_UPDATED,
        ROWS_DELETED,
        COMPILATION_TIME / 1000 AS compilation_time_seconds,
        EXECUTION_TIME / 1000 AS execution_time_seconds,
        QUEUED_OVERLOAD_TIME / 1000 AS queued_time_seconds,
        TRANSACTION_BLOCKED_TIME / 1000 AS blocked_time_seconds,
        START_TIME,
        END_TIME,
        EXECUTION_STATUS
    FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
    WHERE USER_NAME = ? 
        AND WAREHOUSE_NAME = ?
        AND EXECUTION_STATUS = 'SUCCESS'
        AND START_TIME > DATEADD(DAY, -30, CURRENT_TIMESTAMP())
    ORDER BY TOTAL_ELAPSED_TIME DESC
    LIMIT 1
    """
    
    try:
        cursor = conn.cursor()
        cursor.execute(query, (user_name, warehouse_name))
        df = cursor.fetch_pandas_all()
        # Normaliser les noms de colonnes en minuscules
        df.columns = df.columns.str.lower()
        return df
    except Exception as e:
        st.error(f"Erreur lors de la récupération du texte de la requête: {str(e)}")
        return None

def extract_tables_from_sql(sql_text: str) -> List[str]:
    """Extrait les noms de tables depuis le texte SQL"""
    # Pattern pour identifier les tables (FROM, JOIN, etc.)
    # Support pour database.schema.table, schema.table, ou table
    patterns = [
        r'FROM\s+([\w\.`"]+)',
        r'JOIN\s+([\w\.`"]+)',
        r'INTO\s+([\w\.`"]+)',
        r'UPDATE\s+([\w\.`"]+)',
        r'MERGE\s+INTO\s+([\w\.`"]+)',
        r'TABLE\s+([\w\.`"]+)',
    ]
    
    tables = set()
    for pattern in patterns:
        matches = re.findall(pattern, sql_text, re.IGNORECASE)
        for match in matches:
            # Nettoyer le nom de la table (enlever backticks, guillemets, espaces)
            table = match.strip().strip('`').strip('"').strip()
            # Filtrer les alias (AS alias) et les mots-clés SQL
            if table and table.upper() not in ['AS', 'ON', 'WHERE', 'GROUP', 'ORDER', 'HAVING', 'SELECT']:
                # Enlever les alias potentiels après un espace
                table = table.split()[0] if ' ' in table else table
                if table and not table.startswith('('):
                    tables.add(table)
    
    return sorted(list(tables))


@st.cache_data
def fetch_pandas_all(expensive_queries_sql):
    return conn.cursor().execute(expensive_queries_sql).fetch_pandas_all()

def get_table_metadata(table_name: str, conn):
    """Récupère les métadonnées d'une table"""
    # Séparer database.schema.table si nécessaire
    parts = table_name.split('.')
    
    if len(parts) == 3:
        database, schema, table = parts
    elif len(parts) == 2:
        database = None
        schema, table = parts
    else:
        database = None
        schema = None
        table = table_name
    
    metadata = {}
    
    try:
        # Récupérer les colonnes de la table
        if database and schema:
            query_columns = f"""
            SELECT 
                COLUMN_NAME,
                DATA_TYPE,
                IS_NULLABLE,
                COLUMN_DEFAULT,
                COMMENT
            FROM {database}.INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{table}'
            ORDER BY ORDINAL_POSITION
            """
        elif schema:
            query_columns = f"""
            SELECT 
                COLUMN_NAME,
                DATA_TYPE,
                IS_NULLABLE,
                COLUMN_DEFAULT,
                COMMENT
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{table}'
            ORDER BY ORDINAL_POSITION
            """
        else:
            query_columns = f"""
            SELECT 
                COLUMN_NAME,
                DATA_TYPE,
                IS_NULLABLE,
                COLUMN_DEFAULT,
                COMMENT
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = '{table}'
            ORDER BY ORDINAL_POSITION
            """
        
        cursor = conn.cursor()
        cursor.execute(query_columns)
        columns_df = cursor.fetch_pandas_all()
        # Normaliser les noms de colonnes en minuscules
        if not columns_df.empty:
            columns_df.columns = columns_df.columns.str.lower()
        metadata['columns'] = columns_df.to_dict('records') if not columns_df.empty else []
        
        # Récupérer les statistiques de la table
        if database and schema:
            query_stats = f"""
            SELECT 
                ROW_COUNT,
                BYTES,
                RETENTION_TIME,
                CREATED,
                LAST_ALTERED
            FROM {database}.INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{table}'
            """
        elif schema:
            query_stats = f"""
            SELECT 
                ROW_COUNT,
                BYTES,
                RETENTION_TIME,
                CREATED,
                LAST_ALTERED
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{table}'
            """
        else:
            query_stats = f"""
            SELECT 
                ROW_COUNT,
                BYTES,
                RETENTION_TIME,
                CREATED,
                LAST_ALTERED
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = '{table}'
            """
        
        cursor.execute(query_stats)
        stats_df = cursor.fetch_pandas_all()
        # Normaliser les noms de colonnes en minuscules
        if not stats_df.empty:
            stats_df.columns = stats_df.columns.str.lower()
        metadata['statistics'] = stats_df.to_dict('records')[0] if not stats_df.empty else {}
        
        # Récupérer les clés primaires et index
        if database and schema:
            query_keys = f"""
            SELECT 
                CONSTRAINT_NAME,
                CONSTRAINT_TYPE
            FROM {database}.INFORMATION_SCHEMA.TABLE_CONSTRAINTS
            WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{table}'
            """
        elif schema:
            query_keys = f"""
            SELECT 
                CONSTRAINT_NAME,
                CONSTRAINT_TYPE
            FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
            WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{table}'
            """
        else:
            query_keys = f"""
            SELECT 
                CONSTRAINT_NAME,
                CONSTRAINT_TYPE
            FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
            WHERE TABLE_NAME = '{table}'
            """
        
        cursor.execute(query_keys)
        keys_df = cursor.fetch_pandas_all()
        # Normaliser les noms de colonnes en minuscules
        if not keys_df.empty:
            keys_df.columns = keys_df.columns.str.lower()
        metadata['constraints'] = keys_df.to_dict('records') if not keys_df.empty else []
        
    except Exception as e:
        st.warning(f"Erreur lors de la récupération des métadonnées pour {table_name}: {str(e)}")
        metadata['error'] = str(e)
    
    return metadata

def call_cortex_ai(query_text: str, execution_metadata: Dict, tables_metadata: Dict[str, Dict], conn):
    """Appelle Cortex AI (Claude Sonnet) pour obtenir des suggestions d'optimisation"""
    
    # Préparer le prompt
    prompt = f"""Tu es un expert en optimisation de requêtes SQL sur Snowflake. 

Analyse la requête SQL suivante et fournis des suggestions d'optimisation détaillées.

## Requête SQL à analyser :

```sql
{query_text}
```

## Métadonnées d'exécution :

{json.dumps(execution_metadata, indent=2, default=str)}

## Métadonnées des tables utilisées :

{json.dumps(tables_metadata, indent=2, default=str)}

## Instructions :

Fournis une analyse complète avec :

1. **Optimisations SQL** :
   - Suggestions de réécriture de la requête
   - Amélioration des JOINs
   - Optimisation des WHERE clauses
   - Utilisation d'index ou de clustering keys
   - Suggestions de CTEs ou de sous-requêtes

2. **Optimisations liées au Warehouse** :
   - Taille de warehouse recommandée
   - Utilisation de multi-clustering
   - Auto-suspend et auto-resume
   - Gestion de la concurrence

3. **Optimisations générales** :
   - Amélioration du temps d'exécution
   - Réduction des coûts
   - Meilleures pratiques Snowflake

Formatte ta réponse de manière claire et structurée avec des sections bien définies."""

    try:
        # Échapper les apostrophes pour SQL
        escaped_prompt = prompt.replace("'", "''")

        # Appel à Cortex AI via SNOWFLAKE.CORTEX.COMPLETE
        # Nouvelle syntaxe: SNOWFLAKE.CORTEX.COMPLETE(model_name, prompt_text, options)
        cortex_query = f"""
        SELECT SNOWFLAKE.CORTEX.COMPLETE(
            'claude-4-sonnet',
            '{escaped_prompt}'
        ) AS response
        """

        cursor = conn.cursor()
        cursor.execute(cortex_query)
        result = cursor.fetchone()
        
        if result and result[0]:
            # Le résultat de CORTEX.COMPLETE est directement le texte généré
            response = result[0]

            # Si c'est déjà une string, la retourner directement
            if isinstance(response, str):
                return response

            # Si c'est un dict, essayer d'extraire le contenu
            if isinstance(response, dict):
                # Vérifier différents formats possibles
                if 'choices' in response and len(response['choices']) > 0:
                    choice = response['choices'][0]
                    if isinstance(choice, dict):
                        if 'message' in choice and 'content' in choice['message']:
                            return choice['message']['content']
                        if 'text' in choice:
                            return choice['text']
                if 'content' in response:
                    return response['content']
                if 'text' in response:
                    return response['text']

                # Si rien n'a fonctionné, retourner le JSON formaté
                return json.dumps(response, indent=2, ensure_ascii=False)

            # Dernier recours: convertir en string
            return str(response)
        else:
            return None
            
    except Exception as e:
        st.error(f"Erreur lors de l'appel à Cortex AI: {str(e)}")
        st.exception(e)
        return None

# Interface principale
conn = init_session()

if conn is None:
    st.stop()

# Section 1: Liste des requêtes coûteuses
st.header("📊 Requêtes SQL les plus coûteuses")

if st.button("🔄 Actualiser la liste"):
    st.cache_data.clear()

try:
    expensive_queries_sql = get_expensive_queries()
    df_queries = fetch_pandas_all(expensive_queries_sql)
    # Normaliser les noms de colonnes en minuscules (Snowflake retourne en majuscules)
    df_queries.columns = df_queries.columns.str.lower()

    if df_queries.empty:
        st.info("Aucune requête coûteuse trouvée.")
    else:
        # Convertir les colonnes numériques (Snowflake peut retourner des strings)
        numeric_cols = ['duration_seconds', 'duration_hours', 'cost_factor', 'cnt']
        for col in numeric_cols:
            if col in df_queries.columns:
                df_queries[col] = pd.to_numeric(df_queries[col], errors='coerce')

        # Formatage des données pour l'affichage
        display_df = df_queries.copy()
        display_df['duration_seconds'] = display_df['duration_seconds'].round(2)
        display_df['duration_hours'] = display_df['duration_hours'].round(4)
        display_df['cost_factor'] = display_df['cost_factor'].round(2)

        # Formater les dates pour l'affichage
        if 'min_start_time' in display_df.columns:
            display_df['min_start_time'] = pd.to_datetime(display_df['min_start_time'])
        if 'max_end_time' in display_df.columns:
            display_df['max_end_time'] = pd.to_datetime(display_df['max_end_time'])

        # Créer une version simplifiée pour l'affichage avec seulement les colonnes demandées
        table_display_df = display_df[['warehouse_name', 'warehouse_size', 'user_name', 'cnt', 'duration_seconds']].copy()

        # Layout en deux colonnes
        col_left, col_right = st.columns([1, 1])

        with col_left:
            event = st.dataframe(
                table_display_df,
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row" #play all rows without pagination
            )

        with col_right:
            st.subheader("💻 Détails SQL")
            # Afficher les détails SQL si une ligne est sélectionnée
            if event.selection and len(event.selection.rows) > 0:
                selected_idx = event.selection.rows[0]
                selected_row = display_df.iloc[selected_idx]

                # Métriques complémentaires
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Facteur de coût", f"{selected_row['cost_factor']:.2f}")
                with col2:
                    if pd.notna(selected_row.get('min_start_time')):
                        st.metric("Première exec.", selected_row['min_start_time'].strftime('%Y-%m-%d %H:%M'))
                with col3:
                    if pd.notna(selected_row.get('max_end_time')):
                        st.metric("Dernière exec.", selected_row['max_end_time'].strftime('%Y-%m-%d %H:%M'))

                # Afficher le texte SQL
                if 'sample_query_text' in selected_row and pd.notna(selected_row['sample_query_text']):
                    st.code(selected_row['sample_query_text'], language='sql', line_numbers=True)
                else:
                    st.info("Aucun texte SQL disponible pour cette requête")

                # Bouton pour analyser cette requête avec l'IA
                if st.button("🚀 Analyser cette requête avec l'IA", use_container_width=True):
                    # Utiliser directement les données de selected_row
                    query_text = selected_row['sample_query_text']
                    query_id = selected_row.get('sample_query_id', 'N/A')

                    # Extraire les tables
                    with st.spinner("Identification des tables utilisées..."):
                        tables = extract_tables_from_sql(query_text)

                    if tables:
                        # Récupérer les métadonnées des tables
                        with st.spinner("Récupération des métadonnées des tables..."):
                            tables_metadata = {}
                            for table in tables:
                                tables_metadata[table] = get_table_metadata(table, conn)

                            # Préparer les métadonnées d'exécution à partir de selected_row
                            execution_metadata = {
                                'query_id': query_id,
                                'duration_seconds': float(selected_row['duration_seconds']),
                                'warehouse_name': selected_row['warehouse_name'],
                                'warehouse_size': selected_row['warehouse_size'],
                                'user_count': int(selected_row['cnt']),
                                'cost_factor': float(selected_row['cost_factor']),
                                'min_start_time': str(selected_row['min_start_time']) if pd.notna(selected_row.get('min_start_time')) else None,
                                'max_end_time': str(selected_row['max_end_time']) if pd.notna(selected_row.get('max_end_time')) else None,
                                # Note: detailed metrics like bytes_scanned not available in selected_row
                            }

                            # Appel à Cortex AI
                            with st.spinner("Analyse par Cortex AI (Claude Sonnet)..."):
                                optimization_suggestions = call_cortex_ai(
                                    query_text,
                                    execution_metadata,
                                    tables_metadata,
                                    conn
                                )

                                # Stocker les résultats dans session state pour affichage en-dessous
                                st.session_state['ai_analysis'] = {
                                    'tables': tables,
                                    'suggestions': optimization_suggestions
                                }
                    else:
                        st.session_state['ai_analysis'] = {
                            'tables': [],
                            'suggestions': None
                        }
            else:
                st.info("👈 Sélectionnez une ligne dans le tableau pour voir le code SQL")

        # Afficher les résultats de l'analyse IA en-dessous des deux colonnes
        if 'ai_analysis' in st.session_state and st.session_state['ai_analysis'] is not None:
            st.divider()
            st.header("🤖 Analyse IA")

            analysis = st.session_state['ai_analysis']

            if analysis['tables']:
                st.subheader("📋 Tables identifiées")
                st.write(", ".join(analysis['tables']))

            if analysis['suggestions']:
                st.subheader("✨ Suggestions d'optimisation")
                st.markdown(analysis['suggestions'])
            elif analysis['tables'] is not None and len(analysis['tables']) == 0:
                st.warning("Aucune table identifiée dans la requête SQL.")
            elif analysis['suggestions'] is None and analysis['tables']:
                st.warning("Impossible d'obtenir des suggestions d'optimisation. Vérifiez que Cortex AI est activé dans votre compte Snowflake.")

except Exception as e:
    st.error(f"Erreur lors de l'exécution de la requête: {str(e)}")
    st.exception(e)

