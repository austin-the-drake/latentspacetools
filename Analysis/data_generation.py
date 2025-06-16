import os
import sys
import json
import random
import copy
import google.generativeai as genai

def generate_spell_tasks(num_tasks=10, output_file="spell_scripting_tasks.json"):
    """
    Generates synthetic tasks for a "spellScripting" model.

    This function prompts a Gemini model to create magical spell descriptions,
    then pairs each description with a random list of "available elements"
    to form an (input, context) pair for a future task.

    Args:
        num_tasks (int): The number of synthetic tasks to generate.
        output_file (str): The name of the JSON file to save the tasks to.
    """
    print("--- Starting Synthetic Spell Task Generation ---")

    # 1. Load the Gemini API key from the environment variable
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key is None:
        print("\nERROR: The GEMINI_API_KEY environment variable is not set.")
        sys.exit(1)
    
    genai.configure(api_key=api_key)

    # 2. Define the master list of possible magical elements
    master_element_list = [
        "Fire", "Water", "Earth", "Air", "Lightning", "Ice", "Light", "Shadow",
        "Poison", "Acid", "Force", "Gravity", "Time", "Space", "Mind", "Spirit",
        "Nature", "Metal", "Wood", "Sound", "Aether", "Nether", "Blood", "Bone",
        "Celestial", "Void", "Sand", "Steam", "Crystal", "Dream", "Fear", "Chaos",
        "Order", "Life", "Death", "Arcane", "Rune", "Illusion", "Distortion"
    ]

    # 3. Configure the generation model and craft the prompt
    generation_config = genai.GenerationConfig(
        temperature=1.0,
        response_mime_type="application/json"
    )
    model = genai.GenerativeModel(
        'gemini-2.5-flash-preview-05-20',
        generation_config=generation_config
    )

    prompt = f"""
    You are a creative loremaster for a fantasy world.
    Generate a list of exactly {num_tasks} short, imaginative descriptions of magical spells.
    Each description should detail a sequence of actions or effects.
    
    Return your response as a single JSON object with one key, "spells", which contains a list of strings.
    """

    print(f"Sending prompt to Gemini to generate {num_tasks} spell descriptions...")

    try:
        response = model.generate_content(prompt)
        response_data = json.loads(response.text)
        spell_descriptions = response_data.get("spells", [])

        if not spell_descriptions or len(spell_descriptions) != num_tasks:
            print(f"ERROR: Model returned an unexpected format or number of spells. Got {len(spell_descriptions)}.")
            print(f"Raw response: {response.text}")
            sys.exit(1)
            
        print(f"Successfully received {len(spell_descriptions)} spell descriptions.")

        final_tasks = []
        for spell_desc in spell_descriptions:
            num_elements_to_select = random.randint(5, 10)
            available_elements = random.sample(master_element_list, num_elements_to_select)
            
            task_pair = {
                "input": spell_desc,
                "context": available_elements
            }
            final_tasks.append(task_pair)

        with open(output_file, 'w') as f:
            json.dump(final_tasks, f, indent=2)
            
        print(f"\nSuccessfully generated and saved {len(final_tasks)} 'spellScripting' tasks to '{output_file}'.")
        
    except Exception as e:
        print(f"\nAn error occurred during 'spellScripting' generation: {e}")
        # Not exiting here to allow other tasks to run
        
def generate_element_editing_tasks(num_tasks=10, output_file="element_editing_tasks.json"):
    """
    Generates synthetic tasks for an "elementEditing" model.

    This function programmatically creates a JSON ruleset for elemental interactions
    and pairs it with a request to add, change, or remove an element.
    """
    print("\n--- Starting Synthetic Element Editing Task Generation ---")
    
    master_element_list = [
        "Fire", "Water", "Earth", "Air", "Lightning", "Ice", "Light", "Shadow",
        "Poison", "Acid", "Force", "Gravity", "Time", "Space", "Mind", "Spirit",
        "Nature", "Metal", "Wood", "Sound", "Aether", "Nether", "Blood", "Bone"
    ]
    sound_libraries = ["energetic", "blowing", "crackling", "flaming", "rumbling"]
    final_tasks = []

    for i in range(num_tasks):
        num_base_elements = random.randint(5, 8)
        current_elements = random.sample(master_element_list, num_base_elements)
        context = {"elements": current_elements}

        for element in current_elements:
            interactions = {other_element.lower(): random.choice([-1.0, 0.0, 1.0]) for other_element in current_elements}
            interactions["RGB_COLOR"] = [float(random.randint(0, 255)), float(random.randint(0, 255)), float(random.randint(0, 255))]
            interactions["SOUND_LIB"] = random.choice(sound_libraries)
            context[element.lower()] = interactions
        
        request_type = random.choice(["add", "change", "remove"])
        input_request = ""

        if request_type == "add":
            possible_new_elements = [elem for elem in master_element_list if elem not in current_elements]
            if possible_new_elements:
                new_element = random.choice(possible_new_elements)
                input_request = f"Please add the element '{new_element}' to the current ruleset. Infer its interactions with the other elements based on its logical nature."
            else:
                request_type = "change"

        if request_type == "change":
            elem1, elem2 = random.sample(current_elements, 2)
            new_relationship = random.choice(["strong against", "weak against", "neutral to"])
            input_request = f"Please change the elemental rules. Make the element '{elem1}' {new_relationship} the element '{elem2}'."
        
        if request_type == "remove":
            element_to_remove = random.choice(current_elements)
            input_request = f"Please remove the element '{element_to_remove}' from the ruleset. Ensure the remaining rules are rebalanced and make logical sense."

        final_tasks.append({"input": input_request, "context": context})

    with open(output_file, 'w') as f:
        json.dump(final_tasks, f, indent=2)
        
    print(f"Successfully generated and saved {len(final_tasks)} 'elementEditing' tasks to '{output_file}'.")


def generate_automata_scripting_tasks(num_tasks=10, output_file="automata_scripting_tasks.json"):
    """
    Generates synthetic tasks for an "automataScripting" model.
    This version sequentially builds the context for each task in the series.
    """
    print("\n--- Starting Synthetic Automata Scripting Task Generation ---")
    
    # 1. Define the base JSON context.
    context_json_string = """
    {"sand":{"actions":[{"actions":[{"direction":"south","actions":[{"direction":"south","type":"do_swap"}],"else_actions":[{"direction":"southeast","actions":[{"direction":"southeast","type":"do_swap"}],"type":"if_neighbor_is","options":["air","gas","water"]}],"type":"if_neighbor_is","options":["air","gas","water"]}],"type":"in_rand_mirror"}]},"water":{"actions":[{"actions":[{"direction":"south","actions":[{"direction":"south","type":"do_swap"}],"else_actions":[{"direction":"southeast","actions":[{"direction":"southeast","type":"do_swap"}],"else_actions":[{"direction":"east","actions":[{"direction":"east","type":"do_swap"}],"type":"if_neighbor_is","options":["air","gas"]}],"type":"if_neighbor_is","options":["air","gas"]}],"type":"if_neighbor_is","options":["air","gas"]}],"type":"in_rand_mirror"}]},"gas":{"actions":[{"actions":[{"direction":"north","actions":[{"direction":"north","type":"do_swap"}],"type":"if_neighbor_is","options":["air"]}],"type":"in_rand_rotation"}]}}
    """
    base_automata_context = json.loads(context_json_string)

    # 2. Configure Gemini API
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("API key not found, assuming it's configured from a previous step.")
    else:
        genai.configure(api_key=api_key)

    generation_config = genai.GenerationConfig(
        temperature=0.9,
        response_mime_type="application/json"
    )
    model = genai.GenerativeModel(
        'gemini-2.5-flash-preview-05-20',
        generation_config=generation_config
    )

    prompt = f"""
    You are a game designer creating a complex, interconnected system of materials for a 2D falling-sand cellular automata simulation.
    Your goal is to describe a single, coherent biological or geological system through a series of related materials.
    Generate a list of exactly {num_tasks} short, descriptive behaviors for materials that interact with or build upon each other. The list should be ordered logically (e.g., seed, then stem, then flower).

    For example, a plant system:
    - "A seed that sprouts into a stem when it touches dirt and water."
    - "A plant stem that grows upwards by consuming water from below."
    - "A flower bud that forms at the top of a mature stem."
    - "A flower petal that spawns from a bud and eventually withers and falls."
    - "Fallen petals that decompose into dirt over time."

    Now, create your own unique, interconnected system.
    Generate a list of exactly {num_tasks} descriptions for the materials in your system.
    Return your response as a single JSON object with one key, "descriptions", which contains a list of dictionaries, each with a "material_name" and a "behavior_description".
    Example: {{"descriptions": [{{"material_name": "seed", "behavior_description": "A seed..."}}]}}
    """

    print(f"Sending prompt to Gemini to generate {num_tasks} interconnected material descriptions...")

    try:
        response = model.generate_content(prompt)
        response_data = json.loads(response.text)
        material_data = response_data.get("descriptions", [])

        if not material_data or len(material_data) != num_tasks:
            print(f"ERROR: Model returned an unexpected format or number of descriptions. Got {len(material_data)}.")
            sys.exit(1)
            
        print(f"Successfully received {len(material_data)} material descriptions.")

        # 3. Sequentially build tasks, updating the context at each step
        final_tasks = []
        # Start with a deep copy of the base context
        current_context = copy.deepcopy(base_automata_context)
        
        for item in material_data:
            material_name = item.get("material_name", "unknown").lower().replace(" ", "_")
            behavior_description = item.get("behavior_description")

            # Create the task with the context *as it currently exists*
            # We use deepcopy to ensure each task has a snapshot of the context at that moment
            task_pair = {
                "input": behavior_description,
                "context": copy.deepcopy(current_context)
            }
            final_tasks.append(task_pair)
            
            # Now, update the context for the *next* iteration
            # Add the current material with a placeholder behavior
            print(f"  -> Adding '{material_name}' to the context for the next step.")
            current_context[material_name] = {"actions": [{"type": "placeholder"}]}


        # 4. Save the tasks to the output file
        with open(output_file, 'w') as f:
            json.dump(final_tasks, f, indent=2)
            
        print(f"Successfully generated and saved {len(final_tasks)} 'automataScripting' tasks to '{output_file}'.")

    except Exception as e:
        print(f"\nAn error occurred during 'automataScripting' generation: {e}")


if __name__ == "__main__":
    # Ensure you have the library installed: pip install google-generativeai
    # Ensure your GEMINI_API_KEY environment variable is set.
    
    generate_spell_tasks(num_tasks=10)
    generate_element_editing_tasks(num_tasks=10)
    generate_automata_scripting_tasks(num_tasks=10)
