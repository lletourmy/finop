import streamlit as st
import pandas as pd
import json
from typing import Dict, List
import re

# Configuration de la page
st.set_page_config(
    page_title="SQL Query Optimizer",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 SQL Query Optimizer")
st.markdown("Analysez et optimisez vos requêtes SQL les plus coûteuses avec l'IA")

# Initialisation de la session Snowflake
@st.cache_resource
def init_session():
    """Initialise la session Snowflake depuis Streamlit in Snowflake"""
    if 'snowpark_session' in st.session_state:
        return st.session_state.snowpark_session
    
    # Dans Streamlit in Snowflake, la session est automatiquement disponible
    # via st.connection ou snowflake.connector
    try:
        # Utilisation de la connexion Streamlit in Snowflake
        conn = st.connection("snowflake")
        return conn
    except:
        # Fallback pour développement local
        st.error("Connexion Snowflake non disponible. Assurez-vous d'être dans Streamlit in Snowflake.")
        return None

def get_expensive_queries():
    """Récupère les requêtes SQL les plus coûteuses"""
    query = """
    with recent_queries AS (
        SELECT
            warehouse_name,
            warehouse_size,
            user_name,
            sum(total_elapsed_time) as total_elapsed_time, -- in milliseconds
            count(*) as cnt,
            -- Récupérer un QUERY_ID représentatif (le plus long pour cette combinaison)
            (SELECT QUERY_ID 
             FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY q2
             WHERE q2.warehouse_name = q1.warehouse_name
               AND q2.user_name = q1.user_name
               AND q2.execution_status = 'SUCCESS'
               AND q2.START_TIME > DATEADD(DAY, -30, CURRENT_TIMESTAMP())
             ORDER BY q2.total_elapsed_time DESC
             LIMIT 1) as sample_query_id,
            ROW_NUMBER() OVER (
                PARTITION BY warehouse_name
                ORDER BY sum(total_elapsed_time) DESC
            ) AS rank    
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY q1
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
        sample_query_id,
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
        # Format: SNOWFLAKE.CORTEX.COMPLETE(model_name, messages_array)
        cortex_query = f"""
        SELECT SNOWFLAKE.CORTEX.COMPLETE(
            'claude-sonnet',
            ARRAY_CONSTRUCT(
                OBJECT_CONSTRUCT(
                    'role', 'user',
                    'content', '{escaped_prompt}'
                )
            )
        ) AS response
        """
        
        cursor = conn.cursor()
        cursor.execute(cortex_query)
        result = cursor.fetchone()
        
        if result and result[0]:
            # Le résultat de CORTEX.COMPLETE est généralement un objet JSON
            response = result[0]
            
            # Si c'est une chaîne JSON, la parser
            if isinstance(response, str):
                try:
                    response = json.loads(response)
                except:
                    pass
            
            # Extraire le contenu selon le format de réponse
            if isinstance(response, dict):
                # Format possible: {'choices': [{'message': {'content': '...'}}]}
                if 'choices' in response and len(response['choices']) > 0:
                    choice = response['choices'][0]
                    if 'message' in choice and 'content' in choice['message']:
                        return choice['message']['content']
                # Format possible: {'content': '...'}
                if 'content' in response:
                    return response['content']
                # Sinon, convertir tout le dict en string
                return json.dumps(response, indent=2, ensure_ascii=False)
            
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
    df_queries = conn.cursor().execute(expensive_queries_sql).fetch_pandas_all()
    
    if df_queries.empty:
        st.info("Aucune requête coûteuse trouvée.")
    else:
        # Formatage des données pour l'affichage
        display_df = df_queries.copy()
        display_df['duration_seconds'] = display_df['duration_seconds'].round(2)
        display_df['duration_hours'] = display_df['duration_hours'].round(4)
        display_df['cost_factor'] = display_df['cost_factor'].round(2)
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )
        
        # Sélection d'une requête
        st.subheader("🔍 Sélectionner une requête pour analyse")
        
        if len(df_queries) > 0:
            # Créer un identifiant unique pour chaque requête
            df_queries['query_key'] = df_queries.apply(
                lambda row: f"{row['user_name']}|{row['warehouse_name']}|{row['duration_seconds']:.2f}",
                axis=1
            )
            
            query_options = df_queries['query_key'].tolist()
            selected_key = st.selectbox(
                "Choisissez une requête à analyser:",
                options=query_options,
                format_func=lambda x: f"{x.split('|')[0]} - {x.split('|')[1]} ({x.split('|')[2]}s)"
            )
            
            if selected_key:
                selected_row = df_queries[df_queries['query_key'] == selected_key].iloc[0]
                
                if st.button("🚀 Analyser cette requête"):
                    with st.spinner("Récupération des détails de la requête..."):
                        # Récupérer le texte SQL et les métadonnées d'exécution
                        # Utiliser QUERY_ID si disponible, sinon fallback sur user/warehouse
                        if 'sample_query_id' in selected_row and pd.notna(selected_row['sample_query_id']):
                            query_details = get_query_details(selected_row['sample_query_id'], conn)
                        else:
                            # Fallback: récupérer par user et warehouse
                            query_details = get_query_text_by_user_warehouse(
                                selected_row['user_name'],
                                selected_row['warehouse_name'],
                                conn
                            )
                        
                        if query_details is not None and not query_details.empty:
                            query_detail = query_details.iloc[0]
                            query_text = query_detail['QUERY_TEXT']
                            query_id = query_detail['QUERY_ID']
                            
                            # Afficher les détails de la requête
                            st.subheader("📝 Détails de la requête")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Durée d'exécution", f"{query_detail['duration_seconds']:.2f} s")
                                st.metric("Warehouse", query_detail['WAREHOUSE_NAME'])
                                st.metric("Taille Warehouse", query_detail['WAREHOUSE_SIZE'])
                                st.metric("Utilisateur", query_detail['USER_NAME'])
                            
                            with col2:
                                st.metric("Bytes scannés", f"{query_detail['BYTES_SCANNED']:,}" if pd.notna(query_detail['BYTES_SCANNED']) else "N/A")
                                st.metric("Rows produits", f"{query_detail['ROWS_PRODUCED']:,}" if pd.notna(query_detail['ROWS_PRODUCED']) else "N/A")
                                st.metric("Temps de compilation", f"{query_detail['compilation_time_seconds']:.2f} s" if pd.notna(query_detail['compilation_time_seconds']) else "N/A")
                                st.metric("Temps d'exécution", f"{query_detail['execution_time_seconds']:.2f} s" if pd.notna(query_detail['execution_time_seconds']) else "N/A")
                            
                            st.subheader("💻 Code SQL")
                            st.code(query_text, language='sql')
                            
                            # Extraire les tables
                            with st.spinner("Identification des tables utilisées..."):
                                tables = extract_tables_from_sql(query_text)
                                
                                if tables:
                                    st.subheader("📋 Tables identifiées")
                                    st.write(", ".join(tables))
                                    
                                    # Récupérer les métadonnées des tables
                                    with st.spinner("Récupération des métadonnées des tables..."):
                                        tables_metadata = {}
                                        for table in tables:
                                            st.write(f"Récupération des métadonnées pour: {table}")
                                            tables_metadata[table] = get_table_metadata(table, conn)
                                        
                                        # Préparer les métadonnées d'exécution
                                        execution_metadata = {
                                            'query_id': query_id,
                                            'duration_seconds': float(query_detail['duration_seconds']),
                                            'warehouse_name': query_detail['WAREHOUSE_NAME'],
                                            'warehouse_size': query_detail['WAREHOUSE_SIZE'],
                                            'bytes_scanned': int(query_detail['BYTES_SCANNED']) if pd.notna(query_detail['BYTES_SCANNED']) else None,
                                            'bytes_spilled_local': int(query_detail['BYTES_SPILLED_TO_LOCAL_STORAGE']) if pd.notna(query_detail['BYTES_SPILLED_TO_LOCAL_STORAGE']) else None,
                                            'bytes_spilled_remote': int(query_detail['BYTES_SPILLED_TO_REMOTE_STORAGE']) if pd.notna(query_detail['BYTES_SPILLED_TO_REMOTE_STORAGE']) else None,
                                            'partitions_scanned': int(query_detail['PARTITIONS_SCANNED']) if pd.notna(query_detail['PARTITIONS_SCANNED']) else None,
                                            'partitions_total': int(query_detail['PARTITIONS_TOTAL']) if pd.notna(query_detail['PARTITIONS_TOTAL']) else None,
                                            'rows_produced': int(query_detail['ROWS_PRODUCED']) if pd.notna(query_detail['ROWS_PRODUCED']) else None,
                                            'compilation_time_seconds': float(query_detail['compilation_time_seconds']) if pd.notna(query_detail['compilation_time_seconds']) else None,
                                            'execution_time_seconds': float(query_detail['execution_time_seconds']) if pd.notna(query_detail['execution_time_seconds']) else None,
                                            'queued_time_seconds': float(query_detail['queued_time_seconds']) if pd.notna(query_detail['queued_time_seconds']) else None,
                                            'blocked_time_seconds': float(query_detail['blocked_time_seconds']) if pd.notna(query_detail['blocked_time_seconds']) else None,
                                            'start_time': str(query_detail['START_TIME']),
                                            'end_time': str(query_detail['END_TIME']),
                                            'execution_status': query_detail['EXECUTION_STATUS']
                                        }
                                        
                                        # Appel à Cortex AI
                                        with st.spinner("Analyse par Cortex AI (Claude Sonnet)..."):
                                            optimization_suggestions = call_cortex_ai(
                                                query_text,
                                                execution_metadata,
                                                tables_metadata,
                                                conn
                                            )
                                            
                                            if optimization_suggestions:
                                                st.subheader("✨ Suggestions d'optimisation")
                                                st.markdown(optimization_suggestions)
                                            else:
                                                st.warning("Impossible d'obtenir des suggestions d'optimisation. Vérifiez que Cortex AI est activé dans votre compte Snowflake.")
                                else:
                                    st.warning("Aucune table identifiée dans la requête SQL.")
                        else:
                            st.error("Impossible de récupérer les détails de la requête sélectionnée.")
                            
except Exception as e:
    st.error(f"Erreur lors de l'exécution de la requête: {str(e)}")
    st.exception(e)

