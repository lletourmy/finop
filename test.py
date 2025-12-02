"""Quick test: connect to Snowflake and execute a query"""
import toml, snowflake.connector, pandas as pd
from pathlib import Path

def sql(cursor, sql, msg):
    print(msg)
    cursor.execute(sql)
    print(pd.DataFrame(cursor.fetchall(), columns=[desc[0] for desc in cursor.description]))
    
p = toml.load(Path.home() / '.snowflake' / 'config.toml')['clarins_cost']
for key in p:
    print(f"{key} : {p[key]}")
print("Connecting...")
conn = snowflake.connector.connect(account=p['account'], user=p['user'], password=p['password'], database=p['database'], schema=p['schema'], warehouse=p['warehouse'], role=p.get('role'), authenticator=p.get('authenticator', 'snowflake'))
cursor = conn.cursor()
sql(cursor, "SHOW WAREHOUSES", "Debugging warehouses...")
sql(cursor, "SELECT 1;", "Executing test query...")
sql(cursor, "SELECT CURRENT_ROLE(), CURRENT_WAREHOUSE(), CURRENT_USER();", "Debugging query...")
#sql(cursor, "USE WAREHOUSE DEV_WH;", "Using default warehouse...")
sql(cursor, "SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY LIMIT 1;", "Executing query_history query...")
conn.close()
