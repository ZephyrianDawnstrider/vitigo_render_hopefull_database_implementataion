import sqlite3
import pyodbc

# MSSQL connection details for Windows Authentication
MSSQL_SERVER = 'localhost'
MSSQL_DATABASE = 'vitigo_render_database'

# Connect to SQLite
sqlite_conn = sqlite3.connect("db.sqlite3")
sqlite_cursor = sqlite_conn.cursor()

# Connect to SQL Server using Windows Authentication
mssql_conn = pyodbc.connect(
    f'DRIVER={{ODBC Driver 17 for SQL Server}};'
    f'SERVER={MSSQL_SERVER};'
    f'DATABASE={MSSQL_DATABASE};'
    f'Trusted_Connection=yes;'
)
mssql_cursor = mssql_conn.cursor()

def get_identity_columns(table_name):
    query = """
    SELECT c.name
    FROM sys.columns c
    JOIN sys.tables t ON c.object_id = t.object_id
    WHERE t.name = ? AND c.is_identity = 1
    """
    mssql_cursor.execute(query, (table_name,))
    return [row[0] for row in mssql_cursor.fetchall()]

def escape_name(name):
    return f'[{name}]'

# Get list of tables from SQLite
sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
tables = [row[0] for row in sqlite_cursor.fetchall()]

for table in tables:
    print(f"Migrating table: {table}")

    # Get column info
    sqlite_cursor.execute(f"PRAGMA table_info({table})")
    columns_info = sqlite_cursor.fetchall()
    columns = [col[1] for col in columns_info]  # column names

    # Escape table and column names
    escaped_table = escape_name(table)
    escaped_columns = [escape_name(col) for col in columns]

    # Fetch all rows from SQLite table
    sqlite_cursor.execute(f"SELECT * FROM {table}")
    rows = sqlite_cursor.fetchall()

    # Prepare insert statement for MSSQL
    columns_str = ', '.join(escaped_columns)
    placeholders = ', '.join(['?' for _ in columns])
    insert_sql = f"INSERT INTO {escaped_table} ({columns_str}) VALUES ({placeholders})"

    identity_columns = get_identity_columns(table)
    has_identity = len(identity_columns) > 0

    if has_identity:
        # Enable IDENTITY_INSERT ON
        mssql_cursor.execute(f"SET IDENTITY_INSERT {escaped_table} ON")

    # Insert rows into MSSQL
    for row in rows:
        try:
            mssql_cursor.execute(insert_sql, row)
        except Exception as e:
            print(f"Error inserting row into {table}: {e}")

    if has_identity:
        # Disable IDENTITY_INSERT OFF
        mssql_cursor.execute(f"SET IDENTITY_INSERT {escaped_table} OFF")

    mssql_conn.commit()
    print(f"Finished migrating table: {table}")

sqlite_conn.close()
mssql_conn.close()
print("Migration completed.")
