# d:\GeneralRepository\PythonProjects\AdventureOfTextland\game_logic.py

def apply_character_choices_and_stats(player_obj, species_id, class_id, char_name, char_gender, items_master_data,
                                      species_master_data, classes_master_data, save_player_data_func):
    """Applies chosen character details and stats to the player_obj."""
    player_obj.species_id = species_id
    player_obj.class_id = class_id
    player_obj.name = char_name
    player_obj.gender = char_gender

    class_info = classes_master_data[class_id]
    species_info = species_master_data[species_id]
    
    class_stats = class_info["base_stats"]
    species_bonuses = species_info["stat_bonuses"]

    # Set base stats
    player_obj.base_max_hp = class_stats["hp"] + species_bonuses.get("hp_bonus", 0)
    player_obj.base_attack_power = class_stats["attack_power"] + species_bonuses.get("attack_bonus", 0)
    player_obj.special_power = class_stats.get("special_power", 0) + species_bonuses.get("special_power_bonus", 0)
    
    # Other initializations
    player_obj.special_moves = dict(class_info.get("special_moves", {}))
    player_obj.special_cooldowns = {move_id: 0 for move_id in player_obj.special_moves}
    player_obj.inventory = ["simple_knife"] # Player starts only with a knife directly
    player_obj.coins = 0
    player_obj.level = 1
    player_obj.xp = 0
    player_obj.xp_to_next_level = 100
    player_obj.equipment = {
        "head": None, "shoulders": None, "chest": None, "hands": None,
        "legs": None, "feet": None, "main_hand": None, "off_hand": None,
        "neck": None, "back": None,
        "trinket1": None, "trinket2": None
    }
    player_obj.flags = {}
    player_obj.game_active = True # Mark game as active after creation

    # Calculate initial derived stats (max_hp, attack_power) based on base stats and any initially equipped items (none yet)
    player_obj._recalculate_derived_stats(items_master_data)
    player_obj.hp = player_obj.max_hp # Full HP at creation

    print(f"\nCharacter '{player_obj.name}' ({player_obj.gender} {species_info['name']} {class_info['name']}) created!")
    # The save_player_data_func now expects the player object (or its dict representation)
    # For now, let's assume save_player_data can handle the object or we convert it.
    # For simplicity, we'll pass the object and modify save_player_data later if needed, or convert to dict here.
    save_player_data_func(player_obj, reason_for_save=f"Character '{player_obj.name}' created and initial state saved")

    return True

def award_item_to_player(player_obj, items_master_data, item_id_to_give, source="unknown", log_event_func=None):
    """Awards an item to the player's inventory, handling special cases like currency pouches."""
    if not isinstance(item_id_to_give, str):
        error_msg = "[Error] Invalid item_id provided to award_item_to_player."
        print(error_msg)
        return error_msg 

    item_details = items_master_data.get(item_id_to_give, {})
    display_name = item_details.get("name", item_id_to_give.replace("_", " ").capitalize())
    message = ""

    if item_id_to_give == "small_pouch_of_coins":
        # Special case: Convert pouch to coins immediately
        coin_value = item_details.get("value", 0) # Get value from item data
        player_obj.add_coins(coin_value, log_event_func=log_event_func, source=f"auto_converted_{item_id_to_give}_from_{source}")
        # player_obj.add_coins already prints terminal feedback
        message = f"You found a {display_name} and gained {coin_value} coins."
        # The pouch itself is not added to inventory
    else:
        # Standard item acquisition: add to inventory
        player_obj.add_item_to_inventory(item_id_to_give)
        message = f"You have acquired: {display_name}."
        print(message) # Print acquisition message for terminal
        if log_event_func:
            log_event_func("item_acquisition", {"item_id": item_id_to_give, "item_name": display_name, "source": source, "player_name": player_obj.name, "location_id": player_obj.current_location_id})
    return message

def remove_item_from_player_inventory(player_obj, items_master_data, item_id_to_remove, source="unknown", log_event_func=None):
    if player_obj.remove_item_from_inventory(item_id_to_remove):
        item_details = items_master_data.get(item_id_to_remove, {})
        display_name = item_details.get("name", item_id_to_remove.replace("_", " ").capitalize())
        if log_event_func:
            log_event_func("item_removal", {
                "item_id": item_id_to_remove, "item_name": display_name, "player_name": player_obj.name,
                "source": source, "location_id": player_obj.current_location_id
            })
        return True
    return False