# CLAUDE.MD - SQL Query Optimizer for Snowflake

## Project Overview

**Name:** SQL Query Optimizer for Snowflake
**Type:** Streamlit in Snowflake (SiS) Web Application
**Purpose:** Automatically analyze and optimize expensive SQL queries using AI-powered recommendations from Claude Sonnet via Snowflake Cortex AI

### What This Application Does

This application helps Snowflake users identify performance bottlenecks and optimize their SQL queries by:

1. Identifying the 20 most expensive queries across all warehouses (last 30 days)
2. Providing detailed execution metadata and performance metrics
3. Analyzing table schemas and statistics for queries
4. Generating intelligent optimization suggestions using Claude Sonnet AI
5. Offering both SQL-level and infrastructure-level (warehouse) optimization recommendations

## Architecture

### Layered Architecture

```
User Interface Layer (Streamlit)
        ↓
Data Retrieval Layer (Snowflake Query Functions)
        ↓
Data Processing Layer (SQL Parsing, Metadata Extraction)
        ↓
AI Analysis Layer (Cortex AI / Claude Sonnet)
        ↓
Snowflake Backend (Account Usage, Information Schema, Cortex API)
```

### Deployment Context

This is a **single-file application** designed for **Streamlit in Snowflake** (native integration) with support for **local development**. The application automatically detects the environment and adapts:

- **Streamlit in Snowflake (SiS):** Uses native `st.connection("snowflake")` for automatic authentication
- **Local Development:** Reads connection parameters from `~/.snowflake/config.toml` and provides a UI for connection selection

The single-file design is intentional for SiS deployments where modularity isn't required.

## Project Structure

```
/
├── app.py                  # Main application (single-file Streamlit app)
├── README.md               # Project documentation (French)
├── requirements.txt        # Python dependencies
├── CLAUDE.MD              # This file
├── .gitignore             # Git configuration
└── .git/                  # Version control
```

## Technology Stack

| Technology | Purpose | Version |
|-----------|---------|---------|
| **Streamlit** | Web UI framework | >=1.28.0 |
| **Snowflake Connector** | Database connectivity | >=3.0.0 |
| **Snowpark Python** | Snowflake Python API | >=1.0.0 |
| **Pandas** | Data manipulation | >=2.0.0 |
| **TOML** | Config file parsing | >=0.10.2 |
| **Python** | Core language | 3.x |

### Snowflake-Specific APIs Used

- `SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY` - Query performance history
- `INFORMATION_SCHEMA.COLUMNS` - Table column definitions
- `INFORMATION_SCHEMA.TABLES` - Table statistics
- `INFORMATION_SCHEMA.TABLE_CONSTRAINTS` - Key/constraint definitions
- `SNOWFLAKE.CORTEX.COMPLETE` - AI model API (Claude Sonnet)

## Key Components

### Core Functions (app.py)

#### Connection Management Functions

**`load_snowflake_config()`** (Lines 22-32)
- Loads available Snowflake connections from `~/.snowflake/config.toml`
- Returns dictionary of connection configurations
- Uses `@st.cache_data` for performance
- Error handling for missing or invalid config files

**`create_snowflake_connection(_conn_params)`** (Lines 34-60)
- Creates a Snowflake connection with provided parameters
- Uses `@st.cache_resource` for connection pooling
- Wraps `snowflake.connector.connect()` in compatibility class
- Returns `SnowflakeConnectionWrapper` for API compatibility

**`init_session()`** (Lines 62-133)
- **Dual-mode connection initialization (NO cache decorator to allow widgets):**
  - **SiS Mode:** Uses `st.connection("snowflake")` for native Streamlit in Snowflake
  - **Local Mode:** Loads connections from `~/.snowflake/config.toml` and provides UI for selection
- Features for local development:
  - Checks `st.session_state` for existing connection first
  - Displays all available connections in sidebar selectbox
  - Shows connection details (account, user, database, schema, warehouse, role)
  - Provides "Connect" button to establish connection
  - Stores connection in `st.session_state` for persistence
  - Calls `create_snowflake_connection()` for cached connection creation
  - Uses `st.rerun()` after successful connection
- Graceful fallback between environments
- Status messages only shown once per session

#### Data Collection Functions

**`get_expensive_queries()`** (Lines 135-187)
- Identifies top 20 most expensive queries
- Filters: Last 30 days, successful executions only
- Partitions by warehouse, ranks by total elapsed time
- Calculates cost factors based on warehouse size
- Returns: warehouse name, user, duration, cost metrics, sample query ID

**`get_query_details(query_id, conn)`** (Lines 189-230)
- Retrieves comprehensive metadata for a specific query by ID
- Includes: execution times, memory spills, partition scans, row counts
- Provides timing breakdown (compilation, execution, queued, blocked)

**`get_query_text_by_user_warehouse(user_name, warehouse_name, conn)`** (Lines 232-278)
- Fallback function for when query ID isn't available
- Retrieves most expensive query for a user-warehouse combination
- Last 30 days, successful executions only

#### Data Processing Functions

**`extract_tables_from_sql(sql_text)`** (Lines 280-306)
- Uses regex patterns to parse SQL and identify table names
- Supports formats: `database.schema.table`, `schema.table`, `table`
- Handles backticks and quoted identifiers
- Filters out SQL keywords and aliases
- Returns sorted list of unique table names

**`get_table_metadata(table_name, conn)`** (Lines 308-442)
- Queries `INFORMATION_SCHEMA.COLUMNS` for column definitions
- Retrieves `INFORMATION_SCHEMA.TABLES` for statistics (row count, bytes, retention)
- Queries `INFORMATION_SCHEMA.TABLE_CONSTRAINTS` for constraints/keys
- Returns comprehensive metadata dictionary
- Includes error handling with warnings

#### AI Analysis Function

**`call_cortex_ai(query_text, execution_metadata, tables_metadata, conn)`** (Lines 444-543)
- Constructs detailed prompt with query, execution stats, and metadata
- Calls `SNOWFLAKE.CORTEX.COMPLETE` with Claude Sonnet model
- Handles JSON response parsing
- Structures prompt with three main sections:
  1. SQL optimizations (rewrites, JOINs, WHERE clauses, clustering)
  2. Warehouse optimizations (size, multi-clustering, auto-suspend)
  3. General best practices
- Returns formatted optimization suggestions

#### Main Application Flow

**Main Interface** (Lines 545+)
1. **Two-Column Layout:**
   - **Left Column:** Interactive dataframe with warehouse, user, query count, and duration
   - **Right Column:** SQL details panel (displayed when row selected)
2. **Query Analysis Workflow:**
   - User clicks row in dataframe to see SQL code
   - Execution metrics displayed (cost factor, first/last execution times)
   - SQL code view with syntax highlighting
   - "Analyser cette requête avec l'IA" button triggers:
     - Table extraction via `extract_tables_from_sql()`
     - Metadata retrieval for each table via `get_table_metadata()`
     - AI analysis via `call_cortex_ai()` with execution metadata from selected_row
     - Display optimization suggestions

## Application Flow

### User Interaction Flow

#### Streamlit in Snowflake (SiS) Mode
1. **Initialization:** App starts, automatically connects via `st.connection("snowflake")`
2. **Data Loading:** "Actualiser la liste" button → `get_expensive_queries()` → Display DataFrame
3. **Query Selection:** User clicks on a row in the interactive dataframe
4. **Analysis Trigger:** "Analyser cette requête avec l'IA" button → Multi-step processing:
   - Extract tables via `extract_tables_from_sql()` (using SQL text from selected_row)
   - Fetch metadata via `get_table_metadata()` for each table
   - Call AI via `call_cortex_ai()` with execution metadata from selected_row
   - Display results in Streamlit UI

#### Local Development Mode
1. **Initialization:** App detects local environment, loads `~/.snowflake/config.toml`
2. **Connection Selection:** User selects connection from sidebar dropdown
3. **Connection Details:** Sidebar displays connection parameters (account, user, database, etc.)
4. **Connect:** User clicks "Se connecter" button to establish connection
5. **Data Loading & Analysis:** Same flow as SiS mode (steps 2-4 above)

### Key Control Flow Points

```python
# Line 448: Check conn is not None (st.stop() if not)
# Line 461: Check if df_queries is empty
# Line 500: Check if sample_query_id exists
# Line 538: Check if tables extracted successfully
```

## Design Patterns & Conventions

### Design Patterns

| Pattern | Usage | Example |
|---------|-------|---------|
| **Caching** | Performance optimization | `@st.cache_resource` for session init |
| **Error Handling** | Graceful degradation | Try-except with Streamlit warnings/errors |
| **Lazy Loading** | User-driven data fetching | Tables only queried when "Analyze" button clicked |
| **Metadata Enrichment** | Context for AI analysis | Collecting execution stats + table stats before AI call |

### SQL Patterns

- **Parameterized Queries:** Uses `?` placeholders with `cursor.execute(query, params)` for safety
- **Window Functions:** `ROW_NUMBER() OVER (PARTITION BY warehouse_name)` for ranking
- **CTEs (Common Table Expressions):** Subquery optimization using `WITH` clause
- **Multi-part Table Names:** Supports `database.schema.table` resolution

### Code Conventions

- **French Documentation:** README, comments, and UI strings in French
- **Type Hints:** Basic typing used (`List`, `Dict`, `str`)
- **Error Messages:** Bilingual approach (French UI, exception messages)
- **Regex Patterns:** List-based pattern matching for flexibility

## Snowflake Integration

### Required Permissions

```sql
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE YOUR_ROLE;
-- For Cortex AI access and Account Usage access
-- Information Schema access is usually inherited
```

### Connection Methods

#### Streamlit in Snowflake (Production)
- Uses native `st.connection("snowflake")`
- Automatically authenticated within Snowflake environment
- No manual credential management required

#### Local Development
- Reads connection parameters from `~/.snowflake/config.toml`
- Supports multiple named connections in TOML format
- Interactive connection selection via Streamlit sidebar
- Connection details displayed (excluding passwords)

### Local Development Setup

To run this application locally for development:

1. **Create configuration file:** `~/.snowflake/config.toml`

```toml
[connection_name]
account = "your_account"
user = "your_username"
password = "your_password"
database = "your_database"
schema = "your_schema"
warehouse = "your_warehouse"
role = "your_role"
authenticator = "snowflake"  # optional, defaults to "snowflake"
client_session_keep_alive = true  # optional
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Run the application:**
```bash
streamlit run app.py
```

4. **Connect:**
   - Select your connection from the sidebar dropdown
   - Review connection parameters
   - Click "Se connecter" to establish connection
   - Application will remember the connection in session state

**TOML Configuration Format:**
- Multiple connections supported (e.g., `[dev]`, `[prod]`, `[staging]`)
- All standard Snowflake connection parameters supported
- Passwords can be plain text or JWT tokens
- File should have restricted permissions (recommended: `chmod 600 ~/.snowflake/config.toml`)

## Security Considerations

- **SQL Injection Prevention:** Uses parameter binding for all queries
- **Prompt Escaping:** Cortex AI prompts escape single quotes (`replace("'", "''")`)
- **Credential Management:**
  - **SiS Mode:** Uses native authentication, no credentials stored
  - **Local Mode:** Credentials stored in `~/.snowflake/config.toml` (should be chmod 600)
  - Passwords never displayed in UI
- **Read-Only Operations:** Application only reads data, does not modify

## Strengths & Limitations

### Strengths

- **Dual Environment Support:** Seamless operation in both SiS and local development
- Clean separation of concerns (data retrieval, processing, AI, UI)
- Robust error handling with user-friendly messages
- Support for flexible table naming conventions
- Intelligent prompt engineering for Claude Sonnet
- Performance optimizations (caching, lazy loading)
- Interactive connection management for local development
- Multiple connection profiles supported via TOML configuration

### Limitations & Considerations

- Regex-based table extraction may miss complex SQL patterns (CTEs, subqueries)
- Single-file design limits reusability (but intentional for SiS)
- Hardcoded French language (adaptable for i18n if needed)
- No persistent storage of analysis results
- Depends on Cortex AI availability and quota
- **Local Mode:** Requires manual connection via button click (by design for explicit user control)
- **Local Mode:** Config file stores passwords in plain text or tokens (ensure file permissions)

## Development Guidelines

### Making Changes

1. **Read First:** Always read `app.py` before making modifications
2. **Test in SiS:** This app is designed for Streamlit in Snowflake, test in that environment
3. **Maintain Single File:** Keep the single-file architecture for SiS deployment simplicity
4. **French UI:** Maintain French language for UI elements unless internationalizing
5. **Error Handling:** Always include try-except blocks with user-friendly messages

### Common Modification Scenarios

**Adding New Query Metrics:**
- Modify `get_query_details()` to add columns from `QUERY_HISTORY`
- Update display logic in main interface section

**Changing AI Model:**
- Modify model name in `call_cortex_ai()` function
- Adjust prompt if model has different capabilities

**Adding Table Statistics:**
- Extend `get_table_metadata()` to query additional `INFORMATION_SCHEMA` views
- Update metadata display in main interface

**Supporting Additional SQL Patterns:**
- Add regex patterns to `extract_tables_from_sql()`
- Test with complex SQL examples

## Deployment

### Prerequisites

1. Snowflake account with Account Usage access
2. Cortex AI enabled in your account
3. Streamlit in Snowflake available
4. Appropriate role permissions (see Required Permissions section)

### Deployment Steps

1. Upload `app.py` to Snowflake stage or use SiS file upload
2. Install dependencies from `requirements.txt`
3. Create Streamlit app in Snowflake UI
4. Grant required permissions to the app's role
5. Launch and test

## Troubleshooting

### Common Issues

#### Connection Issues

**"Connection not available" (SiS Mode)**
- Ensure running in Streamlit in Snowflake environment
- Check that `st.connection("snowflake")` is supported in your SiS version

**"Config file not found" (Local Mode)**
- Verify `~/.snowflake/config.toml` exists
- Check file path is correct: `/Users/yourusername/.snowflake/config.toml` (macOS/Linux) or `C:\Users\yourusername\.snowflake\config.toml` (Windows)
- Ensure proper TOML syntax in config file

**"Connection failed" (Local Mode)**
- Verify account name is correct (without `.snowflakecomputing.com`)
- Check username and password are correct
- Ensure user has appropriate permissions
- Verify warehouse is running and accessible
- Check network connectivity to Snowflake

**"No connections available" (Local Mode)**
- Ensure config.toml has at least one `[connection_name]` section
- Verify TOML syntax is valid (no parsing errors)

#### Data Issues

**"No data returned"**
- Verify Account Usage permissions are granted
- Check that queries exist in last 30 days
- Confirm warehouse names are correct
- Ensure database/schema context is correct

**"Cortex AI error"**
- Verify Cortex AI is enabled in your account
- Check quota limits for Cortex AI usage
- Ensure Claude Sonnet model is available
- Confirm role has access to `SNOWFLAKE.CORTEX` functions

**"Table metadata not found"**
- Check table names are correctly extracted
- Verify Information Schema access permissions
- Confirm tables exist in accessible schemas
- Ensure proper database context is set in connection

## Future Enhancement Ideas

- Add date range selection for query history
- Support multiple languages (i18n)
- Export optimization reports to PDF/CSV
- Track optimization implementation and re-run analysis
- Add cost estimates for optimization recommendations
- Support custom warehouse sizing recommendations
- Add query complexity scoring
- Integrate with query history trends/dashboards

---

**Last Updated:** 2025-11-30
**Current Branch:** kind-euler
**Main Repository:** /Users/laurentletourmy/dev2/finopt
