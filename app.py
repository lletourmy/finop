"""
Application Streamlit pour l'optimisation de requêtes SQL Snowflake

Cette application utilise Cortex AI pour analyser et optimiser les requêtes SQL
les plus coûteuses sur Snowflake.
"""

import streamlit as st
import pandas as pd
from snowflake_connector import SnowflakeConnector
from query_optimizer import QueryOptimizer

# Page configuration
st.set_page_config(
    page_title="SQL Query Optimizer",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 SQL Query Optimizer")
st.markdown("Analyze and optimize your most expensive Snowflake SQL queries with AI")
st.markdown("Made with ❤️ by Devoteam Snowflake Partner - December 2025")

# Snowflake connection initialization
# Note: Do not hide this function because it contains Streamlit widgets
connector = SnowflakeConnector()
conn = connector.init_connection()

# Check if the connection is established
if conn is None:
    st.warning("⚠️ Please connect to Snowflake to continue")
    st.stop()

# Update the connection in the connector
connector._connection = conn

# Add logout button in sidebar when connected
st.sidebar.divider()
if st.sidebar.button("🚪 Logout", use_container_width=True, type="secondary"):
    # Close the connection if it exists
    if connector._connection:
        try:
            connector._connection.close()
        except:
            pass
    
    # Clear all session state related to connection and data
    keys_to_clear = [
        'snowflake_connection',
        'warehouse_name',
        'sis_mode_confirmed',
        'local_mode_shown',
        'df_queries',
        'ai_analysis',
        'connection_selector'
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    # Clear cached connection resource
    try:
        st.cache_resource.clear()
    except:
        pass
    
    # Reset the connector
    connector._connection = None
    
    # Rerun to return to initial state
    st.rerun()

# Initialize the query optimizer
optimizer = QueryOptimizer(connector)

# Main interface
st.header("📊 Most expensive queries")

try:
    days = st.slider("Select the number of days to analyze", min_value=1, max_value=30, value=15, step=1)
    
    # Button to refresh the data
    if st.button("🔄 Refresh the list of queries", type="primary"):
        # Clear cache and reload the data
        if 'ai_analysis' in st.session_state:
            del st.session_state['ai_analysis']

        with st.spinner("Loading expensive queries..."):
            df_queries = optimizer.get_expensive_queries(days)

            if df_queries is not None and not df_queries.empty:
                # Convert the numeric columns
                numeric_cols = ['duration_seconds', 'duration_hours', 'cost_factor', 'cnt']
                for col in numeric_cols:
                    if col in df_queries.columns:
                        df_queries[col] = pd.to_numeric(df_queries[col], errors='coerce')

                # Store in session state
                st.session_state['df_queries'] = df_queries
            else:
                st.warning("No queries found in the last 30 days")

    if 'df_queries' in st.session_state:
        df_queries = st.session_state.df_queries
    else:
        df_queries = None

    if df_queries is not None and not df_queries.empty:
        # Create a copy for display
        display_df = df_queries.copy()

        # Round numeric values
        if 'duration_seconds' in display_df.columns:
            display_df['duration_seconds'] = display_df['duration_seconds'].round(2)
        if 'cost_factor' in display_df.columns:
            display_df['cost_factor'] = display_df['cost_factor'].round(2)

        # Convert dates
        if 'min_start_time' in display_df.columns:
            display_df['min_start_time'] = pd.to_datetime(display_df['min_start_time'])
        if 'max_end_time' in display_df.columns:
            display_df['max_end_time'] = pd.to_datetime(display_df['max_end_time'])

        # Create a simplified version for display
        table_display_df = display_df[['warehouse_name', 'warehouse_size', 'user_name', 'cnt', 'cost_factor']].copy()

        # Layout in two columns
        col_left, col_right = st.columns([3, 5])

        with col_left:
            # Display dataframe with row selection
            try:
                # Try with height="auto" for newer Streamlit versions
                event = st.dataframe(
                    table_display_df,
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row",
                    height="auto"
                )
            except TypeError:
                # Fallback for older Streamlit versions that don't support height parameter
                event = st.dataframe(
                    table_display_df,
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row",
                    height=None
                )

        with col_right:
            st.subheader("💻 SQL details")
            # Display SQL details if a row is selected
            if event.selection and len(event.selection.rows) > 0:
                selected_idx = event.selection.rows[0]
                selected_row = display_df.iloc[selected_idx]

                # Métriques complémentaires
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Cost factor", f"{selected_row['cost_factor']:.2f}")
                with col2:
                    if pd.notna(selected_row.get('min_start_time')):
                        st.metric("First execution", selected_row['min_start_time'].strftime('%Y-%m-%d %H:%M'))
                with col3:
                    if pd.notna(selected_row.get('max_end_time')):
                        st.metric("Last execution", selected_row['max_end_time'].strftime('%Y-%m-%d %H:%M'))
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Database", selected_row['database_name'])
                with col2:
                    st.metric("Schema", selected_row['schema_name'])
                
                # Afficher le texte SQL
                if 'sample_query_text' in selected_row and pd.notna(selected_row['sample_query_text']):
                    st.code(selected_row['sample_query_text'], language='sql', line_numbers=True)
                else:
                    st.info("No SQL text available for this query")

                # Button to analyze this query with AI
                if st.button("🚀 AI optimization", use_container_width=True):
                    # Use directly the data from selected_row
                    query_text = selected_row['sample_query_text']
                    query_id = selected_row.get('sample_query_id', 'N/A')

                    # Extract tables
                    with st.spinner("Identifying used tables..."):
                        tables = optimizer.extract_tables_from_sql(query_text)

                    if tables:
                        # Get table metadata
                        with st.spinner("Retrieving table metadata..."):
                            tables_metadata = {}
                            for table in tables:
                                tables_metadata[table] = optimizer.get_table_metadata(db_name=selected_row['database_name'], schema_name=selected_row['schema_name'], table_name=table)

                            # Prepare execution metadata from selected_row
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

                            # Call Cortex AI for optimization
                            with st.spinner("Analyzing with Cortex AI (Claude Sonnet)..."):
                                optimization_suggestions = optimizer.optimize_query(
                                    query_text,
                                    execution_metadata,
                                    tables_metadata
                                )

                                # Store results in session state
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
                st.info("👈 Select a row in the table to see the SQL code")

        # Display AI analysis results below the two columns
        if 'ai_analysis' in st.session_state and st.session_state['ai_analysis'] is not None:
            st.divider()
            st.header("🤖 AI analysis")

            analysis = st.session_state['ai_analysis']

            if analysis['tables']:
                st.subheader("📋 Identified tables")
                st.write(", ".join(analysis['tables']))

            if analysis['suggestions']:
                st.subheader("✨ Optimization suggestions")
                st.markdown(analysis['suggestions'])
            elif analysis['tables'] is not None and len(analysis['tables']) == 0:
                st.warning("No table identified in the SQL query.")
            elif analysis['suggestions'] is None and analysis['tables']:
                st.warning("Impossible to get optimization suggestions. Check if Cortex AI is enabled in your Snowflake account.")

except Exception as e:
    st.error(f"Error during application execution: {str(e)}")
    st.exception(e)
