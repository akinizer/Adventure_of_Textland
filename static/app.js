let creationStep = 'species'; // 'species', 'class', 'name_gender', 'done'
let chosenSpecies = null;
let chosenClass = null;
let discoveredDeadEnds = {}; // Object to store: e.g., { "locationId_direction": true }
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
    let modalOverlay = document.getElementById('custom-modal-overlay');
    if (modalOverlay) {
        modalOverlay.remove();
    } else { // Fallback to check for the world map modal ID specifically
        modalOverlay = document.getElementById('world-map-modal-overlay');
        if (modalOverlay) modalOverlay.remove();
    }

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
                button.textContent = `${charData.display_name} (Lvl ${charData.level} ${charData.species} ${charData.class})`;
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
            <input type="text" id="charName" name="charName" required maxlength="${MAX_NAME_LENGTH}">
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
        discoveredDeadEnds = {}; // Reset for new character
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
        discoveredDeadEnds = {}; // Reset for loaded character
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
        discoveredDeadEnds = {}; // Reset for resumed session
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

async function toggleWorldMapModal() {
    const existingModal = document.getElementById('world-map-modal-overlay');
    if (existingModal) {
        closeModal(); // Assumes closeModal() removes any modal with 'custom-modal-overlay' or similar
        return;
    }

    if (!gameIsActiveForInput) { // Or check player.game_active if available client-side
        console.log("Game not active, cannot show world map.");
        // Optionally show a small message to the player
        return;
    }

    try {
        const response = await fetch('/api/get_world_map');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const mapData = await response.json();
        showWorldMapInModal(mapData);
    } catch (error) {
        console.error("Error fetching world map data:", error);
        // Optionally show an error to the player
        showMenuModal("Error", `Could not load world map: ${error.message}`, [{text: "Close", action: () => {}}]);
    }
}

function showWorldMapInModal(mapData) {
    const locations = mapData.locations || [];
    const currentLocationId = mapData.current_location_id;

    // Determine map dimensions dynamically or use fixed ones
    let maxX = 0;
    let maxY = 0;
    locations.forEach(loc => {
        if (loc.x > maxX) maxX = loc.x;
        if (loc.y > maxY) maxY = loc.y;
    });

    const gridWidth = maxX + 1; // 0-indexed
    const gridHeight = maxY + 1; // 0-indexed

    // Emojis
    const EMOJI_CURRENT = '📍'; // Or '🧍'
    const EMOJI_VISITED = '🟩';
    const EMOJI_UNVISITED_KNOWN = '🟨'; // If you want to distinguish known but unvisited
    const EMOJI_EMPTY = '⬜'; // For empty grid cells
    const OUTER_BORDER_COLOR = '#777'; 
    const NO_BORDER_STYLE = 'none'; // More forceful way to remove border

    let mapHTML = `<div class="world-map-grid-container" style="font-size: 1.5em; line-height: 1; text-align: center; max-height: 400px; overflow-y: auto;">`;
    mapHTML += `<table style="margin: auto; border-collapse: collapse;">`;

    for (let y = 0; y < gridHeight; y++) {
        mapHTML += '<tr>';
        for (let x = 0; x < gridWidth; x++) {
            const locationAtCell = locations.find(loc => loc.x === x && loc.y === y);
            let cellEmoji = EMOJI_EMPTY;
            let cellTitle = `(${x},${y})`;
            let borderStyles = {
                top: NO_BORDER_STYLE, // Default to no borders for all cells initially
                right: NO_BORDER_STYLE,
                bottom: NO_BORDER_STYLE,
                left: NO_BORDER_STYLE
            };
            
            if (locationAtCell) {
                cellTitle = `${locationAtCell.name} (${x},${y})`;
                if (locationAtCell.exits && Object.keys(locationAtCell.exits).length > 0) {
                    const exitDirections = Object.keys(locationAtCell.exits).join(', ');
                    cellTitle += ` (Exits: ${exitDirections})`;
                }

                // Determine base emoji
                if (locationAtCell.id === currentLocationId) {
                    cellEmoji = EMOJI_CURRENT;
                } else if (locationAtCell.visited) {
                    cellEmoji = EMOJI_VISITED;
                } else {
                    cellEmoji = EMOJI_UNVISITED_KNOWN; // Or EMOJI_EMPTY if you don't want to show unvisited
                }

                // Determine borders based on exits and visited status of neighbors
                if (locationAtCell.visited || locationAtCell.id === currentLocationId) { // Only visited/current can have borders
                    // Default to NO_BORDER_STYLE for visited/current cells.
                    // A border is added ONLY if the player has tried to go that way and failed.
                    borderStyles.top = NO_BORDER_STYLE;
                    borderStyles.right = NO_BORDER_STYLE;
                    borderStyles.bottom = NO_BORDER_STYLE;
                    borderStyles.left = NO_BORDER_STYLE;

                    if (discoveredDeadEnds[`${locationAtCell.id}_north`]) borderStyles.top = `1px solid ${OUTER_BORDER_COLOR}`;
                    if (discoveredDeadEnds[`${locationAtCell.id}_east`]) borderStyles.right = `1px solid ${OUTER_BORDER_COLOR}`;
                    if (discoveredDeadEnds[`${locationAtCell.id}_south`]) borderStyles.bottom = `1px solid ${OUTER_BORDER_COLOR}`;
                    if (discoveredDeadEnds[`${locationAtCell.id}_west`]) borderStyles.left = `1px solid ${OUTER_BORDER_COLOR}`;

                } else if (cellEmoji === EMOJI_UNVISITED_KNOWN) {
                    // Known but unvisited locations also default to NO_BORDER_STYLE (already set)
                } else { // EMOJI_EMPTY or any other unhandled case
                     // For truly empty cells, add a faint grid line
                     borderStyles.top = `1px solid #eee`; 
                     borderStyles.right = `1px solid #eee`;
                     borderStyles.bottom = `1px solid #eee`;
                     borderStyles.left = `1px solid #eee`;
                }
            }
            const cellStyle = `padding: 0px; border-top: ${borderStyles.top}; border-right: ${borderStyles.right}; border-bottom: ${borderStyles.bottom}; border-left: ${borderStyles.left}; width: 1.5em; height: 1.5em; text-align: center; vertical-align: middle;`;
            mapHTML += `<td title="${cellTitle}" style="${cellStyle}">${cellEmoji}</td>`;
        }
        mapHTML += '</tr>';
    }
    mapHTML += `</table>`;

    mapHTML += `<div style="margin-top: 10px; font-size: 0.8em;">Legend: ${EMOJI_CURRENT} Current, ${EMOJI_VISITED} Visited, ${EMOJI_UNVISITED_KNOWN} Known, ${EMOJI_EMPTY} Empty</div>`;
    mapHTML += `</div>`;


    // Use the existing showMenuModal to display this content
    showMenuModal("World Map", mapHTML, [{text: "Close", action: () => {}}]);
    const modalOverlay = document.getElementById('custom-modal-overlay');
    if (modalOverlay) modalOverlay.id = 'world-map-modal-overlay'; // So toggle can find it
}

function displaySceneData(data, actionStringEcho = null) {
    console.trace("displaySceneData called");
    console.log("Data received by displaySceneData:", JSON.parse(JSON.stringify(data))); // Log the data object
    const outputElement = document.getElementById('game-output');

    // Define formatGSBCurrency once at a scope accessible by components
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
        if (silver > 0) parts.push(`${silver}🔘`);
        if (copper > 0 || (gold === 0 && silver === 0)) parts.push(`${copper}🟠`);
        return parts.length > 0 ? parts.join(' ') : "0🟠";
    }

    // --- Component: Game Output Area ---
    function updateGameOutputComponent(data, actionStringEcho) {
        const outputElement = document.getElementById('game-output');
        // Logic to populate discoveredDeadEnds
        if (actionStringEcho && actionStringEcho.toLowerCase().startsWith('go ')) {
            console.log("[DeadEndDebug] 'go' action detected. Echo:", actionStringEcho); //1
            console.log("[DeadEndDebug] Server message:", data.message); //2
            console.log("[DeadEndDebug] Location ID from server (data.player_current_location_id):", data.player_current_location_id); //3

            if (data.message && data.message.toLowerCase().startsWith("you can't go")) { // Check #A
                console.log("[DeadEndDebug] Condition A MET: 'You can't go' message confirmed.");
                const directionAttempted = actionStringEcho.split(' ')[1].toLowerCase();
                const locIdFromWhichAttempted = data.player_current_location_id; 
                
                if (locIdFromWhichAttempted && directionAttempted) { // Check #B
                    console.log("[DeadEndDebug] Condition B MET: locIdFromWhichAttempted AND directionAttempted are present.");
                    const deadEndKey = `${locIdFromWhichAttempted}_${directionAttempted}`;
                    discoveredDeadEnds[deadEndKey] = true;
                    console.log("[DeadEndDebug] SUCCESS: Discovered dead end:", deadEndKey, "Current dead ends:", JSON.parse(JSON.stringify(discoveredDeadEnds)));
                } else {
                    console.error("[DeadEndDebug] FAILED Condition B: Missing locIdFromWhichAttempted or directionAttempted. locId:", locIdFromWhichAttempted, "dir:", directionAttempted);
                }
            } else {
                console.log("[DeadEndDebug] FAILED Condition A: Message ('" + data.message + "') did not indicate a blocked 'go' action.");
            }
        }
        if (!outputElement) return;

        outputElement.innerHTML = ''; // Clear previous output

        if (actionStringEcho) {
            const p_command_echo = document.createElement('p');
            p_command_echo.innerHTML = `<strong>&gt; ${actionStringEcho}</strong>`;
            outputElement.appendChild(p_command_echo);
        }
        if (data.location_name) {
            const p_loc_name = document.createElement('p');
            p_loc_name.innerHTML = `--- ${data.location_name} (HP: ${data.player_hp !== undefined ? data.player_hp : 'N/A'}/${data.player_max_hp !== undefined ? data.player_max_hp : 'N/A'}) ${data.player_name ? '('+data.player_name+')' : ''}`;
            outputElement.appendChild(p_loc_name);
        }
        if (data.description) { 
            const p_desc = document.createElement('p');
            p_desc.textContent = data.description;
            outputElement.appendChild(p_desc);
        }
        if (data.message && data.message.trim() !== "") {
            const p_message = document.createElement('p'); 
            p_message.textContent = data.message; 
            outputElement.appendChild(p_message);
        }
        if (data.map_lines && Array.isArray(data.map_lines)) { 
            data.map_lines.forEach(line => {
                const p_map_line = document.createElement('p');
                p_map_line.style.whiteSpace = "pre"; 
                p_map_line.textContent = line;
                outputElement.appendChild(p_map_line);
            });
        }
        outputElement.scrollTop = outputElement.scrollHeight; // Auto-scroll
    }
    // --- End Component: Game Output Area ---

    // --- Component: Feature Interactions Panel ---

    function updateFeatureInteractionsComponent(featuresData) {
        const featurePanel = document.getElementById('feature-interactions-panel');
        if (!featurePanel) return;

        // Ensure the panel has a container for buttons, or create one
        let featureButtonsContainer = featurePanel.querySelector('.dynamic-buttons-container');
        if (!featureButtonsContainer) {
            featureButtonsContainer = document.createElement('div');
            featureButtonsContainer.classList.add('dynamic-buttons-container'); // Add a class for easier selection
            // Find the paragraph and insert the container after it
            const pElement = featurePanel.querySelector('p');
            if (pElement) {
                pElement.insertAdjacentElement('afterend', featureButtonsContainer);
            } else {
                featurePanel.appendChild(featureButtonsContainer); // Fallback if p is not found
            }
        }
        featureButtonsContainer.innerHTML = ''; // Clear previous feature buttons

        if (featuresData && featuresData.length > 0) {
            featuresData.forEach(feature => {
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
    }
    // --- End Component: Feature Interactions Panel ---

    // --- Component: Room Items Panel ---
    function updateRoomItemsComponent(itemsData) {
        const itemsPanel = document.getElementById('room-items-panel');
         if (!itemsPanel) return;
        // Ensure the panel has a container for buttons, or create one
        let itemsButtonsContainer = itemsPanel.querySelector('.dynamic-buttons-container');
        if (!itemsButtonsContainer) {
            itemsButtonsContainer = document.createElement('div');
            itemsButtonsContainer.classList.add('dynamic-buttons-container'); // Add a class
             const pElement = itemsPanel.querySelector('p');
            if (pElement) { pElement.insertAdjacentElement('afterend', itemsButtonsContainer); } else { itemsPanel.appendChild(itemsButtonsContainer); }
        }
        itemsButtonsContainer.innerHTML = ''; // Clear previous item buttons

        if (itemsData && itemsData.length > 0) {
            itemsData.forEach(item => { // item is now {id: "...", name: "..."}
                const itemButton = document.createElement('button');
                itemButton.textContent = `Take ${item.name}`;
                itemButton.onclick = () => performAction(`take ${item.id}`); // Send item_id
                itemsButtonsContainer.appendChild(itemButton);
            });
            itemsPanel.style.display = 'block';
        } else {
            itemsPanel.style.display = 'none';
        }
    }
    // --- End Component: Room Items Panel ---

    // --- Component: Dynamic Header ---
    function updateDynamicHeaderComponent(headerData) {
        const headerInfoDiv = document.getElementById('dynamic-header-info');
        if (!headerInfoDiv) return;

        // Now uses the formatGSBCurrency defined at the higher scope
        headerInfoDiv.textContent = `Location: ${headerData.location_name || 'Unknown'} | Player: ${headerData.player_name || 'Adventurer'} - Level: ${headerData.player_level !== undefined ? headerData.player_level : 'N/A'} (XP: ${headerData.player_xp !== undefined ? headerData.player_xp : 'N/A'}/${headerData.player_xp_to_next_level !== undefined ? headerData.player_xp_to_next_level : 'N/A'}) - Coins: ${formatGSBCurrency(headerData.player_coins)} - Diamond: 0💎`;
    }
    // --- End Component: Dynamic Header ---

    // --- Component: Character Panel ---
    function updateCharacterPanelComponent(playerData) {
        const charPanelName = document.getElementById('char-panel-name');
        const charPanelClass = document.getElementById('char-panel-class');
        const charPanelSpecies = document.getElementById('char-panel-species');
        const charPanelLevel = document.getElementById('char-panel-level');
        const charPanelXp = document.getElementById('char-panel-xp');
        const charPanelHp = document.getElementById('char-panel-hp');
        const charPanelAttack = document.getElementById('char-panel-attack');
        const charPanelCoins = document.getElementById('char-panel-coins');
        const equipGrid = document.getElementById('char-panel-equipment-grid');

        if (charPanelName) charPanelName.textContent = `Name: ${playerData.player_name || 'N/A'}`;
        if (charPanelClass) charPanelClass.textContent = `Class: ${playerData.player_class_name || 'N/A'}`;
        if (charPanelSpecies) charPanelSpecies.textContent = `Species: ${playerData.player_species_name || 'N/A'}`;
        if (charPanelLevel) charPanelLevel.textContent = `Level: ${playerData.player_level !== undefined ? playerData.player_level : 'N/A'}`;
        if (charPanelXp) charPanelXp.textContent = `XP: ${playerData.player_xp !== undefined ? playerData.player_xp : 'N/A'} / ${playerData.player_xp_to_next_level !== undefined ? playerData.player_xp_to_next_level : 'N/A'}`;
        if (charPanelHp) charPanelHp.textContent = `HP: ${playerData.player_hp !== undefined ? playerData.player_hp : 'N/A'} / ${playerData.player_max_hp !== undefined ? playerData.player_max_hp : 'N/A'}`;
        if (charPanelAttack) charPanelAttack.textContent = `Attack: ${playerData.player_attack_power !== undefined ? playerData.player_attack_power : 'N/A'}`;
        if (charPanelCoins) charPanelCoins.textContent = `Coins: ${formatGSBCurrency(playerData.player_coins)}`;

        const equipSlots = {
            head: document.getElementById('char-panel-equip-head'),
            shoulders: document.getElementById('char-panel-equip-shoulders'),
            chest: document.getElementById('char-panel-equip-chest'),
            hands: document.getElementById('char-panel-equip-hands'),
            legs: document.getElementById('char-panel-equip-legs'),
            feet: document.getElementById('char-panel-equip-feet'),
            main_hand: document.getElementById('char-panel-equip-main_hand'),
            off_hand: document.getElementById('char-panel-equip-off_hand'),
            neck: document.getElementById('char-panel-equip-neck'), // New
            back: document.getElementById('char-panel-equip-back'),   // New
            trinket1: document.getElementById('char-panel-equip-trinket1'), // New
            trinket2: document.getElementById('char-panel-equip-trinket2')  // New
        };
        const equipSlotPrefixes = {
            head: "H", shoulders: "S", chest: "C", hands: "G", legs: "L", feet: "F", 
            main_hand: "MH", off_hand: "OH", neck: "N", back: "B", 
            trinket1: "T1", trinket2: "T2" // New
        };

        for (const slotKey in equipSlots) {
            if (equipSlots[slotKey]) {
                const itemName = playerData.player_equipment && playerData.player_equipment[slotKey] ? playerData.player_equipment[slotKey] : 'Empty';
                const prefix = equipSlotPrefixes[slotKey] || slotKey.substring(0,1).toUpperCase();
                equipSlots[slotKey].textContent = `${prefix}: ${itemName}`;

                if (playerData.player_equipment && playerData.player_equipment[`${slotKey}_id`]) {
                     equipSlots[slotKey].setAttribute('data-item-id', playerData.player_equipment[`${slotKey}_id`]);
                     equipSlots[slotKey].style.borderColor = '#007bff'; 
                } else {
                     equipSlots[slotKey].removeAttribute('data-item-id');
                     equipSlots[slotKey].style.borderColor = '#b0b0b0'; 
                }
            }
        }
        // Re-attach double-click listeners to equipped slots within this component
        if (equipGrid) {
            equipGrid.querySelectorAll('.equip-slot[data-item-id]').forEach(slotElement => {
                // Remove old listener to prevent duplicates if any, then add new one
                slotElement.removeEventListener('dblclick', handleUnequipDoubleClick); // Ensure handleUnequipDoubleClick is accessible
                slotElement.addEventListener('dblclick', handleUnequipDoubleClick);
            });
        }
    }
    // --- End Component: Character Panel ---

    // --- Component: Game Actions Panel ---
    function updateGameActionsComponent(data) {
        const gameActionsPanel = document.getElementById('game-actions-panel');
        if (!gameActionsPanel) return;

        // Ensure a container for buttons exists, or create one
        let buttonsContainer = gameActionsPanel.querySelector('.dynamic-buttons-container');
        if (!buttonsContainer) {
            buttonsContainer = document.createElement('div');
            buttonsContainer.classList.add('dynamic-buttons-container');
            const pElement = gameActionsPanel.querySelector('p'); // Assuming a <p><strong>Game Actions:</strong></p> exists
            if (pElement) { pElement.insertAdjacentElement('afterend', buttonsContainer); } else { gameActionsPanel.appendChild(buttonsContainer); }
        }
        buttonsContainer.innerHTML = ''; // Clear previous buttons

        if (data.can_save_in_city) {
            const saveButton = document.createElement('button');
            saveButton.textContent = 'Save Game';
            saveButton.onclick = async () => { // Make sure this async logic is appropriate here or refactored
                const response = await fetch('/api/save_game_state', { method: 'POST' });
                const result = await response.json();
                appendMessageToOutput(result.message); // appendMessageToOutput needs to be accessible
            };
            buttonsContainer.appendChild(saveButton);
            gameActionsPanel.style.display = 'block';
        } else {
            gameActionsPanel.style.display = 'none';
        }
    }
    // --- End Component: Game Actions Panel ---

    // --- Component: Inventory Modal ---
    function updateInventoryModalComponent(data, actionStringEcho) {
        if (actionStringEcho === 'inventory') {
            let sortButtonHTML = `<div style="margin-bottom: 10px;"><button onclick="performAction('sort_inventory_by_id_action')">Sort by ID</button></div>`;
            let inventoryGridHTML = '<div id="modal-backpack-grid" style="display: grid; grid-template-columns: repeat(8, 1fr); grid-auto-rows: minmax(60px, auto); gap: 5px; padding: 10px; max-height: 400px; overflow-y: auto;">';

            if (data.inventory_list && data.inventory_list.length > 0) {
                inventoryGridHTML += '</div>'; // Close the grid div
            } else {
                inventoryGridHTML = "<p>Your inventory is empty.</p>"; // If empty, replace grid with message
            }
            
            let modalDisplayContent = sortButtonHTML + inventoryGridHTML;
            showMenuModal("Backpack", modalDisplayContent, [{text: "Close", action: () => {}}]);
            
            // Populate the grid if inventory_list is available and not empty
            if (data.inventory_list && data.inventory_list.length > 0) {
                renderOrUpdateModalBackpackGrid(data.inventory_list);
            }
            // Clear any default message like "Your inventory is empty" from main output if modal is shown
            if (document.getElementById('game-output') && data.message === "Your inventory is empty.") {
                data.message = ""; // This might need careful handling if message is also used by game output component
            }

        } else if (actionStringEcho === 'sort_inventory_by_id_action' && data.inventory_list) {
            const modalGrid = document.getElementById('modal-backpack-grid');
            // Check if the modal is actually visible (custom-modal-overlay exists)
            if (modalGrid && document.getElementById('custom-modal-overlay')) {
                renderOrUpdateModalBackpackGrid(data.inventory_list);
            }
        }
    }
    // --- End Component: Inventory Modal ---

    // Helper function to render or update the backpack grid within the modal
    function renderOrUpdateModalBackpackGrid(itemsToDisplay) {
        const modalGridContainer = document.getElementById('modal-backpack-grid');
        if (!modalGridContainer) return; // Modal or grid not found

        let gridHTML = '';
        const totalSlots = 48; // 6 rows * 8 columns
        for (let i = 0; i < totalSlots; i++) {
            if (i < itemsToDisplay.length) {
                const item = itemsToDisplay[i]; // item is an object {id, name, type, equip_slot}
                let slotHTML = `<div class="inventory-slot" title="${item.name}" data-item-id="${item.id}"`;
                if (item.equip_slot) { // Mark equippable items visually
                    slotHTML += ` style="border-color: #007bff;"`; // Example: blue border for equippable
                }
                slotHTML += `>${item.name}</div>`;
                gridHTML += slotHTML;
            } else {
                gridHTML += `<div class="inventory-slot">&nbsp;</div>`; // Empty slot
            }
        }
        modalGridContainer.innerHTML = gridHTML;

        // Re-attach double-click listeners to the newly rendered items in the modal
        modalGridContainer.querySelectorAll('.inventory-slot[data-item-id]').forEach(slotElement => {
            slotElement.addEventListener('dblclick', function(event) {
                event.preventDefault(); 
                const itemId = this.getAttribute('data-item-id');
                performAction(`equip ${itemId}`);
                closeModal(); 
            });
        });
    }

    // Define the unequip double-click handler function within displaySceneData scope
    // This needs to be accessible by updateCharacterPanelComponent
    function handleUnequipDoubleClick(event) {
        event.preventDefault(); 
        const itemId = this.getAttribute('data-item-id');
        // const slotKey = this.getAttribute('data-slot-key'); // slotKey is on the element itself
        console.log(`Double-clicked equipped item ID: ${itemId}`);
        if (itemId) performAction(`unequip ${itemId}`);
    }

        updateInventoryModalComponent(data, actionStringEcho);
        updateGameOutputComponent(data, actionStringEcho);

        // Call the component function to update the Dynamic Header
        updateDynamicHeaderComponent(data); // Pass the whole data object, component will pick what it needs

        // Call the component function to update the Character Panel
        updateCharacterPanelComponent(data); 

        // Call the component functions to update Feature and Item panels
        updateFeatureInteractionsComponent(data.interactable_features);
        updateRoomItemsComponent(data.room_items);

        // Call the component function to update the Game Actions Panel
        updateGameActionsComponent(data);

        // --- Component: NPC Interactions Panel ---
        function updateNPCInteractionPanelComponent(npcsData) {
            const npcPanel = document.getElementById('npc-interactions-panel');
            if (!npcPanel) return;

            let npcButtonsContainer = npcPanel.querySelector('.dynamic-buttons-container');
            if (!npcButtonsContainer) {
                npcButtonsContainer = document.createElement('div');
                npcButtonsContainer.classList.add('dynamic-buttons-container');
                const pElement = npcPanel.querySelector('p');
                if (pElement) {
                    pElement.insertAdjacentElement('afterend', npcButtonsContainer);
                } else {
                    npcPanel.appendChild(npcButtonsContainer);
                }
            }
            npcButtonsContainer.innerHTML = ''; // Clear previous NPC buttons

            if (npcsData && npcsData.length > 0) {
                npcsData.forEach(npc => {
                    const npcButton = document.createElement('button');
                    npcButton.textContent = `Talk to ${npc.name}`;
                    // Send action "talk <npc_id>" (npc.id should be the unique identifier)
                    npcButton.onclick = () => performAction(`talk ${npc.id}`); 
                    npcButtonsContainer.appendChild(npcButton);
                });
                npcPanel.style.display = 'block';
            } else {
                npcPanel.style.display = 'none';
            }
        }
        // --- End Component: NPC Interactions Panel ---
        updateNPCInteractionPanelComponent(data.npcs_in_room);
}

// Initial load
window.onload = () => {
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
        if (gameIsPaused && document.getElementById('custom-modal-overlay') && (event.key !== 'p' && event.key !== 'P')) {
            // Potentially block other keys if needed
        }
        if ((event.key === 'p' || event.key === 'P') && !event.repeat && gameIsActiveForInput) {
            togglePauseGame();
        }
        // Add listener for 'M' key to toggle world map
        if ((event.key === 'm' || event.key === 'M') && !event.repeat && gameIsActiveForInput) {
            event.preventDefault(); // Prevent 'm' from typing if in an input field (though unlikely here)
            toggleWorldMapModal();
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