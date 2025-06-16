import json

def validate_elemental_data(response_text: str) -> bool:
    """
    Validates if the LLM response for the elemental data task is syntactically correct.

    This function checks for:
    1.  Valid JSON format.
    2.  Presence of a top-level 'elements' list.
    3.  Presence of a corresponding detail map for each element in the list.
    4.  Correct format for 'RGB_COLOR' (a list of 3 numbers).
    5.  Correct format for 'SOUND_LIB' (a valid string from the allowed options).

    Args:
        response_text: A string containing the raw JSON output from the LLM.

    Returns:
        True if the response is valid, False otherwise.
    """
    ALLOWED_SOUNDS = {"flaming", "blowing", "crackling", "energetic"}

    # 1. Is the response valid JSON?
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        print("Validation Error: Response is not valid JSON.")
        return False

    # 2. Does it have the basic structure?
    if not isinstance(data, dict) or 'elements' not in data or not isinstance(data['elements'], list):
        print("Validation Error: JSON must be an object with an 'elements' list.")
        return False

    element_list = data['elements']
    
    # 3. Loop through each element and validate its detail map
    for element_name in element_list:
        # Does the detail map exist and is it an object?
        detail_map = data.get(element_name)
        if not isinstance(detail_map, dict):
            print(f"Validation Error: Element '{element_name}' is missing its detail map.")
            return False

        # Validate RGB_COLOR
        color = detail_map.get('RGB_COLOR')
        if not isinstance(color, list) or len(color) != 3 or not all(isinstance(c, (int, float)) for c in color):
            print(f"Validation Error: Element '{element_name}' has an invalid 'RGB_COLOR'. Must be a list of 3 numbers.")
            return False

        # Validate SOUND_LIB
        sound = detail_map.get('SOUND_LIB')
        if not isinstance(sound, str) or sound not in ALLOWED_SOUNDS:
            print(f"Validation Error: Element '{element_name}' has an invalid 'SOUND_LIB'.")
            return False
            
    # If all checks pass
    return True

# --- Example Usage ---
if __name__ == '__main__':
    # A valid response that should pass
    VALID_RESPONSE = """
    {
        "elements": ["fire", "water"],
        "fire": {
            "RGB_COLOR": [255, 100, 0],
            "SOUND_LIB": "flaming",
            "fire": 0,
            "water": -1
        },
        "water": {
            "RGB_COLOR": [0, 100, 255],
            "SOUND_LIB": "blowing",
            "fire": 1,
            "water": 0
        }
    }
    """

    # Invalid responses for testing
    INVALID_JSON = '{"elements": ["fire}' # Malformed JSON
    MISSING_ELEMENT_MAP = '{"elements": ["fire"]}' # 'fire' map is missing
    BAD_COLOR_FORMAT = '{"elements": ["fire"], "fire": {"RGB_COLOR": [255, 0], "SOUND_LIB": "flaming"}}' # Color has 2 values
    BAD_SOUND_LIB = '{"elements": ["fire"], "fire": {"RGB_COLOR": [255, 0, 0], "SOUND_LIB": "burning"}}' # Invalid sound

    print(f"Validating good response... Result: {validate_elemental_data(VALID_RESPONSE)}")
    print("-" * 20)
    print(f"Validating bad JSON... Result: {validate_elemental_data(INVALID_JSON)}")
    print("-" * 20)
    print(f"Validating missing map... Result: {validate_elemental_data(MISSING_ELEMENT_MAP)}")
    print("-" * 20)
    print(f"Validating bad color... Result: {validate_elemental_data(BAD_COLOR_FORMAT)}")
    print("-" * 20)
    print(f"Validating bad sound... Result: {validate_elemental_data(BAD_SOUND_LIB)}")


    import json

def validate_spell_script(response_text: str) -> bool:
    """
    Validates if the LLM response for the spell scripting task is syntactically correct.

    This function checks for:
    1.  Valid JSON format.
    2.  Presence of root keys: 'friendlyName' (string) and 'components' (list).
    3.  That each component in the 'components' list is an object with a 'componentType' key.
    4.  The structural integrity of key components (e.g., 'color' has an 'rgb' list).
    5.  Recursively validates the structure of any 'payload_components' within triggers.

    Args:
        response_text: A string containing the raw JSON output from the LLM.

    Returns:
        True if the response is valid, False otherwise.
    """
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        print("Validation Error: Response is not valid JSON.")
        return False

    # Check top-level structure
    if not isinstance(data, dict):
        print("Validation Error: Top-level structure must be a JSON object.")
        return False
    if not isinstance(data.get('friendlyName'), str) or not isinstance(data.get('components'), list):
        print("Validation Error: Must have 'friendlyName' (string) and 'components' (list) at the root.")
        return False

    # Start recursive validation on the main components list
    return _validate_components_list(data['components'])


def _validate_components_list(components: list) -> bool:
    """A helper function to recursively validate a list of spell components."""
    
    # A set of known trigger types that must contain a payload
    TRIGGER_TYPES = {"timerTrigger", "buttonTrigger", "impactTrigger", "deathTrigger"}

    if not isinstance(components, list):
        print(f"Validation Error: Expected a list of components, but got {type(components)}.")
        return False

    for component in components:
        if not isinstance(component, dict) or 'componentType' not in component:
            print(f"Validation Error: Found an item in a components list that is not an object with a 'componentType'. Item: {component}")
            return False

        comp_type = component['componentType']

        # Example of a type-specific check
        if comp_type == 'color' and (not isinstance(component.get('rgb'), list) or len(component['rgb']) != 3):
            print(f"Validation Error: 'color' component has an invalid 'rgb' property.")
            return False
            
        # Example of a numeric check
        if comp_type == 'projectile' and not isinstance(component.get('radius'), (int, float)):
             print(f"Validation Error: 'projectile' component has an invalid 'radius' property.")
             return False

        # If the component is a trigger, it must have a valid payload, which we validate recursively
        if comp_type in TRIGGER_TYPES:
            payload = component.get('payload_components')
            if not isinstance(payload, list):
                print(f"Validation Error: Trigger '{comp_type}' is missing a 'payload_components' list.")
                return False
            
            # Recursive call
            if not _validate_components_list(payload):
                return False # Propagate failure from the recursive call

    # If the loop completes without returning, all components in this list are valid
    return True


# --- Example Usage ---
if __name__ == '__main__':
    # A valid response that should pass, including recursion
    VALID_SPELL = """
    {
        "friendlyName": "Recursive Fireball",
        "components": [
            { "componentType": "projectile", "radius": 10, "speed": 15 },
            { "componentType": "color", "rgb": [255, 100, 0] },
            {
                "componentType": "impactTrigger",
                "payload_components": [
                    { "componentType": "explosion", "radius": 50 }
                ]
            }
        ]
    }
    """

    # Invalid responses for testing
    INVALID_JSON = '{"friendlyName": "test"'
    MISSING_TOP_LEVEL_KEY = '{"friendlyName": "test"}' # Missing 'components'
    COMPONENT_NOT_OBJECT = '{"friendlyName": "test", "components": ["projectile"]}'
    MISSING_COMPONENT_TYPE = '{"friendlyName": "test", "components": [{"radius": 10}]}'
    BAD_PAYLOAD = '{"friendlyName": "test", "components": [{"componentType": "impactTrigger", "payload_components": {"type": "explosion"}}]}'

    print(f"Validating good spell... Result: {validate_spell_script(VALID_SPELL)}")
    print("-" * 20)
    print(f"Validating bad JSON... Result: {validate_spell_script(INVALID_JSON)}")
    print("-" * 20)
    print(f"Validating missing key... Result: {validate_spell_script(MISSING_TOP_LEVEL_KEY)}")
    print("-" * 20)
    print(f"Validating bad component... Result: {validate_spell_script(COMPONENT_NOT_OBJECT)}")
    print("-" * 20)
    print(f"Validating missing type... Result: {validate_spell_script(MISSING_COMPONENT_TYPE)}")
    print("-" * 20)
    print(f"Validating bad payload... Result: {validate_spell_script(BAD_PAYLOAD)}")

    import json
import re

def validate_ca_script(response_text: str) -> bool:
    """
    Validates if the LLM response for the cellular automata task is syntactically correct.

    This function checks for:
    1.  A valid JSON object, even if it's embedded in other text.
    2.  Presence of root keys: 'name', 'color_hex', and 'behavior'.
    3.  Correct format for 'name' (lowercase string, <= 5 chars) and 'color_hex' (#RRGGBB).
    4.  The 'behavior' object must contain an 'actions' list.
    5.  Recursively validates that all nodes in 'actions' lists have a 'type' key
        and that nodes that should contain other actions (e.g., conditionals) do.

    Args:
        response_text: A string containing the raw output from the LLM.

    Returns:
        True if the response is valid, False otherwise.
    """
    # 1. Clean the string to extract only the JSON object
    match = re.search(r"\{.*\}", response_text, re.DOTALL)
    if not match:
        print("Validation Error: No valid JSON object found in the response text.")
        return False
    cleaned_json_string = match.group(0)

    # 2. Is the extracted content valid JSON?
    try:
        data = json.loads(cleaned_json_string)
    except json.JSONDecodeError:
        print("Validation Error: Extracted content is not valid JSON.")
        return False

    # 3. Validate the root structure and formats
    if not isinstance(data, dict):
        return False
        
    name = data.get('name')
    color = data.get('color_hex')
    behavior = data.get('behavior')

    if not (isinstance(name, str) and name.islower() and 0 < len(name) <= 15):
        print(f"Validation Error: 'name' is invalid. Got: {name}")
        return False

    if not (isinstance(color, str) and re.match(r"^#[0-9a-fA-F]{6}$", color)):
        print(f"Validation Error: 'color_hex' is invalid. Got: {color}")
        return False

    if not (isinstance(behavior, dict) and isinstance(behavior.get('actions'), list)):
        print("Validation Error: 'behavior' must be an object with an 'actions' list.")
        return False

    # 4. Start recursive validation on the actions list
    return _validate_actions_list(behavior['actions'])


def _validate_actions_list(actions: list) -> bool:
    """A helper function to recursively validate a list of CA nodes."""
    
    # Node types that can contain a nested 'actions' or 'else_actions' list
    RECURSIVE_NODE_TYPES = {
        "in_rand_rotation", "in_rand_mirror", "in_rand_flip",
        "if_neighbor_is", "if_neighbor_is_not", "if_alpha",
        "if_neighbor_count", "if_chance", "do_swap"
    }

    if not isinstance(actions, list):
        return False

    for node in actions:
        if not isinstance(node, dict) or not isinstance(node.get('type'), str):
            print(f"Validation Error: Found an item in an actions list without a valid 'type'. Item: {node}")
            return False

        # If a node is a recursive type, check its nested actions
        if node['type'] in RECURSIVE_NODE_TYPES:
            if 'actions' in node and not _validate_actions_list(node['actions']):
                return False # Propagate failure
            # Special case for if-else
            if 'else_actions' in node and not _validate_actions_list(node['else_actions']):
                return False # Propagate failure
    
    return True


# --- Example Usage ---
if __name__ == '__main__':
    # A valid script that should pass
    VALID_CA_SCRIPT = """
    Here is the JSON you requested:
    ```json
    {
        "name": "steam",
        "color_hex": "#E0E0E0",
        "behavior": {
            "actions": [
                {
                    "type": "if_chance",
                    "percent": 50,
                    "actions": [
                        { "type": "do_swap", "direction": "north" }
                    ]
                }
            ]
        }
    }
    ```
    I hope this helps!
    """
    # Invalid scripts for testing
    BAD_JSON = '{"name": "bad"'
    MISSING_KEY = '{"name": "test", "color_hex": "#FFFFFF"}' # Missing behavior
    BAD_NAME_FORMAT = '{"name": "TooLong", "color_hex": "#FFFFFF", "behavior": {"actions":[]}}'
    BAD_COLOR_FORMAT = '{"name": "test", "color_hex": "#FFF", "behavior": {"actions":[]}}'
    MISSING_NODE_TYPE = '{"name": "test", "color_hex": "#FFFFFF", "behavior": {"actions":[{"direction": "north"}]}}'

    print(f"Validating good script... Result: {validate_ca_script(VALID_CA_SCRIPT)}")
    print("-" * 20)
    print(f"Validating bad JSON... Result: {validate_ca_script(BAD_JSON)}")
    print("-" * 20)
    print(f"Validating missing key... Result: {validate_ca_script(MISSING_KEY)}")
    print("-" * 20)
    print(f"Validating bad name... Result: {validate_ca_script(BAD_NAME_FORMAT)}")
    print("-" * 20)
    print(f"Validating bad color... Result: {validate_ca_script(BAD_COLOR_FORMAT)}")
    print("-" * 20)
    print(f"Validating missing node type... Result: {validate_ca_script(MISSING_NODE_TYPE)}")