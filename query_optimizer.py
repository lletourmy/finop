"""
Module d'optimisation de requêtes SQL

Ce module fournit une classe pour:
- Récupérer les requêtes lentes
- Analyser les métadonnées des tables
- Générer des prompts d'optimisation
- Utiliser Cortex AI pour optimiser les requêtes
"""

import pandas as pd
import streamlit as st
import json
import re
from typing import Dict, List, Optional, Any
from snowflake_connector import SnowflakeConnector


class QueryOptimizer:
    """
    Classe pour l'optimisation de requêtes SQL Snowflake
    """

    def __init__(self, connector: SnowflakeConnector):
        """
        Initialise l'optimiseur de requêtes

        Args:
            connector: Instance de SnowflakeConnector
        """
        self.connector = connector

    def get_expensive_queries(self) -> Optional[pd.DataFrame]:
        """
        Récupère les 20 requêtes les plus coûteuses (30 derniers jours)

        Returns:
            DataFrame avec les requêtes coûteuses ou None si erreur
        """
        query = """
        SELECT
            warehouse_name,
            warehouse_size,
            user_name,
            COUNT(*) as cnt,
            MAX(query_id) as sample_query_id,
            MAX(query_text) as sample_query_text,
            MIN(start_time) as min_start_time,
            MAX(end_time) as max_end_time,
            SUM(total_elapsed_time) / 1000 AS duration_seconds,
            SUM(total_elapsed_time) / 1000 / 60 / 60 AS duration_hours,
            SUM(total_elapsed_time) / 1000 / 60 / 60 *
                CASE warehouse_size
                    WHEN 'X-Small' THEN 1
                    WHEN 'Small' THEN 2
                    WHEN 'Medium' THEN 4
                    WHEN 'Large' THEN 8
                    WHEN 'X-Large' THEN 16
                    WHEN '2X-Large' THEN 32
                    ELSE 1
                END AS cost_factor
        FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE
            warehouse_name IS NOT NULL
            AND execution_status = 'SUCCESS'
            AND START_TIME > DATEADD(DAY, -30, CURRENT_TIMESTAMP())
        GROUP BY warehouse_name, warehouse_size, user_name
        ORDER BY duration_seconds DESC
        LIMIT 30
        """

        return self.connector.execute_query(query)

    def get_query_details(self, query_id: str) -> Optional[pd.DataFrame]:
        """
        Récupère les détails d'une requête spécifique

        Args:
            query_id: ID de la requête

        Returns:
            DataFrame avec les détails de la requête ou None si erreur
        """
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

        return self.connector.execute_query(query, (query_id,))

    @staticmethod
    def extract_tables_from_sql(sql_text: str) -> List[str]:
        """
        Extrait les noms de tables depuis le texte SQL

        Args:
            sql_text: Texte SQL à analyser

        Returns:
            Liste des noms de tables trouvés
        """
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

    def get_table_metadata(self, table_name: str) -> Dict[str, Any]:
        """
        Récupère les métadonnées d'une table

        Args:
            table_name: Nom de la table (format: database.schema.table ou schema.table ou table)

        Returns:
            Dictionnaire avec les métadonnées de la table
        """
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
        conn = self.connector.get_connection()

        if not conn:
            return {'error': 'No active connection'}

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

            columns_df = self.connector.execute_query(query_columns)
            metadata['columns'] = columns_df.to_dict('records') if columns_df is not None and not columns_df.empty else []

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

            stats_df = self.connector.execute_query(query_stats)
            metadata['statistics'] = stats_df.to_dict('records')[0] if stats_df is not None and not stats_df.empty else {}

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

            keys_df = self.connector.execute_query(query_keys)
            metadata['constraints'] = keys_df.to_dict('records') if keys_df is not None and not keys_df.empty else []

        except Exception as e:
            st.warning(f"Erreur lors de la récupération des métadonnées pour {table_name}: {str(e)}")
            metadata['error'] = str(e)

        return metadata

    def build_optimization_prompt(
        self,
        query_text: str,
        execution_metadata: Dict[str, Any],
        tables_metadata: Dict[str, Dict[str, Any]]
    ) -> str:
        """
        Build the prompt for query optimization

        Args:
            query_text: Text of the SQL query
            execution_metadata: Execution metadata
            tables_metadata: Tables metadata

        Returns:
            Prompt formatted for Cortex AI
        """
        prompt = f"""You are an expert in SQL query optimization on Snowflake.

Analyze the following SQL query and provide detailed optimization suggestions.

## SQL query to analyze:

```sql
{query_text}
```

## Execution metadata:

{json.dumps(execution_metadata, indent=2, default=str)}

## Metadata of tables used:

{json.dumps(tables_metadata, indent=2, default=str)}

## Instructions:

Provide a complete analysis with:

1. **SQL Optimizations**:
   - Query rewrite suggestions
   - JOIN improvements
   - WHERE clause optimization
   - Use of indexes or clustering keys
   - CTE or subquery suggestions

2. **Warehouse-related optimizations**:
   - Recommended warehouse size
   - Use of multi-clustering
   - Auto-suspend and auto-resume
   - Concurrency management

3. **General optimizations**:
   - Execution time improvement
   - Cost reduction
   - Snowflake best practices

Format your response clearly and structured with well-defined sections."""

        return prompt

    def optimize_query(
        self,
        query_text: str,
        execution_metadata: Dict[str, Any],
        tables_metadata: Dict[str, Dict[str, Any]],
        model: str = 'claude-3-5-sonnet'
    ) -> Optional[str]:
        """
        Optimize a SQL query using Cortex AI

        Args:
            query_text: Text of the SQL query
            execution_metadata: Execution metadata
            tables_metadata: Tables metadata
            model: Cortex AI model to use

        Returns:
            Optimization suggestions or None if error
        """
        # Build the prompt
        prompt = self.build_optimization_prompt(query_text, execution_metadata, tables_metadata)

        # Call Cortex AI
        response = self.connector.call_cortex_ai(prompt, model)

        return response
