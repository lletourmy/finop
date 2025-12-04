# SQL Query Optimizer for Snowflake

Streamlit application to automatically analyze and optimize the most expensive SQL queries in Snowflake, using Snowflake Cortex AI (Claude Sonnet) to generate optimization recommendations.

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Usage](#usage)
6. [Troubleshooting](#troubleshooting)

---

## Overview

### Features

- ✅ Identification of the 20 most expensive queries (last 30 days)
- ✅ Display of execution and performance metrics
- ✅ Automatic analysis of table schemas and statistics
- ✅ AI-powered optimization recommendations (Claude Sonnet)
- ✅ Dual support: Streamlit in Snowflake (SiS) and local development

### Use Cases

- **Cost optimization**: Identify queries that consume the most credits
- **Performance improvement**: Reduce execution times
- **Performance audit**: Analyze warehouse usage by user

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

### Project Structure

```
├── app.py                      # Main Streamlit application
├── snowflake_connector.py      # Connection and data access
├── query_optimizer.py          # Business logic and optimization
├── requirements.txt            # Python dependencies
└── README.md                   # Documentation
```

### Technologies

- **Python** 3.8+
- **Streamlit** ≥1.28.0
- **Snowflake Connector** ≥3.0.0
- **Pandas** ≥2.0.0

---

## Installation

### Deployment to Streamlit in Snowflake

#### Using Git Repository Integration (Recommended)

Snowflake provides native Git repository integration, allowing you to synchronize your remote Git repository with Snowflake and deploy Streamlit apps directly from Git. This enables version control, collaborative development, and streamlined deployment workflows.

**Supported Git Platforms:**
- GitHub
- GitLab
- BitBucket
- Azure DevOps
- AWS CodeCommit

**Prerequisites:**
- A remote Git repository (e.g., GitHub: `https://github.com/lletourmy/finop`)
- Snowflake account with appropriate permissions
- ACCOUNTADMIN role or role with CREATE INTEGRATION, CREATE SECRET, and CREATE GIT REPOSITORY privileges

**Step 1: Set Up Git Repository in Snowflake**

1. **Create a secret for Git authentication** (if using HTTPS with credentials)
   ```sql
   CREATE SECRET git_credentials
     TYPE = GENERIC_STRING
     SECRET_STRING = 'your_username:your_personal_access_token';
   ```

   Or use OAuth integration for GitHub:
   ```sql
   CREATE SECRET git_oauth
     TYPE = OAUTH2
     OAUTH_CLIENT_ID = 'your_client_id'
     OAUTH_CLIENT_SECRET = 'your_client_secret'
     OAUTH_REFRESH_TOKEN = 'your_refresh_token';
   ```

2. **Create API integration** (for GitHub, GitLab, etc.)
   ```sql
   CREATE API INTEGRATION git_api_integration
     API_PROVIDER = git_https_api
     API_ALLOWED_PREFIXES = ('https://github.com', 'https://gitlab.com')
     ALLOWED_AUTHENTICATION_SECRETS = (git_credentials)
     ENABLED = TRUE;
   ```

3. **Create Git repository in Snowflake**
   ```sql
   CREATE GIT REPOSITORY finopt_repo
     API_INTEGRATION = git_api_integration
     GIT_CREDENTIALS = git_credentials
     ORIGIN = 'https://github.com/lletourmy/finop.git';
   ```

**Step 2: Fetch from Remote Repository**

Synchronize the remote repository to the Git repository clone in Snowflake:

```sql
ALTER GIT REPOSITORY finopt_repo FETCH;
```

**Step 3: Create Streamlit App from Git Repository**

Create your Streamlit app referencing files from the Git repository:

```sql
CREATE STREAMLIT sql_query_optimizer
  ROOT_LOCATION = '@finopt_repo/branches/main'
  MAIN_FILE = 'app.py'
  QUERY_WAREHOUSE = 'YOUR_WAREHOUSE';
```

Or specify a specific branch or tag:
```sql
CREATE STREAMLIT sql_query_optimizer
  ROOT_LOCATION = '@finopt_repo/branches/main'
  MAIN_FILE = 'app.py'
  QUERY_WAREHOUSE = 'YOUR_WAREHOUSE';
```

**Step 4: Grant Permissions**

```sql
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE YOUR_ROLE;
GRANT USAGE ON WAREHOUSE YOUR_WAREHOUSE TO ROLE YOUR_ROLE;
GRANT USAGE ON STREAMLIT sql_query_optimizer TO ROLE YOUR_ROLE;
```

**Step 5: Update Your App**

When you push changes to your remote Git repository, fetch the latest version:

```sql
ALTER GIT REPOSITORY finopt_repo FETCH;
```

Then recreate or alter your Streamlit app to use the updated files. Streamlit apps automatically pick up changes from the Git repository clone.

**Benefits of Git Integration:**
- ✅ Native version control integration
- ✅ Automatic synchronization with remote repository
- ✅ Support for branches and tags
- ✅ Collaborative development workflow
- ✅ CI/CD pipeline support
- ✅ No manual file uploads required

**Viewing Repository Contents:**

```sql
-- List branches
SHOW GIT BRANCHES IN finopt_repo;

-- List tags
SHOW GIT TAGS IN finopt_repo;

-- View repository details
DESCRIBE GIT REPOSITORY finopt_repo;
```

**References:**
- [Snowflake Git Repository Overview](https://docs.snowflake.com/en/developer-guide/git/git-overview)
- [Setting up Snowflake to use Git](https://docs.snowflake.com/en/developer-guide/git/setup)
- [Git operations in Snowflake](https://docs.snowflake.com/en/developer-guide/git/operations)
- [Streamlit Git Integration](https://docs.snowflake.com/en/developer-guide/streamlit/git-integration)

#### Alternative: Using Snowflake CLI

You can also use the Snowflake CLI for deployment:

1. **Install Snowflake CLI**
   ```bash
   pip install snowflake-cli
   ```

2. **Configure and deploy**
   ```bash
   snow connection add
   snow streamlit deploy --replace
   ```

#### Alternative: Using SQL Commands with Stage (Traditional Method)

If you prefer not to use Git integration:

1. **Create a stage and upload files**
   ```sql
   CREATE STAGE IF NOT EXISTS streamlit_stage;
   PUT file://app.py @streamlit_stage AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
   PUT file://snowflake_connector.py @streamlit_stage AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
   PUT file://query_optimizer.py @streamlit_stage AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
   ```

2. **Create the Streamlit application**
   ```sql
   CREATE STREAMLIT sql_query_optimizer
     ROOT_LOCATION = '@streamlit_stage'
     MAIN_FILE = 'app.py'
     QUERY_WAREHOUSE = 'YOUR_WAREHOUSE';
   ```

### Local Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/lletourmy/finop.git
   cd finop
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure connection** (see Configuration section)

4. **Run the application**
   ```bash
   streamlit run app.py
   ```

---

## Configuration

### Local Configuration File

**Location:** `~/.snowflake/config.toml`

**Format:**
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

**Security:**
```bash
chmod 600 ~/.snowflake/config.toml
```

### Required Snowflake Permissions

```sql
-- Access to Account Usage
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE YOUR_ROLE;

-- Warehouse access
GRANT USAGE ON WAREHOUSE YOUR_WAREHOUSE TO ROLE YOUR_ROLE;

-- Access to databases to analyze
GRANT USAGE ON DATABASE YOUR_DATABASE TO ROLE YOUR_ROLE;
GRANT SELECT ON ALL TABLES IN DATABASE YOUR_DATABASE TO ROLE YOUR_ROLE;
```

---

## Usage

### Streamlit in Snowflake (SiS) Mode

1. The application automatically connects via `st.connection("snowflake")`
2. Click "🔄 Refresh the list of queries"
3. Select a query from the table
4. Click "🚀 AI optimization"
5. Review the optimization suggestions

### Local Development Mode

1. Launch the application: `streamlit run app.py`
2. In the sidebar, select a connection from `config.toml`
3. Click "Connect"
4. Use the application as in SiS mode

---

## Troubleshooting

### Connection Issues

- **"Connection not available" (SiS)**: Verify you are in SiS mode and check role permissions
- **"Config file not found" (Local)**: Verify `~/.snowflake/config.toml` exists and is properly formatted
- **"Connection failed"**: Verify connection parameters (account, user, password, warehouse)

### Data Issues

- **"No queries found"**: 
  - Verify Account Usage permissions: `GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE YOUR_ROLE`
  - Verify there are queries in the last 30 days
  - Wait for data propagation (45-minute delay for Account Usage)

- **"Cortex AI error"**: 
  - Verify Cortex AI is enabled
  - Verify permissions: `GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE`
  - Try a different model (e.g., 'claude-3-haiku')

- **"Table metadata not found"**: 
  - Verify the table exists and is accessible
  - Verify SELECT permissions on the table
  - Verify the name format (database.schema.table)

### Performance Issues

- **Slow application**: Use a larger warehouse or reduce the time window
- **AI timeout**: Reduce the number of tables analyzed or use a faster model

---

## Main Components

### SnowflakeConnector (`snowflake_connector.py`)

Manages all interactions with Snowflake.

**Main methods:**
- `init_connection()`: Initializes connection (SiS or local)
- `execute_query(query, params=None)`: Executes a SQL query
- `call_cortex_ai(prompt, model='claude-3-5-sonnet')`: Calls Cortex AI

### QueryOptimizer (`query_optimizer.py`)

Contains the optimization business logic.

**Main methods:**
- `get_expensive_queries()`: Retrieves the 20 most expensive queries
- `get_query_details(query_id)`: Retrieves query details
- `extract_tables_from_sql(sql_text)`: Extracts tables from SQL
- `get_table_metadata(table_name)`: Retrieves table metadata
- `optimize_query(...)`: Generates optimization recommendations via AI

### Streamlit Application (`app.py`)

User interface and component orchestration.

**Workflow:**
1. Loading expensive queries
2. Selecting a query from the table
3. Displaying SQL and metrics
4. AI analysis with table extraction and recommendation generation

---

## Security

- **SQL Injection Prevention**: Parameterized queries only
- **Prompt Injection Prevention**: Escaping apostrophes in prompts
- **Credential Management**: 
  - SiS Mode: Native authentication
  - Local Mode: Credentials in `~/.snowflake/config.toml` (restricted permissions)
- **Read-Only Operations**: The application only performs SELECT operations
- **Network Security**: HTTPS connections only

---

## Roadmap

- [ ] Export recommendations to PDF/CSV
- [ ] Analysis history
- [ ] Before/after optimization comparison
- [ ] Performance trends dashboard
- [ ] Automatic alerts
- [ ] Unit tests and CI/CD

---

## Support

- **GitHub Repository**: https://github.com/lletourmy/finop
- **Issues**: https://github.com/lletourmy/finop/issues
- **Snowflake Cortex AI Documentation**: https://docs.snowflake.com/en/user-guide/snowflake-cortex/llm-functions

---

## License

This project is licensed under the MIT License.

---

**Last updated:** December 2025  
**Author:** Laurent Le Tourmy
