import os
import re
import hashlib
import sqlite3
import logging
from datetime import datetime

# Import the database utility function from our other script
from db_utils import create_connection

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_dummy_data(master_folder):
    """
    Creates a dummy folder structure and data in the .txt format for testing.
    This version is focused only on the response logs needed for ingestion.
    """
    if not os.path.exists(master_folder):
        logging.info(f"Creating master folder: {master_folder}")
        os.makedirs(master_folder)

    structure = {
        "model_group_1": {
            "session_A.txt": """[task1-2025-06-15-09-30-01]
input::An input for task 1.
context::["Some context for task 1."]
response::{"text": "model 1 response to task 1"}
---END_SECTION---
[task2-2025-06-15-09-32-15]
input::An input for task 2.
context::["Some context for task 2."]
response::{"text": "model 1 response to task 2"}
---END_SECTION---
""",
            "session_B.txt": """[task1-2025-06-15-09-31-05]
input::An input for task 1.
context::["Some context for task 1."]
response::{"text": "a different model 1 response to task 1"}
---END_SECTION---
"""
        },
        "model_group_2": {
            "session_C.txt": """[task1-2025-06-15-09-30-02]
input::An input for task 1.
context::["Some context for task 1."]
response::{"text": "model 2 response to task 1"}
---END_SECTION---
[task3-2025-06-15-09-35-40]
input::An input for task 3.
context::["Some context for task 3."]
response::{"text": "model 2 response to task 3"}
---END_SECTION---
"""
        }
    }

    for group, sessions in structure.items():
        group_path = os.path.join(master_folder, group)
        os.makedirs(group_path, exist_ok=True)
        for session_name, content in sessions.items():
            with open(os.path.join(group_path, session_name), 'w') as f:
                f.write(content.strip())
    logging.info("Dummy data created successfully.")


def parse_custom_log_format(file_path):
    """
    Parses the custom 'key::value' log format, handling multi-line JSON.
    (Reused from the original script)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
        return []

    parsed_sections = []
    sections = content.strip().split('---END_SECTION---')

    for section_text in sections:
        section_text = section_text.strip()
        if not section_text:
            continue

        lines = section_text.split('\n')
        header = lines[0].strip()[1:-1] # Get content inside brackets
        
        section_data = {'task_key': header}
        current_key = None
        current_value_lines = []

        for line in lines[1:]:
            if '::' in line:
                if current_key:
                    section_data[current_key] = '\n'.join(current_value_lines).strip()
                parts = line.split('::', 1)
                current_key = parts[0].strip()
                current_value_lines = [parts[1].strip()]
            elif current_key:
                current_value_lines.append(line.strip())
        
        if current_key:
            section_data[current_key] = '\n'.join(current_value_lines).strip()
        
        parsed_sections.append(section_data)
    return parsed_sections


def insert_response(conn, response_data):
    """
    Inserts a single response record into the database.
    Uses 'INSERT OR IGNORE' to prevent creating duplicates based on the
    unique index on (group_name, session_name, task_key).

    Args:
        conn (sqlite3.Connection): An active SQLite connection.
        response_data (dict): A dictionary containing all the data for the new row.

    Returns:
        int: The rowid of the newly inserted row, or None if it was ignored.
    """
    sql = """
    INSERT OR IGNORE INTO responses (
        problem_hash, group_name, session_name, task_key, input, context, 
        model_response, ingested_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """
    try:
        cursor = conn.cursor()
        cursor.execute(sql, tuple(response_data.values()))
        # Return the last inserted rowid if a row was actually inserted
        return cursor.lastrowid if cursor.rowcount > 0 else None
    except sqlite3.Error as e:
        logging.error(f"Failed to insert data for task {response_data.get('task_key')}: {e}")
        return None


def ingest_log_files(db_file, master_folder):
    """
    Walks the data folder, parses all .txt files, and ingests them into the DB.
    """
    logging.info(f"--- Starting Data Ingestion from '{master_folder}' ---")
    conn = create_connection(db_file)
    if not conn:
        logging.error("Could not create database connection. Aborting ingestion.")
        return

    newly_inserted_count = 0
    ignored_count = 0

    # Walk through all groups and sessions in the master folder
    for group_name in os.listdir(master_folder):
        group_path = os.path.join(master_folder, group_name)
        if os.path.isdir(group_path):
            for session_name in os.listdir(group_path):
                if session_name.endswith(".txt"):
                    file_path = os.path.join(group_path, session_name)
                    parsed_data = parse_custom_log_format(file_path)

                    for task_data in parsed_data:
                        # Prepare data for insertion
                        input_val = task_data.get('input', '')
                        context_val = task_data.get('context', '')
                        
                        # Calculate the problem_hash for grouping
                        id_string = str(input_val) + str(context_val)
                        problem_hash = hashlib.sha256(id_string.encode('utf-8')).hexdigest()

                        record_to_insert = {
                            "problem_hash": problem_hash,
                            "group_name": group_name,
                            "session_name": session_name.replace('.txt', ''),
                            "task_key": task_data.get('task_key'),
                            "input": input_val,
                            "context": context_val,
                            "model_response": task_data.get('response', ''),
                            # UPDATED LINE: Convert datetime object to ISO 8601 string format
                            "ingested_at": datetime.now().isoformat()
                        }
                        
                        # Insert the record and check if it was new
                        inserted_id = insert_response(conn, record_to_insert)
                        if inserted_id:
                            newly_inserted_count += 1
                            logging.debug(f"Inserted new record with row_id {inserted_id}")
                        else:
                            ignored_count += 1
    
    # Commit all changes and close the connection
    conn.commit()
    conn.close()
    
    logging.info("--- Data Ingestion Complete ---")
    logging.info(f"Summary: {newly_inserted_count} new records inserted, {ignored_count} records ignored as duplicates.")


if __name__ == '__main__':
    DB_FILE = "judgements.db"
    MASTER_DATA_FOLDER = "pretend_data_txt"

    # Step 1: Generate dummy data for demonstration purposes.
    # In a real scenario, this folder would already exist with your data.
    create_dummy_data(MASTER_DATA_FOLDER)
    
    # Step 2: Run the ingestion process.
    # This is idempotent and can be run multiple times.
    ingest_log_files(DB_FILE, MASTER_DATA_FOLDER)
    
    # You can run it again to see that it ignores all records.
    print("\nRunning ingestion a second time to demonstrate idempotency...")
    ingest_log_files(DB_FILE, MASTER_DATA_FOLDER)