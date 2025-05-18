# d:\GeneralRepository\PythonProjects\AdventureOfTextland\entities.py

class Player:
    def __init__(self, name="Adventurer", gender="Unspecified"):
        self.name = name
        self.gender = gender
        self.species_id = None
        self.class_id = None

        self.current_location_id = None
        # For detailed city maps
        self.current_map_type = "zone"  # Can be "zone" or "city"
        self.current_city_id = None     # e.g., "riverford", "eldoria"
        self.current_city_x = None
        self.current_city_y = None
        self.last_zone_location_id = None # To remember the zone map node when entering a city
        self.inventory = []
        self.game_active = False

        # Base stats (from class/species, set during character creation)
        self.base_max_hp = 0
        self.base_attack_power = 0
        # Derived stats (calculated from base + equipment)
        self.hp = 0
        self.max_hp = 0
        self.attack_power = 0

        self.special_power = 0
        self.special_moves = {}
        self.special_cooldowns = {}
        self.combat_target_id = None
        self.is_deflecting = False
        self.dialogue_npc_id = None
        self.dialogue_options_pending = {}
        self.flags = {}
        self.coins = 0
        self.level = 1
        self.xp = 0
        self.xp_to_next_level = 100
        self.equipment = {
            "head": None, "shoulders": None, "chest": None, "hands": None,
            "legs": None, "feet": None, "main_hand": None, "off_hand": None,
            "neck": None,
            "back": None,
            "trinket1": None, # New Trinket Slot 1
            "trinket2": None  # New Trinket Slot 2
        }
        self.is_paused = False
        self.visited_locations = set() # To store IDs of visited locations
        self.preferences = {
            "auto_equip_from_inventory_panel_enabled": False
        }

    def _recalculate_derived_stats(self, items_master_data):
        """Recalculates derived stats based on base stats, class/species, and equipment."""
        # Start with base stats (which should include class/species contributions from creation)
        current_max_hp = self.base_max_hp
        current_attack_power = self.base_attack_power
        # Add other stats like defense, special_power if they can be modified by equipment

        for slot, item_id in self.equipment.items():
            if item_id:
                item_details = items_master_data.get(item_id, {})
                bonuses = item_details.get("stat_bonuses", {})
                current_max_hp += bonuses.get("max_hp", 0)
                current_attack_power += bonuses.get("attack_power", 0)
                # Add other stat bonuses here

        self.max_hp = current_max_hp
        self.attack_power = current_attack_power

        # Ensure current HP doesn't exceed new max_hp
        if self.hp > self.max_hp:
            self.hp = self.max_hp
        # print(f"Stats recalculated: MaxHP={self.max_hp}, Attack={self.attack_power}")

    def set_active(self, is_active):
        self.game_active = is_active

    def enter_combat(self, target_id):
        self.combat_target_id = target_id
        self.end_dialogue() # Cannot be in dialogue and combat

    def leave_combat(self):
        self.combat_target_id = None

    def start_dialogue(self, npc_id, options):
        self.dialogue_npc_id = npc_id
        self.dialogue_options_pending = options
        self.leave_combat() # Cannot be in combat and dialogue

    def end_dialogue(self):
        self.dialogue_npc_id = None
        self.dialogue_options_pending = {}

    def move_to(self, new_location_id):
        self.current_location_id = new_location_id
        self.visited_locations.add(new_location_id) # Record visited location
        # print(f"{self.name} moves to {new_location_id}.")

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp < 0:
            self.hp = 0
        # print(f"{self.name} takes {amount} damage. HP is now {self.hp}/{self.max_hp}")

    def heal(self, amount):
        self.hp += amount
        if self.hp > self.max_hp:
            self.hp = self.max_hp
        # print(f"{self.name} heals for {amount}. HP is now {self.hp}/{self.max_hp}")

    def add_item_to_inventory(self, item_id):
        self.inventory.append(item_id)
        # print(f"{item_id} added to inventory.")

    def remove_item_from_inventory(self, item_id):
        if item_id in self.inventory:
            self.inventory.remove(item_id)
            # print(f"{item_id} removed from inventory.")
            return True
        return False

    def equip_item(self, item_id_to_equip, slot_to_equip_to, items_master_data, log_event_func=None):
        """Equips an item, handling unequip of existing item and inventory."""
        item_details = items_master_data.get(item_id_to_equip)
        
        item_equip_slot_type = item_details.get("equip_slot")
        can_equip_to_chosen_slot = (item_equip_slot_type == slot_to_equip_to) or \
                                   (item_equip_slot_type == "trinket" and slot_to_equip_to in ["trinket1", "trinket2"])

        if not item_details or not can_equip_to_chosen_slot:
            return f"Cannot equip {item_details.get('name', item_id_to_equip)} to {slot_to_equip_to}. Item is for {item_equip_slot_type}."
        
        message = ""
        # Unequip current item in that slot, if any
        currently_equipped_item_id = self.equipment.get(slot_to_equip_to)
        if currently_equipped_item_id:
            self.add_item_to_inventory(currently_equipped_item_id)
            if log_event_func:
                log_event_func("item_unequipped", {"item_id": currently_equipped_item_id, "slot": slot_to_equip_to, "moved_to_inventory": True, "player_name": self.name})
            message += f"You unequipped {items_master_data.get(currently_equipped_item_id,{}).get('name', currently_equipped_item_id)}.\n"
        
        self.equipment[slot_to_equip_to] = item_id_to_equip
        self.remove_item_from_inventory(item_id_to_equip) # Assumes item was in inventory
        message += f"You equipped {item_details.get('name', item_id_to_equip)}."
        self._recalculate_derived_stats(items_master_data)
        if log_event_func:
            log_event_func("item_equipped", {"item_id": item_id_to_equip, "slot": slot_to_equip_to, "player_name": self.name})
        return message

    def unequip_item(self, slot_key, items_master_data, log_event_func=None):
        """Unequips an item from a given slot and adds it to inventory."""
        item_id_to_unequip = self.equipment.get(slot_key)
        if item_id_to_unequip:
            self.add_item_to_inventory(item_id_to_unequip)
            self.equipment[slot_key] = None
            item_name = items_master_data.get(item_id_to_unequip, {}).get("name", item_id_to_unequip)
            self._recalculate_derived_stats(items_master_data)
            if log_event_func:
                log_event_func("item_unequipped", {"item_id": item_id_to_unequip, "slot": slot_key, "moved_to_inventory": True, "player_name": self.name})
            return f"You unequipped {item_name} from your {slot_key.replace('_', ' ')} slot."
        return f"Nothing equipped in {slot_key.replace('_', ' ')} slot."

    def add_xp(self, amount, log_event_func=None):
        """Awards XP to the player and handles leveling up."""
        if not self.game_active:
            return

        self.xp += amount
        print(f"You gained {amount} XP.")
        if log_event_func:
            log_event_func("xp_gained", {"amount": amount, "current_xp": self.xp, "level": self.level, "player_name": self.name})

        leveled_up_this_cycle = False
        while self.xp >= self.xp_to_next_level:
            leveled_up_this_cycle = True
            self.level += 1
            self.xp -= self.xp_to_next_level
            self.xp_to_next_level = int(self.xp_to_next_level * 1.5)

            # Apply level-up bonuses
            self.base_max_hp += 10 # Increase base stat
            self.base_attack_power += 2 # Increase base stat
            # Derived stats (max_hp, attack_power) will be updated by _recalculate_derived_stats()
            # which should be called after this if items_master_data is available, or on next equip/unequip.
            self.hp = self.base_max_hp # For now, heal to new base_max_hp. Full recalc will adjust.

            print(f"\n*** LEVEL UP! You are now Level {self.level}! ***")
            print(f"Max HP increased to {self.max_hp}. Attack Power increased to {self.attack_power}.")
            print(f"XP to next level: {self.xp_to_next_level}. Current XP: {self.xp}.")
            if log_event_func:
                log_event_func("level_up", {"new_level": self.level, "max_hp": self.max_hp, "attack_power": self.attack_power, "player_name": self.name})
        return leveled_up_this_cycle

    def add_coins(self, amount, log_event_func=None, source="unknown"):
        self.coins += amount
        if log_event_func:
            log_event_func("currency_gained", {"amount": amount, "unit": "copper", "source": source, "player_name": self.name, "location_id": self.current_location_id})
        # print(f"Gained {amount} coins. Total: {self.coins}")

    def update_special_cooldowns(self):
        for move in self.special_cooldowns:
            if self.special_cooldowns[move] > 0:
                self.special_cooldowns[move] -= 1

    def set_deflecting(self, is_deflecting_flag):
        self.is_deflecting = is_deflecting_flag

    def handle_defeat(self):
        print("\nYour vision fades... You have been defeated.")
        print("--- GAME OVER ---")
        self.set_active(False)
        self.end_dialogue()
        self.leave_combat()

# d:\GeneralRepository\PythonProjects\AdventureOfTextland\entities.py
# ... (Player class above) ...

class NPC:
    def __init__(self, npc_id, name, description, dialogue="...", npc_type="neutral", hostile=False,
                 hp=10, max_hp=10, attack_power=1, loot=None,
                 dialogue_options=None, pre_combat_dialogue=None,
                 quest_item_needed=None, quest_reward_item=None, dialogue_after_quest_complete=None,
                 dialogue_after_quest_incomplete=None, quest_reward_currency=0, wares=None, stock=None):
        self.id = npc_id
        self.name = name
        self.description = description
        self.dialogue = dialogue # Default dialogue
        self.type = npc_type
        # Merchant specific attributes
        self.wares = wares if wares is not None else {}
        self.stock = stock if stock is not None else {}
        # Combat related attributes
        self.hostile = hostile
        self.hp = hp
        self.max_hp = max_hp
        self.attack_power = attack_power
        self.loot = loot if loot is not None else []
        self.dialogue_options = dialogue_options if dialogue_options is not None else {}
        self.pre_combat_dialogue = pre_combat_dialogue
        # Quest related attributes
        self.quest_item_needed = quest_item_needed
        self.quest_reward_item = quest_reward_item
        self.dialogue_after_quest_complete = dialogue_after_quest_complete
        self.dialogue_after_quest_incomplete = dialogue_after_quest_incomplete
        self.quest_reward_currency = quest_reward_currency

    def is_alive(self):
        return self.hp > 0

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp < 0:
            self.hp = 0
    
    def get_item_price(self, item_id):
        """Get price of an item if NPC sells it"""
        return self.wares.get(item_id)
        
    def has_stock(self, item_id):
        """Check if item is in stock"""
        stock_amount = self.stock.get(item_id, 0)
        return stock_amount == -1 or stock_amount > 0
        
    def reduce_stock(self, item_id):
        """Reduce stock after purchase"""
        if self.stock.get(item_id, 0) > 0:
            self.stock[item_id] -= 1
