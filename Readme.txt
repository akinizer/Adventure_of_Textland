# Adventure of Textland

Adventure of Textland is an interactive text-based RPG written in Python, with an optional browser-based interface. Embark on a journey, create your character, explore different zones, interact with NPCs and features, and manage your inventory.

## Features

- **Character Creation & Management:**
    - Choose from multiple species (Human, Elf, Orc) with unique stat bonuses and backstories.
    - Select a class (Warrior, Mage, Rogue) with distinct base stats, special moves, and starter items.
    - Name your character (with validation for length, allowed characters, and RPG-style naming conventions) and choose a gender (Male/Female).
    - Character data is saved locally, allowing you to:
        - View a list of existing characters (displaying name, species, class).
        - Load an existing character to continue their adventure.
        - Create new characters.
        - Delete existing characters with a confirmation prompt.
- **Gameplay:**
    - Explore a world comprised of different locations and zones.
    - Interact with Non-Player Characters (NPCs) for dialogue, quests (basic implementation), and combat.
    - Engage in turn-based combat with hostile NPCs.
        - Basic attacks.
        - Class-specific special moves with cooldowns.
        - Deflect option to reduce incoming damage.
    - Interact with environmental features (e.g., search, open chests).
        - The browser interface dynamically displays buttons for interactable room features (e.g., "Open Worn Crate").
    - Collect items and manage your inventory.
    - Basic map system to view your current zone.
- **Dual Interface:**
    - **Terminal Play:** Classic text adventure experience with full character management.
    - **Browser Interface:** Play through a web browser with a more visual, button-driven UI.
        - Character creation, loading, and deletion.
        - Dynamic display of room descriptions, inventory, map, and interactable room features.
        - Buttons for common actions.
        - Pause/Unpause game (P key).
        - In-game menu (gear icon) to return to the main character selection screen.
- **Data Persistence:**
    - Player character data (stats, inventory, location, flags) is saved in JSON format in a `player_data` directory, organized by character name.

## Prerequisites

- Python 3.x
- Flask (optional, for browser interface): `pip install Flask` (Run this in your terminal/command prompt)

## How to Run

### Terminal Mode:
1.  Open a terminal or command prompt.
2.  Navigate to the directory where `Adventure of Textland.py` is saved.
3.  Run the script: `python "Adventure of Textland.py"`
    - On first run or if no characters exist, you'll be prompted to create a new character.
    - If characters exist, you'll see a list to load an existing character, create a new one, or delete an existing one.

### Browser Mode:
1.  **Install Flask (if not already installed):**
    ```bash
    pip install Flask
    ```
2.  Open a terminal or command prompt.
3.  Navigate to the directory where `Adventure of Textland.py` is saved.
4.  Run the script with the `--browser` flag:
    ```bash
    python "Adventure of Textland.py" --browser
    ```
    - This will start a local web server and attempt to open the game in your default web browser (typically at `http://127.0.0.1:5000/`).
    - The browser will present a character selection/creation screen.
    - The terminal window will show server logs and any Python `print` statements.

### Command-Line Arguments:
- `--browser`: Launches the game with the browser interface.
- `--autostart`:
    - In terminal mode: If existing characters are found, it attempts to load the first one. Otherwise, it starts new character creation.
    - In browser mode: This flag is less impactful as the browser handles its own startup flow (character selection/creation).

## Basic Commands (Terminal)

-   `!start`: Begins the adventure (if not already started).
-   `!quit`: Exits the game.
-   `!start_browser`: Attempts to launch the browser interface from within the terminal game (Flask must be installed).
-   `!map`: Displays a map of the current zone.
-   `look`: Describes your current surroundings, including visible items, NPCs, and features.
-   `go <direction>` (e.g., `go north`, `go south`): Moves your character.
-   `take <item_name>`: Picks up an item from the room.
-   `inventory` or `i`: Shows the items you are carrying.
-   `talk <npc_name>`: Initiates a conversation with an NPC.
-   `use <item_name> on <feature_name>`: Uses an item on a feature (e.g., `use rusty_key on chest`).
-   `<action> <feature_name>` (e.g., `search loose_rocks`, `open worn_crate`): Interacts with an environmental feature.
-   **Combat Commands (when in combat):**
    -   `attack`: Perform a basic attack.
    -   `special <move_name>` (e.g., `special power_strike`): Use a special ability.
    -   `deflect`: Attempt to reduce damage from the next enemy attack.
    -   `item <item_name>`: Use a consumable item (e.g., `item healing_potion`).

## Basic Controls

### Terminal:
-   **Navigation & Interaction:** Type commands as listed above (e.g., `go north`, `look`, `take apple`, `open worn_crate`).
-   **Character Selection:** Use numbers to select from the list of existing characters, create a new one, or delete a character.
-   **Dialogue/Combat Choices:** Type the number corresponding to your desired option.

### Browser:
-   **Navigation & Interaction:** Click the on-screen buttons for movement, common actions (Look, Inventory, Map), and context-specific feature interactions (dynamically shown under "Room Features").
-   **Character Selection/Creation:** Click buttons to load, delete, or create new characters, and make choices for species, class, name, and gender.
-   **Pause/Unpause:** Press the "P" key.
-   **Game Menu:** Click the gear icon (⚙️) in the top-right corner to access options like "Main Menu".

## Development Notes

-   The game state is managed globally in Python dictionaries.
-   The browser interface communicates with the Python backend via a Flask web server and JSON API endpoints.
-   Player data (character details, stats, inventory, current location, flags) is saved locally in a `player_data` directory, with each character having their own sub-directory and `character_creation.json` file (this file effectively acts as the save file).
