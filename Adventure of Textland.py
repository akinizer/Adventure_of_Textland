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
    from flask import Flask, request, jsonify
    flask_available = True
except ImportError:
    flask_available = False

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

# --- Game Data ---
# Initialize as empty dicts; will be populated by load_all_game_data()
locations = {}
zone_layouts = {}
items_data = {}
species_data = {}
classes_data = {}

BASE_LOCATIONS_DATA = { # Keep your original structure here for initial load
    # --- Eldoria City ---
    "eldoria_square": {
        "name": "Eldoria Town Square",
        "zone": "Eldoria",
        "description": "The bustling heart of Eldoria. A grand fountain stands in the center. Paths lead east to the market and south towards the city gate.",
        "exits": {"east": "eldoria_market", "south": "eldoria_south_gate"},
        "items": ["shiny_coin", "healing_potion"], # Added healing potion
        "npcs": {
            "elder_maeve": {
                "name": "Elder Maeve",
                "description": "A wise-looking woman with kind eyes, sitting by the town fountain.",
                "dialogue": "Hey you there, I am looking for an adventurer. We've had reports of strange creatures in the Whispering Woods. Could you investigate?",
                "type": "quest_giver",
                "hostile": False
            },
            "guard_thomas": {
                "name": "Guard Thomas",
                "description": "A stern-faced guard in polished armor, watching over the square.",
                "dialogue": "Keep the peace, citizen. If you need help, Elder Maeve is wise, or check the market for goods.",
                "type": "neutral",
                "hostile": False
            }
        }
    },
    "eldoria_market": {
        "name": "Eldoria Market",
        "zone": "Eldoria",
        "description": "A vibrant street filled with stalls. Merchants call out, offering various goods. The town square is to the west.",
        "exits": {"west": "eldoria_square"},
        "items": ["apple", "bread_loaf"],
        "npcs": {
            "merchant_sarah": {
                "name": "Merchant Sarah",
                "description": "A cheerful merchant with a wide array of goods on display.",
                "dialogue": "Welcome to my stall! Finest goods in Eldoria!",
                "type": "vendor",
                "hostile": False
            },
            "grumpy_old_man": {
                "name": "Grumpy Old Man",
                "description": "An old man muttering to himself on a bench, eyeing passersby with suspicion.",
                "dialogue": "Hmph. Get away from me, you bother.",
                "type": "dismissive",
                "hostile": False
            }
        }
    },
    "eldoria_south_gate": {
        "name": "Eldoria South Gate",
        "zone": "Eldoria",
        "description": "Massive wooden gates mark the southern exit of Eldoria. A well-worn path leads south into the countryside. The town square is to the north.",
        "exits": {"north": "eldoria_square", "south": "southern_road_1"},
        "npcs": {}
    },

    # --- Paths ---
    "southern_road_1": {
        "name": "Southern Road - Part 1",
        "zone": "SouthernRoad",
        "description": "You are on a dusty road leading south from Eldoria. Fields stretch to either side. To the east, you spot the dark opening of a cave. The road continues south.",
        "exits": {"north": "eldoria_south_gate", "south": "southern_road_2", "east": "gloomy_cave_entrance"},
        "items": [],
        "npcs": {}
    },
    "gloomy_cave_entrance": {
        "name": "Gloomy Cave Entrance",
        "zone": "SouthernRoad",
        "description": "The air is cold and damp around this dark cave mouth. Strange noises echo from within. This looks like a dangerous place.",
        "exits": {"west": "southern_road_1"},
        "items": ["rusty_key"],
        "features": {
            "loose_rocks": {
                "description": "A pile of loose rocks near the entrance. They look unstable.",
                "actions": {
                    "search": {
                        "outcomes": [
                            {"type": "message", "message": "You sift through the rocks but find nothing of interest."},
                            {"type": "item", "item_id": "grimy_coin", "message": "You find a grimy old coin hidden amongst the rocks!"}
                        ],
                        "probabilities": [0.7, 0.3]
                    },
                    "kick": {
                        "outcomes": [{"type": "message", "message": "You kick the rocks. A few skitter away. Nothing else happens."}]
                    }
                }
            }
        },
        "npcs": {
            "cave_lurker": {
                "name": "Cave Lurker",
                "description": "A shadowy figure with glowing eyes, partially hidden in the darkness.",
                "dialogue": "*A guttural growl echoes from the shadows... It lunges!*",
                "type": "mob",
                "hostile": True,
                "hp": 30,
                "max_hp": 30,
                "attack_power": 5,
                "loot": ["tattered_pelt"]
            }
        }
    },
    "southern_road_2": {
        "name": "Southern Road - Part 2",
        "zone": "SouthernRoad",
        "description": "The road continues south. In the distance, you can see the town of Riverford nestled by a river. The path north leads back towards Eldoria.",
        "exits": {"north": "southern_road_1", "south": "riverford_north_gate"},
        "items": [],
        "npcs": {}
    },

    # --- Riverford City ---
    "riverford_north_gate": {
        "name": "Riverford North Gate",
        "zone": "Riverford",
        "description": "You stand at the northern gate of Riverford. The town looks quieter than Eldoria. The main square is to the south.",
        "exits": {"north": "southern_road_2", "south": "riverford_square"},
        "npcs": {}
    },
    "riverford_square": {
        "name": "Riverford Town Square",
        "zone": "Riverford",
        "description": "A quaint town square with a small, bubbling spring. A few townsfolk go about their business. The docks are to the east.",
        "exits": {"north": "riverford_north_gate", "east": "riverford_docks"},
        "items": [],
        "npcs": {
            "concerned_villager": {
                "name": "Concerned Villager",
                "description": "A villager who keeps glancing around nervously, clutching a small note.",
                "dialogue": "Psst, come here stranger. I have urgent news about the goings-on in the MurkWaste Swamp!",
                "type": "quest_giver_urgent",
                "hostile": False
            }
        }
    },
    "riverford_docks": {
        "name": "Riverford Docks",
        "zone": "Riverford",
        "description": "Wooden planks form a series of docks along the river. Fishing boats are moored here. The town square is to the west.",
        "exits": {"west": "riverford_square"},
        "items": ["fishing_net_scraps"],
        "npcs": {
            "old_fisherman": {
                "name": "Old Fisherman",
                "description": "An old fisherman mending his nets, he doesn't look up from his work.",
                "dialogue": "Hmph. River's been quiet lately... too quiet.",
                "type": "dismissive_hint",
                "hostile": False
            }
        }
    },
     "deep_woods": {
        "name": "Deep Woods",
        "zone": "WhisperingWoods",
        "description": "You are deep within the woods. It's eerily quiet. The path back south is the only clear way out.\nYou spot a small, old chest on the ground.",
        "exits": {"south": "forest_entrance_placeholder"},
        "items": [],
        "features": {
            "chest": {
                "description_locked": "A small, old wooden chest, bound with iron. It appears to be locked.",
                "description_unlocked": "The chest is open. It's empty now.",
                "locked": True,
                "key_needed": "rusty_key",
                "unlock_message": "You use the rusty_key. With a satisfying *click*, the chest unlocks!",
                "contains_item_on_unlock": "golden_amulet"
            }
        },
        "npcs": {}
    },
    "forest_entrance_placeholder": {
        "name": "Edge of the Deep Woods",
        "zone": "WhisperingWoods",
        "description": "You are at an entrance to the Deep Woods. It looks untamed.",
        "exits": {"north": "deep_woods", "east": "whispering_woods_path"},
        "items": ["strange_berries"],
        "npcs": {
            "nervous_scout": {
                "name": "Nervous Scout",
                "description": "A scout pacing back and forth, muttering about 'the beast'.",
                "hostile": False,
                "dialogue": "You there! Have you seen it? The... the beast of the woods! It took my lucky charm!",
                "type": "quest_giver_simple",
                "quest_item_needed": "lucky_charm_figurine",
                "quest_reward_item": "scouts_map_fragment",
                "dialogue_after_quest_incomplete": "Please, find my lucky charm! I can't go on without it.",
                "dialogue_after_quest_complete": "My charm! You found it! Oh, thank you! Here, take this for your trouble."
            }
        }
    },
    "whispering_woods_path": {
        "name": "Whispering Woods Path",
        "zone": "WhisperingWoods",
        "description": "A winding path through the Whispering Woods. Sunlight dapples through the leaves. You hear rustling nearby.",
        "exits": {"west": "forest_entrance_placeholder", "east": "ancient_grove"},
        "items": [],
        "features": {
            "glowing_mushroom_patch": {
                "description": "A patch of faintly glowing mushrooms.",
                "actions": {
                    "pick": {
                        "outcomes": [
                            {"type": "item", "item_id": "glowing_mushroom", "message": "You carefully pick a glowing mushroom."},
                            {"type": "message", "stat_effect_temp": "dizzy", "message": "You pick a mushroom, and a puff of spores makes you feel dizzy for a moment."}
                        ],
                        "probabilities": [0.8, 0.2]
                    }
                }
            },
            "hollow_log": {
                "description": "An old, hollow log lies by the path.",
                "actions": {"search": {"outcomes": [{"type": "item", "item_id": "lucky_charm_figurine", "message": "You search the hollow log and find a small, carved figurine!"}]}}
            }
        },
        "npcs": {
            "wandering_spirit": {
                "name": "Wandering Spirit",
                "description": "A translucent figure that seems to hum a sad tune.",
                "hostile": False,
                "type": "easter_egg",
                "dialogue": "Lost... so long lost... Have you seen the silver locket that shines like the moon?"
            },
            "territorial_boar": {
                "name": "Territorial Boar",
                "description": "A large, angry-looking boar, snorting and pawing the ground.",
                "hostile": True,
                "hp": 40, "max_hp": 40, "attack_power": 8, "loot": ["boar_tusk", "raw_meat"],
                "pre_combat_dialogue": "The boar glares at you, lets out a loud snort, and seems ready to charge.",
                "dialogue_options": {
                    "1": {"text": "Try to calm it down.", "action": "attempt_calm", "response": "You try to soothe the boar, but it only seems to enrage it further! It charges!" , "triggers_combat": True},
                    "2": {"text": "Slowly back away.", "action": "back_away", "response": "You slowly back away. The boar watches you intently but doesn't follow. You avoid a fight... for now.", "triggers_combat": False, "action_type": "end_conversation"},
                    "3": {"text": "Attack the boar!", "action": "initiate_combat", "response": "You ready your weapon and charge the boar!", "triggers_combat": True}
                }
            }
        }
    },
    "ancient_grove": {
        "name": "Ancient Grove",
        "zone": "WhisperingWoods",
        "description": "A serene grove with a very old, wise-looking tree at its center.",
        "exits": {"west": "whispering_woods_path"},
        "features": {
            "wise_old_tree": {
                "description": "A truly ancient tree. It seems to radiate a calm energy.",
                "actions": {
                    "touch": {"outcomes": [{"type": "message", "message": "You touch the ancient bark and feel a sense of peace wash over you."}]},
                    "rest": {"outcomes": [{"type": "stat_change", "stat": "hp", "amount": 10, "message": "You rest under the wise old tree and recover 10 HP."}]}
                }
            }
        },
        "npcs": {}
    },
    "generic_start_room": { # New generic starting location
        "name": "Dimly Lit Chamber",
        "zone": "StartingZone",
        "description": "This small, stone chamber is cold and damp. A faint light filters in from a crack in the ceiling. There's a worn wooden crate in one corner.",
        "exits": {"out": "eldoria_square"}, # Simplified exit for now
        "items": [],
        "features": {
            "worn_crate": {
                "description_closed": "A worn wooden crate. It seems easy to open.",
                "description_opened": "The crate is now open and empty.",
                "closed": True,
                "actions": { # Add actions for the crate
                    "open": { # Define an "open" action
                        "outcomes": [{"type": "reveal_items", "message": "You pry open the crate."}]
                    }
                },
                "contains_on_open": [] # Starter items will be placed here
            }
        },
        "npcs": {}
    }
}

BASE_ZONE_LAYOUTS_DATA = {
    "Eldoria": {
        "title": "Map of Eldoria",
        "grid": [ "           ", "  [M]----[S]", "   |      | ", "   +-----[G]", "           " ],
        "mapping": { 'M': "eldoria_market", 'S': "eldoria_square", 'G': "eldoria_south_gate" }
    },
    "Riverford": {
        "title": "Map of Riverford",
        "grid": [ "           ", "  [S]----[D]", "   |       ", "  [N]      ", "           " ],
        "mapping": { 'S': "riverford_square", 'D': "riverford_docks", 'N': "riverford_north_gate" }
    }
}

BASE_ITEMS_DATA = {
    "healing_potion": {"name": "Healing Potion", "type": "consumable", "effect": "heal", "amount": 20, "description": "A vial of swirling red liquid. Restores 20 HP."},
    "shiny_coin": {"name": "Shiny Coin", "type": "currency", "description": "A well-polished gold coin."},
    "apple": {"name": "Apple", "type": "food", "description": "A crisp red apple."},
    "bread_loaf": {"name": "Bread Loaf", "type": "food", "description": "A hearty loaf of bread."},
    "rusty_key": {"name": "Rusty Key", "type": "key_item", "description": "An old, rusty key."},
    "fishing_net_scraps": {"name": "Fishing Net Scraps", "type": "junk", "description": "Torn pieces of an old fishing net."},
    "golden_amulet": {"name": "Golden Amulet", "type": "treasure", "description": "A beautiful golden amulet."},
    "tattered_pelt": {"name": "Tattered Pelt", "type": "material", "description": "A worn piece of animal fur."},
    "grimy_coin": {"name": "Grimy Coin", "type": "currency", "description": "A dirty, old coin. Might be worth something."},
    "glowing_mushroom": {"name": "Glowing Mushroom", "type": "reagent", "description": "A mushroom that emits a soft, ethereal glow."},
    "lucky_charm_figurine": {"name": "Lucky Charm Figurine", "type": "quest_item", "description": "A small, intricately carved wooden figurine."},
    "scouts_map_fragment": {"name": "Scout's Map Fragment", "type": "quest_reward", "description": "A piece of a map, perhaps leading somewhere interesting."},
    "boar_tusk": {"name": "Boar Tusk", "type": "material", "description": "A sharp tusk from a wild boar."},
    "raw_meat": {"name": "Raw Meat", "type": "food_raw", "description": "A fresh slab of raw meat. Needs cooking."},
    "strange_berries": {"name": "Strange Berries", "type": "food_raw", "description": "Some unusual looking berries. Edible?"},
    "bandage": {
        "name": "Bandage",
        "description": "A simple cloth bandage. Heals a minor wound.", # type: consumable
        "type": "consumable",
        "effect": "heal",
        "amount": 10, "value": 5}, # Added value for consistency
    "leather_armor": {"name": "Leather Armor", "type": "armor", "equip_slot": "chest", "description": "Simple but effective leather armor."},
    "worn_staff": {"name": "Worn Staff", "type": "weapon", "equip_slot": "main_hand", "description": "An old wooden staff, good for channeling energies."},
    "simple_robes": {"name": "Simple Robes", "type": "armor", "equip_slot": "chest", "description": "Basic robes often worn by apprentices."},
    "pair_of_daggers": {"name": "Pair of Daggers", "type": "weapon", "equip_slot": "main_hand", "description": "A set of sharp, easily concealed daggers."},
    "shadowy_cloak": {"name": "Shadowy Cloak", "type": "armor", "equip_slot": "chest", "description": "A dark cloak that helps blend into the shadows."}, # Assuming chest for now, could be 'back'
    "city_map_eldoria": {"name": "Map of Eldoria", "type": "map", "description": "A crudely drawn map of Eldoria."},
    "small_pouch_of_coins": {"name": "Small Pouch of Coins", "type": "currency", "value": 10, "description": "A few coins to get you started."},
    "simple_knife": {"name": "Simple Knife", "type": "weapon", "equip_slot": "main_hand", "attack_power_bonus": 1, "description": "A basic utility knife. Better than nothing."},
    "blank_map_scroll": {"name": "Blank Map Scroll", "type": "map_scroll", "description": "A rolled-up piece of parchment. Perhaps you can view a map with this?"}
}

# --- Species and Class Data ---
BASE_SPECIES_DATA = {
    "human": {
        "name": "Human", "description": "Adaptable and versatile.",
        "stat_bonuses": {"hp_bonus": 5, "attack_bonus": 1},
        "starting_location_tag": "generic_start",
        "backstory_intro": "You awaken with a gasp, memories hazy, a sense of urgency pricking at you."
    },
    "elf": {
        "name": "Elf", "description": "Graceful and attuned to nature.",
        "stat_bonuses": {"attack_bonus": 2, "special_power_bonus": 5},
        "starting_location_tag": "forest_start",
        "backstory_intro": "Sunlight dapples through ancient leaves, stirring you from a deep slumber."
    },
    "orc": {
        "name": "Orc", "description": "Strong and resilient.",
        "stat_bonuses": {"hp_bonus": 10, "attack_bonus": 3},
        "starting_location_tag": "rugged_start",
        "backstory_intro": "The clang of distant metal and the smell of smoke rouse you. Your muscles ache."
    }
}

BASE_CLASSES_DATA = {
    "warrior": {
        "name": "Warrior", "description": "Masters of melee combat.",
        "base_stats": {"hp": 60, "attack_power": 12},
        "special_moves": {"power_strike": {"name": "Power Strike", "damage_multiplier": 1.5, "cooldown_max": 2, "description": "A strong attack that deals 1.5x damage."}},
        "starter_items": ["leather_armor", "small_pouch_of_coins"] # Removed simple_knife (given directly)
    },
    "mage": {
        "name": "Mage", "description": "Wielders of arcane energies.",
        "base_stats": {"hp": 40, "attack_power": 6, "special_power": 15},
        "special_moves": {"fireball": {"name": "Fireball", "damage": 20, "cooldown_max": 1, "description": "Hurls a flaming sphere."}},
        "starter_items": ["simple_robes", "small_pouch_of_coins"] # Removed worn_staff
    },
    "rogue": {
        "name": "Rogue", "description": "Agile and cunning.",
        "base_stats": {"hp": 50, "attack_power": 10},
        "special_moves": {"quick_strike": {"name": "Quick Strike", "damage_multiplier": 1.2, "cooldown_max": 0, "description": "A swift, less powerful attack."}},
        "starter_items": ["shadowy_cloak", "small_pouch_of_coins"] # Removed pair_of_daggers
    }
}

player = {
    "current_location_id": None,
    "inventory": [],
    "game_active": False,
    "hp": 0, 
    "max_hp": 0, 
    "attack_power": 0, 
    "special_power": 0,
    "name": "Adventurer", # Default name
    "gender": "Unspecified", # Default gender
    "species": None,
    "class": None,
    "special_moves": {},
    "special_cooldowns": {},
    "combat_target_id": None,
    "is_deflecting": False,
    "dialogue_npc_id": None,
    "dialogue_options_pending": {},
    "flags": {},
    "coins": 0, # Player's currency
    "level": 1, # Player's level
    "xp": 0, # Player's experience points
    "xp_to_next_level": 100, # XP needed for the next level
    "equipment": { # New dictionary for equipped items
        "head": None,
        "shoulders": None,
        "chest": None, # Was armor_body
        "hands": None,
        "legs": None,
        "feet": None,
        "main_hand": None, # Was weapon
        "off_hand": None

    },
    "is_paused": False # New flag for game pause state
}

PLAYER_LOGS_DIR = "player_data"
MAX_NAME_LENGTH = 20
CITY_ZONES = ["Eldoria", "Riverford"] # Zones considered as cities for saving
# Stricter pattern for humanoid names: only letters, spaces, hyphens, apostrophes.
ALLOWED_HUMANOID_NAME_PATTERN = re.compile(r"^[a-zA-Z '-]+$") 

STEPTRACKER_DIR = "steptracker"
STEPTRACKER_FILE = os.path.join(STEPTRACKER_DIR, "function_trace.log")

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

def load_all_game_data():
    """Loads all game data from their base structures or JSON files."""
    global locations, zone_layouts, items_data, species_data, classes_data
    
    # For now, we're using the in-script dictionaries.
    # If these were in JSON files, you'd load them here.
    # Example for JSON loading (if you move them to files later):
    # locations = load_json_data('locations.json', "Locations")
    # items_data = load_json_data('items_data.json', "Items")
    # ... and so on

    locations = BASE_LOCATIONS_DATA.copy() # Use .copy() if you might modify them in-memory later and want to preserve original
    zone_layouts = BASE_ZONE_LAYOUTS_DATA.copy()
    items_data = BASE_ITEMS_DATA.copy()
    species_data = BASE_SPECIES_DATA.copy()
    classes_data = BASE_CLASSES_DATA.copy()

    print("[Game Data] All game data reloaded.")

    # Post-load validation/checks (optional but recommended)
    if not locations:
        print("[ERROR] Locations data is empty after reload!")
    if not items_data:
        print("[ERROR] Items data is empty after reload!")
    # Add more checks as needed

# Initial load of game data when the script starts
load_all_game_data()


web_server_thread = None
flask_app_instance = None

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
    if os.path.exists(PLAYER_LOGS_DIR):
        for entry in os.listdir(PLAYER_LOGS_DIR):
            char_dir_path = os.path.join(PLAYER_LOGS_DIR, entry)
            if os.path.isdir(char_dir_path):
                # Try to read character_creation.json to get details
                char_file_path = os.path.join(char_dir_path, "character_creation.json")
                if os.path.exists(char_file_path):
                    try:
                        with open(char_file_path, 'r') as f:
                            data = json.load(f)
                            characters.append({
                                "display_name": data.get("name", entry.replace("_", " ")), # Use actual name if available
                                "class": classes_data.get(data.get("class"), {}).get("name", "Unknown"),
                                "species": species_data.get(data.get("species"), {}).get("name", "Unknown")
                            })
                    except Exception: # pylint: disable=broad-except
                        characters.append({"display_name": entry.replace("_", " "), "class": "N/A", "species": "N/A"}) # Fallback
    return characters


def sanitize_filename(name):
    """Sanitizes a string to be used as a filename/directory name."""
    name = name.strip().replace(" ", "_")
    name = re.sub(r'(?u)[^-\w.]', '', name) # Remove non-alphanumeric (excluding -, _, .)
    return name if name else "invalid_name"

def save_player_data(reason_for_save="Game state saved"):
    """Saves current player data to their character_creation.json file."""
    if not player.get("name"):
        print("[Error] Cannot save game: Player name not set.")
        return False # Indicate failure

    if not os.path.exists(PLAYER_LOGS_DIR):
        try:
            os.makedirs(PLAYER_LOGS_DIR)
        except OSError as e:
            print(f"[Error] Could not create player logs directory: {e}")
            return False

    player_name_sanitized = sanitize_filename(player.get("name")) # Name is validated before this point
    player_specific_dir = os.path.join(PLAYER_LOGS_DIR, player_name_sanitized)

    if not os.path.exists(player_specific_dir):
        try:
            os.makedirs(player_specific_dir)
        except OSError as e:
            print(f"[Error] Could not create directory for player '{player.get('name')}': {e}")
            return False

    # Always save to the canonical save file name that load_character_data uses.
    save_file_path = os.path.join(player_specific_dir, "character_creation.json")
    try:
        with open(save_file_path, 'w') as f:
            json.dump(player, f, indent=4)
        print(f"[Save] {reason_for_save}. Player data for '{player.get('name')}' saved to {save_file_path}")
        return True # Indicate success
    except Exception as e:
        print(f"[Error] Failed to save player data for '{player.get('name')}': {e}")
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
                loaded_data = json.load(f)
            player = loaded_data # Replace global player dict
            player["game_active"] = True # Ensure game is marked active
            print(f"\nCharacter '{player.get('name')}' loaded successfully.")
            return True
        except Exception as e:
            print(f"Error loading character data for '{character_display_name}': {e}")
            return False
    print(f"No save data found for character '{character_display_name}'.")
    return False

def log_game_event(event_type, data_dict):
    """Logs a specific game event to a character's event log file."""
    if not player.get("name") or not player.get("game_active"): # Don't log if no active character or game
        return

    player_name_sanitized = sanitize_filename(player.get("name", "unknown_player_event_log"))
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

    try:
        with open(log_file_path, 'a') as f: # Append mode
            json.dump(log_entry, f)
            f.write('\n') # Newline for JSON Lines
    except Exception as e:
        print(f"[Error] Failed to write to event log {log_file_path}: {e}")

def _apply_character_choices_and_stats(species_id, class_id, char_name, char_gender):
    """Applies chosen character details and stats to the player object."""
    player["species"] = species_id
    player["class"] = class_id
    player["name"] = char_name
    player["gender"] = char_gender

    class_info = classes_data[class_id]
    species_info = species_data[species_id]
    
    class_stats = class_info["base_stats"]
    species_bonuses = species_info["stat_bonuses"]

    player["max_hp"] = class_stats["hp"] + species_bonuses.get("hp_bonus", 0)
    player["hp"] = player["max_hp"]
    player["attack_power"] = class_stats["attack_power"] + species_bonuses.get("attack_bonus", 0)
    player["special_power"] = class_stats.get("special_power", 0) + species_bonuses.get("special_power_bonus", 0)
    player["special_moves"] = dict(class_info.get("special_moves", {})) 
    player["special_cooldowns"] = {move_id: 0 for move_id in player["special_moves"]}    
    # Give basic starting items directly after character creation
    player["inventory"] = ["simple_knife", "blank_map_scroll"] 
    player["coins"] = 0 # Initialize coins
    player["level"] = 1 # Initialize level
    player["xp"] = 0
    player["xp_to_next_level"] = 100 # Initial XP for level 2
    player["equipment"] = { # Initialize equipment for new character
        "head": None,
        "shoulders": None,
        "chest": None,
        "hands": None,
        "legs": None,
        "feet": None,
        "main_hand": None,
        "off_hand": None
    }
    player["flags"] = {} # Reset flags for a new character

    print(f"\nCharacter '{player['name']}' ({player['gender']} {species_info['name']} {class_info['name']}) created!")
    # Save the initial state of the newly created character.
    save_player_data(reason_for_save=f"Character '{player['name']}' created and initial state saved")
    return True


def initialize_game_state():
    """Guides through new character creation and sets up initial game state."""
    # For terminal play, get choices first
    species_id, class_id, char_name, char_gender = _get_terminal_character_choices()
    if not _apply_character_choices_and_stats(species_id, class_id, char_name, char_gender):
        player["game_active"] = False
        print("Character creation cancelled. Game not started.")
        # No return here, _apply_character_choices_and_stats returns bool but doesn't stop execution
        return

    player["game_active"] = True
    player["combat_target_id"] = None
    player["dialogue_npc_id"] = None
    player["dialogue_options_pending"] = {}
    player["flags"]["found_starter_items"] = False 
    
    species_info = species_data[player["species"]]
    print(f"\n{species_info['backstory_intro']}")

    start_room_id = "generic_start_room" 
    player["current_location_id"] = start_room_id
    class_info = classes_data[player["class"]]
    if start_room_id in locations and "worn_crate" in locations[start_room_id].get("features", {}):
        locations[start_room_id]["features"]["worn_crate"]["contains_on_open"] = list(class_info["starter_items"])
        locations[start_room_id]["features"]["worn_crate"]["closed"] = True 
    
    print(f"You feel a pull towards the {locations[start_room_id]['name']}.")

def start_combat(npc_id):
    player["combat_target_id"] = npc_id
    current_loc_npcs = locations[player["current_location_id"]].get("npcs", {})
    if npc_id not in current_loc_npcs or not current_loc_npcs[npc_id].get("hp"):
        return
    npc_data = current_loc_npcs[npc_id]
    print(f"\n--- COMBAT START ---")
    print(f"You are attacked by {npc_data['name']}!")

def handle_player_defeat():
    print("\nYour vision fades... You have been defeated.")
    print("--- GAME OVER ---")
    player["game_active"] = False
    player["dialogue_npc_id"] = None
    player["dialogue_options_pending"] = {}
    player["combat_target_id"] = None

def award_xp(amount):
    """Awards XP to the player and checks for level up."""
    if not player["game_active"]:
        return

    player["xp"] += amount
    print(f"You gained {amount} XP.")
    log_game_event("xp_gained", {"amount": amount, "current_xp": player["xp"], "level": player["level"]})

    while player["xp"] >= player["xp_to_next_level"]:
        player["level"] += 1
        player["xp"] -= player["xp_to_next_level"] # Subtract XP used for this level
        # Increase XP needed for the *next* level (e.g., 50% more than previous)
        player["xp_to_next_level"] = int(player["xp_to_next_level"] * 1.5) 
        
        # Apply level-up bonuses (example)
        player["max_hp"] += 10
        player["hp"] = player["max_hp"] # Full heal on level up
        player["attack_power"] += 2

        print(f"\n*** LEVEL UP! You are now Level {player['level']}! ***")
        print(f"Max HP increased to {player['max_hp']}. Attack Power increased to {player['attack_power']}.")
        print(f"XP to next level: {player['xp_to_next_level']}. Current XP: {player['xp']}.")
        log_game_event("level_up", {"new_level": player["level"], "max_hp": player["max_hp"], "attack_power": player["attack_power"]})

def handle_npc_defeat(npc_id):
    current_loc_data = locations[player["current_location_id"]]
    npc_data = current_loc_data["npcs"][npc_id]
    print(f"\n{npc_data['name']} has been defeated!")
    
    loot_item_ids = npc_data.get("loot", [])
    if loot_item_ids:
        dropped_items_details = []
        for item_id in loot_item_ids:
            item_detail = {"id": item_id, "name": items_data.get(item_id, {}).get("name", item_id)}
            if items_data.get(item_id, {}).get("type") == "currency" and "value" in items_data.get(item_id, {}):
                item_detail["value"] = items_data.get(item_id, {}).get("value")
            dropped_items_details.append(item_detail)
        log_game_event("npc_loot_dropped", {
            "npc_id": npc_id, "npc_name": npc_data.get("name"), "dropped_items": dropped_items_details,
            "location_id": player.get("current_location_id")
        })
        for item_id in npc_data["loot"]:
            current_loc_data.setdefault("items", []).append(item_id)
            print(f"{npc_data['name']} dropped a {items_data.get(item_id, {}).get('name', item_id)}!")
    
    # Award XP for defeating NPC
    xp_reward = npc_data.get("xp_reward", 25) # Default XP or define in NPC data
    award_xp(xp_reward)

    del current_loc_data["npcs"][npc_id]
    player["combat_target_id"] = None 
    player["dialogue_npc_id"] = None 
    player["dialogue_options_pending"] = {}

def npc_combat_turn():
    if not player["combat_target_id"] or not player["game_active"]:
        return

    npc_id = player["combat_target_id"]
    current_loc_data = locations[player["current_location_id"]]
    
    if npc_id not in current_loc_data["npcs"]:
        return 

    npc_data = current_loc_data["npcs"][npc_id]

    if npc_data["hp"] <= 0: 
        return

    print(f"\n{npc_data['name']}'s turn...")
    damage_to_player = npc_data["attack_power"]
    
    if player["is_deflecting"]:
        damage_to_player = max(0, damage_to_player // 2) 
        print(f"You deflect part of the blow!")
        player["is_deflecting"] = False 

    player["hp"] -= damage_to_player
    print(f"{npc_data['name']} attacks you for {damage_to_player} damage.")
    print(f"You have {player['hp']}/{player['max_hp']} HP remaining.")

    if player["hp"] <= 0:
        handle_player_defeat()
    
    for move in player["special_cooldowns"]:
        if player["special_cooldowns"][move] > 0:
            player["special_cooldowns"][move] -= 1

@trace_function_calls
def award_item_to_player(item_id_to_give, source="unknown"):
    if not isinstance(item_id_to_give, str):
        error_msg = "[Error] Invalid item_id provided to award_item_to_player."
        print(error_msg)
        return error_msg # Return error message
    player["inventory"].append(item_id_to_give)
    item_details = items_data.get(item_id_to_give, {})
    display_name = item_details.get("name", item_id_to_give.replace("_", " ").capitalize())
    success_msg = f"You have acquired: {display_name}."
    print(success_msg)
    log_game_event("item_acquisition", {
        "item_id": item_id_to_give, "item_name": display_name, "source": source,
        "location_id": player.get("current_location_id")
    })
    return success_msg # Return success message

@trace_function_calls
def remove_item_from_player_inventory(item_id_to_remove, source="unknown"):
    """Removes an item from the player's inventory and logs the event."""
    if item_id_to_remove in player["inventory"]:
        player["inventory"].remove(item_id_to_remove)
        item_details = items_data.get(item_id_to_remove, {})
        display_name = item_details.get("name", item_id_to_remove.replace("_", " ").capitalize())
        log_game_event("item_removal", {
            "item_id": item_id_to_remove,
            "item_name": display_name,
            "source": source,
            "location_id": player.get("current_location_id")
        })
        # print(f"You no longer have: {display_name}.") # Optional: print removal message
        return True
    # print(f"[Warning] Tried to remove item '{item_id_to_remove}' but it was not in inventory.")
    return False

@trace_function_calls
def handle_environmental_interaction(feature_id, action_verb):
    loc_data = locations[player["current_location_id"]]
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
        award_item_to_player(chosen_outcome["item_id"], source=f"feature_interaction_{feature_id}_{action_verb}")
    elif chosen_outcome.get("type") == "reveal_items" and feature_id == "worn_crate":
        if feature.get("closed"):
            items_in_crate = list(feature.get("contains_on_open", [])) # Make a copy
            if items_in_crate:
                print("You pry open the crate and find some items inside!") # Updated message
                
                acquired_item_names = []
                for item_id in items_in_crate: # Iterate through items to award them
                    award_item_to_player(item_id, source=f"opened_{feature_id}")
                    acquired_item_names.append(items_data.get(item_id, {}).get("name", item_id))
                
                if player["current_location_id"] == "generic_start_room": # Specific message for starter crate
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
                    "location_id": player["current_location_id"]
                })
            feature["contains_on_open"] = [] # Empty the crate's internal list
            feature["closed"] = False
            player["flags"]["found_starter_items"] = True # Still set this flag
    elif chosen_outcome.get("type") == "stat_change" and chosen_outcome.get("stat") == "hp":
        player["hp"] = min(player["max_hp"], player["hp"] + chosen_outcome.get("amount", 0))
        print(f"Your HP is now {player['hp']}/{player['max_hp']}.")

def run_minimal_web_server():
    global flask_app_instance
    if not flask_available:
        return

    flask_app_instance = Flask(__name__)

    @flask_app_instance.route('/')
    def web_index():
        html_content_template = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Text RPG - Browser Version</title>
            <style> # pragma: no cover
                body { font-family: sans-serif; margin: 20px; background-color: #f0f0f0; color: #333; }
                .container { background-color: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
                h1 { color: #5a5a5a; }
                .equip-slot {
                    border: 1px solid #b0b0b0;
                    padding: 8px;
                    text-align: center;
                    background-color: #e9e9e9;
                    min-height: 20px; /* Ensure a minimum height */
                }
                /* Disable text selection */
                body {
                    user-select: none; /* Standard */
                    -webkit-user-select: none; /* Safari */
                }
                #settings-button-container { position: fixed; top: 10px; right: 10px; z-index: 1001;}
                .inventory-slot {
                    border: 1px solid #ccc;
                    padding: 8px;
                    text-align: center;
                    background-color: #f0f0f0;
                    min-height: 50px; /* Adjust as needed */
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    word-break: break-word; /* For longer item names */
                }
                #settings-gear-button { font-size: 24px; background: none; border: none; cursor: pointer; padding: 5px;}
                .actions-panel { margin-bottom: 15px; }
                .actions-panel button { margin-right: 5px; margin-bottom: 5px; }
                .dynamic-options button { display: block; margin-bottom: 5px; }
                .output-area { border: 1px solid #ccc; padding: 10px; height: 300px; overflow-y: scroll; background-color: #f9f9f9; margin-bottom: 10px; }
                button { padding: 10px 15px; background-color: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
                button:hover { background-color: #0056b3; }
                #pause-overlay {
                    position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                    background-color: rgba(0,0,0,0.7); color: white;
                    display: none; /* Hidden by default */
                    justify-content: center; align-items: center;
                    font-size: 3em; font-weight: bold;
                    z-index: 2000; /* Above everything else */
                }
                .modal-menu-button { margin: 5px; } /* Style for buttons in our custom modal */
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Text RPG - Browser Version</h1>
                <div id="character-creation-area">
                    <!-- Content will be dynamically loaded here -->
                </div>
                <div id="settings-button-container" style="display: none;">
                    <button id="settings-gear-button">⚙️</button>
                </div>
                <div id="game-interface" style="display: none;"> <!-- Initially hidden -->
                    <div id="dynamic-header-info" style="padding: 5px; margin-bottom: 5px; border: 1px solid #ccc; font-weight: bold; background-color: #e9ecef;">
                        <!-- Dynamic header will be populated here by JS -->
                    </div>
                    <div id="main-game-content-area" style="display: flex; margin-bottom: 10px;">
                        <div id="character-panel" style="width: 250px; border: 1px solid #ccc; padding: 10px; background-color: #f9f9f9; height: 322px; /* Match output-area height */ overflow-y: auto; margin-right: 10px;">
                            <h4 style="margin-top: 0; margin-bottom: 10px; border-bottom: 1px solid #ccc; padding-bottom: 5px;">Character</h4>
                            <div id="char-panel-stats" style="margin-bottom: 15px;">
                                <div id="char-panel-name">Name: N/A</div>
                                <div id="char-panel-class">Class: N/A</div>
                                <div id="char-panel-species">Species: N/A</div>
                                <div id="char-panel-level">Level: N/A</div>
                                <div id="char-panel-xp">XP: N/A / N/A</div>
                                <div id="char-panel-hp">HP: N/A / N/A</div>
                                <div id="char-panel-attack">Attack: N/A</div>
                                <div id="char-panel-coins">Coins: N/A</div>
                            </div>
                            <h5 style="margin-bottom: 5px; margin-top: 0; border-bottom: 1px solid #ddd; padding-bottom: 3px;">Equipment</h5>
                            <div id="char-panel-equipment-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 5px; font-size: 0.9em;">
                                <div id="char-panel-equip-head" class="equip-slot" title="Head" data-slot-key="head">H: Empty</div>
                                <div id="char-panel-equip-shoulders" class="equip-slot" title="Shoulders" data-slot-key="shoulders">S: Empty</div>
                                <div id="char-panel-equip-chest" class="equip-slot" title="Chest" data-slot-key="chest">C: Empty</div>
                                <div id="char-panel-equip-hands" class="equip-slot" title="Hands" data-slot-key="hands">G: Empty</div>
                                <div id="char-panel-equip-legs" class="equip-slot" title="Legs" data-slot-key="legs">L: Empty</div>
                                <div id="char-panel-equip-feet" class="equip-slot" title="Feet" data-slot-key="feet">F: Empty</div>
                                <div id="char-panel-equip-main_hand" class="equip-slot" title="Main Hand" data-slot-key="main_hand">MH: Empty</div>
                                <div id="char-panel-equip-off_hand" class="equip-slot" title="Off-Hand" data-slot-key="off_hand">OH: Empty</div>
                            </div>

                        </div>
                        <div id="game-output" class="output-area" style="flex-grow: 1;">
                            <!-- Game messages will appear here -->
                        </div>
                    </div>
                    <div class="actions-panel">
                        <p><strong>Common Actions:</strong></p>
                        <button onclick="performAction('inventory')">Check Inventory</button>
                        <button onclick="performAction('!map')">View Map</button>
                    </div>
                    <div id="game-actions-panel" class="actions-panel" style="display: none;">
                        <p><strong>Game Actions:</strong></p>
                        <!-- Save button will go here -->
                    </div>
                    <div class="actions-panel">
                        <p><strong>Movement:</strong> (Would show available directions)</p>
                        <button onclick="performAction('go north')">Go North</button>
                        <button onclick="performAction('go south')">Go South</button>
                        <button onclick="performAction('go east')">Go East</button>
                        <button onclick="performAction('go west')">Go West</button>
                    </div>
                    <div class="actions-panel dynamic-options">
                        <p><strong>Interactions:</strong> (Would show available items/NPCs/features)</p>
                        <!-- "Search Feature" button removed as it's handled by the dynamic feature-interactions-panel -->
                        <!-- Consider if "Talk to NPC" and "Use Item On..." are still needed as placeholders -->
                        <button onclick="performAction('talk <npc_example>')">Talk to NPC</button>
                        <button onclick="performAction('use <item> on <feature>')">Use Item On...</button>
                    </div>
                    <p><small>Click actions to interact with the game. Some actions are more fully implemented than others in this browser view.</small></p>
                </div>
                <div id="feature-interactions-panel" class="actions-panel" style="display: none;">
                    <p><strong>Room Features:</strong></p>
                    <!-- Dynamic feature buttons will go here -->
                </div>
                <div id="room-items-panel" class="actions-panel" style="display: none;">
                    <p><strong>Items on the ground:</strong></p>
                    <div><!-- Dynamic item buttons will go here --></div>
                </div>
                <div id="pause-overlay">PAUSED</div>
            </div>
            <script>
                let creationStep = 'species'; // 'species', 'class', 'name_gender', 'done'
                let chosenSpecies = null;
                let chosenClass = null;
                let gameIsPaused = false;
                let gameIsActiveForInput = false; // True when game interface is shown
                const SESSION_STORAGE_GAME_ACTIVE_KEY = 'textRpgGameSessionActive';
                const SESSION_STORAGE_CHAR_NAME_KEY = 'textRpgCharacterName';

                 // Centralized pause/resume logic
                function togglePauseGame() {
                    // If modal is visible and related to pause, this call is to resume.
                    // Otherwise, this call is to pause.
                    if (gameIsPaused && document.getElementById('custom-modal-overlay') && document.getElementById('custom-modal-overlay').querySelector('h3').textContent === "Game Paused") {
                        // Resuming game
                        gameIsPaused = false;
                        console.log("Game Resumed");
                        closeModal();
                    } else if (!gameIsPaused && gameIsActiveForInput) {
                        // Pausing game
                        gameIsPaused = true;
                        console.log("Game Paused");
                        showMenuModal("Game Paused", "The game is currently paused.", [
                            {text: "Resume Game (P)", action: togglePauseGame } // Clicking Resume calls this again
                        ]);
                    }
                }

                // Simple Modal Logic
                
                function showMenuModal(title, message, buttonsConfig) {
                    closeModal(); // Close any existing modal first
                    let buttonsHTML = '';
                    if (buttonsConfig && buttonsConfig.length > 0) {
                        buttonsHTML = buttonsConfig.map((btn, index) => `<button class="modal-menu-button" id="modal-btn-${index}">${btn.text}</button>`).join(' ');
                    }

                    const modalHTML = `
                        <div id="custom-modal-overlay" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5); display: flex; justify-content: center; align-items: center; z-index: 1000;">
                            <div id="custom-modal-content" style="background-color: white; padding: 20px; border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.25); text-align: center;">
                                <h3>${title}</h3>
                                <p>${message}</p>
                                <div>${buttonsHTML}</div>
                            </div>
                        </div>`;
                    document.body.insertAdjacentHTML('beforeend', modalHTML);
                    if (buttonsConfig && buttonsConfig.length > 0) {
                        buttonsConfig.forEach((btn, index) => {
                            document.getElementById(`modal-btn-${index}`).onclick = () => { btn.action(); closeModal(); };
                        });
                    }
                }
                function closeModal() {
                    const modalOverlay = document.getElementById('custom-modal-overlay');
                    if (modalOverlay) modalOverlay.remove();
                }

                async function showInitialCharacterScreen() {
                    console.trace("showInitialCharacterScreen called");
                    console.log("showInitialCharacterScreen called.");
                    const creationArea = document.getElementById('character-creation-area');
                    if (!creationArea) {
                        console.error("CRITICAL ERROR: The 'character-creation-area' DIV was not found in the HTML. Cannot proceed with character screen.");
                        return;
                    }
                    creationArea.innerHTML = '<h2>Load Character or Create New:</h2><div id="character-options-buttons" class="dynamic-options"><p>Loading character list...</p></div>';
                    const charOptionsDiv = document.getElementById('character-options-buttons');
                    if (!charOptionsDiv) {
                        console.error("CRITICAL ERROR: The 'character-options-buttons' DIV was not found after setting innerHTML for creationArea. Cannot display character options.");
                        return;
                    }

                    try {
                        const response = await fetch('/api/get_characters'); // This is the API call
                        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                        const characters = await response.json();
                        
                        charOptionsDiv.innerHTML = ''; // Clear loading message

                        if (characters.length > 0) {
                            characters.forEach(charData => {
                                const charEntryDiv = document.createElement('div');
                                // Styling for the div that holds load and delete buttons for a character
                                charEntryDiv.style.display = 'flex'; // Use flexbox for alignment
                                charEntryDiv.style.alignItems = 'center'; // Vertically align items in the center
                                charEntryDiv.style.marginBottom = '8px'; // Space between character entries
                                charEntryDiv.style.padding = '8px';
                                charEntryDiv.style.border = '1px solid #ddd';
                                charEntryDiv.style.borderRadius = '4px';
                                const button = document.createElement('button');
                                button.textContent = `${charData.display_name} ( ${charData.species} ${charData.class} )`;
                                button.onclick = () => handleLoadCharacter(charData.display_name);
                                charEntryDiv.appendChild(button);

                                const deleteButton = document.createElement('button');
                                deleteButton.textContent = 'X';
                                deleteButton.style.backgroundColor = 'red';
                                deleteButton.style.color = 'white';
                                deleteButton.style.marginLeft = '10px'; // Add a small space to the left of the delete button
                                deleteButton.style.padding = '5px 8px'; // Make it a bit smaller
                                deleteButton.onclick = () => confirmDeleteCharacter(charData.display_name);
                                charEntryDiv.appendChild(deleteButton);
                                charOptionsDiv.appendChild(charEntryDiv);
                            });
                        }

                        const newCharButton = document.createElement('button');
                        newCharButton.textContent = "Create New Character";
                        newCharButton.onclick = () => loadSpecies(); // Start new character creation flow
                        charOptionsDiv.appendChild(newCharButton);

                    } catch (error) {
                        console.error("Error occurred in showInitialCharacterScreen while fetching or processing characters:", error);
                        if (charOptionsDiv) { // Ensure charOptionsDiv was found before trying to modify it
                            charOptionsDiv.innerHTML = `<p>Error loading character list: ${error.message || error}. <button onclick="loadSpecies()">Create New Character</button></p>`;
                        } else {
                            creationArea.innerHTML = `<h2>Error Displaying Character List</h2><p>A problem occurred. Please check the browser console for details. You can try to <button onclick="loadSpecies()">Create New Character</button>.</p>`;
                        }
                    }
                    creationArea.style.display = 'block'; // Ensure it's visible
                    document.getElementById('game-interface').style.display = 'none'; // Ensure game interface is hidden
                    document.getElementById('settings-button-container').style.display = 'none';
                    document.getElementById('feature-interactions-panel').style.display = 'none'; // Explicitly hide
                    document.getElementById('room-items-panel').style.display = 'none'; // Explicitly hide
                    sessionStorage.removeItem(SESSION_STORAGE_GAME_ACTIVE_KEY);
                    sessionStorage.removeItem(SESSION_STORAGE_CHAR_NAME_KEY);
                    gameIsActiveForInput = false;
                }

                async function loadSpecies() {
                    console.trace("loadSpecies called");
                    const creationArea = document.getElementById('character-creation-area');
                    creationArea.innerHTML = '<h2>Choose your Species:</h2><div id="species-options-buttons" class="dynamic-options"><p>Loading species...</p></div>';
                    const speciesOptionsDiv = document.getElementById('species-options-buttons');
                    try {
                        const response = await fetch('/get_species');
                        console.log("Fetched species response:", response);
                        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                        const speciesList = await response.json();
                        
                        speciesOptionsDiv.innerHTML = ''; // Clear loading message
                        speciesList.forEach(species => {
                            const button = document.createElement('button');
                            button.textContent = `${species.name} - ${species.description}`;
                            console.log("Creating button for species:", species.id);
                            button.onclick = () => selectSpecies(species.id);
                            speciesOptionsDiv.appendChild(button);
                        });
                    } catch (error) {
                        speciesOptionsDiv.innerHTML = `<p>Error loading species: ${error}</p>`;
                    }
                }

                async function selectSpecies(speciesId) {
                    console.trace("selectSpecies called with ID:", speciesId);
                    console.log("selectSpecies called with ID:", speciesId);
                    chosenSpecies = speciesId;
                    creationStep = 'class';
                    console.log("creationStep set to 'class', chosenSpecies:", chosenSpecies);
                    await loadClasses();
                }

                async function loadClasses() {
                    console.trace("loadClasses called");
                    console.log("loadClasses called. Fetching classes...");
                    const creationArea = document.getElementById('character-creation-area');
                    creationArea.innerHTML = `<h2>Choose your Class:</h2><div id="class-options-buttons" class="dynamic-options"><p>Loading classes...</p></div>`;
                    const classOptionsDiv = document.getElementById('class-options-buttons');
                    try {
                        const response = await fetch('/get_classes'); // Add ?species_id=${chosenSpecies} if classes are species-dependent
                        console.log("Fetched classes response:", response);
                        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                        const classList = await response.json();
                        
                        classOptionsDiv.innerHTML = '';
                        classList.forEach(cls => {
                            const button = document.createElement('button');
                            button.textContent = `${cls.name} - ${cls.description}`;
                            console.log("Creating button for class:", cls.id);
                            button.onclick = () => selectClass(cls.id);
                            classOptionsDiv.appendChild(button);
                        });
                    } catch (error) {
                        classOptionsDiv.innerHTML = `<p>Error loading classes: ${error}</p>`;
                    }
                }

                function selectClass(classId) {
                    console.trace("selectClass called with ID:", classId);
                    console.log("selectClass called with ID:", classId);
                    chosenClass = classId;
                    creationStep = 'name_gender';
                    console.log("creationStep set to 'name_gender', chosenClass:", chosenClass);
                    loadNameGenderForm();
                }
                function loadNameGenderForm() {
                    console.trace("loadNameGenderForm called");
                    console.log("loadNameGenderForm called.");
                    const creationArea = document.getElementById('character-creation-area');
                    creationArea.innerHTML = `
                        <h2>Enter Name and Choose Gender:</h2>
                        <div>
                            <label for="charName">Name:</label>
                            <input type="text" id="charName" name="charName" required maxlength="__MAX_NAME_LENGTH_PLACEHOLDER__">
                        </div>
                        <div style="margin-top: 10px;">
                            <label>Gender:</label><br>
                            <input type="radio" id="genderMale" name="charGender" value="Male" checked> <label for="genderMale">Male</label><br>
                            <input type="radio" id="genderFemale" name="charGender" value="Female"> <label for="genderFemale">Female</label><br>
                        </div>
                        <button onclick="submitCharacterCreation()" style="margin-top: 15px;">Start Adventure</button>
                    `;
                    // Add event listener for real-time name input filtering
                    const charNameInput = document.getElementById('charName');
                    if (charNameInput) {
                        charNameInput.addEventListener('input', function(event) {
                            const allowedPattern = /^[a-zA-Z '-]*$/; // JavaScript equivalent of your Python regex
                            let value = event.target.value;
                            let filteredValue = value.split('').filter(char => allowedPattern.test(char)).join('');
                            event.target.value = filteredValue;
                            // Note: The maxlength attribute is handled directly in the HTML input tag.
                        });
                    }
                }

                async function submitCharacterCreation() {
                    console.trace("submitCharacterCreation called");
                    const charNameInput = document.getElementById('charName');
                    const charName = charNameInput.value.trim();
                    if (!charName) {
                        alert("Please enter a name for your character.");
                        charNameInput.focus();
                        return;
                    }
                    if (charName.match(/^\d+$/)) { // Check if name is purely numeric
                        alert("Name cannot be purely numeric. Please try again.");
                        charNameInput.focus();
                        return;
                    }
                    const chosenGender = document.querySelector('input[name="charGender"]:checked').value;

                    console.log("Submitting Character:", chosenSpecies, chosenClass, charName, chosenGender);

                    const creationArea = document.getElementById('character-creation-area');
                    const gameInterface = document.getElementById('game-interface');
                    const outputElement = document.getElementById('game-output');
                    outputElement.innerHTML = '<p>Creating character on server...</p>';

                    try {
                        const response = await fetch('/api/create_character', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                species_id: chosenSpecies,
                                class_id: chosenClass,
                                player_name: charName,
                                player_gender: chosenGender
                            })
                        });
                        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                        const initialSceneData = await response.json();

                        creationArea.style.display = 'none';
                        gameInterface.style.display = 'block';
                        outputElement.innerHTML = ''; // Clear "creating character" message
                        displaySceneData(initialSceneData, "Character created! Your adventure begins.");
                        document.getElementById('settings-button-container').style.display = 'block';
                        sessionStorage.setItem(SESSION_STORAGE_GAME_ACTIVE_KEY, 'true');
                        sessionStorage.setItem(SESSION_STORAGE_CHAR_NAME_KEY, charName);
                        gameIsActiveForInput = true;

                    } catch (error) {
                        outputElement.innerHTML = `<p>Error creating character: ${error}</p>`;
                    }
                }

                function confirmDeleteCharacter(characterName) {
                    console.trace("confirmDeleteCharacter called for:", characterName);
                    showMenuModal(
                        'Confirm Deletion',
                        `This operation is permanent for character '${characterName}', proceed cautiously.`,
                        [{text: "Do it", action: () => executeDeleteCharacter(characterName)}, {text: "Cancel", action: () => {}}]
                    );
                }

                async function executeDeleteCharacter(characterName) {
                    console.trace("executeDeleteCharacter called for:", characterName);
                    console.log("executeDeleteCharacter called for:", characterName);
                    try {
                        const response = await fetch('/api/delete_character', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ character_name: characterName })
                        });
                        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                        await showInitialCharacterScreen(); // Refresh the list
                    } catch (error) {
                        alert(`Error deleting character ${characterName}: ${error}`); // Simple alert for error
                    }
                }

                async function handleLoadCharacter(characterName) {
                    console.trace("handleLoadCharacter called for:", characterName);
                    console.log("handleLoadCharacter called for:", characterName);
                    const creationArea = document.getElementById('character-creation-area');
                    const gameInterface = document.getElementById('game-interface');
                    const outputElement = document.getElementById('game-output');
                    outputElement.innerHTML = `<p>Loading character: ${characterName}...</p>`;

                    try {
                        const response = await fetch('/api/load_character', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ character_name: characterName })
                        });
                        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                        const loadedSceneData = await response.json();

                        creationArea.style.display = 'none';
                        gameInterface.style.display = 'block';
                        outputElement.innerHTML = ''; 
                        displaySceneData(loadedSceneData, `Loaded character: ${characterName}.`);
                        document.getElementById('settings-button-container').style.display = 'block';
                        sessionStorage.setItem(SESSION_STORAGE_GAME_ACTIVE_KEY, 'true');
                        sessionStorage.setItem(SESSION_STORAGE_CHAR_NAME_KEY, characterName);
                        gameIsActiveForInput = true;
                    } catch (error) {
                        outputElement.innerHTML = `<p>Error loading character ${characterName}: ${error}</p>`;
                    }
                }
                function goToMainMenu() {
                    console.trace("goToMainMenu called");
                    closeModal(); // Close any open modal like settings or pause
                    sessionStorage.removeItem(SESSION_STORAGE_GAME_ACTIVE_KEY);
                    sessionStorage.removeItem(SESSION_STORAGE_CHAR_NAME_KEY);
                    // Optionally, tell the server to clear the active player state if necessary (e.g., via an API call)
                    showInitialCharacterScreen();
                }
                async function attemptResumeSession(characterName) {
                    console.log("Attempting to resume session for:", characterName);
                    const creationArea = document.getElementById('character-creation-area');
                    const gameInterface = document.getElementById('game-interface');
                    const outputElement = document.getElementById('game-output');
                    outputElement.innerHTML = `<p>Resuming session for ${characterName}...</p>`;

                    try {
                        const response = await fetch('/api/resume_session', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ character_name: characterName })
                        });
                        if (!response.ok) {
                            // If resume fails (e.g. server restarted and lost in-memory state, or char name mismatch)
                            // fall back to full load.
                            console.warn(`Resume session failed with status ${response.status}. Attempting full load.`);
                            throw new Error(`Resume failed, try full load.`);
                        }
                        const resumedSceneData = await response.json();

                        creationArea.style.display = 'none';
                        gameInterface.style.display = 'block';
                        outputElement.innerHTML = ''; 
                        displaySceneData(resumedSceneData, `Session resumed for ${characterName}.`);
                        document.getElementById('settings-button-container').style.display = 'block';
                        sessionStorage.setItem(SESSION_STORAGE_GAME_ACTIVE_KEY, 'true'); // Re-affirm session
                        sessionStorage.setItem(SESSION_STORAGE_CHAR_NAME_KEY, characterName); // Re-affirm character
                        gameIsActiveForInput = true;
                    } catch (error) {
                        console.error("Error resuming session directly, trying full load:", error);
                        // Fallback to full load if direct resume fails
                        // This ensures that if the server restarted, we still try to load from file.
                        await handleLoadCharacter(characterName);
                    }
                }

                async function performAction(actionString) { 
                    console.trace("performAction called with action:", actionString);
                    if (gameIsPaused) {
                        console.log("Game is paused. Action not sent.");
                        // Optionally display a message in the game output
                        // const outputElement = document.getElementById('game-output');
                        // outputElement.innerHTML += "<p>Game is paused. Press 'P' to resume.</p>";
                        // outputElement.scrollTop = outputElement.scrollHeight;
                        return;
                    }
                    const outputElement = document.getElementById('game-output');
                    
                    const p_attempt = document.createElement('p');
                    p_attempt.textContent = "Attempting action: " + actionString;
                    outputElement.appendChild(p_attempt);
                    
                    try {
                        const serverResponse = await fetch('/process_game_action', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json', },
                            body: JSON.stringify({ action: actionString }),
                        });
                        if (!serverResponse.ok) throw new Error(`HTTP error! status: ${serverResponse.status}`);
                        const data = await serverResponse.json();
                        displaySceneData(data, actionString); // Use a helper to display
                    } catch (error) {
                        const p_error = document.createElement('p');
                        p_error.textContent = "Error: " + error; 
                        outputElement.appendChild(p_error);
                    }
                    outputElement.scrollTop = outputElement.scrollHeight;
                }

                function displaySceneData(data, actionStringEcho = null) {
                    console.trace("displaySceneData called");
                    console.log("Data received by displaySceneData:", JSON.parse(JSON.stringify(data))); // Log the data object
                    const outputElement = document.getElementById('game-output');

                    // --- Inventory Modal Handling ---
                    if (actionStringEcho === 'inventory') {
                        let inventoryContent = "<p>Your inventory is empty.</p>"; // Default message for modal
                        if (data.inventory_list && data.inventory_list.length > 0) {
                            inventoryContent = '<div style="display: grid; grid-template-columns: repeat(8, 1fr); grid-auto-rows: minmax(60px, auto); gap: 5px; padding: 10px; max-height: 400px; overflow-y: auto;">'; // 6x8 grid
                            const totalSlots = 48; // 6 rows * 8 columns

                            for (let i = 0; i < totalSlots; i++) {
                                if (i < data.inventory_list.length) {
                                    const item = data.inventory_list[i]; // item is an object {id, name, type, equip_slot}
                                    let slotHTML = `<div class="inventory-slot" title="${item.name}" data-item-id="${item.id}"`;
                                    if (item.equip_slot) { // Mark equippable items visually
                                        slotHTML += ` style="border-color: #007bff;"`; // Example: blue border for equippable
                                    }
                                    slotHTML += `>${item.name}</div>`;
                                    inventoryContent += slotHTML;
                                } else {
                                    inventoryContent += `<div class="inventory-slot">&nbsp;</div>`; // Empty slot
                                }
                            }

                            inventoryContent += '</div>';
                        }
                        showMenuModal("Backpack", inventoryContent, [{text: "Close", action: () => {}}]);
                        data.message = ""; // Clear any default message like "Your inventory is empty" from main output
                    }
                    // After modal is shown (or would have been shown), add event listeners if it was inventory
                    // Check if the modal content element exists, which indicates the modal is currently displayed
                    if (actionStringEcho === 'inventory' && document.getElementById('custom-modal-content')) {
                        const inventorySlotsInModal = document.getElementById('custom-modal-content').querySelectorAll('.inventory-slot');
                        inventorySlotsInModal.forEach(slotElement => {
                            slotElement.addEventListener('dblclick', function(event) {
                                event.preventDefault(); // Prevent default text selection on double-click
                                const itemId = this.getAttribute('data-item-id');
                                console.log("Double-clicked item ID:", itemId);
                                performAction(`equip ${itemId}`);
                                closeModal(); // Close backpack after attempting to equip
                            });
                        });
                    }
                    // --- End Inventory Modal Handling ---

                    if (actionStringEcho) { // Optionally echo the command that led to this scene
                        const p_command_echo = document.createElement('p');
                        p_command_echo.innerHTML = `<strong>&gt; ${actionStringEcho}</strong>`;
                            outputElement.appendChild(p_command_echo);
                    }
                        if(data.location_name) {
                            const p_loc_name = document.createElement('p');
                            p_loc_name.innerHTML = `--- ${data.location_name} (HP: ${data.player_hp !== undefined ? data.player_hp : 'N/A'}/${data.player_max_hp !== undefined ? data.player_max_hp : 'N/A'}) ${data.player_name ? '('+data.player_name+')' : ''}`;
                            outputElement.appendChild(p_loc_name);
                        }
                        if(data.description) { 
                            const p_desc = document.createElement('p');
                            p_desc.textContent = data.description;
                            outputElement.appendChild(p_desc);
                        }
                        const p_message = document.createElement('p'); 
                        if(data.message && data.message.trim() !== "") p_message.textContent = data.message; 
                        outputElement.appendChild(p_message);
                        
                        function formatGSBCurrency(totalCopper) {
                            if (totalCopper === undefined || totalCopper === null) totalCopper = 0;
                            if (totalCopper === 0) return "0🟠";

                            const COPPER_PER_SILVER = 100;
                            const SILVER_PER_GOLD = 100;
                            const COPPER_PER_GOLD = COPPER_PER_SILVER * SILVER_PER_GOLD;

                            let gold = Math.floor(totalCopper / COPPER_PER_GOLD);
                            let remainingCopperAfterGold = totalCopper % COPPER_PER_GOLD;

                            let silver = Math.floor(remainingCopperAfterGold / COPPER_PER_SILVER);
                            let copper = remainingCopperAfterGold % COPPER_PER_SILVER;

                            let parts = [];
                            if (gold > 0) parts.push(`${gold}🟡`); 
                            if (silver > 0) parts.push(`${silver}🔘`); // Gray circle for Silver
                            
                            // Always show copper if it's non-zero, or if gold and silver are both zero (to ensure "0c" or "Xc")
                            if (copper > 0 || (gold === 0 && silver === 0)) {
                                parts.push(`${copper}🟠`); // Orange circle for Copper
                            }
                            return parts.length > 0 ? parts.join(' ') : "0🟠"; // Fallback to "0" with copper circle
                        }

                        // Update dynamic header
                        const headerInfoDiv = document.getElementById('dynamic-header-info');
                        if (headerInfoDiv) {
                            // Ensure header is visible only when game interface is active
                            headerInfoDiv.style.display = document.getElementById('game-interface').style.display === 'block' ? 'block' : 'none';
                            headerInfoDiv.textContent = `Location: ${data.location_name || 'Unknown'} | Player: ${data.player_name || 'Adventurer'} - Level: ${data.player_level !== undefined ? data.player_level : 'N/A'} (XP: ${data.player_xp !== undefined ? data.player_xp : 'N/A'}/${data.player_xp_to_next_level !== undefined ? data.player_xp_to_next_level : 'N/A'}) - Coins: ${formatGSBCurrency(data.player_coins)} - Diamond: 0💎`;
                        }

                        // Populate Character Panel
                        const charPanelName = document.getElementById('char-panel-name');
                        const charPanelClass = document.getElementById('char-panel-class');
                        const charPanelSpecies = document.getElementById('char-panel-species');
                        const charPanelLevel = document.getElementById('char-panel-level');
                        const charPanelXp = document.getElementById('char-panel-xp');
                        const charPanelHp = document.getElementById('char-panel-hp');
                        const charPanelAttack = document.getElementById('char-panel-attack');
                        const charPanelCoins = document.getElementById('char-panel-coins');
                        // Equipment Slots
                        const equipGrid = document.getElementById('char-panel-equipment-grid');
                        const equipSlots = {
                            head: document.getElementById('char-panel-equip-head'),
                            shoulders: document.getElementById('char-panel-equip-shoulders'),
                            chest: document.getElementById('char-panel-equip-chest'),
                            hands: document.getElementById('char-panel-equip-hands'),
                            legs: document.getElementById('char-panel-equip-legs'),
                            feet: document.getElementById('char-panel-equip-feet'),
                            main_hand: document.getElementById('char-panel-equip-main_hand'),
                            off_hand: document.getElementById('char-panel-equip-off_hand')
                        };
                        const equipSlotPrefixes = {
                            head: "H", shoulders: "S", chest: "C", hands: "G", legs: "L", feet: "F", main_hand: "MH", off_hand: "OH"
                        };

                        if (charPanelName) charPanelName.textContent = `Name: ${data.player_name || 'N/A'}`;
                        if (charPanelClass) charPanelClass.textContent = `Class: ${data.player_class_name || 'N/A'}`;
                        if (charPanelSpecies) charPanelSpecies.textContent = `Species: ${data.player_species_name || 'N/A'}`;
                        if (charPanelLevel) charPanelLevel.textContent = `Level: ${data.player_level !== undefined ? data.player_level : 'N/A'}`;
                        if (charPanelXp) charPanelXp.textContent = `XP: ${data.player_xp !== undefined ? data.player_xp : 'N/A'} / ${data.player_xp_to_next_level !== undefined ? data.player_xp_to_next_level : 'N/A'}`;
                        if (charPanelHp) charPanelHp.textContent = `HP: ${data.player_hp !== undefined ? data.player_hp : 'N/A'} / ${data.player_max_hp !== undefined ? data.player_max_hp : 'N/A'}`;
                        if (charPanelAttack) charPanelAttack.textContent = `Attack: ${data.player_attack_power !== undefined ? data.player_attack_power : 'N/A'}`;
                        if (charPanelCoins) charPanelCoins.textContent = `Coins: ${formatGSBCurrency(data.player_coins)}`;
                        for (const slotKey in equipSlots) {
                            if (equipSlots[slotKey]) {
                                const itemName = data.player_equipment && data.player_equipment[slotKey] ? data.player_equipment[slotKey] : 'Empty';
                                const prefix = equipSlotPrefixes[slotKey] || slotKey.substring(0,1).toUpperCase();
                                equipSlots[slotKey].textContent = `${prefix}: ${itemName}`;

                                // Store the item ID on the slot element if an item is equipped
                                if (data.player_equipment && data.player_equipment[`${slotKey}_id`]) { // Assuming backend sends item_id as slotKey_id
                                     equipSlots[slotKey].setAttribute('data-item-id', data.player_equipment[`${slotKey}_id`]);
                                     equipSlots[slotKey].style.borderColor = '#007bff'; // Example: Highlight equipped slots
                                } else {
                                     equipSlots[slotKey].removeAttribute('data-item-id');
                                     equipSlots[slotKey].style.borderColor = '#b0b0b0'; // Default border
                                }

                            }
                        }
                        // Add double-click listeners to equipped slots
                        // Define the unequip double-click handler function within displaySceneData scope
                        function handleUnequipDoubleClick(event) {
                            event.preventDefault(); // Prevent default text selection on double-click
                            const itemId = this.getAttribute('data-item-id');
                            const slotKey = this.getAttribute('data-slot-key'); // Get the slot key
                            console.log(`Double-clicked equipped item ID: ${itemId} in slot: ${slotKey}`);
                            if (itemId) { // Only attempt to unequip if there's an item ID
                                performAction(`unequip ${itemId}`); // Send the unequip command
                            }
                        }
                        if (equipGrid) { // equipGrid is document.getElementById('char-panel-equipment-grid')
                            equipGrid.querySelectorAll('.equip-slot[data-item-id]').forEach(slotElement => {
                                slotElement.addEventListener('dblclick', handleUnequipDoubleClick);
                            });
                        }

                        if(data.map_lines && Array.isArray(data.map_lines)) { 
                            data.map_lines.forEach(line => {
                                const p_map_line = document.createElement('p');
                                p_map_line.style.whiteSpace = "pre"; 
                                p_map_line.textContent = line;
                                outputElement.appendChild(p_map_line);
                            });
                        }
                        // The block that previously printed inventory to the main output is removed
                        // as it's now handled by the modal.
                        // if(data.inventory_list && Array.isArray(data.inventory_list)) {
                        //     const p_inv_header = document.createElement('p');
                        //     p_inv_header.textContent = "You are carrying:";
                        //     outputElement.appendChild(p_inv_header);
                        //     if (data.inventory_list.length > 0) {
                        //         data.inventory_list.forEach(item_name => {
                        //             const p_inv_item = document.createElement('p');
                        //             p_inv_item.textContent = `  - ${item_name}`;
                        //             outputElement.appendChild(p_inv_item);
                        //         });
                        //     }
                        //}

                        // Handle interactable features
                        const featurePanel = document.getElementById('feature-interactions-panel');
                        const featureButtonsContainer = featurePanel.querySelector('p').nextElementSibling || document.createElement('div'); // Get/create div for buttons
                        if (!featurePanel.querySelector('div')) featurePanel.appendChild(featureButtonsContainer); // Append if new
                        featureButtonsContainer.innerHTML = ''; // Clear previous feature buttons

                        if (data.interactable_features && data.interactable_features.length > 0) {
                            data.interactable_features.forEach(feature => {
                                const featureButton = document.createElement('button');
                                // Example: "Open Worn Crate" or "Search Loose Rocks"
                                featureButton.textContent = `${feature.action.charAt(0).toUpperCase() + feature.action.slice(1)} ${feature.name}`;
                                featureButton.onclick = () => performAction(`${feature.action} ${feature.id}`); // e.g., "open worn_crate"
                                featureButtonsContainer.appendChild(featureButton);
                            });
                            featurePanel.style.display = 'block';
                        } else {
                            featurePanel.style.display = 'none';
                        }

                        // Handle items on the ground
                        const itemsPanel = document.getElementById('room-items-panel');
                        // Ensure the panel and its inner div for buttons exist
                        const itemsContainer = itemsPanel.querySelector('div'); // Assumes HTML: <div id="room-items-panel"><p>...</p><div></div></div>
                        if (itemsContainer) {
                            itemsContainer.innerHTML = ''; // Clear previous item buttons

                            if (data.room_items && data.room_items.length > 0) {
                                data.room_items.forEach(item => { // item is now {id: "...", name: "..."}
                                    const itemButton = document.createElement('button');
                                    itemButton.textContent = `Take ${item.name}`;
                                    itemButton.onclick = () => performAction(`take ${item.id}`); // Send item_id
                                    itemsContainer.appendChild(itemButton);
                                });
                                itemsPanel.style.display = 'block';
                            } else {
                                itemsPanel.style.display = 'none';
                            }
                        }
                }
                
                function setupGameActions(data) {
                    const gameActionsPanel = document.getElementById('game-actions-panel');
                    if (!gameActionsPanel) return;

                    const buttonsContainer = gameActionsPanel.querySelector('div') || document.createElement('div');
                    if (!gameActionsPanel.contains(buttonsContainer)) gameActionsPanel.appendChild(buttonsContainer);
                    buttonsContainer.innerHTML = ''; // Clear previous buttons

                    if (data.can_save_in_city) {
                        const saveButton = document.createElement('button');
                        saveButton.textContent = 'Save Game';
                        saveButton.onclick = async () => {
                            const response = await fetch('/api/save_game_state', { method: 'POST' });
                            const result = await response.json();
                            appendMessageToOutput(result.message); // Helper to add message to game output
                        };
                        buttonsContainer.appendChild(saveButton);
                        gameActionsPanel.style.display = 'block';
                    } else {
                        gameActionsPanel.style.display = 'none';
                    }
                }

                // Initial load
                window.onload = () => {
                    // showInitialCharacterScreen(); // REMOVE THIS UNCONDITIONAL CALL
                    const isGameSessionActive = sessionStorage.getItem(SESSION_STORAGE_GAME_ACTIVE_KEY);
                    const activeCharName = sessionStorage.getItem(SESSION_STORAGE_CHAR_NAME_KEY);

                    if (isGameSessionActive === 'true' && activeCharName) {
                        attemptResumeSession(activeCharName).then(() => {
                            console.log("Session resume attempt finished.");
                        }).catch(error => {
                            console.error("Error resuming session by reloading character:", error);
                            sessionStorage.removeItem(SESSION_STORAGE_GAME_ACTIVE_KEY);
                            sessionStorage.removeItem(SESSION_STORAGE_CHAR_NAME_KEY);
                            showInitialCharacterScreen(); // Fallback to main screen
                        });
                    } else {
                        showInitialCharacterScreen(); // Start with character selection/load screen
                    }

                    const settingsButton = document.getElementById('settings-gear-button');
                    if(settingsButton) {
                        settingsButton.onclick = () => {
                            showMenuModal("Game Menu", "", [
                                {text: "Main Menu", action: goToMainMenu},
                                {text: "Cancel", action: () => {}} // Empty action for cancel
                            ]);
                        };
                    }

                    document.addEventListener('keydown', function(event) {
                         // If a modal is open (like the pause modal), generally let modal buttons or specific keys (like 'P' for unpausing) handle actions.
                        // Prevent other game-related key actions if paused and modal is up.
                        if (gameIsPaused && document.getElementById('custom-modal-overlay') && (event.key !== 'p' && event.key !== 'P')) {
                            // console.log("Game paused, modal open. Key '" + event.key + "' interaction potentially blocked.");
                            // You might add event.preventDefault() here if needed for specific keys,
                            // but the main game actions are blocked by `performAction`'s check.
                        }
                        if ((event.key === 'p' || event.key === 'P') && !event.repeat && gameIsActiveForInput) {
                            togglePauseGame();
                        }
                    });
                };

                function appendMessageToOutput(messageText) {
                    const outputElement = document.getElementById('game-output');
                    const p_msg = document.createElement('p');
                    p_msg.textContent = messageText;
                    outputElement.appendChild(p_msg);
                    outputElement.scrollTop = outputElement.scrollHeight;
                }
            </script>
        </body>
        </html>
        """
        html_content = html_content_template.replace("__MAX_NAME_LENGTH_PLACEHOLDER__", str(MAX_NAME_LENGTH))
        return html_content

    # Optional: Flask endpoint to sync pause state with server if needed later
    # @flask_app_instance.route('/api/set_pause_state', methods=['POST'])
    # def set_pause_state_route():
    #     data = request.get_json()
    #     player["is_paused"] = data.get("paused", False)
    #     return jsonify({"message": "Pause state updated", "is_paused": player["is_paused"]})


    @flask_app_instance.route('/process_game_action', methods=['POST'])
    def process_game_action_route():
        data = request.get_json()
        action = data.get('action')

        # Ensure player object and essential keys exist, especially current_location_id
        if not player or "current_location_id" not in player or player["current_location_id"] is None:
            # This might happen if character creation/load didn't complete properly for the web session
            # Or if an action is attempted before the game is truly active for the web.
            player["current_location_id"] = "generic_start_room" # Default to a safe starting point
            player.setdefault("name", "Unknown Adventurer")
            player.setdefault("hp", 0)
            player.setdefault("max_hp", 0)
            player.setdefault("inventory", [])
            player.setdefault("game_active", False) # Mark as not fully active if we had to reset

        game_response = {
            "message": "",
            "player_hp": player.get("hp"),
            "player_name": player.get("name"),
            "player_max_hp": player.get("max_hp"),
            "location_name": "Unknown Area", # Default
            "description": "An unfamiliar place.", # Default
            "player_coins": player.get("coins", 0),
            "player_level": player.get("level", 1),
            "player_xp": player.get("xp", 0),
            "player_xp_to_next_level": player.get("xp_to_next_level", 100),
            "player_class_name": classes_data.get(player.get("class", ""), {}).get("name", "N/A"),
            "player_species_name": species_data.get(player.get("species", ""), {}).get("name", "N/A"),
            "player_attack_power": player.get("attack_power", 0),
            "player_equipment": { # Initialize with all expected slots
                "head": "Empty", "shoulders": "Empty", "chest": "Empty", "hands": "Empty",
                "legs": "Empty", "feet": "Empty", "main_hand": "Empty", "off_hand": "Empty"
            },
            "interactable_features": [], 
            "room_items": [], # List of items in the room
            "can_save_in_city": False # Default save status
        }

        if not player.get("game_active") and action not in ['!start']: # Check game_active safely
             game_response["message"] = "Game not started. Please start the game first (this might require a terminal interaction if using --browser at launch without --autostart)."
             return jsonify(game_response)

        if action == 'look':
            loc_id = player["current_location_id"]
            if loc_id in locations:
                # location_name and description already set by default above
                game_response["location_name"] = locations[loc_id].get("name", "Unknown Area")
                game_response["description"] = locations[loc_id]["description"]
                game_response["message"] = "" # Description is primary
            else:
                game_response["message"] = "Current location is unknown."
        elif action.startswith('go '):
            direction = action.split(' ', 1)[1] 
            current_loc_id = player["current_location_id"]
            current_location_data = locations.get(current_loc_id, {})
            
            if direction in current_location_data.get("exits", {}):
                player["current_location_id"] = current_location_data["exits"][direction]
                new_loc_id = player["current_location_id"]
                new_location_data = locations.get(new_loc_id, {})
                game_response["message"] = f"You walk {direction}."
                game_response["location_name"] = new_location_data.get("name", "Unknown Area")
                game_response["description"] = new_location_data.get("description", "An unfamiliar place.")
            else:
                game_response["message"] = f"You can't go {direction} from here."
                game_response["location_name"] = current_location_data.get("name", "Unknown Area")
                game_response["description"] = current_location_data.get("description", "An unfamiliar place.")
        elif action == 'inventory':
            # Ensure inventory key exists
            player_inventory = player.get("inventory", [])
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
            loc_id = player.get("current_location_id")
            if loc_id and loc_id in locations:
                map_data_lines = draw_zone_map(loc_id) 
                game_response["map_lines"] = map_data_lines 
                game_response["message"] = "Map information:"
                game_response["location_name"] = locations[loc_id].get("name", "Unknown Area") # Also send current loc
                game_response["description"] = locations[loc_id].get("description", "An unfamiliar place.")
            else:
                game_response["message"] = "Cannot display map: Current location is unknown or invalid."
                game_response["location_name"] = "Unknown Area"
                game_response["description"] = "You are lost and cannot see a map."
        elif action.startswith('take '):
            item_id_to_take = action.split(' ', 1)[1]
            current_loc_id = player["current_location_id"]
            location_data = locations.get(current_loc_id, {})
            room_items = location_data.get("items", [])

            if item_id_to_take in room_items:
                if item_id_to_take == "small_pouch_of_coins":
                    coin_value = items_data.get(item_id_to_take, {}).get("value", 0)
                    player["coins"] = player.get("coins", 0) + coin_value 
                    log_game_event("currency_gained", {"amount": coin_value, "unit": "copper", "source": f"take_room_web_{current_loc_id}_{item_id_to_take}", "item_id_source": item_id_to_take, "location_id": current_loc_id})
                    game_response["message"] = f"You picked up the {items_data.get(item_id_to_take, {}).get('name', item_id_to_take)} and gained {coin_value} copper coins."
                    room_items.remove(item_id_to_take)
                else:
                    award_message = award_item_to_player(item_id_to_take, source=f"take_room_web_{current_loc_id}")
                    game_response["message"] = award_message
                    room_items.remove(item_id_to_take)
                
                # Update location name and description for the response as they might be cleared by default
                game_response["location_name"] = location_data.get("name", "Unknown Area")
                game_response["description"] = location_data.get("description", "An unfamiliar place.")
            else:
                game_response["message"] = f"There is no '{items_data.get(item_id_to_take, {}).get('name', item_id_to_take.replace('_',' '))}' here to take."
                game_response["location_name"] = location_data.get("name", "Unknown Area")
                game_response["description"] = location_data.get("description", "An unfamiliar place.")
        
        elif action == "open worn_crate" and player["current_location_id"] == "generic_start_room":
            # This specific handler for "open worn_crate"
            crate = locations["generic_start_room"]["features"]["worn_crate"]
            if crate.get("closed"):
                game_response["message"] = "You pry open the crate." 
                items_in_crate = list(crate.get("contains_on_open", []))
                found_items_desc_web = []
                if items_in_crate:
                    for item_id in items_in_crate:
                        locations[player["current_location_id"]].setdefault("items", []).append(item_id)
                        found_items_desc_web.append(items_data.get(item_id, {}).get("name", item_id))
                    game_response["message"] += f"\nInside, you find: {', '.join(found_items_desc_web)}."
                    if player["current_location_id"] == "generic_start_room": # Specific message for starter crate
                        game_response["message"] += "\nAmong the items, you find a map of a nearby settlement and a small pouch of coins."
                
                crate["contains_on_open"] = [] 
                crate["closed"] = False
                player["flags"]["found_starter_items"] = True
            else:
                game_response["message"] = "The crate is already open and empty."
        elif action.startswith('unequip '):
            item_id_to_unequip = action.split(' ', 1)[1]
            # Find the item in equipped slots
            item_id_found_in_equipment = None
            slot_unequipped_from = None
            player_equipment_data = player.get("equipment", {})
            for slot, item_id in player_equipment_data.items():
                if item_id == item_id_to_unequip: # Match by item ID
                    item_id_found_in_equipment = item_id
                    slot_unequipped_from = slot
                    break

            if item_id_found_in_equipment:
                player["inventory"].append(item_id_found_in_equipment)
                player["equipment"][slot_unequipped_from] = None
                game_response["message"] = f"You unequipped {items_data.get(item_id_found_in_equipment,{}).get('name', item_id_found_in_equipment)} from your {slot_unequipped_from.replace('_', ' ')} slot."
                log_game_event("item_unequipped", {"item_id": item_id_found_in_equipment, "slot": slot_unequipped_from, "moved_to_inventory": True})
                # TODO: Adjust player stats based on unequipped item
            else:
                # This case might happen if the client state is out of sync or item wasn't equipped
                game_response["message"] = f"That item doesn't seem to be equipped."
            
            # Ensure current location data is still part of the response
            current_loc_id_for_unequip = player.get("current_location_id")
            game_response["location_name"] = locations.get(current_loc_id_for_unequip, {}).get("name", "Unknown Area")
            game_response["description"] = locations.get(current_loc_id_for_unequip, {}).get("description", "An unfamiliar place.")

        elif action.startswith('equip '):
            item_id_to_equip = action.split(' ', 1)[1]
            if item_id_to_equip in player.get("inventory", []):
                item_details = items_data.get(item_id_to_equip)
                if item_details and item_details.get("equip_slot"):
                    slot_to_equip_to = item_details["equip_slot"]
                    
                    # Unequip current item in that slot, if any
                    currently_equipped_item_id = player["equipment"].get(slot_to_equip_to)
                    if currently_equipped_item_id:
                        player["inventory"].append(currently_equipped_item_id)
                        # Log unequip event if needed
                        log_game_event("item_unequipped", {"item_id": currently_equipped_item_id, "slot": slot_to_equip_to, "moved_to_inventory": True})
                        game_response["message"] = f"You unequipped {items_data.get(currently_equipped_item_id,{}).get('name', currently_equipped_item_id)}.\n"
                    
                    player["equipment"][slot_to_equip_to] = item_id_to_equip
                    player["inventory"].remove(item_id_to_equip)
                    game_response["message"] += f"You equipped {item_details.get('name', item_id_to_equip)}."
                    log_game_event("item_equipped", {"item_id": item_id_to_equip, "slot": slot_to_equip_to})
                    # TODO: Adjust player stats based on equipped item
                else:
                    game_response["message"] = f"You cannot equip {items_data.get(item_id_to_equip,{}).get('name', item_id_to_equip)}."
            else:
                game_response["message"] = f"You don't have {items_data.get(item_id_to_equip,{}).get('name', item_id_to_equip)} in your inventory."
            # Ensure current location data is still part of the response
            current_loc_id_for_equip = player.get("current_location_id")
            game_response["location_name"] = locations.get(current_loc_id_for_equip, {}).get("name", "Unknown Area")
            game_response["description"] = locations.get(current_loc_id_for_equip, {}).get("description", "An unfamiliar place.")
        else:
            game_response["message"] = f"The action '{action}' is not fully implemented or recognized for the browser interface yet."
            # Ensure location details are still sent for unrecognized actions
            current_loc_id_for_else = player.get("current_location_id")
            if current_loc_id_for_else and current_loc_id_for_else in locations:
                game_response["location_name"] = locations[current_loc_id_for_else].get("name", "Unknown Area")
                game_response["description"] = locations[current_loc_id_for_else].get("description", "An unfamiliar place.")

        # --- Final response assembly ---
        # Ensure current location data is fresh for populating features and items
        current_loc_id_for_response = player.get("current_location_id")
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
        
        # Always include player stats
        game_response["player_hp"] = player.get("hp")
        game_response["player_max_hp"] = player.get("max_hp")
        game_response["player_name"] = player.get("name")
        game_response["player_coins"] = player.get("coins", 0)
        game_response["player_level"] = player.get("level", 1)
        game_response["player_xp"] = player.get("xp", 0)
        game_response["player_xp_to_next_level"] = player.get("xp_to_next_level", 100)
        game_response["player_class_name"] = classes_data.get(player.get("class", ""), {}).get("name", "N/A")
        game_response["player_species_name"] = species_data.get(player.get("species", ""), {}).get("name", "N/A")
        game_response["player_attack_power"] = player.get("attack_power", 0)
        
        # Populate equipped items names
        game_response["player_equipment"] = {}
        player_equipment_data = player.get("equipment", {})
        # Ensure all defined slots are present in the response
        expected_slots = ["head", "shoulders", "chest", "hands", "legs", "feet", "main_hand", "off_hand"]
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
            print(f"DEBUG: Missing data in /api/create_character: {data}")
            return jsonify({"error": "Missing character creation data."}), 400

        if _apply_character_choices_and_stats(species_id, class_id, player_name, player_gender):
            player["game_active"] = True 
            species_info = species_data[player["species"]]
            
            start_room_id = "generic_start_room" 
            player["current_location_id"] = start_room_id
            class_info_for_items = classes_data[player["class"]]
            if start_room_id in locations and "worn_crate" in locations[start_room_id].get("features", {}):
                locations[start_room_id]["features"]["worn_crate"]["contains_on_open"] = list(class_info_for_items["starter_items"])
                locations[start_room_id]["features"]["worn_crate"]["closed"] = True
            
            # Prepare initial scene data for the response
            initial_scene_data = {
                "message": f"{species_info['backstory_intro']}\nYou feel a pull towards the {locations[start_room_id]['name']}.",
                "player_hp": player.get("hp"),
                "player_name": player.get("name"),
                "player_max_hp": player.get("max_hp"),
                "location_name": locations.get(player["current_location_id"], {}).get("name"),
                "description": locations.get(player["current_location_id"], {}).get("description"),
                "player_coins": player.get("coins", 0),
                "player_level": player.get("level", 1),
                "player_xp": player.get("xp", 0),
                "player_xp_to_next_level": player.get("xp_to_next_level", 100),
                "player_class_name": classes_data.get(player.get("class", ""), {}).get("name", "N/A"),
                "player_species_name": species_data.get(player.get("species", ""), {}).get("name", "N/A"),
                "player_attack_power": player.get("attack_power", 0),
                "player_equipment": {
                    "head": "Empty", "shoulders": "Empty", "chest": "Empty", "hands": "Empty",
                    "legs": "Empty", "feet": "Empty", "main_hand": "Empty", "off_hand": "Empty"
                },
                "interactable_features": [], # Will be populated by final assembly logic
                "room_items": [] # Will be populated by final assembly logic
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
            player_equipment_data_init = player.get("equipment", {})
            expected_slots_init = ["head", "shoulders", "chest", "hands", "legs", "feet", "main_hand", "off_hand"]
            for slot in expected_slots_init:
                item_id = player_equipment_data_init.get(slot) # Get item_id from player's equipment dict

                # Send both the item name and the item ID for the frontend
                if item_id:
                     initial_scene_data["player_equipment"][f"{slot}_id"] = item_id # Send item ID
                if item_id and item_id in items_data:
                    initial_scene_data["player_equipment"][slot] = items_data[item_id].get("name", "Unknown Item")

            # Items in the room (should be empty at start, items are in crate)
            # initial_scene_data["room_items"] = [...] 

            return jsonify(initial_scene_data)
        else:
            print(f"DEBUG: _apply_character_choices_and_stats failed for web creation: {data}")
            return jsonify({"error": "Failed to create character on server."}), 500

    @flask_app_instance.route('/api/load_character', methods=['POST'])
    def load_character_web_route():
        data = request.get_json()
        character_name = data.get('character_name')
        if not character_name:
            return jsonify({"error": "Character name not provided."}), 400
        
        if load_character_data(character_name):
            # Character data is now in global 'player'
            current_loc_id = player.get("current_location_id")
            current_loc_data = locations.get(current_loc_id, {})
            
            loaded_scene_data = {
                "message": f"Welcome back, {player.get('name')}!",
                "player_hp": player.get("hp"),
                "player_name": player.get("name"),
                "player_max_hp": player.get("max_hp"),
                "location_name": current_loc_data.get("name"),
                "description": current_loc_data.get("description"),
                "player_coins": player.get("coins", 0),
                "player_level": player.get("level", 1),
                "player_xp": player.get("xp", 0),
                "player_xp_to_next_level": player.get("xp_to_next_level", 100),
                "player_class_name": classes_data.get(player.get("class", ""), {}).get("name", "N/A"),
                "player_species_name": species_data.get(player.get("species", ""), {}).get("name", "N/A"),
                "player_attack_power": player.get("attack_power", 0),
                "player_equipment": {
                    "head": "Empty", "shoulders": "Empty", "chest": "Empty", "hands": "Empty",
                    "legs": "Empty", "feet": "Empty", "main_hand": "Empty", "off_hand": "Empty"
                },
                "interactable_features": [],
                "room_items": []
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
            # Populate equipped items for loaded scene
            player_equipment_data_load = player.get("equipment", {})
            expected_slots_load = ["head", "shoulders", "chest", "hands", "legs", "feet", "main_hand", "off_hand"]
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
        if player.get("game_active") and player.get("name") == character_name_from_client:
            # Server state is consistent with client's session, return current state
            current_loc_id = player.get("current_location_id")
            current_loc_data = locations.get(current_loc_id, {})
            
            scene_data = {
                "message": f"Session continued for {player.get('name')}.",
                "player_hp": player.get("hp"),
                "player_name": player.get("name"),
                "player_max_hp": player.get("max_hp"),
                "location_name": current_loc_data.get("name"),
                "description": current_loc_data.get("description"),
                "player_coins": player.get("coins", 0),
                "player_level": player.get("level", 1),
                "player_xp": player.get("xp", 0),
                "player_xp_to_next_level": player.get("xp_to_next_level", 100),
                "player_class_name": classes_data.get(player.get("class", ""), {}).get("name", "N/A"),
                "player_species_name": species_data.get(player.get("species", ""), {}).get("name", "N/A"),
                "player_attack_power": player.get("attack_power", 0),
                "player_equipment": {
                    "head": "Empty", "shoulders": "Empty", "chest": "Empty", "hands": "Empty",
                    "legs": "Empty", "feet": "Empty", "main_hand": "Empty", "off_hand": "Empty"
                },
                "interactable_features": [], # Populate these like in process_game_action
                "room_items": []
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
            
            # Populate equipped items for resumed scene
            player_equipment_data_resume = player.get("equipment", {})
            expected_slots_resume = ["head", "shoulders", "chest", "hands", "legs", "feet", "main_hand", "off_hand"]
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
        if not player.get("game_active") or not player.get("name"):
            return jsonify({"message": "Cannot save: No active character or game not started."}), 400

        current_loc_id = player.get("current_location_id")
        current_zone = locations.get(current_loc_id, {}).get("zone")
        if current_zone not in CITY_ZONES:
            return jsonify({"message": "Cannot save here. You must be in a city."}), 403

        if save_player_data(reason_for_save="Game progress saved via web interface"):
            return jsonify({"message": f"Game saved successfully for {player.get('name')}."})
        return jsonify({"message": "Failed to save game on server."}), 500

    @flask_app_instance.route('/test')
    def test_route():
        print("Test route accessed!")
        return "This is the test route. If you see this, routing is partially working."

    print("Starting web server on http://127.0.0.1:5000/ ...")
    try:
        flask_app_instance.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
    except Exception as e:
        print(f"Failed to start or run web server: {e}")

def launch_web_interface():
    global web_server_thread
    if not flask_available:
        print("\nFlask library not found. Cannot start browser interface.")
        print("Please install Flask to use this feature (e.g., 'pip install Flask').")
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
    if not player["game_active"]:
        print("\nWelcome to the Text RPG Adventure!")
        print("Type '!start' to begin your journey or '!quit' to exit.")
        print("\nAvailable commands:")
        print("  !start         - Begin the adventure.")
        print("  !quit          - Exit the game.")
        return

    if player["dialogue_npc_id"] and player["dialogue_options_pending"]:
        npc_id = player["dialogue_npc_id"]
        npc_data = locations[player["current_location_id"]]["npcs"][npc_id]
        print(f"\n--- Talking to {npc_data['name']} ---")
        print("Choose an option:")
        for key, option_data in player["dialogue_options_pending"].items():
            print(f"  {key}. {option_data['text']}")
        print("\n(Type the number of your choice, or 'leave' to end conversation)")
        return

    if player["combat_target_id"]:
        npc_id = player["combat_target_id"]
        if npc_id not in locations[player["current_location_id"]]["npcs"]:
            print(f"[Error] Combat target {npc_id} not found. Ending combat.")
            player["combat_target_id"] = None
        else:
            npc_data = locations[player["current_location_id"]]["npcs"][npc_id]
            print("\n--- IN COMBAT ---")
            print(f"Your HP: {player['hp']}/{player['max_hp']}")
            print(f"Enemy: {npc_data['name']} | HP: {npc_data['hp']}/{npc_data['max_hp']}")
            print(HOSTILE_MOB_VISUAL)
            
            print("\nCombat Commands:")
            print("  attack                  - Perform a basic attack.")
            for move_id, move_data in player["special_moves"].items():
                cooldown_status = f"(Ready)" if player["special_cooldowns"].get(move_id, 0) == 0 else f"(Cooldown: {player['special_cooldowns'].get(move_id, 0)})"
                print(f"  special {move_id.replace('_',' ')}   - {move_data['description']} {cooldown_status}")
            print("  deflect                 - Reduce damage from the next attack.")
            print("  item <item_name>        - Use an item from your inventory.")
            return 

    loc_id = player["current_location_id"]
    if loc_id not in locations:
        print(f"\n[ERROR] Current location '{loc_id}' not found. Resetting.")
        player["current_location_id"] = "generic_start_room" # Default to start room if error
        loc_id = player["current_location_id"]
    
    location_data = locations[loc_id]
    print(f"\n--- {location_data['name']} (HP: {player['hp']}/{player['max_hp']}) ---")
    if player.get("species") and player.get("class"):
        player_name_display = player.get("name", "Adventurer")
        species_name = species_data.get(player['species'], {}).get('name', 'Unknown Species')
        class_name = classes_data.get(player['class'], {}).get('name', 'Unknown Class')
        gender_display = player.get('gender', 'Unspecified')
        print(f"    ({player_name_display} - {gender_display} {species_name} {class_name})")

    print(location_data["description"])
    if loc_id == "generic_start_room" and not player["flags"].get("found_starter_items"):
        print("The air is thick with anticipation. You feel compelled to check the worn crate.")


    room_npcs = location_data.get("npcs", {})
    hostiles_present_desc = False
    for npc_id, npc_data in room_npcs.items():
        if npc_data.get("hostile") and player["combat_target_id"] != npc_id :
            if not hostiles_present_desc:
                print("\nDanger!")
                hostiles_present_desc = True
            print(f"A menacing {npc_data['name']} is here!")

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
        for npc_id, npc_data in room_npcs.items():
            if not npc_data.get("hostile") or (npc_data.get("hostile") and player["combat_target_id"] != npc_id):
                 print(f"  - {npc_data['name']} ({npc_data.get('description', 'An interesting individual.')})")
    
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
    
    inv_status = "(empty)" if not player["inventory"] else f"({len(player['inventory'])} item(s))"
    print(f"  inventory (i)  - Check your inventory {inv_status}.")

    if "features" in location_data:
        for fname, fdata in location_data["features"].items():
            if fname == "chest" and fdata.get("locked") and fdata.get("key_needed"):
                print(f"  use <item> on {fname}")
                break 
            elif fname == "worn_crate" and fdata.get("closed"): # Suggest opening the crate
                print(f"  open worn crate") # Or search, depending on defined actions
                break
    
    if any(not npc.get("hostile") or (npc.get("hostile") and player["combat_target_id"] != npc_id) for npc_id, npc in room_npcs.items()):
        available_to_talk = [npc["name"] for npc_id, npc in room_npcs.items() if not npc.get("hostile") or (npc.get("hostile") and player["combat_target_id"] != npc_id)]
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


def draw_zone_map(current_loc_id):
    """Draws or lists locations in the current zone and returns them as a list of strings."""
    map_output_lines = [] 
    current_zone = locations[current_loc_id].get("zone")
    if not current_zone:
        map_output_lines.append("This area is uncharted (no zone data).")
        return map_output_lines 

    if current_zone in zone_layouts:
        layout = zone_layouts[current_zone]
        map_output_lines.append(f"--- {layout['title']} ---")
        map_grid_lines = [list(line) for line in layout["grid"]]
        mapped_loc_ids = {char: loc_id for char, loc_id in layout["mapping"].items()}

        for r_idx, row_str in enumerate(layout["grid"]):
            for c_idx, char_in_grid in enumerate(row_str):
                if char_in_grid in mapped_loc_ids:
                    loc_id_at_char = mapped_loc_ids[char_in_grid]
                    if loc_id_at_char == current_loc_id:
                        if c_idx > 0 and c_idx < len(row_str) -1 and \
                           map_grid_lines[r_idx][c_idx-1] == '[' and \
                           map_grid_lines[r_idx][c_idx+1] == ']':
                             map_grid_lines[r_idx][c_idx] = '@'
        
        for row_list in map_grid_lines:
            map_output_lines.append("".join(row_list))
        map_output_lines.append("") 
        map_output_lines.append("@ - You are here")
        map_output_lines.append("Other symbols represent locations.")
    else:
        map_output_lines.append(f"--- Area: {current_zone} ---")
        map_output_lines.append("Locations in this area:")
        zone_locs = [f"  - {data['name']}{' (You are here)' if loc_id == current_loc_id else ''}" 
                     for loc_id, data in locations.items() if data.get("zone") == current_zone]
        if zone_locs:
            map_output_lines.extend(zone_locs)
        else:
            map_output_lines.append("  (No specific locations marked for this area map.)")
    return map_output_lines


def process_command(full_command_input):
    full_command = full_command_input.lower().strip()
    parts = full_command.split()
    if not parts: return True
    command = parts[0]
    args = parts[1:]

    if command == "!start":
        if player["game_active"]: print("The game has already started!")
        else:
            initialize_game_state() 
        return True
    elif command == "!start_browser": 
        launch_web_interface()
        return True
    elif command == "!save":
        if not player["game_active"]:
            print("Game not active. Cannot save.")
            return True
        current_zone = locations[player["current_location_id"]].get("zone")
        if current_zone in CITY_ZONES:
            save_player_data(reason_for_save="Game progress manually saved")
        else:
            print("You can only save your progress in a city.")
        return True # Command processed, show scene again
    elif command == "!reload_data":
        print("Attempting to reload game data...")
        load_all_game_data()
        return True # Show scene again to reflect any changes
    elif command == "!quit": 
        print(f"\nYou decide to end your adventure here. Farewell!" if player["game_active"] else "\nFarewell!")
        return False
    
    if not player["game_active"]:
        print(f"Unknown command: '{full_command}'. Type '!start' to begin.")
        return True

    if player["dialogue_npc_id"] and player["dialogue_options_pending"]:
        npc_id = player["dialogue_npc_id"]
        npc_data = locations[player["current_location_id"]]["npcs"][npc_id]
        
        if full_command == "leave":
            print(f"You end the conversation with {npc_data['name']}.")
            player["dialogue_npc_id"] = None
            player["dialogue_options_pending"] = {}
            return True

        chosen_option_data = player["dialogue_options_pending"].get(full_command) 
        if chosen_option_data:
            print(f"\n> {chosen_option_data['text']}") 
            if chosen_option_data.get("response"):
                print(f"{npc_data['name']} says: \"{chosen_option_data['response']}\"")
            
            if chosen_option_data.get("triggers_combat"):
                player["dialogue_npc_id"] = None 
                player["dialogue_options_pending"] = {}
                start_combat(npc_id)
            elif chosen_option_data.get("action_type") == "end_conversation":
                player["dialogue_npc_id"] = None
                player["dialogue_options_pending"] = {}
        else:
            print("Invalid choice. Please type the number of the option or 'leave'.")
        return True 

    if player["combat_target_id"]:
        npc_id = player["combat_target_id"]
        if npc_id not in locations[player["current_location_id"]]["npcs"]:
            print(f"[Warning] Target {npc_id} seems to be gone. Ending combat.")
            player["combat_target_id"] = None
            return True 

        npc_data = locations[player["current_location_id"]]["npcs"][npc_id]
        action_taken = False

        if command == "attack":
            damage = player["attack_power"]
            npc_data["hp"] -= damage
            print(f"You attack {npc_data['name']} for {damage} damage.")
            if npc_data["hp"] <= 0:
                handle_npc_defeat(npc_id)
            action_taken = True
        elif command == "special":
            if not args: print("Which special move? (Specify the move like 'special power strike')")
            else:
                move_input = "_".join(args) 
                if move_input in player["special_moves"]:
                    if player["special_cooldowns"].get(move_input, 0) == 0:
                        move_details = player["special_moves"][move_input]
                        damage = int(player["attack_power"] * move_details["damage_multiplier"])
                        npc_data["hp"] -= damage
                        print(f"You use {move_details['name']} on {npc_data['name']} for {damage} damage!")
                        player["special_cooldowns"][move_input] = move_details["cooldown_max"]
                        if npc_data["hp"] <= 0:
                            handle_npc_defeat(npc_id)
                        action_taken = True
                    else:
                        print(f"{player['special_moves'][move_input]['name']} is on cooldown ({player['special_cooldowns'][move_input]} turns left).")
                else:
                    print(f"You don't know a special move called '{' '.join(args)}'.")
        elif command == "deflect":
            player["is_deflecting"] = True
            print("You brace yourself, preparing to deflect the next attack.")
            action_taken = True
        elif command == "item":
            if not args: print("Use which item?")
            else:
                item_name_input = " ".join(args)
                item_id_to_use = None
                for inv_item_id in player["inventory"]:
                    if item_name_input == items_data.get(inv_item_id, {}).get("name", "").lower() or \
                       item_name_input == inv_item_id.replace("_", " "):
                        item_id_to_use = inv_item_id
                        break
                
                if item_id_to_use:
                    item_detail = items_data.get(item_id_to_use)
                    if item_detail and item_detail["type"] == "consumable" and item_detail["effect"] == "heal":
                        heal_amount = item_detail["amount"]
                        player["hp"] = min(player["max_hp"], player["hp"] + heal_amount)
                        player["inventory"].remove(item_id_to_use)
                        print(f"You use the {item_detail['name']} and restore {heal_amount} HP. You now have {player['hp']}/{player['max_hp']} HP.")
                        action_taken = True 
                    else:
                        print(f"You can't use the {item_name_input} in that way right now.")
                else:
                    print(f"You don't have a '{item_name_input}'.")
        else:
            print(f"Unknown combat command: '{command}'. Valid commands: attack, special, deflect, item.")
        
        # After player action in combat, check if combat should continue (NPC still alive)
        if action_taken and player["combat_target_id"] and player["game_active"]: 
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
            for slot, item_id in player.get("equipment", {}).items():
                if item_id and (item_name_input == items_data.get(item_id, {}).get("name", "").lower() or item_name_input == item_id.replace("_", " ")):
                    item_id_to_unequip = item_id
                    slot_unequipped_from = slot
                    break
            if item_id_to_unequip:
                player["inventory"].append(item_id_to_unequip)
                player["equipment"][slot_unequipped_from] = None
                print(f"You unequipped {items_data.get(item_id_to_unequip,{}).get('name', item_id_to_unequip)} from your {slot_unequipped_from.replace('_', ' ')} slot.")
            else:
                print(f"You don't have '{item_name_input}' equipped.")
        return True # Command processed, show scene again
    # --- End Unequip Command Handler (Terminal) ---

        if action_taken and player["combat_target_id"] and player["game_active"]: 
            npc_combat_turn()
        return True 

    loc_id = player["current_location_id"]
    location_data = locations[loc_id]

    if command == "!map" or (command == "view" and " ".join(args) == "map scroll"): # Allow "view map scroll"
        if command == "view" and "blank_map_scroll" not in player["inventory"]:
            print("You don't have a map scroll to view.")
            return True
        if command == "view":
            print("You unfurl the map scroll...")

        map_lines_for_terminal = draw_zone_map(loc_id)
        for line in map_lines_for_terminal:
            print(line)
    elif command == "look": print("\nYou take a closer look around...")
    elif command == "go":
        if not args: print("Go where? (Specify a direction like 'go north')")
        else:
            direction = args[0]
            if direction in location_data.get("exits", {}):
                player["current_location_id"] = location_data["exits"][direction]
                print(f"You walk {direction}.")
            else: print(f"You can't go {direction} from here.")
    elif command == "open" and " ".join(args) == "worn crate": # Specific for starter task
        if player["current_location_id"] == "generic_start_room":
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
                        player["coins"] = player.get("coins", 0) + coin_value 
                        log_game_event("currency_gained", {"amount": coin_value, "unit": "copper", "source": f"take_room_{loc_id}_{r_item_id}", "item_id_source": r_item_id, "location_id": loc_id})
                        print(f"You picked up the {item_data.get('name', r_item_id)} and gained {coin_value} copper coins.")
                        room_items.remove(r_item_id) # Remove from the original list
                        item_to_take = "currency_handled" 
                        break 
                    else:
                        item_to_take = r_item_id
                        break 
            
            if item_to_take and item_to_take != "currency_handled":
                award_item_to_player(item_to_take, source=f"take_room_{loc_id}") 
                room_items.remove(item_to_take) # Remove from the original list
            elif not item_to_take: # Only print if not found and not handled as currency
                print(f"There is no {item_name_input} here to take.")

    elif command == "inventory" or command == "i":
        if player["inventory"]:
            print("\nYou are carrying:")
            for item_id in player["inventory"]: print(f"  - {items_data.get(item_id, {}).get('name', item_id.replace('_',' '))}")
        else: print("Your inventory is empty.")
    elif command == "use":
        if len(args) < 3 or args[1] != "on": print("How to use: 'use <item_name> on <target_name>'")
        else:
            item_input = args[0]
            target_input = args[2]
            item_in_inv_id = next((inv_id for inv_id in player["inventory"] if item_input == items_data.get(inv_id,{}).get("name","").lower() or item_input == inv_id.replace("_"," ")), None)
            target_feature_id = next((f_id for f_id in location_data.get("features",{}).keys() if target_input == f_id.replace("_"," ")), None)

            if not item_in_inv_id: print(f"You don't have a {item_input}.")
            elif not target_feature_id: print(f"There is no {target_input} here to use the {item_input} on.")
            else:
                feature = location_data["features"][target_feature_id]
                if feature.get("locked") and feature.get("key_needed") == item_in_inv_id:
                    print(feature["unlock_message"])
                    feature["locked"] = False
                    remove_item_from_player_inventory(item_in_inv_id, source=f"used_on_{target_feature_id}")
                    if "contains_item_on_unlock" in feature:
                        new_item = feature.pop("contains_item_on_unlock")
                        location_data.setdefault("items", []).append(new_item)
                        # Log item revealed from a locked feature
                        log_game_event("feature_item_revealed", {
                            "feature_id": target_feature_id,
                            "revealed_item_id": new_item,
                            "location_id": player.get("current_location_id")
                        })
                        print(f"The {target_feature_id.replace('_', ' ')} creaks open. You see a {items_data.get(new_item,{}).get('name',new_item)} inside!")
                elif not feature.get("locked"): print(f"The {target_feature_id.replace('_', ' ')} is already unlocked/used.")
                else: print(f"The {item_input} doesn't seem to work on the {target_feature_id.replace('_', ' ')}.")
    elif command == "talk":
        if not args: print("Talk to whom?")
        else:
            npc_name_input = " ".join(args)
            room_npcs = location_data.get("npcs", {})
            found_npc_id, npc_data_found = next(((npc_id, data) for npc_id, data in room_npcs.items() if npc_name_input == data["name"].lower() or npc_name_input == npc_id.lower()), (None, None))

            if npc_data_found:
                print(f"\nYou approach {npc_data_found['name']}.")
                if npc_data_found.get("pre_combat_dialogue") and npc_data_found.get("dialogue_options"):
                    print(f"{npc_data_found['name']} says: \"{npc_data_found['pre_combat_dialogue']}\"")
                    player["dialogue_npc_id"] = found_npc_id
                    player["dialogue_options_pending"] = npc_data_found["dialogue_options"]
                elif npc_data_found.get("type") == "quest_giver_simple":
                    if npc_data_found.get("quest_item_needed") in player["inventory"]:
                        print(f"{npc_data_found['name']} says: \"{npc_data_found.get('dialogue_after_quest_complete', 'Thank you!')}\"")
                        remove_item_from_player_inventory(npc_data_found["quest_item_needed"], source=f"quest_turn_in_{found_npc_id}")
                        if npc_data_found.get("quest_reward_item"):
                            # award_item_to_player is already called and logs "item_acquisition"
                            # which covers "player is rewarded with"
                            award_item_to_player(npc_data_found["quest_reward_item"], source=f"quest_reward_{found_npc_id}")
                        # If there's a currency reward for the quest
                        if npc_data_found.get("quest_reward_currency"):
                            log_game_event("currency_gained", {"amount": npc_data_found["quest_reward_currency"], "source": f"quest_reward_{found_npc_id}", "location_id": loc_id})
                            print(f"You are also rewarded with {npc_data_found['quest_reward_currency']} coins.")
                    else:
                        print(f"{npc_data_found['name']} says: \"{npc_data_found.get('dialogue_after_quest_incomplete', npc_data_found['dialogue'])}\"")
                elif npc_data_found.get("hostile"): 
                    print(npc_data_found['dialogue']) 
                    start_combat(found_npc_id) 
                elif npc_data_found.get("type") == "vendor":
                    print(VENDOR_STALL_VISUAL)
                    print(f"{npc_data_found['name']} says: \"{npc_data_found['dialogue']}\"")
                else:
                    print(f"{npc_data_found['name']} says: \"{npc_data_found['dialogue']}\"")
            else:
                print(f"There is no one named '{npc_name_input}' here to talk to.")
    else:
        potential_verb = command
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
    if not player["game_active"]:
        show_current_scene() # Shows initial welcome
    else:
        show_current_scene() # Shows the scene for the current location if game is active

    while True:
        prompt_text = "> "
        if player["game_active"]:
            if player["dialogue_npc_id"] and player["dialogue_options_pending"]:
                prompt_text = "[DIALOGUE] > "
            elif player["combat_target_id"]:
                prompt_text = "[COMBAT] > "
            elif player["current_location_id"] and player["current_location_id"] in locations:
                loc_name = locations[player["current_location_id"]]["name"]
                prompt_text = f"[{loc_name}] > "
            else: 
                # This case should ideally not be reached if game_active is true and character creation sets a location
                print("[Error: Current location unknown, but game is active. Resetting to start room.]")
                player["current_location_id"] = "generic_start_room" 
        
        user_input = input(prompt_text)
        if not process_command(user_input): break 
        
        if player["game_active"]: 
            show_current_scene()
        elif not player["game_active"] and player["combat_target_id"] is None and player["dialogue_npc_id"] is None : 
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
    
    if start_browser_on_launch:
        if flask_available:
            launch_web_interface() 
            # If browser is launched, main_game_loop for terminal might not be desired,
            # or it could run in parallel. For now, let's assume if --browser is used,
            # the primary interaction is expected via browser.
            # The web server runs in a daemon thread, so the main thread will continue.
            # If we want the script to *only* serve the web and not run terminal game:
            if web_server_thread and web_server_thread.is_alive():
                print("Web server is running. Terminal game loop will not start if browser is primary.")
                try:
                    while web_server_thread.is_alive(): # Keep main thread alive while server runs
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\nShutting down web server and game.")
                sys.exit(0) # Exit after web server stops or on interrupt
            else:
                print("Failed to start web server. Terminal game might proceed if configured.")
        else:
            print("\n[INFO] Flask library not found. Cannot start browser interface.")
            print("       Please install Flask (e.g., 'pip install Flask') and run with --browser again.")
            print("       Proceeding with terminal mode if character was created/loaded.")
            if not player["game_active"] and (run_character_creation_on_start or auto_start_game):
                 initialize_game_state() # Ensure game starts if browser failed but CC was intended

    # Only run main_game_loop if not exclusively in browser mode or if browser failed to start
    if player["game_active"] or (not start_browser_on_launch and not player["game_active"]):
        main_game_loop()