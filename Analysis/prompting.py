import os
import sys
import json
import argparse
from datetime import datetime
import google.generativeai as genai
import openai

# --- API-Specific Functions ---

# --- Gemini Functions ---

def setup_gemini(api_key):
    """Configures the Gemini API."""
    try:
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        print(f"Error configuring Gemini: {e}")
        return False

def prompt_gemini_model(model_name, full_prompt):
    """
    Sends a prompt to a specified Gemini model and returns the response text.

    Args:
        model_name (str): The name of the Gemini model to use.
        full_prompt (str): The complete prompt to send to the model.

    Returns:
        str: The text content of the model's response.
    """
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(full_prompt)
        print(f"  -> Success: Received response from model.")
        return response.text
    except Exception as e:
        print(f"  -> ERROR: An error occurred during Gemini API call: {e}")
        return json.dumps({"error": str(e)})

# --- OpenAI Functions (Updated for openai>=1.0.0) ---

def setup_openai(api_key):
    """
    Configures and returns an OpenAI client instance.
    
    Returns:
        openai.OpenAI: An instance of the OpenAI client, or None on failure.
    """
    try:
        client = openai.OpenAI(api_key=api_key)
        # A simple check to see if the client is configured correctly.
        client.models.list() 
        return client
    except Exception as e:
        print(f"Error configuring OpenAI client: {e}")
        return None

def prompt_openai_model(client, model_name, full_prompt):
    """
    Sends a prompt to a specified OpenAI model using the new client syntax.

    Args:
        client (openai.OpenAI): The configured OpenAI client instance.
        model_name (str): The name of the OpenAI model to use (e.g., 'gpt-4.1').
        full_prompt (str): The complete prompt to send to the model.

    Returns:
        str: The text content of the model's response.
    """
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "user", "content": full_prompt}
            ]
        )
        print(f"  -> Success: Received response from model.")
        return response.choices[0].message.content
    except Exception as e:
        print(f"  -> ERROR: An error occurred during OpenAI API call: {e}")
        return json.dumps({"error": str(e)})


# --- Generic Workflow Functions ---

def format_prompt(preamble, task_input, task_context):
    """Formats the final prompt string to be sent to the model."""
    context_str = json.dumps(task_context, indent=2)
    
    return f"""{preamble}

### User input to fulfil
{task_input}

### Relevant context
```json
{context_str}
```
"""

def format_log_entry(task_type, task_input, task_context, model_response_text):
    """Formats a single entry for the output log file."""
    timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    header = f"[{task_type}-{timestamp}]"
    context_str = json.dumps(task_context)
    response_str = model_response_text
    
    return f"""{header}
input::{task_input}
context::{context_str}
response::{response_str}
---END_SECTION---
"""

def run_prompting_session(task_type, model_name, prompt_preamble, input_json_file, output_log_dir):
    """
    Reads tasks from a JSON file, prompts a specified model via its API, 
    and writes the results to a structured log file.
    """
    print("--- Starting New Prompting Session ---")
    print(f"  Task Type: {task_type}")
    print(f"  Model: {model_name}")
    print(f"  Input File: {input_json_file}")
    print("------------------------------------")

    # 1. Load input data
    try:
        with open(input_json_file, 'r') as f:
            tasks = json.load(f)
        print(f"Successfully loaded {len(tasks)} tasks from '{input_json_file}'.")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        sys.exit(f"Error reading input file: {e}")

    # 2. Prepare output log file
    os.makedirs(output_log_dir, exist_ok=True)
    session_timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    safe_model_name = model_name.replace("/", "_")
    log_filename = f"LatentSpaceLog-{safe_model_name}-{session_timestamp}.txt"
    log_filepath = os.path.join(output_log_dir, log_filename)
    print(f"Will write results to: {log_filepath}\n")
    
    # 3. Setup APIs based on model type
    api_client = None
    if 'gemini' in model_name.lower():
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or not setup_gemini(api_key):
            sys.exit("Failed to configure Gemini API. Is GEMINI_API_KEY set?")
    elif 'gpt' in model_name.lower():
        api_key = os.getenv("OPENAI_API_KEY")
        api_client = setup_openai(api_key) # This now returns a client object
        if not api_client:
            sys.exit("Failed to configure OpenAI API. Is OPENAI_API_KEY set and valid?")
    else:
        sys.exit(f"Unknown model provider for '{model_name}'. Cannot determine which API key to use.")

    # 4. Process each task and write to log immediately
    with open(log_filepath, 'w', encoding='utf-8') as log_file:
        for i, task in enumerate(tasks):
            print(f"Processing task {i+1}/{len(tasks)}...")
            full_prompt = format_prompt(prompt_preamble, task['input'], task['context'])
            
            # --- Model Dispatcher ---
            response_text = ""
            if 'gemini' in model_name.lower():
                response_text = prompt_gemini_model(model_name, full_prompt)
            elif 'gpt' in model_name.lower() and api_client:
                response_text = prompt_openai_model(api_client, model_name, full_prompt)
            else:
                print(f"  -> ERROR: Unknown or unconfigured model provider for '{model_name}'. Skipping.")
                response_text = json.dumps({"error": f"Unknown or unconfigured model provider for '{model_name}'"})

            # Format and write the log entry
            log_entry = format_log_entry(task_type, task['input'], task['context'], response_text)
            log_file.write(log_entry + "\n")
    
    print("\n--- Prompting Session Complete ---")
    print(f"All {len(tasks)} tasks have been processed and logged to {log_filepath}.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run a prompting session against a specified LLM.")
    parser.add_argument("task_type", help="The type of task being run (e.g., 'spellScripting').")
    parser.add_argument("model_name", help="The model to use (e.g., 'gemini-2.5-flash-preview-05-20', 'gpt-4.1').")
    parser.add_argument("preamble_file", help="Path to a .txt file containing the prompt preamble.")
    parser.add_argument("input_json", help="Path to the .json file containing the tasks.")
    parser.add_argument("--output_dir", default="session_logs", help="Directory to save the output log file.")
    
    args = parser.parse_args()

    try:
        with open(args.preamble_file, 'r') as f:
            preamble = f.read()
    except FileNotFoundError:
        sys.exit(f"Error: Preamble file not found at '{args.preamble_file}'")

    run_prompting_session(
        task_type=args.task_type,
        model_name=args.model_name,
        prompt_preamble=preamble,
        input_json_file=args.input_json,
        output_log_dir=args.output_dir
    )
