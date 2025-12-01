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

### Layered Architecture (Refactored)

```
User Interface Layer (Streamlit - app.py)
        ↓
Business Logic Layer (QueryOptimizer class)
        ↓
Data Access Layer (SnowflakeConnector class)
        ↓
Snowflake Backend (Account Usage, Information Schema, Cortex API)
```

### Class-Based Architecture

The application has been refactored into a modular, class-based architecture:

1. **SnowflakeConnector** (`snowflake_connector.py`):
   - Manages Snowflake connections (SiS and local modes)
   - Executes SQL queries
   - Handles Cortex AI calls
   - Provides connection abstraction

2. **QueryOptimizer** (`query_optimizer.py`):
   - Retrieves expensive queries
   - Extracts table names from SQL
   - Fetches table metadata
   - Builds optimization prompts
   - Orchestrates query optimization workflow

3. **Streamlit UI** (`app.py`):
   - User interface and interaction
   - Data visualization
   - Session state management
   - Coordinates connector and optimizer

### Deployment Context

This application supports both **Streamlit in Snowflake (SiS)** and **local development**:

- **Streamlit in Snowflake (SiS):** Uses native `st.connection("snowflake")` for automatic authentication
- **Local Development:** Reads connection parameters from `~/.snowflake/config.toml` and provides a UI for connection selection

The modular class-based design improves maintainability, testability, and code reusability.

## Project Structure

```
/
├── app.py                      # Main Streamlit application (refactored)
├── snowflake_connector.py      # Snowflake connection and query execution
├── query_optimizer.py          # Query optimization business logic
├── app_old.py                  # Backup of original single-file app
├── README.md                   # Project documentation (French)
├── requirements.txt            # Python dependencies
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

### Class: SnowflakeConnector (snowflake_connector.py)

This class encapsulates all Snowflake connection and data access logic.

#### Methods

**`__init__(connection=None)`**
- Initializes the connector with optional existing connection

**`load_config_file()` (static, cached)**
- Loads available Snowflake connections from `~/.snowflake/config.toml`
- Returns dictionary of connection configurations
- Uses `@st.cache_data` for performance
- Error handling for missing or invalid config files

**`create_connection(_conn_params)` (static, cached)**
- Creates a Snowflake connection with provided parameters
- Uses `@st.cache_resource` for connection pooling
- Wraps `snowflake.connector.connect()` in compatibility class
- Returns `SnowflakeConnectionWrapper` for API compatibility

**`init_connection()`**
- Dual-mode connection initialization:
  - **SiS Mode:** Uses `st.connection("snowflake")` for native Streamlit in Snowflake
  - **Local Mode:** Loads connections from `~/.snowflake/config.toml` and provides UI for selection
- Features for local development:
  - Checks `st.session_state` for existing connection first
  - Displays all available connections in sidebar selectbox
  - Shows connection details (account, user, database, schema, warehouse, role)
  - Provides "Connect" button to establish connection
  - Stores connection in `st.session_state` for persistence
  - Uses `st.rerun()` after successful connection
- Graceful fallback between environments

**`get_connection()`**
- Returns the current active connection

**`execute_query(query, params=None)`**
- Executes a SQL query and returns a pandas DataFrame
- Supports parameterized queries for security
- Normalizes column names to lowercase
- Error handling with Streamlit error messages

**`call_cortex_ai(prompt, model='claude-3-5-sonnet')`**
- Calls Snowflake Cortex AI with a prompt
- Escapes apostrophes for SQL injection prevention
- Returns AI-generated response text
- Error handling for Cortex AI failures

### Class: QueryOptimizer (query_optimizer.py)

This class contains all business logic for query optimization.

#### Methods

**`__init__(connector: SnowflakeConnector)`**
- Initializes the optimizer with a SnowflakeConnector instance

**`get_expensive_queries()`**
- Identifies top 20 most expensive queries
- Filters: Last 30 days, successful executions only
- Partitions by warehouse, ranks by total elapsed time
- Calculates cost factors based on warehouse size
- Returns: warehouse name, user, duration, cost metrics, sample query ID

**`get_query_details(query_id)`**
- Retrieves comprehensive metadata for a specific query by ID
- Includes: execution times, memory spills, partition scans, row counts
- Provides timing breakdown (compilation, execution, queued, blocked)

**`extract_tables_from_sql(sql_text)` (static)**
- Uses regex patterns to parse SQL and identify table names
- Supports formats: `database.schema.table`, `schema.table`, `table`
- Handles backticks and quoted identifiers
- Filters out SQL keywords and aliases
- Returns sorted list of unique table names

**`get_table_metadata(table_name)`**
- Retrieves metadata for a specific table
- Queries: COLUMNS, TABLES, TABLE_CONSTRAINTS from INFORMATION_SCHEMA
- Returns dictionary with: columns, statistics, constraints
- Error handling with warnings for missing tables

**`build_optimization_prompt(query_text, execution_metadata, tables_metadata)`**
- Constructs the optimization prompt for Cortex AI
- Includes: SQL query, execution metrics, table metadata
- Structured with three main sections:
  1. SQL optimizations (rewrites, JOINs, WHERE clauses, clustering)
  2. Warehouse optimizations (size, multi-clustering, auto-suspend)
  3. General best practices
- Returns formatted prompt string

**`optimize_query(query_text, execution_metadata, tables_metadata, model='claude-3-5-sonnet')`**
- Main orchestration method for query optimization
- Builds prompt using `build_optimization_prompt()`
- Calls Cortex AI via connector
- Returns optimization suggestions

### Main Application (app.py)

The Streamlit application coordinates the UI and uses the classes above.

#### Application Structure

**Initialization:**
- Configures Streamlit page (title, icon, layout)
- Creates `SnowflakeConnector` instance using `@st.cache_resource`
- Initializes connection via `connector.init_connection()`
- Creates `QueryOptimizer` instance with the connector
- Stops execution if no connection available

**Main Interface:**
1. **Data Loading Section:**
   - "Actualiser la liste" button to refresh queries
   - Fetches expensive queries via `optimizer.get_expensive_queries()`
   - Stores results in `st.session_state['df_queries']`
   - Converts numeric columns and datetime fields

2. **Two-Column Layout:**
   - **Left Column:** Interactive dataframe with warehouse, user, query count, and duration
   - **Right Column:** SQL details panel (displayed when row selected)
     - Shows cost factor, first/last execution times
     - Displays SQL code with syntax highlighting
     - "Analyser cette requête avec l'IA" button

3. **AI Analysis Section (below columns):**
   - Shows tables identified
   - Displays optimization suggestions from Cortex AI
   - Results stored in `st.session_state['ai_analysis']`

**Query Analysis Workflow:**
- User clicks row in dataframe to see SQL code
- Clicks "Analyser cette requête avec l'IA" button
- Process:
  1. Extract tables via `optimizer.extract_tables_from_sql()`
  2. Fetch metadata via `optimizer.get_table_metadata()` for each table
  3. Build execution metadata from selected row
  4. Call `optimizer.optimize_query()` with all context
  5. Store and display results below the two-column layout

## Application Flow

### User Interaction Flow

#### Streamlit in Snowflake (SiS) Mode
1. **Initialization:**
   - `SnowflakeConnector` initialized
   - Automatically connects via `st.connection("snowflake")`
   - `QueryOptimizer` created with connector
2. **Data Loading:**
   - "Actualiser la liste" button clicked
   - `optimizer.get_expensive_queries()` fetches data
   - Display DataFrame in left column
3. **Query Selection:** User clicks on a row in the interactive dataframe
4. **Analysis Trigger:** "Analyser cette requête avec l'IA" button → Multi-step processing:
   - Extract tables via `optimizer.extract_tables_from_sql()`
   - Fetch metadata via `optimizer.get_table_metadata()` for each table
   - Call `optimizer.optimize_query()` with execution metadata
   - Display results below two-column layout

#### Local Development Mode
1. **Initialization:**
   - `SnowflakeConnector` detects local environment
   - Loads `~/.snowflake/config.toml`
2. **Connection Selection:** User selects connection from sidebar dropdown
3. **Connection Details:** Sidebar displays connection parameters
4. **Connect:** User clicks "Se connecter" button
   - `connector.create_connection()` establishes connection
   - `QueryOptimizer` created with connector
5. **Data Loading & Analysis:** Same flow as SiS mode (steps 2-4 above)

## Design Patterns & Conventions

### Design Patterns

| Pattern | Usage | Example |
|---------|-------|---------|
| **Class-Based Architecture** | Separation of concerns | SnowflakeConnector (data access), QueryOptimizer (business logic) |
| **Dependency Injection** | Loose coupling | QueryOptimizer receives SnowflakeConnector instance |
| **Caching** | Performance optimization | `@st.cache_resource` for connector, `@st.cache_data` for config |
| **Error Handling** | Graceful degradation | Try-except with Streamlit warnings/errors |
| **Lazy Loading** | User-driven data fetching | Tables only queried when "Analyze" button clicked |
| **Metadata Enrichment** | Context for AI analysis | Collecting execution stats + table stats before AI call |
| **Static Methods** | Utility functions | `extract_tables_from_sql()`, `load_config_file()` |

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

- **Modular Class-Based Architecture:** Clean separation between data access and business logic
- **Dual Environment Support:** Seamless operation in both SiS and local development
- **Testability:** Classes can be unit tested independently
- **Reusability:** SnowflakeConnector and QueryOptimizer can be used in other projects
- **Maintainability:** Clear separation of concerns makes code easier to modify
- **Robust error handling:** User-friendly messages throughout
- **Support for flexible table naming conventions:** Handles various SQL patterns
- **Intelligent prompt engineering:** Structured prompts for Claude Sonnet
- **Performance optimizations:** Caching, lazy loading, session state management
- **Interactive connection management:** Easy local development setup
- **Multiple connection profiles:** TOML configuration for different environments

### Limitations & Considerations

- Regex-based table extraction may miss complex SQL patterns (CTEs, subqueries)
- Hardcoded French language (adaptable for i18n if needed)
- No persistent storage of analysis results
- Depends on Cortex AI availability and quota
- **Local Mode:** Requires manual connection via button click (by design for explicit user control)
- **Local Mode:** Config file stores passwords in plain text or tokens (ensure file permissions)

## Development Guidelines

### Making Changes

1. **Understand the Architecture:** Review the class structure before modifying
2. **Modify the Right Class:**
   - **Connection/Query changes:** Update `SnowflakeConnector`
   - **Business logic changes:** Update `QueryOptimizer`
   - **UI changes:** Update `app.py`
3. **Test Both Environments:** Test in both SiS and local development modes
4. **French UI:** Maintain French language for UI elements unless internationalizing
5. **Error Handling:** Always include try-except blocks with user-friendly messages
6. **Type Hints:** Add type hints for new methods

### Common Modification Scenarios

**Adding New Query Metrics:**
- Modify `get_expensive_queries()` SQL in `QueryOptimizer` class
- Add columns from `QUERY_HISTORY`
- Update display logic in `app.py`

**Changing AI Model:**
- Modify default model parameter in `QueryOptimizer.optimize_query()` method
- Adjust prompt in `build_optimization_prompt()` if model has different capabilities

**Adding Table Statistics:**
- Extend `QueryOptimizer.get_table_metadata()` method
- Query additional `INFORMATION_SCHEMA` views
- Update metadata display in `app.py`

**Supporting Additional SQL Patterns:**
- Add regex patterns to `QueryOptimizer.extract_tables_from_sql()` static method
- Test with complex SQL examples

**Adding New Connector Method:**
- Add method to `SnowflakeConnector` class
- Follow existing patterns (error handling, DataFrame normalization)
- Update CLAUDE.MD documentation

## Deployment

### Prerequisites

1. Snowflake account with Account Usage access
2. Cortex AI enabled in your account
3. Streamlit in Snowflake available
4. Appropriate role permissions (see Required Permissions section)

### Deployment Steps

**For Streamlit in Snowflake:**
1. Upload all Python files to Snowflake stage:
   - `app.py`
   - `snowflake_connector.py`
   - `query_optimizer.py`
2. Install dependencies from `requirements.txt`
3. Create Streamlit app in Snowflake UI
4. Grant required permissions to the app's role
5. Launch and test

**For Local Development:**
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Create `~/.snowflake/config.toml` with connection parameters
4. Run: `streamlit run app.py`
5. Select connection and click "Se connecter"

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
