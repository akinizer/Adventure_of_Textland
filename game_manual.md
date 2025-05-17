# Adventure of Textland - Game Manual

## Launch Options
1. Terminal Only:
```
python "Adventure of Textland.py"
```

2. Terminal with Auto-start:
```
python "Adventure of Textland.py" --autostart
```

3. Browser Interface:
```
python "Adventure of Textland.py" --browser
```

4. Browser with Auto-start:
```
python "Adventure of Textland.py" --browser --autostart
```

## Terminal Game Usage
1. **Game Start**
   - Launch the game using one of the terminal commands above
   - Choose to load existing character or create new one
   - Type '!start' if game isn't auto-started

2. **Basic Commands**
   - `look` - Examine your surroundings
   - `inventory` or `i` - Check your items
   - `!map` - View zone map
   - `examine` or `survey` - Get location details
   - `go <direction>` - Move in specified direction

3. **Item Management**
   - `take <item>` - Pick up items
   - `use <item> on <target>` - Use items on objects
   - `equip <item>` - Wear/wield equipment
   - `unequip <item>` - Remove equipment

4. **Interaction**
   - `talk <npc>` - Speak with NPCs
   - `open <object>` - Open containers/doors
   - `enter city` - Enter city detailed map
   - `exit city` - Leave city detailed map

5. **System Commands**
   - `!save` - Save progress (in cities only)
   - `!quit` - Exit game
   - `!start_browser` - Launch web interface

## Browser Game Usage
1. **Access**
   - Launch with `--browser` flag
   - Browser opens to http://127.0.0.1:5000/
   - Or manually navigate to URL

2. **Interface Elements**
   - Character panel (top)
   - Main game area (center)
   - Action buttons (various locations)
   - Zone map (side panel)
   - Inventory panel (toggleable)

3. **Navigation**
   - Click directional buttons
   - Type commands in text input
   - Use map for location reference
   - Click "Enter City"/"Exit City" when available

4. **Inventory Management**
   - Click items to view options
   - "Equip" button on equippable items
   - "Use" button on usable items
   - "Take" button for items in location

5. **Interactions**
   - Click NPCs to interact
   - Click features to interact
   - Use command input for specific actions
   - Click save button in cities

## Map Legend
- `@` - Your current location
- `V` - Visited location
- `?` - Known but unvisited location
- `.` - Empty space

## Notes
- Save only works in city zones
- Maximum of 12 characters per account
- Browser interface requires Flask installed
- Terminal always available as fallback