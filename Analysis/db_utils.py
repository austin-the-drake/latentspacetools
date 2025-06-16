import sqlite3
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_connection(db_file):
    """
    Create a database connection to a SQLite database specified by db_file.

    Args:
        db_file (str): Path to the database file.

    Returns:
        sqlite3.Connection: Connection object or None if an error occurs.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        logging.info(f"Successfully connected to SQLite database: {db_file}")
        return conn
    except sqlite3.Error as e:
        logging.error(f"Error connecting to database: {e}")
        return None

def create_db_tables(conn):
    """
    Create the necessary tables and indexes in the database.
    Uses 'IF NOT EXISTS' to be safely runnable multiple times.

    Args:
        conn (sqlite3.Connection): An active SQLite connection.
    """
    if not conn:
        logging.error("Connection object is not valid. Cannot create tables.")
        return

    create_table_sql = """
    CREATE TABLE IF NOT EXISTS responses (
        row_id INTEGER PRIMARY KEY AUTOINCREMENT,
        problem_hash TEXT NOT NULL,
        group_name TEXT NOT NULL,
        session_name TEXT NOT NULL,
        task_key TEXT NOT NULL,
        input TEXT,
        context TEXT,
        model_response TEXT,
        status TEXT NOT NULL DEFAULT 'pending',
        judge_scores_json TEXT,
        judge_rationales_json TEXT,
        judged_at DATETIME,
        ingested_at DATETIME NOT NULL
    );
    """
    create_unique_source_index_sql = """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_source
    ON responses (group_name, session_name, task_key);
    """
    create_problem_hash_index_sql = """
    CREATE INDEX IF NOT EXISTS idx_problem_hash
    ON responses (problem_hash);
    """
    try:
        cursor = conn.cursor()
        logging.info("Creating 'responses' table if it doesn't exist...")
        cursor.execute(create_table_sql)
        logging.info("Creating unique index 'idx_source' for data ingestion...")
        cursor.execute(create_unique_source_index_sql)
        logging.info("Creating index 'idx_problem_hash' for analysis...")
        cursor.execute(create_problem_hash_index_sql)
        conn.commit()
        logging.info("Database tables and indexes are set up successfully.")
    except sqlite3.Error as e:
        logging.error(f"Error creating database objects: {e}")

# --- New Utility Functions ---

def clear_all_responses(conn):
    """
    Deletes all records from the 'responses' table and resets the autoincrement sequence.
    
    Args:
        conn (sqlite3.Connection): An active SQLite connection.
    """
    sql_delete = "DELETE FROM responses;"
    sql_reset_sequence = "DELETE FROM sqlite_sequence WHERE name='responses';"
    try:
        cursor = conn.cursor()
        logging.warning("Clearing all records from the 'responses' table.")
        cursor.execute(sql_delete)
        # Reset the autoincrement counter so new records start from 1
        cursor.execute(sql_reset_sequence)
        conn.commit()
        logging.info("Table 'responses' has been cleared.")
    except sqlite3.Error as e:
        logging.error(f"Failed to clear table: {e}")

def get_record_count(conn):
    """Gets the total number of records in the 'responses' table."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM responses;")
        count = cursor.fetchone()[0]
        logging.info(f"Total records in database: {count}")
        return count
    except sqlite3.Error as e:
        logging.error(f"Failed to count records: {e}")
        return -1

def get_status_breakdown(conn):
    """Gets the count of records for each status."""
    sql = "SELECT status, COUNT(*) FROM responses GROUP BY status;"
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        logging.info("Status breakdown:")
        if not rows:
            logging.info("  No records found.")
        for row in rows:
            logging.info(f"  - Status: {row[0]}, Count: {row[1]}")
        return rows
    except sqlite3.Error as e:
        logging.error(f"Failed to get status breakdown: {e}")
        return []

def show_all_records(conn, limit=10):
    """Fetches and prints records from the responses table."""
    sql = f"SELECT row_id, status, group_name, session_name, task_key FROM responses LIMIT ?;"
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (limit,))
        rows = cursor.fetchall()
        logging.info(f"--- Showing first {limit} records ---")
        if not rows:
            logging.info("No records to show.")
        for row in rows:
            print(f"  row_id: {row[0]}, status: {row[1]}, group: {row[2]}, session: {row[3]}, task: {row[4]}")
        print("-" * 20)
        return rows
    except sqlite3.Error as e:
        logging.error(f"Failed to fetch records: {e}")
        return []


if __name__ == '__main__':
    DB_FILE = "judgements.db"
    
    logging.info(f"--- Running Full Utility Demo for {DB_FILE} ---")
    connection = create_connection(DB_FILE)

    if connection:
        # 1. Setup the database tables and indexes
        create_db_tables(connection)
        
        # 2. Show initial state (should be empty or have old data)
        print("\n--- 1. Initial State ---")
        get_record_count(connection)
        
        # 3. Clear any existing data for a fresh start
        print("\n--- 2. Clearing Database ---")
        clear_all_responses(connection)
        get_record_count(connection)
        
        # 4. We would now run ingest_data.py to populate the DB.
        #    For this demo, we'll just log a message.
        print("\n--- 3. In a real workflow, you would now run 'ingest_data.py' ---")
        logging.info("To see the utilities with data, please run 'ingest_data.py' and then run this script again.")

        # 5. Show final state
        print("\n--- 4. Current State (after potential ingestion) ---")
        get_record_count(connection)
        get_status_breakdown(connection)
        show_all_records(connection, limit=5)
        
        connection.close()
        logging.info("--- Demo complete. Connection closed. ---")
    else:
        logging.error("--- Demo failed. Could not connect to database. ---")