# d:\GeneralRepository\PythonProjects\AdventureOfTextland\game_logic.py

def apply_character_choices_and_stats(player_dict, species_id, class_id, char_name, char_gender,
                                      species_master_data, classes_master_data, save_player_data_func):
    """Applies chosen character details and stats to the player_dict."""
    player_dict["species"] = species_id
    player_dict["class"] = class_id
    player_dict["name"] = char_name
    player_dict["gender"] = char_gender

    class_info = classes_master_data[class_id]
    species_info = species_master_data[species_id]
    
    class_stats = class_info["base_stats"]
    species_bonuses = species_info["stat_bonuses"]

    player_dict["max_hp"] = class_stats["hp"] + species_bonuses.get("hp_bonus", 0)
    player_dict["hp"] = player_dict["max_hp"]
    player_dict["attack_power"] = class_stats["attack_power"] + species_bonuses.get("attack_bonus", 0)
    player_dict["special_power"] = class_stats.get("special_power", 0) + species_bonuses.get("special_power_bonus", 0)
    player_dict["special_moves"] = dict(class_info.get("special_moves", {})) 
    player_dict["special_cooldowns"] = {move_id: 0 for move_id in player_dict["special_moves"]}    
    player_dict["inventory"] = ["simple_knife", "blank_map_scroll"] 
    player_dict["coins"] = 0 
    player_dict["level"] = 1 
    player_dict["xp"] = 0
    player_dict["xp_to_next_level"] = 100 
    player_dict["equipment"] = { 
        "head": None, "shoulders": None, "chest": None, "hands": None,
        "legs": None, "feet": None, "main_hand": None, "off_hand": None
    }
    player_dict["flags"] = {} 

    print(f"\nCharacter '{player_dict['name']}' ({player_dict['gender']} {species_info['name']} {class_info['name']}) created!")
    # The save_player_data_func (which is save_player_data from the main script) now expects player_dict as the first arg.
    save_player_data_func(player_dict, reason_for_save=f"Character '{player_dict['name']}' created and initial state saved") 

    return True

def award_item_to_player(player_dict, items_master_data, item_id_to_give, source="unknown", log_event_func=None):
    if not isinstance(item_id_to_give, str):
        error_msg = "[Error] Invalid item_id provided to award_item_to_player."
        print(error_msg)
        return error_msg 
    player_dict["inventory"].append(item_id_to_give)
    item_details = items_master_data.get(item_id_to_give, {})
    display_name = item_details.get("name", item_id_to_give.replace("_", " ").capitalize())
    success_msg = f"You have acquired: {display_name}."
    print(success_msg)
    if log_event_func:
        log_event_func("item_acquisition", {
            "item_id": item_id_to_give, "item_name": display_name, "source": source,
            "location_id": player_dict.get("current_location_id")
        })
    return success_msg

def remove_item_from_player_inventory(player_dict, items_master_data, item_id_to_remove, source="unknown", log_event_func=None):
    if item_id_to_remove in player_dict["inventory"]:
        player_dict["inventory"].remove(item_id_to_remove)
        item_details = items_master_data.get(item_id_to_remove, {})
        display_name = item_details.get("name", item_id_to_remove.replace("_", " ").capitalize())
        if log_event_func:
            log_event_func("item_removal", {
                "item_id": item_id_to_remove, "item_name": display_name,
                "source": source, "location_id": player_dict.get("current_location_id")
            })
        return True
    return False