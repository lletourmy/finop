"""
Module de connexion et d'interaction avec Snowflake

Ce module fournit une classe pour gérer:
- La connexion à Snowflake
- L'exécution de requêtes SQL
- Les appels à Cortex AI
"""

import pandas as pd
import streamlit as st
import snowflake.connector
from typing import Dict, Any, Optional, List
import toml
from pathlib import Path


class SnowflakeConnector:
    """
    Classe pour gérer la connexion et les interactions avec Snowflake
    """

    def __init__(self, connection=None):
        """
        Initialise le connecteur Snowflake

        Args:
            connection: Connexion Snowflake existante (optionnel)
        """
        self._connection = connection

    @staticmethod
    @st.cache_data
    def load_config_file() -> Optional[Dict]:
        """
        Charge les connexions disponibles depuis ~/.snowflake/config.toml

        Returns:
            Dictionnaire des configurations de connexion ou None si erreur
        """
        config_path = Path.home() / '.snowflake' / 'config.toml'
        if config_path.exists():
            try:
                config = toml.load(config_path)
                return config
            except Exception as e:
                st.error(f"Erreur lors de la lecture de config.toml: {str(e)}")
                return None
        return None

    @staticmethod
    @st.cache_resource
    def create_connection(_conn_params: Dict[str, Any]):
        """
        Crée une connexion Snowflake avec les paramètres fournis

        Args:
            _conn_params: Dictionnaire des paramètres de connexion

        Returns:
            Wrapper de connexion Snowflake
        """
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

    def init_connection(self) -> Optional[Any]:
        """
        Initialise la connexion Snowflake depuis Streamlit in Snowflake ou local

        Returns:
            Objet de connexion Snowflake ou None si erreur
        """
        # Vérifier si déjà connecté en mode local
        if 'snowflake_connection' in st.session_state:
            self._connection = st.session_state['snowflake_connection']
            return self._connection

        # Tenter d'abord la connexion Streamlit in Snowflake
        try:
            conn = st.connection("snowflake")
            if 'sis_mode_confirmed' not in st.session_state:
                st.success("✅ Connecté via Streamlit in Snowflake")
                st.session_state['sis_mode_confirmed'] = True
            self._connection = conn
            return conn
        except Exception as e:
            # Fallback pour développement local
            if 'local_mode_shown' not in st.session_state:
                st.info("📌 Mode développement local - Connexion depuis config.toml")
                st.session_state['local_mode_shown'] = True

            # Charger les connexions disponibles
            config = self.load_config_file()
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

            # Afficher les détails de la connexion
            conn_params = config[selected_connection]
            st.sidebar.write("**Détails de la connexion:**")
            st.sidebar.write(f"- Account: `{conn_params.get('account')}`")
            st.sidebar.write(f"- User: `{conn_params.get('user')}`")
            st.sidebar.write(f"- Database: `{conn_params.get('database')}`")
            st.sidebar.write(f"- Schema: `{conn_params.get('schema')}`")
            st.sidebar.write(f"- Warehouse: `{conn_params.get('warehouse')}`")
            st.sidebar.write(f"- Role: `{conn_params.get('role')}`")

            # Bouton de connexion
            if st.sidebar.button("Se connecter", type="primary"):
                try:
                    conn = self.create_connection(conn_params)
                    st.session_state['snowflake_connection'] = conn
                    st.success(f"✅ Connecté avec succès à {selected_connection}")
                    self._connection = conn
                    st.rerun()
                except Exception as conn_error:
                    st.error(f"❌ Erreur de connexion: {str(conn_error)}")
                    return None

            return None

    def get_connection(self):
        """Retourne la connexion courante"""
        return self._connection

    def execute_query(self, query: str, params: tuple = None) -> Optional[pd.DataFrame]:
        """
        Exécute une requête SQL et retourne un DataFrame

        Args:
            query: Requête SQL à exécuter
            params: Paramètres de la requête (optionnel)

        Returns:
            DataFrame pandas avec les résultats ou None si erreur
        """
        if not self._connection:
            st.error("❌ Pas de connexion active")
            return None

        try:
            cursor = self._connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # Récupérer les résultats
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            cursor.close()

            # Créer le DataFrame
            df = pd.DataFrame(data, columns=columns)

            # Normaliser les noms de colonnes en minuscules
            df.columns = df.columns.str.lower()

            return df

        except Exception as e:
            st.error(f"❌ Erreur lors de l'exécution de la requête: {str(e)}")
            return None

    def call_cortex_ai(self, prompt: str, model: str = 'claude-3-5-sonnet') -> Optional[str]:
        """
        Appelle Cortex AI avec un prompt

        Args:
            prompt: Prompt à envoyer à Cortex AI
            model: Nom du modèle à utiliser (défaut: claude-3-5-sonnet)

        Returns:
            Réponse de Cortex AI ou None si erreur
        """
        if not self._connection:
            st.error("❌ Pas de connexion active")
            return None

        try:
            # Échapper les apostrophes dans le prompt
            escaped_prompt = prompt.replace("'", "''")

            # Construire la requête Cortex AI
            cortex_query = f"""
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                '{model}',
                '{escaped_prompt}'
            ) AS response
            """

            # Exécuter la requête
            cursor = self._connection.cursor()
            cursor.execute(cortex_query)
            result = cursor.fetchone()
            cursor.close()

            if result and result[0]:
                return result[0]
            else:
                st.warning("⚠️ Aucune réponse de Cortex AI")
                return None

        except Exception as e:
            st.error(f"❌ Erreur lors de l'appel à Cortex AI: {str(e)}")
            return None
