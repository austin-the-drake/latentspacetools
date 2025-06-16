import os
import re
import json
import sys
import sqlite3
import logging
from datetime import datetime
import google.generativeai as genai

# Import utilities from our other scripts
# Note: Ensure these files exist in the same directory.
from db_utils import create_connection, get_status_breakdown
from response_validation import validate_elemental_data, validate_spell_script, validate_ca_script

# --- CONFIGURE GEMINI API ---
# For security, the API key is read from an environment variable.
# Ensure you have set `export GOOGLE_API_KEY="your_key_here"` in your terminal.
try:
    GOOGLE_API_KEY = os.environ["GEMINI_API_KEY"]
    genai.configure(api_key=GOOGLE_API_KEY)
    JUDGE_MODEL_NAME = "models/gemini-2.5-flash-preview-05-20" # Use the stable model identifier
except KeyError:
    print("FATAL ERROR: The 'GEMINI_API_KEY' environment variable is not set.")
    print("Please set the variable and try again.")
    sys.exit(1)


# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Map task types to their validation function
VALIDATION_MAP = {
    'elementalData': validate_elemental_data,
    'spellScripting': validate_spell_script,
    'automataScripting': validate_ca_script
}


def create_dummy_data_with_prompts(master_folder):
    """
    Creates dummy data, including prompt components with the new nested schema.
    """
    if not os.path.exists(master_folder):
        logging.info(f"Creating master folder: {master_folder}")
        os.makedirs(master_folder)

    # This dummy data is for the `ingest_data.py` script to process.
    log_structure = {
        "model_group_1": {
            "session_A.txt": """[task1-2025-06-15-10-12-01]
input::An input for task 1.
context::["Some context for task 1."]
response::{"text": "model 1 response to task 1"}
---END_SECTION---
[task2-2025-06-15-10-14-15]
input::An input for task 2.
context::["Some context for task 2."]
response::{"text": "model 1 response to task 2"}
---END_SECTION---
"""
        },
        "model_group_2": {
            "session_C.txt": """[task1-2025-06-15-10-12-02]
input::An input for task 1.
context::["Some context for task 1."]
response::{"text": "model 2 response to task 1"}
---END_SECTION---
"""
        }
    }

    for group, sessions in log_structure.items():
        group_path = os.path.join(master_folder, group)
        os.makedirs(group_path, exist_ok=True)
        for session_name, content in sessions.items():
            with open(os.path.join(group_path, session_name), 'w') as f:
                f.write(content.strip())
    logging.info("Dummy response log files created.")

    # --- MODIFIED: Schemas are now updated to request the nested structure ---
    prompt_components = {
        "task1_rules.txt": "Rules for task 1: Focus on clarity and directness.",
        "task1_rubric.txt": "Rubric for task 1: Evaluate based on factual accuracy.",
        "task1_schema.txt": "Schema for task 1: Output a single JSON object. It MUST contain two top-level keys: 'scores' and 'rationales'. 'scores' must be a dictionary of numeric scores (e.g., 'accuracy': 5). 'rationales' must be a dictionary of corresponding string explanations (e.g., 'accuracy': 'The response was factually correct.').",
        "task2_rules.txt": "Rules for task 2: Be creative and engaging.",
        "task2_rubric.txt": "Rubric for task 2: Evaluate based on originality.",
        "task2_schema.txt": "Schema for task 2: Output a single JSON object. It MUST contain two top-level keys: 'scores' and 'rationales'. 'scores' must be a dictionary of numeric scores (e.g., 'creativity': 4). 'rationales' must be a dictionary of corresponding string explanations (e.g., 'creativity': 'The idea was novel.')."
    }

    for filename, content in prompt_components.items():
        file_path = os.path.join(master_folder, filename)
        with open(file_path, 'w') as f:
            f.write(content)
    logging.info("Dummy prompt component files created.")


def get_llm_judgement(prompt: str) -> str | None:
    """
    Calls the Gemini API to get a judgement for a given prompt.

    Args:
        prompt: The fully constructed prompt for the LLM judge.

    Returns:
        The text content of the LLM's response, or None if an error occurred.
    """
    logging.info("Sending request to Gemini API...")
    try:
        model = genai.GenerativeModel(JUDGE_MODEL_NAME)
        # Enforce JSON output from the model for consistency
        generation_config = genai.GenerationConfig(response_mime_type="application/json")
        response = model.generate_content(prompt, generation_config=generation_config)
        return response.text
    except Exception as e:
        logging.error(f"An error occurred while calling the Gemini API: {e}")
        return None


def build_judge_prompt(rules_file, rubric_file, schema_file, task_input, task_context, task_response, validation_status):
    """
    Builds a complete prompt for the LLM judge from modular components.
    """
    try:
        with open(rules_file, 'r') as f: rules = f.read()
        with open(rubric_file, 'r') as f: rubric = f.read()
        with open(schema_file, 'r') as f: schema = f.read()
    except FileNotFoundError as e:
        return f"Error: Could not find a prompt component file: {e}"

    prompt = f"""
You are an expert evaluator. Your task is to act as a judge and assess the quality of a response based on the provided context and input. Your output MUST be a single, valid JSON object and nothing else.

### TASK RULES ###
{rules}

### EVALUATION RUBRIC ###
{rubric}

### OUTPUT SCHEMA ###
{schema}

### ALGORITHMIC PRE-CHECK ###
A programmatic check was run on the response to validate its basic structure and syntax.
Syntactic Validation Status: {validation_status}
(You should factor this pre-check into your final evaluation, especially for correctness scores.)

### TASK FOR EVALUATION ###
**Input:**
{task_input}

**Context:**
{task_context}

**Response to Evaluate:**
{task_response}

### YOUR EVALUATION (JSON ONLY) ###
"""
    return prompt.strip()


def update_judged_record(conn, row_id, scores_json, rationales_json):
    """Updates a record in the database with the judging results."""
    sql = """
    UPDATE responses
    SET status = 'judged',
        judge_scores_json = ?,
        judge_rationales_json = ?,
        judged_at = ?
    WHERE row_id = ?;
    """
    try:
        cursor = conn.cursor()
        judged_at_timestamp = datetime.now().isoformat()
        cursor.execute(sql, (scores_json, rationales_json, judged_at_timestamp, row_id))
        logging.info(f"Successfully updated record {row_id} with judging results.")
    except sqlite3.Error as e:
        logging.error(f"Failed to update record {row_id}: {e}")


def process_unjudged_instances(db_file, prompt_folder, limit=5):
    """
    Fetches pending records, runs validation, calls the LLM judge, and updates the DB.
    """
    logging.info(f"--- Starting Judging Process for up to {limit} records ---")
    conn = create_connection(db_file)
    if not conn:
        logging.error("Could not connect to database. Aborting.")
        return

    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM responses WHERE status = 'pending' LIMIT ?;", (limit,))
    pending_records = cursor.fetchall()

    if not pending_records:
        logging.info("No pending records to be judged. All done!")
        conn.close()
        return

    logging.info(f"Found {len(pending_records)} records to process.")

    for record in pending_records:
        match = re.match(r'^[a-zA-Z0-9]+', record['task_key'])
        if not match:
            logging.warning(f"Could not extract base task name from '{record['task_key']}'. Skipping row_id {record['row_id']}.")
            continue
        base_task_name = match.group(0)

        validation_status = "skipped"
        validator_func = VALIDATION_MAP.get(base_task_name)
        if validator_func:
            original_stdout = sys.stdout
            sys.stdout = open(os.devnull, 'w')
            try:
                is_valid = validator_func(record['model_response'])
                validation_status = "Passed" if is_valid else "Failed"
            finally:
                sys.stdout.close()
                sys.stdout = original_stdout
        else:
            logging.info(f"No validator found for task type '{base_task_name}'.")

        rules_path = os.path.join(prompt_folder, f"{base_task_name}_rules.txt")
        rubric_path = os.path.join(prompt_folder, f"{base_task_name}_rubric.txt")
        schema_path = os.path.join(prompt_folder, f"{base_task_name}_schema.txt")

        judge_prompt = build_judge_prompt(
            rules_file=rules_path, rubric_file=rubric_path, schema_file=schema_path,
            task_input=record['input'], task_context=record['context'],
            task_response=record['model_response'], validation_status=validation_status
        )

        llm_response_text = get_llm_judgement(judge_prompt)

        if not llm_response_text:
            logging.warning(f"Skipping row_id {record['row_id']} due to an API call failure.")
            continue

        try:
            judgement_data = json.loads(llm_response_text)
        except json.JSONDecodeError:
            logging.error(f"Skipping row_id {record['row_id']} due to malformed JSON from LLM.")
            logging.debug(f"Malformed response: {llm_response_text}")
            continue

        # --- NEW PARSING LOGIC ---
        # Extract the 'scores' and 'rationales' nested dictionaries.
        scores_dict = judgement_data.get("scores")
        rationales_dict = judgement_data.get("rationales")

        # Validate the structure of the parsed data.
        if not isinstance(scores_dict, dict) or not isinstance(rationales_dict, dict):
            logging.error(f"Skipping row_id {record['row_id']} due to invalid JSON structure. 'scores' or 'rationales' key is missing or not a dictionary.")
            logging.debug(f"Received data: {judgement_data}")
            continue
        # --- END NEW PARSING LOGIC ---

        # Add the programmatic validation status to the scores, preserving existing logic.
        scores_dict["programmatic_validation"] = validation_status

        # Convert the separated dictionaries back into JSON strings for the database.
        final_scores_json = json.dumps(scores_dict)
        final_rationales_json = json.dumps(rationales_dict)

        # Update the record in the database with the real results.
        update_judged_record(conn, record['row_id'], final_scores_json, final_rationales_json)

    conn.commit()
    conn.close()
    logging.info("--- Judging Process Finished for this Batch ---")


if __name__ == '__main__':
    DB_FILE = "judgements.db"
    PROMPT_COMPONENT_FOLDER = "judge_prompts"

    # NOTE: This step is for initial setup.
    create_dummy_data_with_prompts(PROMPT_COMPONENT_FOLDER)
    print("\nReminder: This script assumes an ingestion process has populated the database.")
    print("If the database is empty, please run your ingestion script first.")
    
    # Run the judging process on the ingested data.
    process_unjudged_instances(DB_FILE, PROMPT_COMPONENT_FOLDER, limit=10)

    # Show the final results
    print("\n--- Final Status Breakdown ---")
    final_conn = create_connection(DB_FILE)
    if final_conn:
        get_status_breakdown(final_conn)
        final_conn.close()