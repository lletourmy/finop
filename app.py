"""
Application Streamlit pour l'optimisation de requêtes SQL Snowflake

Cette application utilise Cortex AI pour analyser et optimiser les requêtes SQL
les plus coûteuses sur Snowflake.
"""

import streamlit as st
import pandas as pd
from snowflake_connector import SnowflakeConnector
from query_optimizer import QueryOptimizer

# Configuration de la page
st.set_page_config(
    page_title="SQL Query Optimizer",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 SQL Query Optimizer")
st.markdown("Analysez et optimisez vos requêtes SQL les plus coûteuses avec l'IA")

# Initialisation de la connexion Snowflake
# Note: Ne pas cacher cette fonction car elle contient des widgets Streamlit
connector = SnowflakeConnector()
conn = connector.init_connection()

# Vérifier si la connexion est établie
if conn is None:
    st.warning("⚠️ Veuillez établir une connexion à Snowflake pour continuer")
    st.stop()

# Mettre à jour la connexion dans le connecteur
connector._connection = conn

# Initialiser l'optimiseur de requêtes
optimizer = QueryOptimizer(connector)

# Interface principale
st.header("📊 Requêtes les plus coûteuses")

try:
    # Bouton pour actualiser les données
    if st.button("🔄 Actualiser la liste des requêtes", type="primary"):
        # Effacer le cache et recharger
        if 'df_queries' in st.session_state:
            del st.session_state['df_queries']
        if 'ai_analysis' in st.session_state:
            del st.session_state['ai_analysis']

    # Récupérer les requêtes coûteuses
    if 'df_queries' not in st.session_state:
        with st.spinner("Chargement des requêtes coûteuses..."):
            df_queries = optimizer.get_expensive_queries()

            if df_queries is not None and not df_queries.empty:
                # Convertir les colonnes numériques
                numeric_cols = ['duration_seconds', 'duration_hours', 'cost_factor', 'cnt']
                for col in numeric_cols:
                    if col in df_queries.columns:
                        df_queries[col] = pd.to_numeric(df_queries[col], errors='coerce')

                # Stocker dans session state
                st.session_state['df_queries'] = df_queries
            else:
                st.warning("Aucune requête trouvée dans les 30 derniers jours")
                st.stop()

    # Récupérer les données depuis session state
    df_queries = st.session_state['df_queries']

    if df_queries is not None and not df_queries.empty:
        # Créer une copie pour l'affichage
        display_df = df_queries.copy()

        # Arrondir les valeurs numériques
        if 'duration_seconds' in display_df.columns:
            display_df['duration_seconds'] = display_df['duration_seconds'].round(2)
        if 'cost_factor' in display_df.columns:
            display_df['cost_factor'] = display_df['cost_factor'].round(2)

        # Convertir les dates
        if 'min_start_time' in display_df.columns:
            display_df['min_start_time'] = pd.to_datetime(display_df['min_start_time'])
        if 'max_end_time' in display_df.columns:
            display_df['max_end_time'] = pd.to_datetime(display_df['max_end_time'])

        # Créer une version simplifiée pour l'affichage
        table_display_df = display_df[['warehouse_name', 'warehouse_size', 'user_name', 'cnt', 'duration_seconds']].copy()

        # Layout en deux colonnes
        col_left, col_right = st.columns([1, 1])

        with col_left:
            event = st.dataframe(
                table_display_df,
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                height=None  # Display all rows without pagination
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
                        tables = optimizer.extract_tables_from_sql(query_text)

                    if tables:
                        # Récupérer les métadonnées des tables
                        with st.spinner("Récupération des métadonnées des tables..."):
                            tables_metadata = {}
                            for table in tables:
                                tables_metadata[table] = optimizer.get_table_metadata(table)

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
                            }

                            # Appel à Cortex AI pour optimisation
                            with st.spinner("Analyse par Cortex AI (Claude Sonnet)..."):
                                optimization_suggestions = optimizer.optimize_query(
                                    query_text,
                                    execution_metadata,
                                    tables_metadata
                                )

                                # Stocker les résultats dans session state
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
    st.error(f"Erreur lors de l'exécution de l'application: {str(e)}")
    st.exception(e)
