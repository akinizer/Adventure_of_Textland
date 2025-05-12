# d:\GeneralRepository\PythonProjects\AdventureOfTextland\entities.py

class Player:
    def __init__(self, name="Adventurer", gender="Unspecified"):
        self.name = name
        self.gender = gender
        self.species_id = None
        self.class_id = None

        self.current_location_id = None
        self.inventory = []
        self.game_active = False
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
            "legs": None, "feet": None, "main_hand": None, "off_hand": None
        }
        self.is_paused = False

    def move_to(self, new_location_id):
        self.current_location_id = new_location_id
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

    def equip_item(self, item_id, slot, item_name="Unknown Item"):
        # Basic equip, assumes item is valid for slot.
        # More complex logic (unequipping old, stat changes) would go here or be called from here.
        self.equipment[slot] = item_id
        # print(f"{item_name} equipped to {slot}.")

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
            self.max_hp += 10
            self.hp = self.max_hp # Full heal
            self.attack_power += 2

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