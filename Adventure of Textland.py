# d:\GeneralRepository\PythonProjects\AdventureOfTextland\Adventure of Textland.py
# --- ASCII Art ---
import webbrowser
import threading
import time
import sys
import os
import functools # For creating decorators
import re
import shutil
import json
import random # Added for probability in environmental interactions
# Attempt to import Flask, but don't make it a hard requirement for the text game to run
try:
    from flask import Flask, request, jsonify, render_template # Added render_template
    flask_available = True
except ImportError:
    flask_available = False

import game_logic # Import our new game logic module
from entities import Player, NPC # Import the Player and NPC classes
HOSTILE_MOB_VISUAL = """
  .--""--.
 /        \\
|  O  O   |
|   \/    |
 \  --   /
  '.____.'
    /  \\
   |    |
"""

VENDOR_STALL_VISUAL = """
  _________
 /        //
/________//
|        | |
| GOODS! | |
|________|/
"""

# --- Path Constants ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
PLAYER_LOGS_DIR = os.path.join(SCRIPT_DIR, "player_data") # Adjusted to be relative to script
STEPTRACKER_DIR = os.path.join(SCRIPT_DIR, "steptracker") # Adjusted to be relative to script
STEPTRACKER_FILE = os.path.join(STEPTRACKER_DIR, "function_trace.log")

# --- Game Data ---
# Initialize as empty dicts; will be populated by load_all_game_data()
locations = {}
zone_layouts = {}
items_data = {}
city_maps_data = {} # To store loaded city map details
species_data = {}
classes_data = {}
environmental_feature_models = {} # New: To store loaded environmental feature models

# Initialize player as an instance of the Player class
player = Player()

MAX_NAME_LENGTH = 20
CITY_ZONES = ["Eldoria", "Riverford"] # Zones considered as cities for saving
# Stricter pattern for humanoid names: only letters, spaces, hyphens, apostrophes.
ALLOWED_HUMANOID_NAME_PATTERN = re.compile(r"^[a-zA-Z '-]+$") 

def _ensure_steptracker_dir_exists():
    """Ensures the steptracker directory exists."""
    if not os.path.exists(STEPTRACKER_DIR):
        try:
            os.makedirs(STEPTRACKER_DIR)
        except OSError as e:
            print(f"[ERROR] Could not create steptracker directory: {e}")
            # Decide if this is a critical failure or if the game can continue without this specific logging

def log_function_call_to_steptracker(func_name):
    """Logs a function call to the steptracker log file."""
    _ensure_steptracker_dir_exists()
    try:
        with open(STEPTRACKER_FILE, "a") as f:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            f.write(f"{timestamp} - Function called: {func_name}\n")
    except Exception as e:
        print(f"[ERROR] Failed to write to steptracker log: {e}")

def trace_function_calls(func):
    """Decorator to log function calls to the steptracker."""
    @functools.wraps(func) # Preserves original function metadata
    def wrapper(*args, **kwargs):
        log_function_call_to_steptracker(func.__name__)
        return func(*args, **kwargs)
    return wrapper

def _load_and_handle_json_errors(filepath, data_description):
    """Internal helper to load a single JSON file and handle common errors."""
    try:
        # Ensure the directory of the file exists before trying to open the file
        # This is more robust for files in subdirectories.
        file_dir = os.path.dirname(filepath)
        if file_dir: # Check if there's a directory part (not a top-level file in DATA_DIR)
            os.makedirs(file_dir, exist_ok=True)

        os.makedirs(DATA_DIR, exist_ok=True) # Ensure data directory exists
        if not os.path.exists(filepath):
            print(f"[WARNING] Data file not found: {filepath}. Attempting to create with empty data for {data_description}.")
            # Create an empty file so the game doesn't crash hard on first run if files are missing
            # The user should populate these files with actual game data.
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({}, f)
            return {} # Return empty dict if file was just created

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"[Game Data] Successfully loaded {data_description} from {filepath}")
            return data
    except FileNotFoundError: # Should be caught by the os.path.exists check, but as a fallback
        print(f"[ERROR] Data file not found during load: {filepath}. Returning empty data for {data_description}.")
        return {}
    except json.JSONDecodeError as e:
        print(f"[ERROR] Error decoding JSON from {filepath}: {e}. Returning empty data for {data_description}.")
        return {}
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred while loading {filepath}: {e}. Returning empty data for {data_description}.")
        return {}

def _load_json_data_from_file(filename, data_description):
    """Helper function to load data from a JSON file directly in the DATA_DIR."""
    filepath = os.path.join(DATA_DIR, filename)
    return _load_and_handle_json_errors(filepath, data_description)

def _load_json_data_from_directory(directory_name, data_description):
    """Helper function to load data from all JSON files in a subdirectory of DATA_DIR."""
    dir_path = os.path.join(DATA_DIR, directory_name)
    all_data = {}
    try:
        if not os.path.exists(dir_path):
            print(f"[WARNING] Data directory not found: {dir_path}. No {data_description} will be loaded.")
            os.makedirs(dir_path, exist_ok=True) # Create it for future use
            return {}

        for filename in os.listdir(dir_path):
            if filename.endswith(".json"):
                filepath = os.path.join(dir_path, filename)
                file_data = _load_and_handle_json_errors(filepath, f"{data_description} from {filename}")
                all_data.update(file_data) # Assumes top-level keys in JSON files are unique model IDs

        print(f"[Game Data] Successfully loaded {len(all_data)} {data_description} from {dir_path}")
        return all_data
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred while loading {data_description} from {dir_path}: {e}. Returning empty data.")
        return {}

def load_all_game_data():
    """Loads all game data from their base structures or JSON files."""
    global locations, zone_layouts, items_data, species_data, classes_data, city_maps_data, environmental_feature_models
    locations = _load_json_data_from_file("locations.json", "Locations")
    zone_layouts = _load_json_data_from_file("zone_layouts.json", "Zone Layouts")
    items_data = _load_json_data_from_file("items.json", "Items")
    species_data = _load_json_data_from_file("species.json", "Species")
    classes_data = _load_json_data_from_file("classes.json", "Classes")

    # Load city maps
    city_ids_to_load = ["riverford", "eldoria"] # Define which city maps to attempt to load
    for city_id in city_ids_to_load:
        map_details = _load_city_map_data_from_file(city_id)
        if map_details:
            city_maps_data[city_id] = map_details

    # Load environmental feature models
    environmental_feature_models = _load_json_data_from_directory("environmental_features", "Environmental Feature Models")

    # Instantiate features in locations using models
    for loc_id, loc_data in list(locations.items()): # Iterate over a copy if modifying dict
        if "features" in loc_data and isinstance(loc_data["features"], dict):
            instantiated_features = {}
            for feature_instance_id, instance_data in loc_data["features"].items():
                model_id = instance_data.get("model_id")
                if model_id and model_id in environmental_feature_models:
                    # Start with a deep copy of the model data to avoid modifying the original model
                    instantiated_feature = json.loads(json.dumps(environmental_feature_models[model_id])) # Deep copy
                    # Override with instance-specific data (excluding model_id itself)
                    override_data = {k: v for k, v in instance_data.items() if k != "model_id"}
                    instantiated_feature.update(override_data)
                    instantiated_features[feature_instance_id] = instantiated_feature
                else: # If no model_id or model not found, keep the original instance data
                    instantiated_features[feature_instance_id] = instance_data.copy() # Important to copy
            locations[loc_id]["features"] = instantiated_features

    # Convert NPC dictionaries in locations to NPC objects
    for loc_id, loc_data in locations.items():
        if "npcs" in loc_data and isinstance(loc_data["npcs"], dict):
            npc_objects = {}
            for npc_id, npc_dict_data in loc_data["npcs"].items():
                # Prepare kwargs for NPC constructor, mapping "type" from JSON to "npc_type"
                npc_init_kwargs = npc_dict_data.copy() # Start with a copy of the NPC data
                if "type" in npc_init_kwargs:
                    npc_init_kwargs["npc_type"] = npc_init_kwargs.pop("type") # Rename key for constructor
                
                npc_objects[npc_id] = NPC(
                    npc_id=npc_id,
                    **npc_init_kwargs # Unpack the potentially modified kwargs
                )
            locations[loc_id]["npcs"] = npc_objects
        elif "npcs" in loc_data and not isinstance(loc_data["npcs"], dict):
            print(f"[WARNING] NPCs data for location '{loc_id}' is not a dictionary. Skipping NPC object conversion for this location.")

    # Post-load validation/checks (optional but recommended)
    if not locations:
        print("[ERROR] Locations data is empty after reload!")
    if not items_data:
        print("[ERROR] Items data is empty after reload!")
    # Add more checks as needed
    if not species_data:
        print("[ERROR] Species data is empty after reload!")
    if not classes_data:
        print("[ERROR] Classes data is empty after reload!")
    if not zone_layouts:
        print("[ERROR] Zone layouts data is empty after reload!")
    if not environmental_feature_models: # Add check for the new models
        print("[WARNING] Environmental feature models data is empty. This is normal if you haven't created any models yet.")

# --- City Map Data Loading ---
def _load_city_map_data_from_file(city_id):
    """Helper function to load data for a specific city map from its JSON file."""
    filename = f"{city_id}_city_map.json"
    filepath = os.path.join(DATA_DIR, filename)
    try:
        if not os.path.exists(filepath):
            print(f"[WARNING] City map data file not found: {filepath}. City map for '{city_id}' will not be available.")
            return None
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"[Game Data] Successfully loaded city map for '{city_id}' from {filepath}")
            return data
    except json.JSONDecodeError as e:
        print(f"[ERROR] Error decoding JSON from city map file {filepath}: {e}. City map for '{city_id}' will not be available.")
        return None
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred while loading city map {filepath}: {e}. City map for '{city_id}' will not be available.")
        return None


# Initial load of game data when the script starts
load_all_game_data()

web_server_thread = None

# Create Flask app instance at the global level if flask is available
if flask_available:
    flask_app_instance = Flask(__name__)
else:
    flask_app_instance = None # Keep it None if Flask can't be imported

def _get_terminal_character_choices():
    """Handles terminal input for character creation choices."""
    print("\n--- Character Creation ---")

    # Species Selection
    print("Choose your Species:")
    species_options = {str(i+1): s_id for i, s_id in enumerate(species_data.keys())}
    for num, s_id in species_options.items():
        print(f"  {num}. {species_data[s_id]['name']} - {species_data[s_id]['description']}")

    chosen_species_id = None
    while not chosen_species_id:
        choice = input("Enter the number of your species: ").strip()
        if choice in species_options:
            chosen_species_id = species_options[choice]
        else:
            print("Invalid choice. Please try again.")

    # Class Selection
    print("\nChoose your Class:")
    class_options = {str(i+1): c_id for i, c_id in enumerate(classes_data.keys())}
    for num, c_id in class_options.items():
        print(f"  {num}. {classes_data[c_id]['name']} - {classes_data[c_id]['description']}")

    chosen_class_id = None
    while not chosen_class_id:
        choice = input("Enter the number of your class: ").strip()
        if choice in class_options:
            chosen_class_id = class_options[choice]
        else:
            print("Invalid choice. Please try again.")

    # Name Input
    player_name = ""
    name_valid = False
    while not name_valid:
        player_name = input("\nEnter your character's name: ").strip()
        if not player_name:
            print("Name cannot be empty. Please try again.")
        elif len(player_name) > MAX_NAME_LENGTH:
            print(f"Name is too long (max {MAX_NAME_LENGTH} characters). Please try again.")
        # Apply stricter humanoid naming rules for current species
        elif not ALLOWED_HUMANOID_NAME_PATTERN.match(player_name):
            print("Name contains invalid characters. Use only letters, spaces, hyphens (-), or apostrophes ('). Numbers are not allowed for this species.")
        elif player_name.isdigit():
            print("Name cannot be purely numeric. Please try again.")
        else:
            name_valid = True
            

    # Gender Selection
    print("\nChoose your Gender:")
    gender_options = {"1": "Male", "2": "Female"}
    for num, desc in gender_options.items():
        print(f"  {num}. {desc}")
    chosen_gender = None
    while chosen_gender is None:
        choice = input("Enter the number for your gender: ").strip()
        if choice in gender_options:
            chosen_gender = gender_options[choice]
        else:
            print("Invalid choice. Please try again.")
    
    return chosen_species_id, chosen_class_id, player_name, chosen_gender

def list_existing_characters():
    """Scans the player_data directory and returns a list of character names."""
    characters = []
    if os.path.exists(PLAYER_LOGS_DIR): # PLAYER_LOGS_DIR is now absolute
        for entry in os.listdir(PLAYER_LOGS_DIR):
            char_dir_path = os.path.join(PLAYER_LOGS_DIR, entry)
            if os.path.isdir(char_dir_path):
                # Try to read character_creation.json to get details
                char_file_path = os.path.join(char_dir_path, "character_creation.json")
                if os.path.exists(char_file_path):
                    try:
                        with open(char_file_path, 'r') as f:
                            char_json_data = json.load(f) # Renamed to avoid confusion with global 'data'

                        # Try to get ID using the new keys first, then fallback to potentially older keys
                        species_id_from_file = char_json_data.get("species_id")
                        if species_id_from_file is None:
                            species_id_from_file = char_json_data.get("species") # Fallback

                        class_id_from_file = char_json_data.get("class_id")
                        if class_id_from_file is None:
                            class_id_from_file = char_json_data.get("class") # Fallback

                        species_name_display = species_data.get(species_id_from_file, {}).get("name", "Unknown Species")
                        class_name_display = classes_data.get(class_id_from_file, {}).get("name", "Unknown Class")
                        character_level_display = char_json_data.get("level", 1) # Default to 1 if not found
                        
                        characters.append({
                            "display_name": char_json_data.get("name", entry.replace("_", " ")), # Use actual name if available
                            "class": class_name_display,
                            "species": species_name_display,
                            "level": character_level_display
                        })
                    except Exception: # pylint: disable=broad-except
                        characters.append({"display_name": entry.replace("_", " "), "class": "N/A", "species": "N/A", "level": "N/A"}) # Fallback
    return characters


def sanitize_filename(name):
    """Sanitizes a string to be used as a filename/directory name."""
    name = name.strip().replace(" ", "_")
    name = re.sub(r'(?u)[^-\w.]', '', name) # Remove non-alphanumeric (excluding -, _, .)
    return name if name else "invalid_name"

def save_player_data(player_to_save, reason_for_save="Game state saved"):
    """Saves current player data to their character_creation.json file."""
    if not player_to_save.name: # Access attribute directly
        print("[ERROR] Cannot save game: Player name not set.") # Changed to ERROR for consistency
        return False # Indicate failure

    if not os.path.exists(PLAYER_LOGS_DIR):
        try:
            os.makedirs(PLAYER_LOGS_DIR)
        except OSError as e:
            print(f"[ERROR] Could not create player logs directory: {e}")
            return False # Indicate failure

    player_name_sanitized = sanitize_filename(player_to_save.name)
    player_specific_dir = os.path.join(PLAYER_LOGS_DIR, player_name_sanitized)

    if not os.path.exists(player_specific_dir):
        try:
            os.makedirs(player_specific_dir)
        except OSError as e:
            print(f"[ERROR] Could not create directory for player '{player_to_save.name}': {e}")
            return False

    # Always save to the canonical save file name that load_character_data uses.
    save_file_path = os.path.join(player_specific_dir, "character_creation.json")
    try:
        data_to_save = player_to_save.__dict__.copy()
        # Convert set to list for JSON serialization
        if isinstance(data_to_save.get("visited_locations"), set):
            data_to_save["visited_locations"] = list(data_to_save["visited_locations"])
        with open(save_file_path, 'w') as f:
            json.dump(data_to_save, f, indent=4)
        print(f"[Save] {reason_for_save}. Player data for '{player_to_save.name}' saved to {save_file_path}")
        return True # Indicate success
    except Exception as e:
        print(f"[ERROR] Failed to save player data for '{player_to_save.name}': {e}")
        return False

def delete_character_data(character_display_name):
    """Deletes a character's data directory."""
    sanitized_name = sanitize_filename(character_display_name)
    player_specific_dir = os.path.join(PLAYER_LOGS_DIR, sanitized_name)

    if os.path.exists(player_specific_dir) and os.path.isdir(player_specific_dir):
        try:
            shutil.rmtree(player_specific_dir)
            print(f"Character data for '{character_display_name}' deleted successfully.")
            return True
        except Exception as e: # pylint: disable=broad-except
            print(f"Error deleting character data for '{character_display_name}': {e}")
            return False
    print(f"No data directory found for character '{character_display_name}'.")
    return False

def load_character_data(character_display_name):
    """Loads character data from the log file into the global player object."""
    global player
    sanitized_name = sanitize_filename(character_display_name) # Sanitize display name to get dir name
    player_specific_dir = os.path.join(PLAYER_LOGS_DIR, sanitized_name)
    # Assuming the primary log is 'character_creation.json' for now
    log_file_path = os.path.join(player_specific_dir, "character_creation.json")

    if os.path.exists(log_file_path):
        try:
            with open(log_file_path, 'r') as f:
                player_data_dict = json.load(f)
            # Re-initialize player object with loaded data
            player = Player(name=player_data_dict.get("name", "Adventurer"), gender=player_data_dict.get("gender", "Unspecified"))
            for key, value in player_data_dict.items():
                setattr(player, key, value) # Set all attributes from the loaded dict
            
            # Convert loaded list of visited locations back to a set
            if "visited_locations" in player_data_dict and isinstance(player_data_dict["visited_locations"], list):
                player.visited_locations = set(player_data_dict["visited_locations"])
            else: # Ensure it's always a set, even if missing from old save or malformed
                player.visited_locations = set()
            player.game_active = True # Ensure game is marked active
            print(f"\nCharacter '{player.name}' loaded successfully.")
            return True
        except Exception as e:
            print(f"Error loading character data for '{character_display_name}': {e}")
            return False
    print(f"No save data found for character '{character_display_name}'.")
    return False

def log_game_event(event_type, data_dict):
    """Logs a specific game event to a character's event log file."""
    if not player.name or not player.game_active: # Don't log if no active character or game
        return

    player_name_sanitized = sanitize_filename(player.name if player.name else "unknown_player_event_log")
    player_specific_dir = os.path.join(PLAYER_LOGS_DIR, player_name_sanitized)

    if not os.path.exists(player_specific_dir):
        try:
            os.makedirs(player_specific_dir)
        except OSError as e:
            print(f"[Error] Could not create directory for event log: {player_specific_dir}. Details: {e}")
            return # Cannot log if directory can't be made

    # Using .jsonl for JSON Lines format (one JSON object per line)
    log_file_path = os.path.join(player_specific_dir, "events.jsonl")

    log_entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), # UTC timestamp
        "event_type": event_type,
        **data_dict # Merge the specific event data
    }
    
    # --- Reporting "enter" events to console ---
    enter_event_types = ["enter_city_map_via_command", "auto_move_to_city_map"]
    if event_type in enter_event_types:
        print(f"[CONSOLE_REPORT] 'Enter' event logged: Type='{event_type}', Data='{data_dict.get('to_city', data_dict.get('to', 'N/A'))}'")

    try:
        with open(log_file_path, 'a') as f: # Append mode
            json.dump(log_entry, f)
            f.write('\n') # Newline for JSON Lines
    except Exception as e:
        print(f"[Error] Failed to write to event log {log_file_path}: {e}")

def initialize_game_state():
    """Guides through new character creation and sets up initial game state."""
    # For terminal play, get choices first
    species_id, class_id, char_name, char_gender = _get_terminal_character_choices()

    if not game_logic.apply_character_choices_and_stats(player, species_id, class_id, char_name, char_gender, items_data, species_data, classes_data, save_player_data):
        player.game_active = False
        print("Character creation cancelled. Game not started.")
        # No return here, _apply_character_choices_and_stats returns bool but doesn't stop execution
        return

    # player.game_active is set within apply_character_choices_and_stats
    player.combat_target_id = None
    player.dialogue_npc_id = None
    player.dialogue_options_pending = {}
    player.flags["found_starter_items"] = False
    
    species_info = species_data[player.species_id]
    print(f"\n{species_info['backstory_intro']}")
    player.visited_locations.add("generic_start_room") # Mark starting room as visited

    start_room_id = "generic_start_room" 
    player.move_to(start_room_id) # Player object's method
    class_info = classes_data[player.class_id]
    if start_room_id in locations and "worn_crate" in locations[start_room_id].get("features", {}):
        crate_contents = list(class_info["starter_items"])
        crate_contents.append("blank_map_scroll") # Add map scroll to the crate
        locations[start_room_id]["features"]["worn_crate"]["contains_on_open"] = crate_contents
        locations[start_room_id]["features"]["worn_crate"]["closed"] = True 
    
    print(f"You feel a pull towards the {locations[start_room_id]['name']}.")

def start_combat(npc_id):
    player.enter_combat(npc_id) # Player object's method
    current_loc_npcs = locations[player.current_location_id].get("npcs", {})
    npc_object = current_loc_npcs.get(npc_id)
    if not npc_object or not npc_object.is_alive(): # Use NPC object method
        return
    print(f"\n--- COMBAT START ---")
    print(f"You are attacked by {npc_object.name}!")

def handle_npc_defeat(npc_id):
    current_loc_data = locations[player.current_location_id]
    npc_object = current_loc_data["npcs"][npc_id] # Get the NPC object
    print(f"\n{npc_object.name} has been defeated!")
    
    loot_item_ids = npc_object.loot # Access attribute
    if loot_item_ids:
        dropped_items_details = []
        for item_id in loot_item_ids:
            item_detail = {"id": item_id, "name": items_data.get(item_id, {}).get("name", item_id)}
            if items_data.get(item_id, {}).get("type") == "currency" and "value" in items_data.get(item_id, {}):
                item_detail["value"] = items_data.get(item_id, {}).get("value")
            dropped_items_details.append(item_detail)
        log_game_event("npc_loot_dropped", {
            "npc_id": npc_id, "npc_name": npc_object.name, "dropped_items": dropped_items_details,
            "location_id": player.current_location_id
        })
        for item_id in npc_object.loot:
            current_loc_data.setdefault("items", []).append(item_id)
            print(f"{npc_object.name} dropped a {items_data.get(item_id, {}).get('name', item_id)}!")
    
    # Award XP for defeating NPC
    xp_reward = getattr(npc_object, 'xp_reward', 25) # Use getattr for optional attribute, or ensure it's in __init__
    player.add_xp(xp_reward, log_event_func=log_game_event) 
    player._recalculate_derived_stats(items_data) # Recalculate stats after potential level up from XP

    del current_loc_data["npcs"][npc_id]
    player.leave_combat() # Player object's method

def npc_combat_turn():
    if not player.combat_target_id or not player.game_active:
        return

    npc_id = player.combat_target_id
    current_loc_data = locations[player.current_location_id]
    
    if npc_id not in current_loc_data["npcs"]:
        return 

    npc_object = current_loc_data["npcs"][npc_id] # Get NPC object

    if not npc_object.is_alive(): # Use NPC method
        return

    print(f"\n{npc_object.name}'s turn...")
    damage_to_player = npc_object.attack_power # Access attribute
    
    if player.is_deflecting:
        damage_to_player = max(0, damage_to_player // 2) 
        print(f"You deflect part of the blow!")
        player.set_deflecting(False) # Player object's method

    player.take_damage(damage_to_player) # Player method
    print(f"{npc_object.name} attacks you for {damage_to_player} damage.")
    print(f"You have {player.hp}/{player.max_hp} HP remaining.")

    if player.hp <= 0:
        player.handle_defeat() # Player object's method
    
    player.update_special_cooldowns()

@trace_function_calls
def handle_environmental_interaction(feature_id, action_verb):
    loc_data = locations[player.current_location_id]
    feature = loc_data.get("features", {}).get(feature_id)

    if not feature:
        print(f"There is no '{feature_id.replace('_', ' ')}' here to interact with.")
        return

    action_details = feature.get("actions", {}).get(action_verb)
    if not action_details:
        print(f"You can't '{action_verb}' the {feature_id.replace('_', ' ')}.")
        return

    outcome_pool = action_details["outcomes"]
    probabilities = action_details.get("probabilities")
    
    if probabilities and len(probabilities) == len(outcome_pool):
        chosen_outcome = random.choices(outcome_pool, weights=probabilities, k=1)[0]
    elif outcome_pool: 
        chosen_outcome = outcome_pool[0]
    else:
        print(f"Nothing seems to happen when you try to {action_verb} the {feature_id.replace('_', ' ')}.")
        return

    print(chosen_outcome.get("message", "You interact with the object."))
    if chosen_outcome.get("type") == "item":
        # This part is for features that directly give an item upon a generic interaction.
        game_logic.award_item_to_player(player, items_data, chosen_outcome["item_id"], source=f"feature_interaction_{feature_id}_{action_verb}", log_event_func=log_game_event)

    elif chosen_outcome.get("type") == "reveal_items" and feature_id == "worn_crate":
        if feature.get("closed"):
            items_in_crate = list(feature.get("contains_on_open", [])) # Make a copy
            if items_in_crate:
                print("You pry open the crate and find some items inside!") # Updated message
                
                for item_id in items_in_crate: # Iterate through items to award them
                    game_logic.award_item_to_player(player, items_data, item_id, source=f"opened_{feature_id}", log_event_func=log_game_event)
                    # acquired_item_names.append(items_data.get(item_id, {}).get("name", item_id)) # Not strictly needed if award_item prints
                
                if player.current_location_id == "generic_start_room": # Specific message for starter crate
                     print("Among the items, you see a map of a nearby settlement and a small pouch of coins.") # Message adjusted
                # Log the contents revealed from the crate
                # This log_game_event call is already good for "player opens chest filled with..."
                # We can enhance it slightly if items have quantities, e.g. coins
                revealed_items_details_for_log = []
                for item_id in items_in_crate:
                    item_data_for_log = {"id": item_id, "name": items_data.get(item_id, {}).get("name", item_id)}
                    if items_data.get(item_id, {}).get("type") == "currency" and "value" in items_data.get(item_id, {}):
                        item_data_for_log["value"] = items_data.get(item_id, {}).get("value")
                    revealed_items_details_for_log.append(item_data_for_log)
                log_game_event("crate_contents_revealed", {
                    "feature_id": feature_id, "revealed_items": revealed_items_details_for_log,
                    "location_id": player.current_location_id
                })
            feature["contains_on_open"] = [] # Empty the crate's internal list
            feature["closed"] = False
            player.flags["found_starter_items"] = True # Still set this flag

            # --- Conditional Auto-Teleport Logic (Specific to starter crate) ---
            # This logic remains as per your previous request for this specific crate
            if player.current_location_id == "generic_start_room":
                start_room_data = locations.get("generic_start_room", {})
                exit_destination_id = start_room_data.get("exits", {}).get("out")

                if exit_destination_id == "eldoria_city_node": # Check if the 'out' exit leads to Eldoria entrance
                    # Transition directly into Eldoria's detailed city map
                    eldoria_city_map_details = city_maps_data.get("eldoria")
                    # Use the entry point defined for the starter area teleport
                    target_entry_point_key = "from_starter_area_teleport" # Ensure this key exists in eldoria_city_map.json
                    entry_coords = eldoria_city_map_details.get("entry_points", {}).get(target_entry_point_key, {"x": 1, "y": 1}) # Fallback coords

                    if eldoria_city_map_details and entry_coords:
                        print("\nThe way out of the chamber seems clear now. You step outside and find yourself within the city of Eldoria.")
                        player.last_zone_location_id = exit_destination_id # Store "eldoria_city_node"
                        player.current_map_type = "city"
                        player.current_city_id = "eldoria"
                        player.current_city_x = entry_coords["x"]
                        player.current_city_y = entry_coords["y"]
                        player.current_location_id = exit_destination_id # Keep context of the zone map node
                        log_game_event("auto_move_to_city_map", {"from": "generic_start_room", "to_city": "eldoria", "coords": f"({entry_coords['x']},{entry_coords['y']})", "reason": "opened_starter_crate_terminal", "player_name": player.name})

    elif chosen_outcome.get("type") == "stat_change" and chosen_outcome.get("stat") == "hp":
        player.heal(chosen_outcome.get("amount", 0)) # Use method
        print(f"Your HP is now {player.hp}/{player.max_hp}.")

def run_minimal_web_server():
    global flask_app_instance
    if not flask_available:
        return

    # Routes are now defined globally, so this function just runs the app
    if not flask_app_instance: # Should not happen if flask_available was true
        print("[ERROR] Flask app instance not created despite Flask being available.")
        # The MAX_NAME_LENGTH will be passed to the template
        return

    # Optional: Flask endpoint to sync pause state with server if needed later
    # @flask_app_instance.route('/api/set_pause_state', methods=['POST'])
    # def set_pause_state_route():
    #     data = request.get_json()
    #     player["is_paused"] = data.get("paused", False)
    #     return jsonify({"message": "Pause state updated", "is_paused": player["is_paused"]})

    # --- Flask Routes Definition ---
    # Move all @flask_app_instance.route decorators here, or ensure they are defined after flask_app_instance is created globally.
    # For simplicity, we'll assume they are already defined globally using the flask_app_instance.
    # The actual run command is at the end of this function.

    print("Starting web server on http://127.0.0.1:5000/ ...")
    try:
        flask_app_instance.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
    except Exception as e:
        print(f"Failed to start or run web server: {e}")

# --- Flask Routes Definition ---
# Define all routes here, using the global flask_app_instance

if flask_app_instance: # Only define routes if Flask app was successfully created
    @flask_app_instance.route('/')
    def web_index():
        # The MAX_NAME_LENGTH will be passed to the template
        return render_template('index.jinja', max_name_length=MAX_NAME_LENGTH)

    @flask_app_instance.route('/process_game_action', methods=['POST'])
    def process_game_action_route():
        data = request.get_json()
        action = data.get('action')

        # Ensure player object and essential keys exist, especially current_location_id
        if not player or player.current_location_id is None:
            # This might happen if character creation/load didn't complete properly for the web session
            # Or if an action is attempted before the game is truly active for the web.
            player.current_location_id = "generic_start_room" # Default to a safe starting point
            if not player.name: player.name = "Unknown Adventurer" # Ensure defaults if object was just created
            if not hasattr(player, 'hp'): player.hp = 0
            if not hasattr(player, 'max_hp'): player.max_hp = 0
            if not hasattr(player, 'inventory'): player.inventory = []
            player.game_active = False # Mark as not fully active if we had to reset

        game_response = {
            "message": "",
            "player_hp": player.hp,
            "player_name": player.name,
            "player_max_hp": player.max_hp,
            "location_name": "Unknown Area", # Default
            "description": "An unfamiliar place.", # Default
            "player_coins": player.coins,
            "player_level": player.level,
            "player_xp": player.xp,
            "player_xp_to_next_level": player.xp_to_next_level,
            "player_class_name": classes_data.get(player.class_id, {}).get("name", "N/A"),
            "player_species_name": species_data.get(player.species_id, {}).get("name", "N/A"),
            "player_attack_power": player.attack_power,
            "player_equipment": { # Initialize with all expected slots
                "head": "Empty", "shoulders": "Empty", "chest": "Empty", "hands": "Empty",
                "legs": "Empty", "feet": "Empty", "main_hand": "Empty", "off_hand": "Empty",
                "neck": "Empty", "back": "Empty", "trinket1": "Empty", "trinket2": "Empty"
            },
            "interactable_features": [], 
            "room_items": [], 
            "npcs_in_room": [], # List of NPCs in the room
                "can_save_in_city": False,
                "available_actions": [], # Initialize available_actions
                "available_exits": [], # For dynamic go buttons
                "current_zone_map_data": None, # Initialize for the side panel zone map
                "available_exits": [] # For dynamic go buttons
            # "dialogue_npc_id": None, 
            # "dialogue_options_pending": {}, 
        }

        if not player.game_active and action not in ['!start']: # Check game_active safely
             game_response["message"] = "Game not started. Please start the game first (this might require a terminal interaction if using --browser at launch without --autostart)."
             return jsonify(game_response)

        if action == 'look':
            loc_id = player.current_location_id
            if loc_id in locations:
                # location_name and description already set by default above
                game_response["location_name"] = locations[loc_id].get("name", "Unknown Area")
                game_response["description"] = locations[loc_id]["description"]
                game_response["message"] = "" # Description is primary
            else:
                game_response["message"] = "Current location is unknown."
        elif action.startswith('go '):
            direction = action.split(' ', 1)[1].lower() # Ensure direction is lowercase

            if player.current_map_type == "city":
                # --- City Map Movement ---
                current_city_map = city_maps_data.get(player.current_city_id)
                if not current_city_map:
                    game_response["message"] = "[ERROR] Current city map data is missing. Cannot move."
                    # location_name and description will be set by the final population logic
                else:
                    grid_width = current_city_map["grid_size"]["width"]
                    grid_height = current_city_map["grid_size"]["height"]
                    
                    new_x, new_y = player.current_city_x, player.current_city_y

                    if direction == "north": new_y -= 1
                    elif direction == "south": new_y += 1
                    elif direction == "east": new_x += 1
                    elif direction == "west": new_x -= 1
                    else:
                        game_response["message"] = f"Unknown direction: {direction}"
                        # No change in location, location_name/description will be set by final population
                    
                    if 0 <= new_x < grid_width and 0 <= new_y < grid_height:
                        target_cell_data = current_city_map["cells"][new_y][new_x]
                        # Define impassable types based on your eldoria_city_map.json
                        impassable_types = ["wall_city_edge", "building_house_large", "building_house_small", 
                                            "building_library_facade", "square_fountain"] # Add more as needed
                        if target_cell_data.get("impassable") or target_cell_data.get("type") in impassable_types:
                            game_response["message"] = f"You can't go {direction}. {target_cell_data.get('description', 'Something blocks your way.')}"
                        else:
                            player.current_city_x = new_x
                            player.current_city_y = new_y
                            game_response["message"] = f"You move {direction}."
                            
                            # Handle cell-specific actions (like exiting the city)
                            cell_action = target_cell_data.get("action")
                            if cell_action:
                                if isinstance(cell_action, dict) and cell_action.get("type") == "exit_to_zone_map" and "target_zone_loc_id" in cell_action:
                                    target_zone_loc = cell_action["target_zone_loc_id"]
                                    game_response["message"] += f" You exit {current_city_map.get('name', player.current_city_id.capitalize())}."
                                    player.current_map_type = "zone"
                                    player.current_location_id = target_zone_loc # This is the zone map node
                                    player.visited_locations.add(target_zone_loc) 
                                    # location_name/description will be set by final population
                                elif isinstance(cell_action, dict) and cell_action.get("type") == "move_to_cell" and "target_cell" in cell_action:
                                    player.current_city_x = cell_action["target_cell"]["x"]
                                    player.current_city_y = cell_action["target_cell"]["y"]
                                    game_response["message"] += f" You are quickly ushered to another part of the area..."
                            
                            # If still in city, location_name/description will be set by final population
                    else:
                        game_response["message"] = f"You can't go {direction}. You've reached the edge of this area."
                        # No change in location, location_name/description will be set by final population
            
            elif player.current_map_type == "zone": # Or default to zone movement
                # --- Zone Map Movement (Modified Existing Logic) ---
                current_loc_id = player.current_location_id # This is the zone map location ID
                current_location_data = locations.get(current_loc_id, {})
                
                if direction in current_location_data.get("exits", {}):
                    destination_loc_id = current_location_data["exits"][direction]
                    
                    # Check if moving to a city node that should trigger city map entry
                    destination_loc_data = locations.get(destination_loc_id, {})
                    city_id_for_destination = destination_loc_data.get("zone") # e.g., "eldoria"
                    city_map_transition_info = destination_loc_data.get("city_map_transitions", {}).get("enter")

                    if city_map_transition_info and \
                       city_id_for_destination == city_map_transition_info.get("city_id") and \
                       city_id_for_destination in city_maps_data:
                        
                        city_map_details = city_maps_data.get(city_id_for_destination)
                        entry_point_key = city_map_transition_info.get("entry_point_key")
                        entry_coords = city_map_details.get("entry_points", {}).get(entry_point_key)

                        if entry_coords:
                            player.last_zone_location_id = destination_loc_id 
                            player.current_map_type = "city"
                            player.current_city_id = city_id_for_destination
                            player.current_city_x = entry_coords["x"]
                            player.current_city_y = entry_coords["y"]
                            player.current_location_id = destination_loc_id # Keep zone context
                            game_response["message"] = f"You walk {direction} and enter {city_map_details.get('name', city_id_for_destination.capitalize())}."
                        else: 
                            player.move_to(destination_loc_id) 
                            game_response["message"] = f"You walk {direction}."
                    else: 
                        player.move_to(destination_loc_id) 
                        game_response["message"] = f"You walk {direction}."
                        
                        # "Listener" for city node arrival
                        new_location_data_after_move = locations.get(player.current_location_id, {})
                        if new_location_data_after_move.get("city_map_transitions", {}).get("enter"):
                            # Add "enter city" action if not already present
                            if "enter city" not in game_response.get("available_actions", []):
                                game_response.setdefault("available_actions", []).append("enter city")
                            
                            # Check for and append a custom on_arrival_message
                            arrival_message = new_location_data_after_move.get("on_arrival_message")
                            if arrival_message:
                                game_response["message"] += f" {arrival_message}"
                            
                            log_game_event("arrived_at_city_node", {
                                "city_node_id": player.current_location_id,
                                "city_name": new_location_data_after_move.get("name", "Unknown City"),
                                "player_name": player.name
                            })
                else:
                    game_response["message"] = f"You can't go {direction} from here."
                    game_response["player_current_location_id"] = player.current_location_id 
            else: 
                game_response["message"] = "Error: Unknown map type for movement."
            # Note: game_response["location_name"] and game_response["description"] will be
            # populated by the final assembly logic based on the new player state.
        elif action == "exit city" and player.current_map_type == "city":
            current_city_map = city_maps_data.get(player.current_city_id)
            if current_city_map:
                px, py = player.current_city_x, player.current_city_y
                if 0 <= py < len(current_city_map.get("cells", [])) and \
                0 <= px < len(current_city_map.get("cells", [])[py]):
                    current_cell_data = current_city_map["cells"][py][px]
                    cell_action_details = current_cell_data.get("action")
                    if isinstance(cell_action_details, dict) and cell_action_details.get("type") == "exit_to_zone_map":
                        target_zone_loc = cell_action_details.get("target_zone_loc_id")
                        if target_zone_loc:
                            game_response["message"] = f"You exit {current_city_map.get('name', player.current_city_id.capitalize())}."
                            player.current_map_type = "zone"
                            player.current_location_id = target_zone_loc
                            player.visited_locations.add(target_zone_loc)
                            # Potentially update player.last_zone_location_id if needed for re-entry context
                            # player.last_zone_location_id = player.current_location_id # Or the city node itself
                        else:
                            game_response["message"] = "This exit seems to lead nowhere specific."
                    else:
                        game_response["message"] = "You can't exit the city from here."
                else:
                    game_response["message"] = "Error: Player is at an invalid position in the city."
            else:
                game_response["message"] = "Error: City data not found."

        elif action == "enter city": # New block for "enter city" command
            if player.current_map_type == "zone":
                current_loc_id = player.current_location_id
                current_location_data = locations.get(current_loc_id, {})

                if "city_map_transitions" in current_location_data and \
                   "enter" in current_location_data["city_map_transitions"]:
                    
                    transition_info = current_location_data["city_map_transitions"]["enter"]
                    city_id_to_enter = transition_info.get("city_id")
                    entry_point_key = transition_info.get("entry_point_key")
                    city_map_details = city_maps_data.get(city_id_to_enter)

                    if city_map_details and entry_point_key and entry_point_key in city_map_details.get("entry_points", {}):
                        entry_coords = city_map_details["entry_points"][entry_point_key]
                        player.last_zone_location_id = current_loc_id # Store where we entered from
                        player.current_map_type = "city"
                        player.current_city_id = city_id_to_enter
                        player.current_city_x = entry_coords["x"]
                        player.current_city_y = entry_coords["y"]
                        # player.current_location_id remains the zone node for context
                        game_response["message"] = f"You step through the gate and enter {city_map_details.get('name', city_id_to_enter.capitalize())}."
                        log_game_event("enter_city_map_via_command", {"from_zone_loc": current_loc_id, "to_city": city_id_to_enter, "coords": f"({entry_coords['x']},{entry_coords['y']})", "player_name": player.name})
                    else:
                        game_response["message"] = f"You are at an entrance, but the detailed map for {city_id_to_enter.capitalize()} seems inaccessible or misconfigured from here."
                else:
                    game_response["message"] = "You are not at a recognized city entrance, or there's no clear way to 'enter city' from here."
            else: # Already in a city
                game_response["message"] = "You are already inside a city."

        elif action == 'inventory':
            # Ensure inventory key exists
            player_inventory = player.inventory
            if player_inventory:
                # Send detailed inventory: list of objects {id, name, type, equip_slot}
                game_response["inventory_list"] = [
                    {
                        "id": item_id,
                        "name": items_data.get(item_id, {}).get("name", item_id.replace("_", " ")),
                        "type": items_data.get(item_id, {}).get("type"),
                        "equip_slot": items_data.get(item_id, {}).get("equip_slot")
                    }
                    for item_id in player_inventory
                ]
                game_response["message"] = "" 
            else:
                game_response["message"] = "Your inventory is empty."
        elif action == '!map':
            # The draw_zone_map function now prints directly to terminal.
            # For the web UI, the zone map is in the side panel.
            # This command in the web input field can just acknowledge.
            game_response["message"] = "Zone map is displayed in the side panel. Use 'View World Map (Modal)' for a larger view."
            current_loc_id_for_map_ack = player.current_location_id
            current_location_data_for_map_ack = locations.get(current_loc_id_for_map_ack, {})
            game_response["location_name"] = current_location_data_for_map_ack.get("name", "Unknown Area")
            game_response["description"] = current_location_data_for_map_ack.get("description", "An unfamiliar place.")
        elif action.startswith('take '):
            item_id_to_take = action.split(' ', 1)[1]
            current_loc_id = player.current_location_id
            location_data = locations.get(current_loc_id, {})
            room_items = location_data.get("items", [])

            if item_id_to_take in room_items:
                if item_id_to_take == "small_pouch_of_coins":
                    coin_value = items_data.get(item_id_to_take, {}).get("value", 0)
                    player.add_coins(coin_value, log_event_func=log_game_event, source=f"take_room_web_{current_loc_id}_{item_id_to_take}")
                    game_response["message"] = f"You picked up the {items_data.get(item_id_to_take, {}).get('name', item_id_to_take)} and gained {coin_value} copper coins."
                    room_items.remove(item_id_to_take)
                else:
                    award_message = game_logic.award_item_to_player(player, items_data, item_id_to_take, source=f"take_room_web_{current_loc_id}", log_event_func=log_game_event)
                    game_response["message"] = award_message
                    room_items.remove(item_id_to_take)
                
                # Update location name and description for the response as they might be cleared by default
                game_response["location_name"] = location_data.get("name", "Unknown Area")
                game_response["description"] = location_data.get("description", "An unfamiliar place.")
            else:
                game_response["message"] = f"There is no '{items_data.get(item_id_to_take, {}).get('name', item_id_to_take.replace('_',' '))}' here to take."
                game_response["location_name"] = location_data.get("name", "Unknown Area")
                game_response["description"] = location_data.get("description", "An unfamiliar place.")
        
        elif action == "open worn_crate" and player.current_location_id == "generic_start_room":
            # This specific handler for "open worn_crate"
            crate = locations["generic_start_room"]["features"]["worn_crate"]
            if crate.get("closed"):
                game_response["message"] = "You pry open the crate." 
                items_in_crate = list(crate.get("contains_on_open", [])) # Make a copy of items to be revealed

                acquired_item_names_for_message = []
                if items_in_crate:
                    # Add a message indicating contents are being revealed
                    game_response["message"] += "\nInside, you find:"

                    for item_id in items_in_crate:
                        # Award item directly to player's inventory
                        acquisition_msg = game_logic.award_item_to_player(
                            player, items_data, item_id, 
                            source=f"opened_worn_crate_web_{player.current_location_id}", 
                            log_event_func=log_game_event
                        ) # award_item_to_player already logs and prints to terminal
                        # For web UI, the message is built separately below

                    # The message about finding items is now built by award_item_to_player
                    # We can add a specific message for the starter crate contents here if needed
                    if player.current_location_id == "generic_start_room": # Specific message for starter crate
                        game_response["message"] += "\nAmong the items, you find a map of a nearby settlement and a small pouch of coins."
                crate["contains_on_open"] = [] 
                crate["closed"] = False
                player.flags["found_starter_items"] = True

                # --- Conditional Auto-Teleport Logic (Specific to starter crate) ---
                # This logic remains as per your previous request for this specific crate
                if player.current_location_id == "generic_start_room": # Check for the specific crate instance
                    start_room_data_web = locations.get("generic_start_room", {})
                    exit_destination_id_web = start_room_data_web.get("exits", {}).get("out")

                    if exit_destination_id_web == "eldoria_city_node": # Check if the 'out' exit leads to Eldoria entrance
                        eldoria_city_map_details_web = city_maps_data.get("eldoria")
                        # Use the entry point defined for the starter area teleport
                        target_entry_point_key_web = "from_starter_area_teleport" # Ensure this key exists in eldoria_city_map.json
                        entry_coords_web = eldoria_city_map_details_web.get("entry_points", {}).get(target_entry_point_key_web, {"x": 1, "y": 1}) # Fallback

                        if eldoria_city_map_details_web and entry_coords_web:
                            game_response["message"] += "\nThe way out of the chamber seems clear now. You step outside and find yourself within the city of Eldoria."
                            player.last_zone_location_id = exit_destination_id_web
                            player.current_map_type = "city"
                            player.current_city_id = "eldoria"
                            player.current_city_x = entry_coords_web["x"]
                            player.current_city_y = entry_coords_web["y"]
                            player.current_location_id = exit_destination_id_web # Keep zone context
                            log_game_event("auto_move_to_city_map", {"from": "generic_start_room", "to_city": "eldoria", "coords": f"({entry_coords_web['x']},{entry_coords_web['y']})", "reason": "opened_starter_crate_web", "player_name": player.name})

            else:
                game_response["message"] = "The crate is already open and empty."
        elif action.startswith('unequip '):
            item_id_to_unequip_from_action = action.split(' ', 1)[1]
            # Find the item in equipped slots
            slot_unequipped_from = None
            for slot_key, equipped_item_id in player.equipment.items():
                if equipped_item_id == item_id_to_unequip_from_action: # Match by item ID
                    slot_unequipped_from = slot_key
                    break

            if slot_unequipped_from:
                unequip_message = player.unequip_item(slot_unequipped_from, items_data, log_event_func=log_game_event)
                game_response["message"] = unequip_message
            else:
                game_response["message"] = f"That item doesn't seem to be equipped."
            
            # Ensure current location data is still part of the response
            current_loc_id_for_unequip = player.current_location_id
            game_response["location_name"] = locations.get(current_loc_id_for_unequip, {}).get("name", "Unknown Area")
            game_response["description"] = locations.get(current_loc_id_for_sort, {}).get("description", "An unfamiliar place.")

        elif action.startswith('use_item_'): # New handler for using items from inventory
            item_id_to_use = action.split('use_item_', 1)[1]

            if item_id_to_use not in player.inventory:
                game_response["message"] = f"You don't have {items_data.get(item_id_to_use, {}).get('name', item_id_to_use.replace('_',' '))} in your inventory."
                # Location data will be populated by final assembly
                return jsonify(game_response)

            item_details = items_data.get(item_id_to_use)
            # Check if the item has a 'use' action defined
            if not item_details or "actions" not in item_details or "use" not in item_details["actions"]:
                 game_response["message"] = f"You can't 'use' the {item_details.get('name', item_id_to_use.replace('_',' '))} in that way."
                 # Location data will be populated by final assembly
                 return jsonify(game_response)

            use_action_details = item_details["actions"]["use"]
            outcome_pool = use_action_details.get("outcomes", [])

            # Append the action message if defined
            if use_action_details.get("message"):
                 game_response["message"] += use_action_details["message"] + "\n"

            # Process outcomes (assuming simple sequential or first outcome for now)
            if not outcome_pool:
                 game_response["message"] += f"Using the {item_details.get('name', item_id_to_use.replace('_',' '))} seems to have no effect."
                 # Location data will be populated by final assembly
                 return jsonify(game_response)

            # For simplicity, process all outcomes listed
            for chosen_outcome in outcome_pool:
                if chosen_outcome.get("message"):
                    game_response["message"] += chosen_outcome["message"] + "\n" # Append outcome-specific message

                if chosen_outcome.get("type") == "add_contained_currency":
                    currency_value = chosen_outcome.get("value", 0)
                    currency_type = chosen_outcome.get("currency_type", "coins") # Default to coins
                    if currency_value > 0:
                        # Assuming player only has 'coins' currency for now
                        player.add_coins(currency_value, log_event_func=log_game_event, source=f"used_item_web_{item_id_to_use}")
                        game_response["message"] += f"The {item_details.get('name', item_id_to_use.replace('_',' '))} yields {currency_value} {currency_type}.\n"
                    else:
                        game_response["message"] += f"The {item_details.get('name', item_id_to_use.replace('_',' '))} seems to be empty of currency.\n"

                elif chosen_outcome.get("type") == "reveal_contained_items":
                     items_to_reveal = chosen_outcome.get("items", [])
                     if items_to_reveal:
                         game_response["message"] += "Inside, you find:\n"
                         for revealed_item_id in items_to_reveal:
                             # award_item_to_player already logs and prints to terminal
                             acquisition_msg = game_logic.award_item_to_player(player, items_data, revealed_item_id, source=f"used_item_web_{item_id_to_use}", log_event_func=log_game_event)
                             # For web UI, add to the response message
                             item_name = items_data.get(revealed_item_id, {}).get("name", revealed_item_id.replace("_"," "))
                             game_response["message"] += f"- {item_name}\n"
                     else:
                         game_response["message"] += f"The {item_details.get('name', item_id_to_use.replace('_',' '))} seems to be empty of items.\n"

                # Add other item use outcome types here (e.g., heal, buff, etc.)
                elif chosen_outcome.get("type") == "heal":
                    heal_amount = chosen_outcome.get("amount", 0)
                    if heal_amount > 0:
                        player.heal(heal_amount)
                        game_response["message"] += f"You feel restored. Your HP is now {player.hp}/{player.max_hp}.\n"

            # After processing outcomes, remove the container item from inventory
            player.remove_item_from_inventory(item_id_to_use)
            game_response["message"] += f"The {item_details.get('name', item_id_to_use.replace('_',' '))} is consumed." # Or "is now empty and discarded."
            game_response["description"] = locations.get(current_loc_id_for_unequip, {}).get("description", "An unfamiliar place.") # Fixed typo here

        elif action.startswith('equip '):
            item_id_to_equip = action.split(' ', 1)[1]
            if item_id_to_equip in player.inventory:
                item_details = items_data.get(item_id_to_equip)
                if item_details and item_details.get("equip_slot"):
                    slot_to_equip_to = item_details["equip_slot"]
                    equip_message = player.equip_item(item_id_to_equip, slot_to_equip_to, items_data, log_event_func=log_game_event)
                    game_response["message"] = equip_message
                else:
                    game_response["message"] = f"You cannot equip {items_data.get(item_id_to_equip,{}).get('name', item_id_to_equip)}."
            else:
                game_response["message"] = f"You don't have {items_data.get(item_id_to_equip,{}).get('name', item_id_to_equip)} in your inventory."
            # Ensure current location data is still part of the response
            current_loc_id_for_equip = player.current_location_id
            game_response["location_name"] = locations.get(current_loc_id_for_equip, {}).get("name", "Unknown Area")
            game_response["description"] = locations.get(current_loc_id_for_equip, {}).get("description", "An unfamiliar place.")
        elif action == 'sort_inventory_by_id_action':
            if player.inventory:
                player.inventory.sort() # Sorts the list of item IDs alphabetically
                game_response["message"] = "Inventory sorted by ID."
                # CRITICAL: Repopulate inventory_list for the response so the UI can update dynamically
                player_inventory_sorted = player.inventory
                game_response["inventory_list"] = [
                    {
                        "id": item_id,
                        "name": items_data.get(item_id, {}).get("name", item_id.replace("_", " ")),
                        "type": items_data.get(item_id, {}).get("type"),
                        "equip_slot": items_data.get(item_id, {}).get("equip_slot")
                    }
                    for item_id in player_inventory_sorted
                ]
            else:
                game_response["message"] = "Inventory is empty, nothing to sort."
            # Ensure current location data is still part of the response for context
            current_loc_id_for_sort = player.current_location_id
            game_response["location_name"] = locations.get(current_loc_id_for_sort, {}).get("name", "Unknown Area")
            game_response["description"] = locations.get(current_loc_id_for_sort, {}).get("description", "An unfamiliar place.")
        elif action.startswith('talk '):
            npc_id_to_talk_to = action.split(' ', 1)[1]
            current_loc_id = player.current_location_id
            current_location_data = locations.get(current_loc_id, {})
            npcs_in_room = current_location_data.get("npcs", {}) # This now contains NPC objects
            
            target_npc_object = npcs_in_room.get(npc_id_to_talk_to) # Renamed for clarity

            if target_npc_object:
                game_response["message"] = f"You approach {target_npc_object.name}.\n"
                
                if target_npc_object.pre_combat_dialogue and target_npc_object.dialogue_options:
                    game_response["message"] += f"{target_npc_object.name} says: \"{target_npc_object.pre_combat_dialogue}\""
                    player.start_dialogue(target_npc_object.id, target_npc_object.dialogue_options)
                    # If you want to send dialogue options to UI:
                    # game_response["dialogue_npc_id"] = player.dialogue_npc_id
                    # game_response["dialogue_options_pending"] = player.dialogue_options_pending
                elif target_npc_object.type == "quest_giver_simple":
                    if target_npc_object.quest_item_needed in player.inventory:
                        game_response["message"] += f"{target_npc_object.name} says: \"{target_npc_object.dialogue_after_quest_complete or 'Thank you!'}\""
                        game_logic.remove_item_from_player_inventory(player, items_data, target_npc_object.quest_item_needed, source=f"quest_turn_in_web_{target_npc_object.id}", log_event_func=log_game_event)
                        if target_npc_object.quest_reward_item:
                            reward_msg = game_logic.award_item_to_player(player, items_data, target_npc_object.quest_reward_item, source=f"quest_reward_web_{target_npc_object.id}", log_event_func=log_game_event)
                            game_response["message"] += f"\n{reward_msg}"
                        if target_npc_object.quest_reward_currency > 0:
                            player.add_coins(target_npc_object.quest_reward_currency, log_event_func=log_game_event, source=f"quest_reward_web_{target_npc_object.id}")
                            game_response["message"] += f"\nYou are also rewarded with {target_npc_object.quest_reward_currency} coins."
                    else:
                        game_response["message"] += f"{target_npc_object.name} says: \"{target_npc_object.dialogue_after_quest_incomplete or target_npc_object.dialogue}\""
                # Add other NPC type interactions (hostile, vendor, standard dialogue) here, similar to process_command
                else: # Standard dialogue for now
                    game_response["message"] += f"{target_npc_object.name} says: \"{target_npc_object.dialogue}\""
            else:
                game_response["message"] = f"You can't find anyone with ID '{npc_id_to_talk_to}' here to talk to." # Changed to ID for clarity
            
            game_response["location_name"] = current_location_data.get("name", "Unknown Area")
            game_response["description"] = current_location_data.get("description", "An unfamiliar place.")
        else:
            game_response["message"] = f"The action '{action}' is not fully implemented or recognized for the browser interface yet."
            # Ensure location details are still sent for unrecognized actions
            current_loc_id_for_else = player.current_location_id
            if current_loc_id_for_else and current_loc_id_for_else in locations:
                game_response["location_name"] = locations[current_loc_id_for_else].get("name", "Unknown Area")
                game_response["description"] = locations[current_loc_id_for_else].get("description", "An unfamiliar place.")

        # --- Final response assembly ---
        # Ensure current location data is fresh for populating features and items
        current_loc_id_for_response = player.current_location_id
        current_location_data_for_response = locations.get(current_loc_id_for_response, {})

        if not game_response.get("location_name") or game_response.get("location_name") == "Unknown Area":
            game_response["location_name"] = current_location_data_for_response.get("name", "Unknown Area")
        if not game_response.get("description") or game_response.get("description") == "An unfamiliar place.":
            game_response["description"] = current_location_data_for_response.get("description", "An unfamiliar place.")

        # Populate interactable features
        game_response["interactable_features"] = [] # Start fresh
        features_in_room_for_response = current_location_data_for_response.get("features", {})
        for f_id, f_data in features_in_room_for_response.items():
            if f_id == "worn_crate":
                if f_data.get("closed") and "open" in f_data.get("actions", {}):
                    game_response["interactable_features"].append({
                        "id": f_id,
                        "name": f_id.replace("_", " ").capitalize(),
                        "action": "open"
                    })
            elif f_data.get("actions"): # For other features, iterate through all their actions
                for action_verb in f_data["actions"].keys():
                    game_response["interactable_features"].append({
                        "id": f_id,
                        "name": f_id.replace("_", " ").capitalize(),
                        "action": action_verb
                    })

        # Populate room items
        room_items_for_response = current_location_data_for_response.get("items", [])
        game_response["room_items"] = [
            {"id": item_id, "name": items_data.get(item_id, {}).get("name", item_id.replace("_", " "))}
            for item_id in room_items_for_response
        ]
        
        # Ensure it's also present if the action was a 'go' action, even if successful,
        # though it's most critical for failed 'go' actions handled earlier.
        game_response["player_current_location_id"] = player.current_location_id

        # Populate NPCs in room
        game_response["npcs_in_room"] = []
        npcs_for_response = current_location_data_for_response.get("npcs", {})
        for npc_id, npc_obj in npcs_for_response.items():
            if npc_obj.is_alive(): # Only list living NPCs
                game_response["npcs_in_room"].append({
                    "id": npc_obj.id,
                    "name": npc_obj.name
                })
        
        # Populate available exits
        game_response["available_exits"] = list(current_location_data_for_response.get("exits", {}).keys())

        # Populate current zone map data for the side panel
        game_response["current_zone_map_data"] = get_world_map_data_for_api(player.visited_locations, locations)

        # Always include player stats
        game_response["player_hp"] = player.hp
        game_response["player_max_hp"] = player.max_hp
        game_response["player_name"] = player.name
        game_response["player_coins"] = player.coins
        game_response["player_level"] = player.level
        game_response["player_xp"] = player.xp
        game_response["player_xp_to_next_level"] = player.xp_to_next_level
        game_response["player_class_name"] = classes_data.get(player.class_id, {}).get("name", "N/A")
        game_response["player_species_name"] = species_data.get(player.species_id, {}).get("name", "N/A")
        game_response["player_attack_power"] = player.attack_power
        
        # Populate equipped items names
        game_response["player_equipment"] = {}
        player_equipment_data = player.equipment
        # Ensure all defined slots (including new ones) are present in the response
        expected_slots = ["head", "shoulders", "chest", "hands", "legs", "feet", "main_hand", "off_hand", "neck", "back", "trinket1", "trinket2"]
        for slot in expected_slots:
            item_id = player_equipment_data.get(slot) # Get item_id from player's equipment dict

            # Send both the item name and the item ID for the frontend
            if item_id:
                 game_response["player_equipment"][f"{slot}_id"] = item_id # Send item ID
            if item_id and item_id in items_data:
                game_response["player_equipment"][slot] = items_data[item_id].get("name", "Unknown Item")
            else:
                game_response["player_equipment"][slot] = "Empty"

        # Determine if saving is allowed
        current_zone_for_save = current_location_data_for_response.get("zone")
        game_response["can_save_in_city"] = current_zone_for_save in CITY_ZONES

        # --- Populate map_type and city-specific details AFTER action processing ---
        game_response["map_type"] = player.current_map_type
        if player.current_map_type == "city":
            current_city_map = city_maps_data.get(player.current_city_id)
            game_response["city_map_data"] = current_city_map
            game_response["player_city_x"] = player.current_city_x
            game_response["player_city_y"] = player.current_city_y
            
            if current_city_map:
                # Only override if the action itself didn't set a more specific location_name/description
                if game_response.get("location_name") == "Unknown Area" or not game_response.get("location_name"):
                    game_response["location_name"] = current_city_map.get("name", player.current_city_id.capitalize())
                if game_response.get("description") == "An unfamiliar place." or not game_response.get("description"):
                    if 0 <= player.current_city_y < len(current_city_map.get("cells", [])) and \
                       0 <= player.current_city_x < len(current_city_map.get("cells", [])[player.current_city_y]):
                        current_cell_data = current_city_map["cells"][player.current_city_y][player.current_city_x]
                        game_response["description"] = current_cell_data.get("description", "An unremarkable part of the city.")
                        # Check if the current cell is a city exit gate
                        cell_action_details = current_cell_data.get("action")
                        if isinstance(cell_action_details, dict) and cell_action_details.get("type") == "exit_to_zone_map":
                            if "exit city" not in game_response.get("available_actions", []):
                                game_response.setdefault("available_actions", []).append("exit city")
                    else:
                        game_response["description"] = "You are at an unknown spot in the city." # Fallback
            
            # Determine available_exits (directions) for city map
            game_response["available_exits"] = [] # Reset for city context
            if current_city_map:
                px, py = player.current_city_x, player.current_city_y
                grid_width = current_city_map["grid_size"]["width"]
                grid_height = current_city_map["grid_size"]["height"]
                # This list should be consistent with the one in the 'go' action for city movement
                impassable_types_for_buttons = ["wall_city_edge", "building_house_large", "building_house_small", 
                                                "building_library_facade", "square_fountain"] # Keep this updated

                # Check North
                if py - 1 >= 0 and not (current_city_map["cells"][py - 1][px].get("impassable") or current_city_map["cells"][py - 1][px].get("type") in impassable_types_for_buttons):
                    game_response["available_exits"].append("north")
                # Check South
                if py + 1 < grid_height and not (current_city_map["cells"][py + 1][px].get("impassable") or current_city_map["cells"][py + 1][px].get("type") in impassable_types_for_buttons):
                    game_response["available_exits"].append("south")
                # Check East
                if px + 1 < grid_width and not (current_city_map["cells"][py][px + 1].get("impassable") or current_city_map["cells"][py][px + 1].get("type") in impassable_types_for_buttons):
                    game_response["available_exits"].append("east")
                # Check West
                if px - 1 >= 0 and not (current_city_map["cells"][py][px - 1].get("impassable") or current_city_map["cells"][py][px - 1].get("type") in impassable_types_for_buttons):
                    game_response["available_exits"].append("west")
        
        # Ensure current_zone_map_data is always populated for the side panel (it was already here, just confirming its placement is fine)
        # game_response["current_zone_map_data"] = get_world_map_data_for_api(player.visited_locations, locations) # This is already populated earlier
        else: # map_type is "zone" or other
            # Populate available_exits from zone map location data (this was done earlier, ensure it's not overwritten if not city)
            if not game_response.get("available_exits"): # If not already set by city logic
                 game_response["available_exits"] = list(current_location_data_for_response.get("exits", {}).keys())
            
            # General check for city entrance based on data
            is_general_city_entrance = current_location_data_for_response.get("city_map_transitions", {}).get("enter")
            
            print(f"\n[PREREQ_LOG] ----- Final Assembly Check -----")
            print(f"[PREREQ_LOG] Current Loc ID for Final Assembly: {player.current_location_id}")
            print(f"[PREREQ_LOG] Location '{player.current_location_id}' has 'city_map_transitions.enter' (general check): {bool(is_general_city_entrance)}")

            if is_general_city_entrance:
                if "enter city" not in game_response.get("available_actions", []):
                    game_response.setdefault("available_actions", []).append("enter city")
                    print(f"[PREREQ_LOG] 'enter city' ADDED by Final Assembly (general check) for {player.current_location_id}.")
            
            # TEST PURPOSE: Ensure "enter city" is visible for eldoria_city_node "no matter what"
            is_eldoria_node_test_case = player.current_location_id == "eldoria_city_node"
            print(f"[PREREQ_LOG] Is current location 'eldoria_city_node' (test case): {is_eldoria_node_test_case}")
            
            if player.current_location_id == "eldoria_city_node":
                if "enter city" not in game_response.get("available_actions", []):
                    game_response.setdefault("available_actions", []).append("enter city")
                    print(f"[PREREQ_LOG] 'enter city' ADDED by Final Assembly (eldoria_city_node specific test) for {player.current_location_id}.")
            
            if not is_general_city_entrance and not is_eldoria_node_test_case:
                 print(f"[PREREQ_LOG] 'enter city' NOT added by Final Assembly for {player.current_location_id} (conditions not met).")
            
            print(f"[PREREQ_LOG] Final available_actions before sending: {game_response.get('available_actions')}")
            print(f"[PREREQ_LOG] ----------------------------------\n")



        return jsonify(game_response)

    @flask_app_instance.route('/get_species', methods=['GET'])
    def get_species_route():
        species_list = []
        for s_id, data in species_data.items():
            species_list.append({"id": s_id, "name": data["name"], "description": data["description"]})
        return jsonify(species_list)

    @flask_app_instance.route('/get_classes', methods=['GET'])
    def get_classes_route():
        class_list = []
        for c_id, data in classes_data.items():
            class_list.append({"id": c_id, "name": data["name"], "description": data["description"]})
        return jsonify(class_list)

    @flask_app_instance.route('/api/delete_character', methods=['POST'])
    def delete_character_route():
        data = request.get_json()
        character_name = data.get('character_name')
        if not character_name:
            return jsonify({"error": "Character name not provided."}), 400
        if delete_character_data(character_name):
            return jsonify({"message": f"Character '{character_name}' deleted successfully."})
        return jsonify({"error": f"Failed to delete character '{character_name}'."}), 500

    @flask_app_instance.route('/api/get_characters', methods=['GET'])
    def get_characters_route():
        characters = list_existing_characters()
        return jsonify(characters)

    @flask_app_instance.route('/api/create_character', methods=['POST'])
    def create_character_web_route():
        data = request.get_json()
        species_id = data.get('species_id')
        class_id = data.get('class_id')
        player_name = data.get('player_name')
        player_gender = data.get('player_gender')

        if not all([species_id, class_id, player_name, player_gender]):
            # print(f"DEBUG: Missing data in /api/create_character: {data}") # Keep for debugging if needed
            return jsonify({"error": "Missing character creation data."}), 400

        if game_logic.apply_character_choices_and_stats(player, species_id, class_id, player_name, player_gender, items_data, species_data, classes_data, save_player_data):
            # player.game_active is set by apply_character_choices_and_stats
            species_info = species_data[player.species_id]
            
            start_room_id = "generic_start_room" 
            player.current_location_id = start_room_id
            class_info_for_items = classes_data[player.class_id]
            if start_room_id in locations and "worn_crate" in locations[start_room_id].get("features", {}):
                crate_contents_web = list(class_info_for_items["starter_items"])
                crate_contents_web.append("blank_map_scroll") # Add map scroll to the crate
                locations[start_room_id]["features"]["worn_crate"]["contains_on_open"] = crate_contents_web
                locations[start_room_id]["features"]["worn_crate"]["closed"] = True
            
            # Prepare initial scene data for the response
            initial_scene_data = {
                "message": f"{species_info['backstory_intro']}\nYou feel a pull towards the {locations[start_room_id]['name']}.", # Ensure player.name is set before this
                "player_hp": player.hp,
                "player_name": player.name,
                "player_max_hp": player.max_hp,
                "location_name": locations.get(player.current_location_id, {}).get("name"),
                "description": locations.get(player.current_location_id, {}).get("description"),
                "player_coins": player.coins,
                "player_level": player.level,
                "player_xp": player.xp,
                "player_xp_to_next_level": player.xp_to_next_level,
                "player_class_name": classes_data.get(player.class_id, {}).get("name", "N/A"),
                "player_species_name": species_data.get(player.species_id, {}).get("name", "N/A"),
                "player_attack_power": player.attack_power,
                "player_equipment": {
                    "head": "Empty", "shoulders": "Empty", "chest": "Empty", "hands": "Empty",
                    "legs": "Empty", "feet": "Empty", "main_hand": "Empty", "off_hand": "Empty",
                    "neck": "Empty", "back": "Empty", "trinket1": "Empty", "trinket2": "Empty"
                },
                "interactable_features": [], # Will be populated by final assembly logic
                "room_items": [], # Will be populated by final assembly logic
                "npcs_in_room": [], # Will be populated
                "current_zone_map_data": None # Initialize
            }
            # Manually populate features and items for the very first response after creation
            current_loc_data = locations.get(start_room_id, {})
            features_in_room = current_loc_data.get("features", {})
            for f_id, f_data in features_in_room.items():
                primary_action = None
                if f_id == "worn_crate" and f_data.get("closed"):
                    primary_action = "open"
                elif f_data.get("actions"):
                    primary_action = list(f_data["actions"].keys())[0]
                if primary_action:
                    initial_scene_data["interactable_features"].append({"id": f_id, "name": f_id.replace("_", " ").capitalize(), "action": primary_action})
            
            # Populate equipped items for initial scene
            player_equipment_data_init = player.equipment
            expected_slots_init = ["head", "shoulders", "chest", "hands", "legs", "feet", "main_hand", "off_hand", "neck", "back", "trinket1", "trinket2"]
            for slot in expected_slots_init:
                item_id = player_equipment_data_init.get(slot) # Get item_id from player's equipment dict

                # Send both the item name and the item ID for the frontend
                if item_id:
                     initial_scene_data["player_equipment"][f"{slot}_id"] = item_id # Send item ID
                if item_id and item_id in items_data:
                    initial_scene_data["player_equipment"][slot] = items_data[item_id].get("name", "Unknown Item")

            # Items in the room (should be empty at start, items are in crate)
            # initial_scene_data["room_items"] = [...] 
            
            # NPCs in the room for initial scene
            initial_npcs_in_room = current_loc_data.get("npcs", {})
            for npc_id, npc_obj in initial_npcs_in_room.items():
                if npc_obj.is_alive():
                    initial_scene_data["npcs_in_room"].append({
                        "id": npc_obj.id, "name": npc_obj.name
                    })
            # Add zone map data for initial scene
            initial_scene_data["current_zone_map_data"] = get_world_map_data_for_api(player.visited_locations, locations)

            return jsonify(initial_scene_data)
        else:
            # print(f"DEBUG: apply_character_choices_and_stats failed for web creation: {data}")
            return jsonify({"error": "Failed to create character on server."}), 500

    @flask_app_instance.route('/api/load_character', methods=['POST'])
    def load_character_web_route():
        data = request.get_json()
        character_name = data.get('character_name')
        if not character_name:
            return jsonify({"error": "Character name not provided."}), 400
        
        if load_character_data(character_name):
            # Character data is now in global 'player'
            current_loc_id = player.current_location_id
            current_loc_data = locations.get(current_loc_id, {})
            
            loaded_scene_data = {
                "message": f"Welcome back, {player.name}!",
                "player_hp": player.hp,
                "player_name": player.name,
                "player_max_hp": player.max_hp,
                "location_name": current_loc_data.get("name"),
                "description": current_loc_data.get("description"),
                "player_coins": player.coins,
                "player_level": player.level,
                "player_xp": player.xp,
                "player_xp_to_next_level": player.xp_to_next_level,
                "player_class_name": classes_data.get(player.class_id, {}).get("name", "N/A"),
                "player_species_name": species_data.get(player.species_id, {}).get("name", "N/A"),
                "player_attack_power": player.attack_power,
                "player_equipment": {
                    "head": "Empty", "shoulders": "Empty", "chest": "Empty", "hands": "Empty",
                    "legs": "Empty", "feet": "Empty", "main_hand": "Empty", "off_hand": "Empty",
                    "neck": "Empty", "back": "Empty", "trinket1": "Empty", "trinket2": "Empty"
                },
                "interactable_features": [],
                "room_items": [],
                "npcs_in_room": [],
                "current_zone_map_data": None # Initialize
            }

            features_in_room = current_loc_data.get("features", {})
            for f_id, f_data in features_in_room.items():
                primary_action = None
                if f_id == "worn_crate" and f_data.get("closed"):
                    primary_action = "open"
                elif f_data.get("actions"):
                    primary_action = list(f_data["actions"].keys())[0]
                if primary_action:
                    loaded_scene_data["interactable_features"].append({"id": f_id, "name": f_id.replace("_", " ").capitalize(), "action": primary_action})

            room_items_list = current_loc_data.get("items", [])
            loaded_scene_data["room_items"] = [
                {"id": item_id, "name": items_data.get(item_id, {}).get("name", item_id.replace("_", " "))}
                for item_id in room_items_list
            ]
            # NPCs in room for loaded scene
            loaded_npcs_in_room = current_loc_data.get("npcs", {})
            for npc_id, npc_obj in loaded_npcs_in_room.items():
                if npc_obj.is_alive():
                    loaded_scene_data["npcs_in_room"].append({
                        "id": npc_obj.id, "name": npc_obj.name
                    })
            # Add zone map data for loaded scene
            loaded_scene_data["current_zone_map_data"] = get_world_map_data_for_api(player.visited_locations, locations)
            # Populate equipped items for loaded scene
            player_equipment_data_load = player.equipment
            expected_slots_load = ["head", "shoulders", "chest", "hands", "legs", "feet", "main_hand", "off_hand", "neck", "back", "trinket1", "trinket2"]
            for slot in expected_slots_load:
                item_id = player_equipment_data_load.get(slot) # Get item_id from player's equipment dict

                # Send both the item name and the item ID for the frontend
                if item_id:
                     loaded_scene_data["player_equipment"][f"{slot}_id"] = item_id # Send item ID
                if item_id and item_id in items_data:
                    loaded_scene_data["player_equipment"][slot] = items_data[item_id].get("name", "Unknown Item")
            return jsonify(loaded_scene_data)
        return jsonify({"error": f"Failed to load character '{character_name}'."}), 404

    @flask_app_instance.route('/api/resume_session', methods=['POST'])
    def resume_session_route():
        data = request.get_json()
        character_name_from_client = data.get('character_name')

        # Check if server's current player matches the client's expected character
        if player.game_active and player.name == character_name_from_client:
            # Server state is consistent with client's session, return current state
            current_loc_id = player.current_location_id
            current_loc_data = locations.get(current_loc_id, {})
            
            scene_data = {
                "message": f"Session continued for {player.name}.",
                "player_hp": player.hp,
                "player_name": player.name,
                "player_max_hp": player.max_hp,
                "location_name": current_loc_data.get("name"),
                "description": current_loc_data.get("description"),
                "player_coins": player.coins,
                "player_level": player.level,
                "player_xp": player.xp,
                "player_xp_to_next_level": player.xp_to_next_level,
                "player_class_name": classes_data.get(player.class_id, {}).get("name", "N/A"),
                "player_species_name": species_data.get(player.species_id, {}).get("name", "N/A"),
                "player_attack_power": player.attack_power,
                "player_equipment": {
                    "head": "Empty", "shoulders": "Empty", "chest": "Empty", "hands": "Empty",
                    "legs": "Empty", "feet": "Empty", "main_hand": "Empty", "off_hand": "Empty",
                    "neck": "Empty", "back": "Empty", "trinket1": "Empty", "trinket2": "Empty"
                },
                "interactable_features": [], # Populate these like in process_game_action
                "room_items": [],
                "npcs_in_room": [],
                "current_zone_map_data": None # Initialize
            }
            # Populate features and items (similar to process_game_action_route's final assembly)
            features_in_room = current_loc_data.get("features", {})
            for f_id, f_data in features_in_room.items():
                # Simplified: send all actions. Refine if needed.
                for action_verb in f_data.get("actions", {}).keys():
                     scene_data["interactable_features"].append({"id": f_id, "name": f_id.replace("_", " ").capitalize(), "action": action_verb})
            
            room_items_list = current_loc_data.get("items", [])
            scene_data["room_items"] = [
                {"id": item_id, "name": items_data.get(item_id, {}).get("name", item_id.replace("_", " "))}
                for item_id in room_items_list ]
            
            # NPCs in room for resumed scene
            resumed_npcs_in_room = current_loc_data.get("npcs", {})
            for npc_id, npc_obj in resumed_npcs_in_room.items():
                if npc_obj.is_alive():
                    scene_data["npcs_in_room"].append({
                        "id": npc_obj.id, "name": npc_obj.name
                    })
            # Add zone map data for resumed scene
            scene_data["current_zone_map_data"] = get_world_map_data_for_api(player.visited_locations, locations)
            
            # Populate equipped items for resumed scene
            player_equipment_data_resume = player.equipment
            expected_slots_resume = ["head", "shoulders", "chest", "hands", "legs", "feet", "main_hand", "off_hand", "neck", "back", "trinket1", "trinket2"]
            for slot in expected_slots_resume:
                item_id = player_equipment_data_resume.get(slot) # Get item_id from player's equipment dict
                # Send both the item name and the item ID for the frontend
                if item_id:
                     scene_data["player_equipment"][f"{slot}_id"] = item_id # Send item ID
                if item_id and item_id in items_data:
                    scene_data["player_equipment"][slot] = items_data[item_id].get("name", "Unknown Item")
            return jsonify(scene_data)
        return jsonify({"error": "Server state mismatch or no active game for this character. Please load character again."}), 400

    @flask_app_instance.route('/api/save_game_state', methods=['POST'])
    def save_game_state_route():
        if not player.game_active or not player.name:
            return jsonify({"message": "Cannot save: No active character or game not started."}), 400

        current_loc_id = player.current_location_id
        current_zone = locations.get(current_loc_id, {}).get("zone")
        if current_zone not in CITY_ZONES:
            return jsonify({"message": "Cannot save here. You must be in a city."}), 403

        if save_player_data(player, reason_for_save="Game progress saved via web interface"): # Pass player object
            return jsonify({"message": f"Game saved successfully for {player.name}."})
        return jsonify({"message": "Failed to save game on server."}), 500

    @flask_app_instance.route('/test')
    def test_route():
        print("Test route accessed!")
        return "This is the test route. If you see this, routing is partially working."

def launch_web_interface():
    global web_server_thread
    if not flask_available:
        print("\nFlask library not found. Cannot start browser interface.")
        print("Please install Flask to use this feature (e.g., 'pip install Flask').")
        return

    if not flask_app_instance:
        print("[ERROR] Flask app instance is not available. Cannot start web server.")
        return

    if web_server_thread and web_server_thread.is_alive():
        print("Web server is already running or was attempted.")
    else:
        print("Attempting to launch web interface server...")
        web_server_thread = threading.Thread(target=run_minimal_web_server, daemon=True)
        web_server_thread.start()

    time.sleep(1.5) 

    try:
        print("Opening browser to http://127.0.0.1:5000/ ...")
        webbrowser.open_new_tab('http://127.0.0.1:5000/')
        print("If the browser did not open, please navigate to http://127.0.0.1:5000/ manually.")
    except Exception as e:
        print(f"Could not open web browser: {e}")
        print("Please navigate to http://127.0.0.1:5000/ manually.")

    print("\nNote: The browser version is under active development.")
    print("The text-based game continues in this terminal.")
    print("To stop the web server, quit this terminal application (which will stop the daemon thread).")

def show_current_scene():
    if not player.game_active:
        print("\nWelcome to the Text RPG Adventure!")
        print("Type '!start' to begin your journey or '!quit' to exit.")
        print("\nAvailable commands:")
        print("  !start         - Begin the adventure.")
        print("  !quit          - Exit the game.")
        return

    if player.dialogue_npc_id and player.dialogue_options_pending:
        npc_id = player.dialogue_npc_id
        npc_object = locations[player.current_location_id]["npcs"][npc_id] # Get NPC object
        print(f"\n--- Talking to {npc_object.name} ---")
        print("Choose an option:")
        for key, option_data in player.dialogue_options_pending.items():
            print(f"  {key}. {option_data['text']}")
        print("\n(Type the number of your choice, or 'leave' to end conversation)")
        return

    if player.current_map_type == "city":
        city_id = player.current_city_id
        city_map = city_maps_data.get(city_id)
        if not city_map:
            print(f"[ERROR] City map data for '{city_id}' not found. Returning to zone map.")
            player.current_map_type = "zone"
            # player.current_location_id should still be set to the city's zone map node
            # Fall through to zone map display
        else:
            px, py = player.current_city_x, player.current_city_y
            cell_data = city_map["cells"][py][px]
            city_name = city_map.get("name", city_id.capitalize())
            
            print(f"\n--- {city_name} ({cell_data.get('name', cell_data.get('type', 'Unknown Area'))}) (HP: {player.hp}/{player.max_hp}) ---")
            print(f"    Location: ({px},{py})")
            print(cell_data.get("description", "You see an unremarkable part of the city."))

            # TODO: Display NPCs at this cell, items, features, available city exits/actions
            print("\nCity Commands:")
            print("  look           - Describe your current spot in the city.")
            print("  go <direction> - Attempt to move within the city.")
            print("  exit city      - Leave the city and return to the zone map.") # Add exit command
            # Add other city-specific commands like "enter <building>", "exit city" (if on a gate)
            return # End here for city view

    # --- Zone Map Display (existing logic) ---
    if player.combat_target_id:
        npc_id = player.combat_target_id
        if npc_id not in locations[player.current_location_id]["npcs"]:
            print(f"[Error] Combat target {npc_id} not found. Ending combat.")
            player.combat_target_id = None
        else:
            npc_object = locations[player.current_location_id]["npcs"][npc_id] # Get NPC object
            print("\n--- IN COMBAT ---")
            print(f"Your HP: {player.hp}/{player.max_hp}")
            print(f"Enemy: {npc_object.name} | HP: {npc_object.hp}/{npc_object.max_hp}")
            print(HOSTILE_MOB_VISUAL)
            
            print("\nCombat Commands:")
            print("  attack                  - Perform a basic attack.")
            for move_id, move_data in player.special_moves.items():
                cooldown_status = f"(Ready)" if player.special_cooldowns.get(move_id, 0) == 0 else f"(Cooldown: {player.special_cooldowns.get(move_id, 0)})"
                print(f"  special {move_id.replace('_',' ')}   - {move_data['description']} {cooldown_status}")
            print("  deflect                 - Reduce damage from the next attack.")
            print("  item <item_name>        - Use an item from your inventory.")
            return 

    loc_id = player.current_location_id
    if loc_id not in locations:
        print(f"\n[ERROR] Current location '{loc_id}' not found. Resetting.")
        player.current_location_id = "generic_start_room" # Default to start room if error
        loc_id = player.current_location_id
    
    location_data = locations[loc_id]
    print(f"\n--- {location_data['name']} (HP: {player.hp}/{player.max_hp}) ---")
    if player.species_id and player.class_id:
        player_name_display = player.name if player.name else "Adventurer"
        species_name = species_data.get(player.species_id, {}).get('name', 'Unknown Species')
        class_name = classes_data.get(player.class_id, {}).get('name', 'Unknown Class')
        gender_display = player.gender if player.gender else 'Unspecified'
        print(f"    ({player_name_display} - {gender_display} {species_name} {class_name})")

    print(location_data["description"])
    if loc_id == "generic_start_room" and not player.flags.get("found_starter_items"):
        print("The air is thick with anticipation. You feel compelled to check the worn crate.")


    room_npcs = location_data.get("npcs", {})
    hostiles_present_desc = False
    for npc_id, npc_object in room_npcs.items(): # Iterate through NPC objects
        if npc_object.hostile and player.combat_target_id != npc_id :
            if not hostiles_present_desc:
                print("\nDanger!")
                hostiles_present_desc = True
            print(f"A menacing {npc_object.name} is here!")

    if "features" in location_data and location_data["features"]:
        print("\nYou notice:")
        for feature_name, feature_data in location_data["features"].items():
            base_desc = feature_data.get('description', 'It looks interesting.')
            if feature_name == "chest": 
                desc = feature_data.get('description_locked' if feature_data.get('locked') else 'description_unlocked', base_desc)
            elif feature_name == "worn_crate": # Specific description for starter crate
                 desc = feature_data.get('description_closed' if feature_data.get('closed') else 'description_opened', base_desc)
            else:
                desc = base_desc
            print(f"  - {feature_name.replace('_', ' ').capitalize()}: {desc}")
            if feature_data.get("actions"):
                print(f"    (Actions: {', '.join(feature_data['actions'].keys())})")

    if room_npcs:
        print("\nPeople here:")
        for npc_id, npc_object in room_npcs.items(): # Iterate through NPC objects
            if not npc_object.hostile or (npc_object.hostile and player.combat_target_id != npc_id):
                 print(f"  - {npc_object.name} ({npc_object.description or 'An interesting individual.'})")
    
    room_items = location_data.get("items", [])
    if room_items:
        print("\nItems here: " + ", ".join([items_data.get(item, {}).get('name', item.replace("_", " ")) for item in room_items]))
    else:
        print("\nYou see no loose items here.")

    print("\nAvailable commands:")
    print("  !quit          - Exit the game.")
    print("  !start_browser - Open conceptual browser interface.")
    print("  !map           - Show a map of the current area.")
    print("  look           - Describe your surroundings and actions again.")
    current_zone = location_data.get("zone")
    if current_zone in CITY_ZONES:
        print("  !save          - Save your progress.")

    print("  go <direction>")
    if location_data.get("exits"):
        print(f"    (Available exits: {', '.join(location_data['exits'].keys())})")
    if room_items: print(f"  take <item>")

    # Add 'enter city' command if the current location is a city node with a defined transition
    if "city_map_transitions" in location_data and "enter" in location_data["city_map_transitions"]:
        city_id_to_enter = location_data["city_map_transitions"]["enter"].get("city_id", "the city")
        print(f"  enter city     - Enter the detailed map for {city_id_to_enter.capitalize()}.")
    
    inv_status = "(empty)" if not player.inventory else f"({len(player.inventory)} item(s))"
    print(f"  inventory (i)  - Check your inventory {inv_status}.")

    if "features" in location_data:
        for fname, fdata in location_data["features"].items():
            if fname == "chest" and fdata.get("locked") and fdata.get("key_needed"):
                print(f"  use <item> on {fname}")
                break 
            elif fname == "worn_crate" and fdata.get("closed"): # Suggest opening the crate
                print(f"  open worn crate") # Or search, depending on defined actions
                break
    
    if any(not npc_obj.hostile or (npc_obj.hostile and player.combat_target_id != npc_id) for npc_id, npc_obj in room_npcs.items()):
        available_to_talk = [npc_obj.name for npc_id, npc_obj in room_npcs.items() if not npc_obj.hostile or (npc_obj.hostile and player.combat_target_id != npc_id)]
        if available_to_talk:
            print(f"  talk <npc_name>")
            if len(available_to_talk) <= 3:
                print(f"    (You can talk to: {', '.join(available_to_talk)})")
            else:
                print(f"    (Several people are here to talk to.)")

    for feature_name, feature_data in location_data.get("features", {}).items():
        if feature_data.get("actions") and not (feature_name == "worn_crate" and feature_data.get("closed")): # Don't suggest generic action if specific "open" is suggested
            first_action = list(feature_data["actions"].keys())[0]
            print(f"  {first_action} {feature_name.replace('_', ' ')}")
    print(f"  worldmap       - View the world map.")


def display_world_map():
    """Displays the world map, showing visited locations."""
    print("\n--- World Map ---")
    
    # Group locations by zone
    locations_by_zone = {}
    for loc_id, loc_data in locations.items():
        zone = loc_data.get("zone", "Uncharted Territories")
        if zone not in locations_by_zone:
            locations_by_zone[zone] = []
        locations_by_zone[zone].append((loc_id, loc_data.get("name", loc_id)))

    sorted_zones = sorted(locations_by_zone.keys())

    for zone in sorted_zones:
        print(f"\n  [{zone}]")
        if not locations_by_zone[zone]:
            print("    (No locations mapped in this zone)")
            continue
        for loc_id, loc_name in sorted(locations_by_zone[zone], key=lambda x: x[1]): # Sort locations by name
            if loc_id in player.visited_locations:
                print(f"    - {loc_name} (Visited)")
            else:
                print(f"    - ??? (Unvisited)") # Or just loc_name if you want to show all names
    print("\n-----------------")

# Ensure this route is also defined only if flask_app_instance exists
if flask_app_instance:
    @flask_app_instance.route('/api/get_world_map', methods=['GET'])
    def get_world_map_route(): # Renamed the function to avoid conflict with the helper
        if not player.game_active: # Ensure game is active and player object exists
            return jsonify({"error": "Game not active or player not loaded."}), 400
        
        world_map_structured_data = get_world_map_data_for_api(player.visited_locations, locations)
        return jsonify(world_map_structured_data)

def get_world_map_data_for_api(player_visited_locations, all_locations_data):
    """
    Prepares world map data structured for API response.
    Returns a list of zones, each containing a list of location info.
    """
    # Send a flat list of ALL locations with coordinates, visited status, and current location
    # Determine player's current zone
    current_zone_name = "Unknown Zone"
    if player and player.game_active and player.current_location_id in all_locations_data:
        current_zone_name = all_locations_data[player.current_location_id].get("zone", "Uncharted Territories")

    map_locations = []
    for loc_id, loc_data in all_locations_data.items():
        if "map_x" in loc_data and "map_y" in loc_data: # Include ALL locations with map coordinates
            map_locations.append({
                "id": loc_id,
                "name": loc_data.get("name", loc_id),
                "x": loc_data["map_x"],
                "y": loc_data["map_y"],
                "visited": loc_id in player_visited_locations,
                "exits": loc_data.get("exits", {})
            })
    
    return {
        "zone_name": current_zone_name,
        "locations": map_locations,
        "current_location_id": player.current_location_id if player and player.game_active else None
    }


def draw_zone_map(current_loc_id, all_locs_data): # Ensure all_locs_data is used
    """
    Draws a textual map of the current zone in the terminal.
    Includes visited locations, the current location, and unvisited but known locations.
    Also lists available exits.
    """
    if not current_loc_id:
        print("Current location unknown, cannot draw map.")
        return
    current_location_data = all_locs_data.get(current_loc_id, {})
    current_zone_name = current_location_data.get("zone")

    if not current_zone_name:
        print("This area is uncharted (no zone data).")
        return
    
    # Attempt to use predefined layout from zone_layouts.json
    if current_zone_name in zone_layouts:
        layout = zone_layouts[current_zone_name]
        print(f"\n--- {layout.get('title', f'Map of {current_zone_name}')} ---")
        
        # Create a mutable copy of the grid for placing the player marker
        display_grid = [list(row_str) for row_str in layout["grid"]]
        
        # Find the player's character in the mapping and replace it on the grid
        # This assumes the mapping characters are unique on the grid where they represent locations
        for r_idx, row_list in enumerate(display_grid):
            for c_idx, char_in_grid in enumerate(row_list):
                if char_in_grid in layout["mapping"]:
                    mapped_loc_id = layout["mapping"][char_in_grid]
                    if mapped_loc_id == current_loc_id:
                        # Check if the character is enclosed in brackets like [S]
                        # If so, replace the character inside the brackets
                        if c_idx > 0 and c_idx < len(row_list) - 1 and \
                           display_grid[r_idx][c_idx-1] == '[' and \
                           display_grid[r_idx][c_idx+1] == ']':
                            display_grid[r_idx][c_idx] = '@'
                        # else: # If not bracketed, replace the char itself (less common for these layouts)
                        #     display_grid[r_idx][c_idx] = '@' 
                            
        for row_list in display_grid:
            print("".join(row_list))
        
        print("\nLegend: @ - You are here. Other symbols represent locations as per map.")

    else: # Fallback to dynamic grid generation if no predefined layout
        print(f"\n--- Dynamically Generated Map of {current_zone_name} ---")
        zone_locations = []
        min_x, max_x, min_y, max_y = float('inf'), float('-inf'), float('inf'), float('-inf')

        for loc_id, loc_data in all_locs_data.items():
            if loc_data.get("zone") == current_zone_name and "map_x" in loc_data and "map_y" in loc_data:
                x, y = loc_data["map_x"], loc_data["map_y"]
                zone_locations.append({
                    "id": loc_id, "name": loc_data.get("name", loc_id),
                    "x": x, "y": y,
                    "visited": loc_id in player.visited_locations
                })
                min_x, max_x = min(min_x, x), max(max_x, x)
                min_y, max_y = min(min_y, y), max(max_y, y)

        if not zone_locations:
            print(f"No locations with map coordinates found in zone: {current_zone_name}")
            # Exits will still be printed below
        else:
            grid_width = max_x - min_x + 1
            grid_height = max_y - min_y + 1
            grid = [['.' for _ in range(grid_width)] for _ in range(grid_height)]

            for loc in zone_locations:
                grid_x, grid_y = loc["x"] - min_x, loc["y"] - min_y
                if loc["id"] == current_loc_id: grid[grid_y][grid_x] = '@'
                elif loc["visited"]: grid[grid_y][grid_x] = 'V'
                else: grid[grid_y][grid_x] = '?'
            
            for row in grid: print(" ".join(row))
            print("\nLegend: @ Current, V Visited, ? Known, . Empty")

    # Display available exits from the current location
    current_exits = current_location_data.get("exits")
    if current_exits:
        print("\nAvailable Exits:")
        for direction, dest_id in current_exits.items():
            # Optional: print destination name if desired
            # dest_name = all_locs_data.get(dest_id, {}).get('name', 'an unknown area')
            # print(f"  - Go {direction.capitalize()} (to {dest_name})")
            print(f"  - Go {direction.capitalize()}")

    else:
        print("\nNo obvious exits from here.")



def process_command(full_command_input):
    full_command = full_command_input.lower().strip()
    parts = full_command.split()
    if not parts: return True
    command = parts[0]
    args = parts[1:]

    if command == "!start":
        if player.game_active: print("The game has already started!")
        else:
            initialize_game_state() 
        return True
    elif command == "!start_browser": 
        launch_web_interface()
        return True
    elif command == "!save":
        if not player.game_active:
            print("Game not active. Cannot save.")
            return True # Command processed, show scene again
        current_zone = locations[player.current_location_id].get("zone")
        if current_zone in CITY_ZONES:
            save_player_data(player, reason_for_save="Game progress manually saved")
        else:
            print("You can only save your progress in a city.")
        return True # Command processed, show scene again
    elif command == "!reload_data":
        print("Attempting to reload game data...")
        load_all_game_data()
        return True # Show scene again to reflect any changes
    elif command == "!quit": 
        print(f"\nYou decide to end your adventure here. Farewell!" if player.game_active else "\nFarewell!")
        return False
    elif command == "worldmap":
        display_world_map()
        return True
    
    if not player.game_active:
        print(f"Unknown command: '{full_command}'. Type '!start' to begin.")
        return True

    if player.dialogue_npc_id and player.dialogue_options_pending:
        npc_id = player.dialogue_npc_id
        npc_object = locations[player.current_location_id]["npcs"][npc_id] # Get NPC object
        
        if full_command == "leave":
            print(f"You end the conversation with {npc_object.name}.")
            player.end_dialogue() # Player object's method
            return True

        chosen_option_data = player.dialogue_options_pending.get(full_command)
        if chosen_option_data:
            print(f"\n> {chosen_option_data['text']}") 
            if chosen_option_data.get("response"):
                print(f"{npc_object.name} says: \"{chosen_option_data['response']}\"")
            
            if chosen_option_data.get("triggers_combat"):
                player.end_dialogue() # End dialogue before starting combat
                player.enter_combat(npc_id) # Player object's method
            elif chosen_option_data.get("action_type") == "end_conversation":
                player.end_dialogue() # Player object's method
        else:
            print("Invalid choice. Please type the number of the option or 'leave'.")
        return True 

    if player.combat_target_id:
        npc_id = player.combat_target_id
        if npc_id not in locations[player.current_location_id]["npcs"]:
            print(f"[Warning] Target {npc_id} seems to be gone. Ending combat.")
            player.leave_combat() # Player object's method
            return True 

        npc_object = locations[player.current_location_id]["npcs"][npc_id] # Get NPC object
        action_taken = False

        if command == "attack":
            damage = player.attack_power
            npc_object.take_damage(damage) # Use NPC method
            print(f"You attack {npc_object.name} for {damage} damage.")
            if not npc_object.is_alive(): # Use NPC method
                handle_npc_defeat(npc_id)
            action_taken = True
        elif command == "special":
            if not args: print("Which special move? (Specify the move like 'special power strike')")
            else:
                move_input = "_".join(args) 
                if move_input in player.special_moves:
                    if player.special_cooldowns.get(move_input, 0) == 0:
                        move_details = player.special_moves[move_input]
                        damage = int(player.attack_power * move_details["damage_multiplier"])
                        npc_object.take_damage(damage) # Use NPC method
                        print(f"You use {move_details['name']} on {npc_object.name} for {damage} damage!")
                        player.special_cooldowns[move_input] = move_details["cooldown_max"]
                        if not npc_object.is_alive(): # Use NPC method
                            handle_npc_defeat(npc_id)
                        action_taken = True
                    else:
                        print(f"{player.special_moves[move_input]['name']} is on cooldown ({player.special_cooldowns[move_input]} turns left).")
                else:
                    print(f"You don't know a special move called '{' '.join(args)}'.")
        elif command == "deflect":
            player.set_deflecting(True) # Player object's method
            print("You brace yourself, preparing to deflect the next attack.")
            action_taken = True
        elif command == "item":
            if not args: print("Use which item?")
            else:
                item_name_input = " ".join(args)
                item_id_to_use = None
                for inv_item_id in player.inventory:
                    if item_name_input == items_data.get(inv_item_id, {}).get("name", "").lower() or \
                       item_name_input == inv_item_id.replace("_", " "):
                        item_id_to_use = inv_item_id
                        break
                
                if item_id_to_use:
                    item_detail = items_data.get(item_id_to_use)
                    if item_detail and item_detail["type"] == "consumable" and item_detail["effect"] == "heal":
                        heal_amount = item_detail["amount"]
                        player.heal(heal_amount) # Use method
                        player.remove_item_from_inventory(item_id_to_use) # Use method
                        print(f"You use the {item_detail['name']} and restore {heal_amount} HP. You now have {player.hp}/{player.max_hp} HP.")
                        action_taken = True 
                    else:
                        print(f"You can't use the {item_name_input} in that way right now.")
                else:
                    print(f"You don't have a '{item_name_input}'.")
        else:
            print(f"Unknown combat command: '{command}'. Valid commands: attack, special, deflect, item.")
        
        # After player action in combat, check if combat should continue (NPC still alive)
        if action_taken and player.combat_target_id and player.game_active:
            npc_combat_turn()
        return True 

    # --- New Unequip Command Handler (Terminal) ---
    # This is a basic terminal handler. The web handler is separate.
    elif command == "unequip":
        if not args: print("Unequip what? (Specify the item name)")
        else:
            item_name_input = " ".join(args)
            # Find the item in equipped slots
            item_id_to_unequip = None
            slot_unequipped_from = None
            for slot, item_id in player.equipment.items():
                if item_id and (item_name_input == items_data.get(item_id, {}).get("name", "").lower() or item_name_input == item_id.replace("_", " ")):
                    item_id_to_unequip = item_id
                    slot_unequipped_from = slot
                    break
            if item_id_to_unequip:
                unequip_message = player.unequip_item(slot_unequipped_from, items_data, log_event_func=log_game_event)
                print(unequip_message)
            else:
                print(f"You don't have '{item_name_input}' equipped.")
        return True # Command processed, show scene again
    # --- End Unequip Command Handler (Terminal) ---

        if action_taken and player.combat_target_id and player.game_active:
            npc_combat_turn()
        return True 

    loc_id = player.current_location_id
    location_data = locations[loc_id]

    if command == "!map" or (command == "view" and " ".join(args) == "map scroll"): # Allow "view map scroll"
        if command == "view" and "blank_map_scroll" not in player.inventory:
            print("You don't have a map scroll to view.")
            return True
        if command == "view":
            print("You unfurl the map scroll...")

        draw_zone_map(player.current_location_id, locations) # Call draw_zone_map directly
    elif command == "look": print("\nYou take a closer look around...")
    elif command == "go":
        if not args: print("Go where? (Specify a direction like 'go north')")
        else:
            direction = args[0]
            if player.current_map_type == "zone":
                if direction in location_data.get("exits", {}):
                    destination_loc_id = location_data["exits"][direction]
                    destination_loc_data = locations.get(destination_loc_id, {})
                    
                    # Check if moving to a city node that should trigger city map entry
                    city_map_transition_info = destination_loc_data.get("city_map_transitions", {}).get("enter")
                    city_id_from_transition = city_map_transition_info.get("city_id") if city_map_transition_info else None

                    if city_map_transition_info and city_id_from_transition and city_id_from_transition in city_maps_data:
                        city_map_details = city_maps_data.get(city_id_from_transition)
                        entry_point_key = city_map_transition_info.get("entry_point_key")
                        entry_coords = city_map_details.get("entry_points", {}).get(entry_point_key)

                        if entry_coords:
                            player.last_zone_location_id = destination_loc_id # Store the city node ID
                            player.current_map_type = "city"
                            player.current_city_id = city_id_from_transition
                            player.current_city_x = entry_coords["x"]
                            player.current_city_y = entry_coords["y"]
                            player.current_location_id = destination_loc_id # Keep track of the zone map "parent" location
                            print(f"You enter the bustling city of {city_map_details.get('name', city_id_from_transition.capitalize())}.")
                        else: 
                            # City transition defined, but entry point key is invalid in city_map.json
                            # or entry_coords are missing.
                            print(f"You arrive at {destination_loc_data.get('name', 'the city entrance')}, but the way into the detailed map is unclear from here.")
                            player.move_to(destination_loc_id)
                            print(f"You walk {direction}.")
                    else: 
                        # Not a city with a detailed map, or no transition info
                        player.move_to(destination_loc_id)
                        print(f"You walk {direction}.")
                else: print(f"You can't go {direction} from here.")
            elif player.current_map_type == "city":
                current_city_map = city_maps_data.get(player.current_city_id)
                if not current_city_map:
                    print("[ERROR] Current city map data is missing. Cannot move.")
                    return True # Or handle error more gracefully

                grid_width = current_city_map["grid_size"]["width"]
                grid_height = current_city_map["grid_size"]["height"]
                
                new_x, new_y = player.current_city_x, player.current_city_y

                if direction == "north": new_y -= 1
                elif direction == "south": new_y += 1
                elif direction == "east": new_x += 1
                elif direction == "west": new_x -= 1
                else:
                    print(f"Unknown direction: {direction}")
                    return True

                # Boundary checks
                if 0 <= new_x < grid_width and 0 <= new_y < grid_height:
                    target_cell_data = current_city_map["cells"][new_y][new_x]
                    if target_cell_data.get("impassable") or target_cell_data.get("type") in ["wall_city_edge", "water_river_edge"]: # Add more impassable types as needed
                        print(f"You can't go {direction}. Something blocks your way ({target_cell_data.get('description', 'an obstacle')}).")
                    else:
                        player.current_city_x = new_x
                        player.current_city_y = new_y
                        print(f"You move {direction}.")
                        # Handle automatic actions on entering a cell, like 'move_to_cell'
                        cell_action = target_cell_data.get("action")
                        if cell_action and cell_action.get("type") == "move_to_cell" and "target_cell" in cell_action:
                            player.current_city_x = cell_action["target_cell"]["x"]
                            player.current_city_y = cell_action["target_cell"]["y"]
                            print(f"You are quickly ushered to another part of the area...") # Or a more specific message
                else:
                    print(f"You can't go {direction}. You've reached the edge of this area.")
    elif command == "enter" and " ".join(args) == "city":
        if player.current_map_type == "zone":
            current_loc_id = player.current_location_id
            current_location_data = locations.get(current_loc_id, {})

            if "city_map_transitions" in current_location_data and \
               "enter" in current_location_data["city_map_transitions"]:
                
                transition_info = current_location_data["city_map_transitions"]["enter"]
                city_id_to_enter = transition_info.get("city_id")
                entry_point_key = transition_info.get("entry_point_key")
                city_map_details = city_maps_data.get(city_id_to_enter)

                if city_map_details and entry_point_key and entry_point_key in city_map_details.get("entry_points", {}):
                    entry_coords = city_map_details["entry_points"][entry_point_key]
                    player.last_zone_location_id = current_loc_id # Store where we entered from
                    player.current_map_type = "city"
                    player.current_city_id = city_id_to_enter
                    player.current_city_x = entry_coords["x"]
                    player.current_city_y = entry_coords["y"]
                    print(f"You step through the gate and enter the detailed map of {city_map_details.get('name', city_id_to_enter.capitalize())}.")
                else:
                    print(f"You are at a city entrance, but the detailed map data for {city_id_to_enter.capitalize()} is missing or misconfigured.")
            else: print("You are not at a recognized city entrance.")
        else: print("You are already inside a city.")
    elif command == "open" and " ".join(args) == "worn crate": # Specific for starter task
        if player.current_location_id == "generic_start_room":
            crate = locations["generic_start_room"]["features"]["worn_crate"]
            if crate["closed"]:
                # Use the environmental interaction handler for consistency
                handle_environmental_interaction("worn_crate", "open")
            else:
                print("The crate is already open and empty.")
        else:
            print("There is no worn crate here to open.")
    elif command == "take":
        if not args: print("Take what?")
        else:
            # This 'take' command logic should now work for items revealed from the crate
            item_name_input = " ".join(args)
            item_to_take = None # This will store the item_id if found, or "currency_handled"
            room_items = location_data.get("items", []) # Get a mutable copy if modification is direct
            
            # Iterate over a copy of room_items if removing while iterating
            for r_item_id in list(room_items): 
                item_data = items_data.get(r_item_id, {})
                current_item_name_lower = item_data.get("name", "").lower()
                current_item_id_as_name = r_item_id.replace("_", " ")

                if item_name_input == current_item_name_lower or item_name_input == current_item_id_as_name:
                    if r_item_id == "small_pouch_of_coins":
                        coin_value = item_data.get("value", 0)
                        player.add_coins(coin_value, log_event_func=log_game_event, source=f"take_room_{loc_id}_{r_item_id}")
                        print(f"You picked up the {item_data.get('name', r_item_id)} and gained {coin_value} copper coins.")
                        room_items.remove(r_item_id) # Remove from the original list
                        item_to_take = "currency_handled" 
                        break 
                    else:
                        item_to_take = r_item_id
                        break 
            
            if item_to_take and item_to_take != "currency_handled":
                game_logic.award_item_to_player(player, items_data, item_to_take, source=f"take_room_{loc_id}", log_event_func=log_game_event) 
                room_items.remove(item_to_take) # Remove from the original list
            elif not item_to_take: # Only print if not found and not handled as currency
                print(f"There is no {item_name_input} here to take.")

    elif command == "inventory" or command == "i":
        if player.inventory:
            print("\nYou are carrying:")
            for item_id in player.inventory: print(f"  - {items_data.get(item_id, {}).get('name', item_id.replace('_',' '))}")
        else: print("Your inventory is empty.")
    elif command == "use":
        if len(args) < 3 or args[1] != "on": print("How to use: 'use <item_name> on <target_name>'")
        else:
            item_input = args[0]
            target_input = args[2]
            item_in_inv_id = next((inv_id for inv_id in player.inventory if item_input == items_data.get(inv_id,{}).get("name","").lower() or item_input == inv_id.replace("_"," ")), None)
            target_feature_id = next((f_id for f_id in location_data.get("features",{}).keys() if target_input == f_id.replace("_"," ")), None)

            if not item_in_inv_id: print(f"You don't have a {item_input}.")
            elif not target_feature_id: print(f"There is no {target_input} here to use the {item_input} on.")
            else:
                feature = location_data["features"][target_feature_id]
                if feature.get("locked") and feature.get("key_needed") == item_in_inv_id:
                    print(feature["unlock_message"])
                    feature["locked"] = False
                    game_logic.remove_item_from_player_inventory(player, items_data, item_in_inv_id, source=f"used_on_{target_feature_id}", log_event_func=log_game_event)
                    if "contains_item_on_unlock" in feature:
                        new_item = feature.pop("contains_item_on_unlock")
                        location_data.setdefault("items", []).append(new_item)
                        # Log item revealed from a locked feature
                        log_game_event("feature_item_revealed", {
                            "feature_id": target_feature_id,
                            "revealed_item_id": new_item,
                            "location_id": player.current_location_id
                        })
                        print(f"The {target_feature_id.replace('_', ' ')} creaks open. You see a {items_data.get(new_item,{}).get('name',new_item)} inside!")
                elif not feature.get("locked"): print(f"The {target_feature_id.replace('_', ' ')} is already unlocked/used.")
                else: print(f"The {item_input} doesn't seem to work on the {target_feature_id.replace('_', ' ')}.")
    elif command == "talk":
        if not args: print("Talk to whom?")
        else:
            npc_name_input = " ".join(args)
            room_npc_objects = location_data.get("npcs", {}) # This now contains NPC objects
            found_npc_object = None
            target_npc_id = None
            for npc_id_key, npc_obj_val in room_npc_objects.items():
                if npc_name_input == npc_obj_val.name.lower() or npc_name_input == npc_id_key.lower():
                    found_npc_object = npc_obj_val
                    target_npc_id = npc_id_key
                    break

            if found_npc_object:
                print(f"\nYou approach {found_npc_object.name}.")
                if found_npc_object.pre_combat_dialogue and found_npc_object.dialogue_options:
                    print(f"{found_npc_object.name} says: \"{found_npc_object.pre_combat_dialogue}\"")
                    player.start_dialogue(target_npc_id, found_npc_object.dialogue_options)
                elif found_npc_object.type == "quest_giver_simple":
                    if found_npc_object.quest_item_needed in player.inventory:
                        print(f"{found_npc_object.name} says: \"{found_npc_object.dialogue_after_quest_complete or 'Thank you!'}\"")
                        game_logic.remove_item_from_player_inventory(player, items_data, found_npc_object.quest_item_needed, source=f"quest_turn_in_{target_npc_id}", log_event_func=log_game_event)
                        if found_npc_object.quest_reward_item:
                            game_logic.award_item_to_player(player, items_data, found_npc_object.quest_reward_item, source=f"quest_reward_{target_npc_id}", log_event_func=log_game_event)

                        # If there's a currency reward for the quest
                        if found_npc_object.quest_reward_currency:
                            player.add_coins(found_npc_object.quest_reward_currency, log_event_func=log_game_event, source=f"quest_reward_{target_npc_id}")
                            print(f"You are also rewarded with {found_npc_object.quest_reward_currency} coins.")
                    else:
                        print(f"{found_npc_object.name} says: \"{found_npc_object.dialogue_after_quest_incomplete or found_npc_object.dialogue}\"")
                elif found_npc_object.hostile:
                    print(found_npc_object.dialogue)
                    player.enter_combat(target_npc_id)
                elif found_npc_object.type == "vendor":
                    print(VENDOR_STALL_VISUAL)
                    print(f"{found_npc_object.name} says: \"{found_npc_object.dialogue}\"")
                else:
                    print(f"{found_npc_object.name} says: \"{found_npc_object.dialogue}\"")
            else:
                print(f"There is no one named '{npc_name_input}' here to talk to.")
    else:
        potential_verb = command
        
        # Check for 'exit city' command specifically
        if command == "exit" and " ".join(args) == "city":
             if player.current_map_type == "city":
                 print(f"You leave {city_maps_data.get(player.current_city_id, {}).get('name', 'the city')} and return to the zone map.")
                 player.current_map_type = "zone"
                 # player.current_location_id is already set to the zone map entry point
             else: print("You are not currently inside a city.")
             return True # Command processed

        potential_target = " ".join(args)
        target_feature_id = None
        for f_id in location_data.get("features", {}).keys():
            if potential_target == f_id.replace("_", " "):
                target_feature_id = f_id
                break
        if target_feature_id and potential_verb in location_data["features"][target_feature_id].get("actions", {}):
            handle_environmental_interaction(target_feature_id, potential_verb)
        else:
            print(f"I don't understand '{full_command}'. Try 'look' or check commands.")
    return True # Command processed

def process_command(full_command_input):
    full_command = full_command_input.lower().strip()
    parts = full_command.split()
    if not parts: return True
    command = parts[0]
    args = parts[1:]

    if command == "!start":
        if player.game_active: print("The game has already started!")
        else:
            initialize_game_state()
        return True
    elif command == "!start_browser":
        launch_web_interface()
        return True
    elif command == "!save":
        if not player.game_active:
            print("Game not active. Cannot save.")
            return True # Command processed, show scene again
        current_zone = locations[player.current_location_id].get("zone")
        if current_zone in CITY_ZONES:
            save_player_data(player, reason_for_save="Game progress manually saved")
        else:
            print("You can only save your progress in a city.")
        return True # Command processed, show scene again
    elif command == "!reload_data":
        print("Attempting to reload game data...")
        load_all_game_data()
        return True # Show scene again to reflect any changes
    elif command == "!quit":
        print(f"\nYou decide to end your adventure here. Farewell!" if player.game_active else "\nFarewell!")
        return False
    elif command == "worldmap":
        display_world_map()
        return True

    if not player.game_active:
        print(f"Unknown command: '{full_command}'. Type '!start' to begin.")
        return True

    if player.dialogue_npc_id and player.dialogue_options_pending:
        npc_id = player.dialogue_npc_id
        npc_object = locations[player.current_location_id]["npcs"][npc_id] # Get NPC object

        if full_command == "leave":
            print(f"You end the conversation with {npc_object.name}.")
            player.end_dialogue() # Player object's method
            return True

        chosen_option_data = player.dialogue_options_pending.get(full_command)
        if chosen_option_data:
            print(f"\n> {chosen_option_data['text']}")
            if chosen_option_data.get("response"):
                print(f"{npc_object.name} says: \"{chosen_option_data['response']}\"")

            if chosen_option_data.get("triggers_combat"):
                player.end_dialogue() # End dialogue before starting combat
                player.enter_combat(npc_id) # Player object's method
            elif chosen_option_data.get("action_type") == "end_conversation":
                player.end_dialogue() # Player object's method
        else:
            print("Invalid choice. Please type the number of the option or 'leave'.")
        return True

    if player.combat_target_id:
        npc_id = player.combat_target_id
        if npc_id not in locations[player.current_location_id]["npcs"]:
            print(f"[Warning] Target {npc_id} seems to be gone. Ending combat.")
            player.leave_combat() # Player object's method
            return True

        npc_object = locations[player.current_location_id]["npcs"][npc_id] # Get NPC object
        action_taken = False

        if command == "attack":
            damage = player.attack_power
            npc_object.take_damage(damage) # Use NPC method
            print(f"You attack {npc_object.name} for {damage} damage.")
            if not npc_object.is_alive(): # Use NPC method
                handle_npc_defeat(npc_id)
            action_taken = True
        elif command == "special":
            if not args: print("Which special move? (Specify the move like 'special power strike')")
            else:
                move_input = "_".join(args)
                if move_input in player.special_moves:
                    if player.special_cooldowns.get(move_input, 0) == 0:
                        move_details = player.special_moves[move_input]
                        damage = int(player.attack_power * move_details["damage_multiplier"])
                        npc_object.take_damage(damage) # Use NPC method
                        print(f"You use {move_details['name']} on {npc_object.name} for {damage} damage!")
                        player.special_cooldowns[move_input] = move_details["cooldown_max"]
                        if not npc_object.is_alive(): # Use NPC method
                            handle_npc_defeat(npc_id)
                        action_taken = True
                    else:
                        print(f"{player.special_moves[move_input]['name']} is on cooldown ({player.special_cooldowns[move_input]} turns left).")
                else:
                    print(f"You don't know a special move called '{' '.join(args)}'.")
        elif command == "deflect":
            player.set_deflecting(True) # Player object's method
            print("You brace yourself, preparing to deflect the next attack.")
            action_taken = True
        elif command == "item":
            if not args: print("Use which item?")
            else:
                item_name_input = " ".join(args)
                item_id_to_use = None
                for inv_item_id in player.inventory:
                    if item_name_input == items_data.get(inv_item_id, {}).get("name", "").lower() or \
                       item_name_input == inv_item_id.replace("_", " "):
                        item_id_to_use = inv_item_id
                        break

                if item_id_to_use:
                    item_detail = items_data.get(item_id_to_use)
                    if item_detail and item_detail["type"] == "consumable" and item_detail["effect"] == "heal":
                        heal_amount = item_detail["amount"]
                        player.heal(heal_amount) # Use method
                        player.remove_item_from_inventory(item_id_to_use) # Use method
                        print(f"You use the {item_detail['name']} and restore {heal_amount} HP. You now have {player.hp}/{player.max_hp} HP.")
                        action_taken = True
                    else:
                        print(f"You can't use the {item_name_input} in that way right now.")
                else:
                    print(f"You don't have a '{item_name_input}'.")
        else:
            print(f"Unknown combat command: '{command}'. Valid commands: attack, special, deflect, item.")

        # After player action in combat, check if combat should continue (NPC still alive)
        if action_taken and player.combat_target_id and player.game_active:
            npc_combat_turn()
        return True

    # --- New Unequip Command Handler (Terminal) ---
    # This is a basic terminal handler. The web handler is separate.
    elif command == "unequip":
        if not args: print("Unequip what? (Specify the item name)")
        else:
            item_name_input = " ".join(args)
            # Find the item in equipped slots
            item_id_to_unequip = None
            slot_unequipped_from = None
            for slot, item_id in player.equipment.items():
                if item_id and (item_name_input == items_data.get(item_id, {}).get("name", "").lower() or item_name_input == item_id.replace("_", " ")):
                    item_id_to_unequip = item_id
                    slot_unequipped_from = slot
                    break
            if item_id_to_unequip:
                unequip_message = player.unequip_item(slot_unequipped_from, items_data, log_event_func=log_game_event)
                print(unequip_message)
            else:
                print(f"You don't have '{item_name_input}' equipped.")
        return True # Command processed, show scene again
    # --- End Unequip Command Handler (Terminal) ---

    loc_id = player.current_location_id
    location_data = locations[loc_id]

    if command == "!map" or (command == "view" and " ".join(args) == "map scroll"): # Allow "view map scroll"
        if command == "view" and "blank_map_scroll" not in player.inventory:
            print("You don't have a map scroll to view.")
            return True
        if command == "view":
            print("You unfurl the map scroll...")

        draw_zone_map(player.current_location_id, locations) # Call draw_zone_map directly
    elif command == "look": print("\nYou take a closer look around...")
    elif command == "go":
        if not args: print("Go where? (Specify a direction like 'go north')")
        else:
            direction = args[0]
            if player.current_map_type == "zone":
                if direction in location_data.get("exits", {}):
                    destination_loc_id = location_data["exits"][direction]
                    destination_loc_data = locations.get(destination_loc_id, {})

                    # Check if moving to a city node that should trigger city map entry
                    city_map_transition_info = destination_loc_data.get("city_map_transitions", {}).get("enter")
                    city_id_from_transition = city_map_transition_info.get("city_id") if city_map_transition_info else None

                    if city_map_transition_info and city_id_from_transition and city_id_from_transition in city_maps_data:
                        city_map_details = city_maps_data.get(city_id_from_transition)
                        entry_point_key = city_map_transition_info.get("entry_point_key")
                        entry_coords = city_map_details.get("entry_points", {}).get(entry_point_key)

                        if entry_coords:
                            player.last_zone_location_id = destination_loc_id # Store the city node ID
                            player.current_map_type = "city"
                            player.current_city_id = city_id_from_transition
                            player.current_city_x = entry_coords["x"]
                            player.current_city_y = entry_coords["y"]
                            player.current_location_id = destination_loc_id # Keep track of the zone map "parent" location
                            print(f"You enter the bustling city of {city_map_details.get('name', city_id_from_transition.capitalize())}.")
                        else:
                            # City transition defined, but entry point key is invalid in city_map.json
                            # or entry_coords are missing.
                            print(f"You arrive at {destination_loc_data.get('name', 'the city entrance')}, but the way into the detailed map is unclear from here.")
                            player.move_to(destination_loc_id)
                            print(f"You walk {direction}.")
                    else:
                        # Not a city with a detailed map, or no transition info
                        player.move_to(destination_loc_id)
                        print(f"You walk {direction}.")
                else: print(f"You can't go {direction} from here.")
            elif player.current_map_type == "city":
                current_city_map = city_maps_data.get(player.current_city_id)
                if not current_city_map:
                    print("[ERROR] Current city map data is missing. Cannot move.")
                    return True # Or handle error more gracefully

                grid_width = current_city_map["grid_size"]["width"]
                grid_height = current_city_map["grid_size"]["height"]

                new_x, new_y = player.current_city_x, player.current_city_y

                if direction == "north": new_y -= 1
                elif direction == "south": new_y += 1
                elif direction == "east": new_x += 1
                elif direction == "west": new_x -= 1
                else:
                    print(f"Unknown direction: {direction}")
                    return True

                # Boundary checks
                if 0 <= new_x < grid_width and 0 <= new_y < grid_height:
                    target_cell_data = current_city_map["cells"][new_y][new_x]
                    if target_cell_data.get("impassable") or target_cell_data.get("type") in ["wall_city_edge", "water_river_edge"]: # Add more impassable types as needed
                        print(f"You can't go {direction}. Something blocks your way ({target_cell_data.get('description', 'an obstacle')}).")
                    else:
                        player.current_city_x = new_x
                        player.current_city_y = new_y
                        print(f"You move {direction}.")
                        # Handle automatic actions on entering a cell, like 'move_to_cell'
                        cell_action = target_cell_data.get("action")
                        if cell_action and cell_action.get("type") == "move_to_cell" and "target_cell" in cell_action:
                            player.current_city_x = cell_action["target_cell"]["x"]
                            player.current_city_y = cell_action["target_cell"]["y"]
                            print(f"You are quickly ushered to another part of the area...") # Or a more specific message
                else:
                    print(f"You can't go {direction}. You've reached the edge of this area.")
    elif command == "enter" and " ".join(args) == "city":
        if player.current_map_type == "zone":
            current_loc_id = player.current_location_id
            current_location_data = locations.get(current_loc_id, {})

            if "city_map_transitions" in current_location_data and \
               "enter" in current_location_data["city_map_transitions"]:

                transition_info = current_location_data["city_map_transitions"]["enter"]
                city_id_to_enter = transition_info.get("city_id")
                entry_point_key = transition_info.get("entry_point_key")
                city_map_details = city_maps_data.get(city_id_to_enter)

                if city_map_details and entry_point_key and entry_point_key in city_map_details.get("entry_points", {}):
                    entry_coords = city_map_details["entry_points"][entry_point_key]
                    player.last_zone_location_id = current_loc_id # Store where we entered from
                    player.current_map_type = "city"
                    player.current_city_id = city_id_to_enter
                    player.current_city_x = entry_coords["x"]
                    player.current_city_y = entry_coords["y"]
                    print(f"You step through the gate and enter the detailed map of {city_map_details.get('name', city_id_to_enter.capitalize())}.")
                else:
                    print(f"You are at a city entrance, but the detailed map data for {city_id_to_enter.capitalize()} is missing or misconfigured.")
            else: print("You are not at a recognized city entrance.")
        else: print("You are already inside a city.")
    elif command == "open" and " ".join(args) == "worn crate": # Specific for starter task
        if player.current_location_id == "generic_start_room":
            crate = locations["generic_start_room"]["features"]["worn_crate"]
            if crate["closed"]:
                # Use the environmental interaction handler for consistency
                handle_environmental_interaction("worn_crate", "open")
            else:
                print("The crate is already open and empty.")
        else:
            print("There is no worn crate here to open.")
    elif command == "take":
        if not args: print("Take what?")
        else:
            # This 'take' command logic should now work for items revealed from the crate
            item_name_input = " ".join(args)
            item_to_take_id = None # This will store the item_id if found
            room_items = location_data.get("items", []) # Get a mutable copy if modification is direct

            # Iterate over a copy of room_items if removing while iterating
            for r_item_id in list(room_items):
                item_data = items_data.get(r_item_id, {})
                current_item_name_lower = item_data.get("name", "").lower()
                current_item_id_as_name = r_item_id.replace("_", " ")

                if item_name_input == current_item_name_lower or item_name_input == current_item_id_as_name:
                    item_to_take_id = r_item_id
                    break

            if item_to_take_id:
                # Use the award_item_to_player function which handles adding to inventory and logging
                game_logic.award_item_to_player(player, items_data, item_to_take_id, source=f"take_room_{loc_id}", log_event_func=log_game_event)
                # Remove from the room's item list
                if item_to_take_id in room_items: # Double check it's still there before removing
                    room_items.remove(item_to_take_id)
            else:
                print(f"There is no {item_name_input} here to take.")

    elif command == "inventory" or command == "i":
        if player.inventory:
            print("\nYou are carrying:")
            for item_id in player.inventory: print(f"  - {items_data.get(item_id, {}).get('name', item_id.replace('_',' '))}")
        else: print("Your inventory is empty.")
    elif command == "use":
        if len(args) == 1: # Handle "use <item>"
            item_input = args[0]
            # Find the item ID in the player's inventory by name or ID
            item_in_inv_id = next((inv_id for inv_id in player.inventory if item_input == items_data.get(inv_id,{}).get("name","").lower() or item_input == inv_id.replace("_"," ")), None)

            if not item_in_inv_id:
                print(f"You don't have a {item_input}.")
                return True

            item_details = items_data.get(item_in_inv_id)
            # Check if the item has a 'use' action defined
            if not item_details or "actions" not in item_details or "use" not in item_details["actions"]:
                 print(f"You can't 'use' the {item_details.get('name', item_input)} in that way.")
                 return True

            use_action_details = item_details["actions"]["use"]
            outcome_pool = use_action_details.get("outcomes", [])

            # Print the action message if defined
            if use_action_details.get("message"):
                 print(use_action_details["message"])

            # Process outcomes (assuming simple sequential or first outcome for now)
            if not outcome_pool:
                 print(f"Using the {item_details.get('name', item_input)} seems to have no effect.")
                 return True

            # For simplicity, process all outcomes listed
            for chosen_outcome in outcome_pool:
                if chosen_outcome.get("message"):
                    print(chosen_outcome["message"]) # Print outcome-specific message

                if chosen_outcome.get("type") == "add_contained_currency":
                    currency_value = chosen_outcome.get("value", 0)
                    currency_type = chosen_outcome.get("currency_type", "coins") # Default to coins
                    if currency_value > 0:
                        # Assuming player only has 'coins' currency for now
                        player.add_coins(currency_value, log_event_func=log_game_event, source=f"used_item_{item_in_inv_id}")
                    else:
                        print(f"The {item_details.get('name', item_input)} seems to be empty of currency.")

                elif chosen_outcome.get("type") == "reveal_contained_items":
                     items_to_reveal = chosen_outcome.get("items", [])
                     if items_to_reveal:
                         print(f"Inside, you find:")
                         for revealed_item_id in items_to_reveal:
                             game_logic.award_item_to_player(player, items_data, revealed_item_id, source=f"used_item_{item_in_inv_id}", log_event_func=log_game_event)
                     else:
                         print(f"The {item_details.get('name', item_input)} seems to be empty of items.")

                # Add other item use outcome types here (e.g., heal, buff, etc.)
                elif chosen_outcome.get("type") == "heal":
                    heal_amount = chosen_outcome.get("amount", 0)
                    if heal_amount > 0:
                        player.heal(heal_amount)
                        print(f"You feel restored. Your HP is now {player.hp}/{player.max_hp}.")
                # Add other outcome types as needed

            # After processing outcomes, remove the container item from inventory
            # This assumes the container is consumed on use. Adjust if some containers are reusable.
            player.remove_item_from_inventory(item_in_inv_id)
            print(f"The {item_details.get('name', item_input)} is consumed.") # Or "is now empty and discarded."

        elif len(args) >= 3 and args[1] == "on": # Existing "use <item> on <target>" logic
            item_input = args[0]
            target_input = args[2]
            item_in_inv_id = next((inv_id for inv_id in player.inventory if item_input == items_data.get(inv_id,{}).get("name","").lower() or item_input == inv_id.replace("_"," ")), None)
            target_feature_id = next((f_id for f_id in location_data.get("features",{}).keys() if target_input == f_id.replace("_"," ")), None)

            if not item_in_inv_id: print(f"You don't have a {item_input}.")
            elif not target_feature_id: print(f"There is no {target_input} here to use the {item_input} on.")
            else:
                feature = location_data["features"][target_feature_id]
                if feature.get("locked") and feature.get("key_needed") == item_in_inv_id:
                    print(feature["unlock_message"])
                    feature["locked"] = False
                    game_logic.remove_item_from_player_inventory(player, items_data, item_in_inv_id, source=f"used_on_{target_feature_id}", log_event_func=log_game_event)
                    if "contains_item_on_unlock" in feature:
                        new_item = feature.pop("contains_item_on_unlock")
                        location_data.setdefault("items", []).append(new_item)
                        # Log item revealed from a locked feature
                        log_game_event("feature_item_revealed", {
                            "feature_id": target_feature_id,
                            "revealed_item_id": new_item,
                            "location_id": player.current_location_id
                        })
                        print(f"The {target_feature_id.replace('_', ' ')} creaks open. You see a {items_data.get(new_item,{}).get('name',new_item)} inside!")
                elif not feature.get("locked"): print(f"The {target_feature_id.replace('_', ' ')} is already unlocked/used.")
                else: print(f"The {item_input} doesn't seem to work on the {target_feature_id.replace('_', ' ')}.")
        else:
            print("Invalid 'use' command format. Try 'use <item_name>' or 'use <item_name> on <target_name>'.")
        return True
    elif command == "talk":
        if not args: print("Talk to whom?")
        else:
            npc_name_input = " ".join(args)
            room_npc_objects = location_data.get("npcs", {}) # This now contains NPC objects
            found_npc_object = None
            target_npc_id = None
            for npc_id_key, npc_obj_val in room_npc_objects.items():
                if npc_name_input == npc_obj_val.name.lower() or npc_name_input == npc_id_key.lower():
                    found_npc_object = npc_obj_val
                    target_npc_id = npc_id_key
                    break

            if found_npc_object:
                print(f"\nYou approach {found_npc_object.name}.")
                if found_npc_object.pre_combat_dialogue and found_npc_object.dialogue_options:
                    print(f"{found_npc_object.name} says: \"{found_npc_object.pre_combat_dialogue}\"")
                    player.start_dialogue(target_npc_id, found_npc_object.dialogue_options)
                elif found_npc_object.type == "quest_giver_simple":
                    if found_npc_object.quest_item_needed in player.inventory:
                        print(f"{found_npc_object.name} says: \"{found_npc_object.dialogue_after_quest_complete or 'Thank you!'}\"")
                        game_logic.remove_item_from_player_inventory(player, items_data, found_npc_object.quest_item_needed, source=f"quest_turn_in_{target_npc_id}", log_event_func=log_game_event)
                        if found_npc_object.quest_reward_item:
                            game_logic.award_item_to_player(player, items_data, found_npc_object.quest_reward_item, source=f"quest_reward_{target_npc_id}", log_event_func=log_game_event)

                        # If there's a currency reward for the quest
                        if found_npc_object.quest_reward_currency:
                            player.add_coins(found_npc_object.quest_reward_currency, log_event_func=log_game_event, source=f"quest_reward_{target_npc_id}")
                            print(f"You are also rewarded with {found_npc_object.quest_reward_currency} coins.")
                    else:
                        print(f"{found_npc_object.name} says: \"{found_npc_object.dialogue_after_quest_incomplete or found_npc_object.dialogue}\"")
                elif found_npc_object.hostile:
                    print(found_npc_object.dialogue)
                    player.enter_combat(target_npc_id)
                elif found_npc_object.type == "vendor":
                    print(VENDOR_STALL_VISUAL)
                    print(f"{found_npc_object.name} says: \"{found_npc_object.dialogue}\"")
                else:
                    print(f"{found_npc_object.name} says: \"{found_npc_object.dialogue}\"")
            else:
                print(f"There is no one named '{npc_name_input}' here to talk to.")
    else:
        potential_verb = command

        # Check for 'exit city' command specifically
        if command == "exit" and " ".join(args) == "city":
             if player.current_map_type == "city":
                 print(f"You leave {city_maps_data.get(player.current_city_id, {}).get('name', 'the city')} and return to the zone map.")
                 player.current_map_type = "zone"
                 # player.current_location_id is already set to the zone map entry point
             else: print("You are not currently inside a city.")
             return True # Command processed

        potential_target = " ".join(args)
        target_feature_id = None
        for f_id in location_data.get("features", {}).keys():
            if potential_target == f_id.replace("_", " "):
                target_feature_id = f_id
                break
        if target_feature_id and potential_verb in location_data["features"][target_feature_id].get("actions", {}):
            handle_environmental_interaction(target_feature_id, potential_verb)
        else:
            print(f"I don't understand '{full_command}'. Try 'look' or check commands.")
    return True

def main_game_loop():
    if not player.game_active:
        show_current_scene() # Shows initial welcome
    else:
        show_current_scene() # Shows the scene for the current location if game is active

    while True:
        prompt_text = "> "
        if player.game_active:
            if player.dialogue_npc_id and player.dialogue_options_pending:
                prompt_text = "[DIALOGUE] > "
            elif player.combat_target_id:
                prompt_text = "[COMBAT] > "
            elif player.current_location_id and player.current_location_id in locations:
                loc_name = locations[player.current_location_id]["name"]
                prompt_text = f"[{loc_name}] > "
            else: 
                # This case should ideally not be reached if game_active is true and character creation sets a location
                print("[Error: Current location unknown, but game is active. Resetting to start room.]")
                player.move_to("generic_start_room")
        
        user_input = input(prompt_text)
        if not process_command(user_input): break 
        
        if player.game_active:
            show_current_scene()
        elif not player.game_active and player.combat_target_id is None and player.dialogue_npc_id is None :
             # Game ended not due to combat/dialogue, or character creation was cancelled
             break 

if __name__ == "__main__":
    auto_start_game = False
    start_browser_on_launch = False
    run_character_creation_on_start = True 

    if "--autostart" in sys.argv:
        auto_start_game = True
    if "--browser" in sys.argv:
        start_browser_on_launch = True

    # --- Character Selection / Creation for Terminal ---
    if not start_browser_on_launch: # If browser is launched, it handles its own CC/load flow
        # This block is for terminal-only startup
        existing_chars = list_existing_characters() 
        if existing_chars and not auto_start_game: 
            print("\n--- Welcome to Adventure of Textland ---")
            options = {}
            current_option = 1
            print("Choose an option:")
            for char_data in existing_chars:
                print(f"  {current_option}. Load: {char_data['display_name']} ({char_data['species']} {char_data['class']})")
                options[str(current_option)] = ("load", char_data['display_name'])
                current_option += 1
            
            print(f"  {current_option}. Create New Character")
            options[str(current_option)] = ("new", None)
            current_option_after_new = current_option + 1

            delete_options_start_index = current_option_after_new
            if existing_chars: 
                print(f"  ---") 
                for i, char_data in enumerate(existing_chars):
                    delete_option_num = delete_options_start_index + i
                    print(f"  {delete_option_num}. Delete: {char_data['display_name']}")
                    options[str(delete_option_num)] = ("delete", char_data['display_name'])
            
            choice_made = False
            while not choice_made:
                try:
                    selection_str = input("Enter your choice: ").strip()
                    if selection_str in options:
                        action, char_name_for_action = options[selection_str]
                        if action == "load":
                            if load_character_data(char_name_for_action):
                                choice_made = True
                        elif action == "new":
                            initialize_game_state() # This sets player["game_active"] = True
                            choice_made = True
                        elif action == "delete":
                            confirm_delete = input(f"Are you sure you want to permanently delete '{char_name_for_action}'? This cannot be undone. (yes/no): ").strip().lower()
                            if confirm_delete == 'yes':
                                delete_character_data(char_name_for_action)
                            print("Please restart to see updated character list after deletion or cancellation.")
                            sys.exit() 
                    else:
                        print("Invalid selection.")
                except ValueError:
                    print("Please enter a number.")
        elif auto_start_game and existing_chars:
             print(f"Autostarting with first available character: {existing_chars[0]['display_name']}")
             load_character_data(existing_chars[0]['display_name'])
        elif run_character_creation_on_start or auto_start_game: # No existing chars, or autostart with no chars
            initialize_game_state()
    
    # --- Browser Launch Logic ---
    if start_browser_on_launch:
        if flask_available:
            launch_web_interface() 
            if web_server_thread and web_server_thread.is_alive():
                print("Web server is running. Terminal game loop will not start if browser is primary.")
                print("The game state will be managed by web requests.")
                print("Close this terminal to stop the web server and the game.")
                # Keep the main thread alive while the web server (daemon thread) runs.
                # This prevents the script from exiting immediately.
                try:
                    while web_server_thread.is_alive(): # Keep main thread alive while server runs
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\nShutting down web server and game.")
                # sys.exit(0) # Exit after web server stops or on interrupt - let it fall through
            else:
                print("[ERROR] Failed to start web server, but --browser was specified.")
                # Decide if we should attempt terminal mode as a fallback
                # If no character is active yet, try to initialize for terminal
                if not player.game_active and (run_character_creation_on_start or auto_start_game):
                    print("Attempting to initialize for terminal mode as a fallback...")
                    initialize_game_state() 
                # Fall through to potentially run main_game_loop if player is active
        else:
            print("\n[INFO] Flask library not found. Cannot start browser interface.")
            print("       Please install Flask (e.g., 'pip install Flask') and run with --browser again.")
            print("       Proceeding with terminal mode if character was created/loaded.")
            if not player.game_active and (run_character_creation_on_start or auto_start_game):
                 initialize_game_state() # Ensure game starts if browser failed but CC was intended
    
    # --- Terminal Game Loop Condition ---
    # Run terminal game loop if:
    # 1. Browser was not requested OR
    # 2. Browser was requested but failed to start AND player is now active (e.g., via fallback CC)
    if not start_browser_on_launch or (start_browser_on_launch and not (web_server_thread and web_server_thread.is_alive())):
        if player.game_active: # Only run if a character is active
            main_game_loop()
        elif not start_browser_on_launch: # If not browser mode and no active char, something went wrong with CC
            print("No active character. Exiting.")
        main_game_loop()
