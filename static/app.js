let creationStep = 'species'; // 'species', 'class', 'name_gender', 'done'
let chosenSpecies = null;
let chosenClass = null;
let discoveredDeadEnds = {}; // Object to store: e.g., { "locationId_direction": true }
let gameIsPaused = false; 
let commandNexusSetup = false; // Flag to ensure Command Nexus setup runs only once
let gameIsActiveForInput = false; // True when game interface is shown
const SESSION_STORAGE_GAME_ACTIVE_KEY = 'textRpgGameSessionActive';
const SESSION_STORAGE_CHAR_NAME_KEY = 'textRpgCharacterName';

 // Centralized pause/resume logic
function togglePauseGame() {
    const modalOverlay = document.getElementById('custom-modal-overlay');
    const modalTitleElement = modalOverlay ? modalOverlay.querySelector('h3') : null;

    if (gameIsPaused && modalTitleElement && modalTitleElement.textContent === "Game Paused") {
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
                <div class="modal-message-content">${message}</div> <!-- Changed <p> to <div> -->
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
        // Container for "Create New Character" button and dice
        const newCharOptionContainer = document.createElement('div');
        newCharOptionContainer.className = 'new-character-option'; // For styling alignment

        const newCharButton = document.createElement('button');
        newCharButton.textContent = "Create New Character";
        newCharButton.onclick = () => loadSpecies(); // Start new character creation flow
        newCharOptionContainer.appendChild(newCharButton);

        // Add the static dice image
        const diceImage = document.createElement('img');
        diceImage.id = 'static-dice-image';
        diceImage.className = 'dice-image-static'; // New class for styling the static image
        diceImage.src = 'static/images/dice_icon.png'; // CHANGE 'dice_icon.png' if your image has a different name
        diceImage.alt = 'Random Character';
        diceImage.title = 'Click to create a random character'; // Tooltip
        diceImage.style.cursor = 'pointer'; // Indicate it's clickable

        diceImage.onclick = async () => {
            console.log("Dice clicked - attempting auto character creation.");
            const creationArea = document.getElementById('character-creation-area');
            creationArea.innerHTML = '<h2>Creating Random Character...</h2><p>Please wait.</p>';

            try {
                // Fetch species and classes
                const [speciesResponse, classesResponse] = await Promise.all([
                    fetch('/get_species'),
                    fetch('/get_classes')
                ]);

                if (!speciesResponse.ok) throw new Error(`Failed to fetch species: ${speciesResponse.status}`);
                if (!classesResponse.ok) throw new Error(`Failed to fetch classes: ${classesResponse.status}`);

                const speciesList = await speciesResponse.json();
                const classList = await classesResponse.json();

                if (!speciesList || speciesList.length === 0) throw new Error("No species available for random selection.");
                if (!classList || classList.length === 0) throw new Error("No classes available for random selection.");

                // Randomly select
                const randomSpecies = speciesList[Math.floor(Math.random() * speciesList.length)];
                const randomClass = classList[Math.floor(Math.random() * classList.length)];
                const randomName = `Hero${Math.floor(Math.random() * 9000) + 1000}`; // e.g., Hero1234
                const randomGender = Math.random() < 0.5 ? "Male" : "Female";

                console.log("Randomly selected:", randomSpecies.id, randomClass.id, randomName, randomGender);

                // Call submitCharacterCreation with these random values
                // We need to set chosenSpecies and chosenClass globally for submitCharacterCreation to use them
                chosenSpecies = randomSpecies.id; // Assuming submitCharacterCreation uses these global vars
                chosenClass = randomClass.id;   // Assuming submitCharacterCreation uses these global vars
                await submitCharacterCreation(randomName, randomGender, true); // Pass a flag for auto-creation
            } catch (error) {
                console.error("Error during auto character creation:", error);
                creationArea.innerHTML = `<h2>Error Creating Random Character</h2><p>${error.message}. Please try again or create manually.</p><button onclick="showInitialCharacterScreen()">Back to Character Select</button>`;
            }
        };
        newCharOptionContainer.appendChild(diceImage);

        charOptionsDiv.appendChild(newCharOptionContainer);


    } catch (error) {
        console.error("Error occurred in showInitialCharacterScreen while fetching or processing characters:", error);
        const errorMessage = `Error loading character list: ${error.message || error}`;
        if (charOptionsDiv) { // Ensure charOptionsDiv was found before trying to modify it
            charOptionsDiv.innerHTML = `<p>${errorMessage}. <button onclick="loadSpecies()">Create New Character</button></p>`;
        } else if (creationArea) {
            creationArea.innerHTML = `<h2>Error Displaying Character List</h2><p>${errorMessage}. You can try to <button onclick="loadSpecies()">Create New Character</button>.</p>`;
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
    setupCommandNexus(); // Setup Command Nexus

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
        const errorMessage = `Error loading species: ${error.message || error}`;
        console.error(errorMessage, error);
        if (speciesOptionsDiv) speciesOptionsDiv.innerHTML = `<p>${errorMessage}</p>`;
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
        const errorMessage = `Error loading classes: ${error.message || error}`;
        console.error(errorMessage, error);
        if (classOptionsDiv) classOptionsDiv.innerHTML = `<p>${errorMessage}</p>`;
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

async function submitCharacterCreation(predefinedName = null, predefinedGender = null, isAutoCreate = false) {
    console.trace("submitCharacterCreation called");
    const charNameInput = document.getElementById('charName');
    const charName = predefinedName || (charNameInput ? charNameInput.value.trim() : `AutoHero${Date.now()}`);
    const chosenGender = predefinedGender || (document.querySelector('input[name="charGender"]:checked') ? document.querySelector('input[name="charGender"]:checked').value : "Male");
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
        setupCommandNexus(); // Setup Command Nexus when game starts
        setupVPad(); // Setup VPad
    } catch (error) {
        const errorMessage = `Error creating character: ${error.message || error}`;
        console.error(errorMessage, error);
        if (outputElement) outputElement.innerHTML = ''; // Clear "Creating character..."
        showMenuModal("Creation Error", errorMessage, [{text: "OK", action: () => { /* Optionally, go back to a previous step or main menu */ }}]);

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
        const errorMessage = `Error deleting character '${characterName}': ${error.message || error}`;
        console.error(errorMessage, error);
        showMenuModal("Deletion Error", errorMessage, [
            {text: "OK", action: () => {}}
        ]);
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
        setupCommandNexus(); // Setup Command Nexus when game loads
        setupVPad(); // Setup VPad
    } catch (error) {
        const errorMessage = `Error loading character '${characterName}': ${error.message || error}`;
        console.error(errorMessage, error);
        if (outputElement) outputElement.innerHTML = ''; // Clear "Loading character..."
        showMenuModal("Load Error", errorMessage, [{text: "OK", action: () => { showInitialCharacterScreen(); }}]);
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
        setupCommandNexus(); // Setup Command Nexus when session resumes
        setupVPad(); // Setup VPad

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
        let userMessage = `Error: ${error.message || "An unknown error occurred."}`;
        if (error instanceof TypeError && error.message.toLowerCase().includes('failed to fetch')) {
            userMessage = "Network connection issue. Please check your internet and try again.";
            // Optionally, offer a retry mechanism or guide to main menu
            showMenuModal("Connection Error", userMessage, [
                { text: "Retry Last Action", action: () => performAction(actionString) },
                { text: "Main Menu", action: goToMainMenu },
                { text: "Close", action: () => {} }
            ]);
            // Remove the "Attempting action..." message if we show a modal
            if (p_attempt && p_attempt.parentNode === outputElement) {
                outputElement.removeChild(p_attempt);
            }
            return; 
        }
        console.error("Error in performAction:", error);
        appendMessageToOutput(userMessage, 'error-message'); // Use new appendMessageToOutput
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
        const errorMessage = `Could not load world map: ${error.message || error}`;
        showMenuModal("Map Error", errorMessage, [{text: "Close", action: () => {}}]);
    }
}

function showWorldMapInModal(mapData) {
    const locations = mapData.locations || [];
    const currentLocationId = mapData.current_location_id;

    // const zoneName = mapData.zone_name || "Current Zone"; // Zone name is less relevant for the full world map modal title

    // Determine map dimensions dynamically based on min/max coordinates across ALL locations
    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;    
    locations.forEach(loc => {
        minX = Math.min(minX, loc.x);
        maxX = Math.max(maxX, loc.x);
        minY = Math.min(minY, loc.y);
        maxY = Math.max(maxY, loc.y);
    });

    const gridWidth = maxX - minX + 1;
    const gridHeight = maxY - minY + 1;

    // Emojis
    const EMOJI_CURRENT = '📍'; // Or '🧍'
    const EMOJI_VISITED = '🟩';
    const EMOJI_UNVISITED_KNOWN = '🟨'; // If you want to distinguish known but unvisited
    const EMOJI_EMPTY = '⬜'; // For empty grid cells
    const OUTER_BORDER_COLOR = '#777'; 
    const NO_BORDER_STYLE = 'none'; // More forceful way to remove border

    let mapHTML = `<div class="world-map-grid-container" style="font-size: 1.5em; line-height: 1; text-align: center; max-height: 400px; overflow-y: auto;">`;
    mapHTML += `<table style="margin: auto; border-collapse: collapse;">`; // Consider adding overflow-x: auto here if map is very wide

    for (let y = 0; y < gridHeight; y++) {
        mapHTML += '<tr>';
        for (let x = 0; x < gridWidth; x++) {
            // Correctly find the location using adjusted grid coordinates relative to minX and minY
            const locationAtCell = locations.find(loc => loc.x === x + minX && loc.y === y + minY);
            let cellEmoji = EMOJI_EMPTY;
            let cellTitle = `(${x + minX},${y + minY})`; // Display actual coordinates in title
            let borderStyles = {
                top: NO_BORDER_STYLE, // Default to no borders for all cells initially
                right: NO_BORDER_STYLE,
                bottom: NO_BORDER_STYLE,
                left: NO_BORDER_STYLE
            };
            
            if (locationAtCell) { // If a location exists at these coordinates
                cellTitle = `${locationAtCell.name} (${locationAtCell.x},${locationAtCell.y})`; // Use actual loc.x, loc.y
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

                // Determine borders based on discoveredDeadEnds
                if (locationAtCell.visited || locationAtCell.id === currentLocationId) {
                    if (discoveredDeadEnds[`${locationAtCell.id}_north`]) borderStyles.top = `1px solid ${OUTER_BORDER_COLOR}`;
                    if (discoveredDeadEnds[`${locationAtCell.id}_east`]) borderStyles.right = `1px solid ${OUTER_BORDER_COLOR}`;
                    if (discoveredDeadEnds[`${locationAtCell.id}_south`]) borderStyles.bottom = `1px solid ${OUTER_BORDER_COLOR}`;
                    if (discoveredDeadEnds[`${locationAtCell.id}_west`]) borderStyles.left = `1px solid ${OUTER_BORDER_COLOR}`;
                }
            } else { // No location at this cell, it's truly empty or outside defined map areas
                // For truly empty cells within the calculated grid, add a faint grid line
                    // For truly empty cells, add a faint grid line
                    borderStyles.top = `1px solid #eee`; 
                    borderStyles.right = `1px solid #eee`;
                    borderStyles.bottom = `1px solid #eee`;
                    borderStyles.left = `1px solid #eee`;
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
    showMenuModal("Full World Map", mapHTML, [{text: "Close", action: ()=>{}}]); // Updated modal title
    const modalOverlay = document.getElementById('custom-modal-overlay');
    if (modalOverlay) modalOverlay.id = 'world-map-modal-overlay'; // So toggle can find it
}

// --- Top-Level Component Update Functions ---

// Helper to ensure panel is in the correct container and has a button div
function setupPanel(panelId, containerId, panelTitle) {
    const panel = document.getElementById(panelId);
    const container = document.getElementById(containerId);
    if (!panel || !container) {
        console.warn(`Panel (${panelId}) or container (${containerId}) not found for setupPanel.`);
        return null;
    }

    if (panel.parentNode !== container) { // Move panel if not already in the container
        container.appendChild(panel);
    }

    // Ensure title paragraph exists and is correct, or create/replace it
    let titlePElement = panel.querySelector('p:first-child');
    const expectedTitleHTML = `<strong>${panelTitle}:</strong>`;

    if (!titlePElement || !titlePElement.innerHTML.includes(expectedTitleHTML)) {
        // If a <p> exists but isn't the title, or no <p> exists, create/replace title
        if (titlePElement && titlePElement.querySelector('strong')) { // It's an old title, remove it
            titlePElement.remove();
        }
        titlePElement = document.createElement('p');
        titlePElement.innerHTML = expectedTitleHTML;
        panel.insertBefore(titlePElement, panel.firstChild);
    }

    let buttonsContainer = panel.querySelector('.dynamic-buttons-container');
    if (!buttonsContainer) {
        buttonsContainer = document.createElement('div');
        buttonsContainer.classList.add('dynamic-buttons-container');
        // Insert buttons container after the title paragraph
        titlePElement.insertAdjacentElement('afterend', buttonsContainer);
    }
    
    buttonsContainer.innerHTML = ''; // Always clear previous buttons
    return buttonsContainer;
}

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

function updateFeatureInteractionsComponent(featuresData) {
    const featurePanel = document.getElementById('feature-interactions-panel');
    const featureButtonsContainer = setupPanel('feature-interactions-panel', 'action-panels-container', 'Room Features');
    if (!featureButtonsContainer || !featurePanel) return;

    if (featuresData && featuresData.length > 0) {
        featuresData.forEach(feature => {
            const featureButton = document.createElement('button');
            featureButton.textContent = `${feature.action.charAt(0).toUpperCase() + feature.action.slice(1)} ${feature.name}`;
            featureButton.onclick = () => performAction(`${feature.action} ${feature.id}`);
            featureButtonsContainer.appendChild(featureButton);
        });
        featurePanel.style.display = 'block';
    } else {
        featurePanel.style.display = 'none';
    }
}

function updateRoomItemsComponent(itemsData) {
    const itemsPanel = document.getElementById('room-items-panel');
    const itemsButtonsContainer = setupPanel('room-items-panel', 'action-panels-container', 'Items on the ground');
    if (!itemsButtonsContainer || !itemsPanel) return;

    if (itemsData && itemsData.length > 0) {
        itemsData.forEach(item => {
            const itemButton = document.createElement('button');
            itemButton.textContent = `Take ${item.name}`;
            itemButton.onclick = () => performAction(`take ${item.id}`);
            itemsButtonsContainer.appendChild(itemButton);
        });
        itemsPanel.style.display = 'block';
    } else {
        itemsPanel.style.display = 'none';
    }
}

function updateDynamicHeaderComponent(headerData) {
    const headerInfoDiv = document.getElementById('dynamic-header-info');
    if (!headerInfoDiv) return;
    headerInfoDiv.textContent = `Location: ${headerData.location_name || 'Unknown'} | Player: ${headerData.player_name || 'Adventurer'} - Level: ${headerData.player_level !== undefined ? headerData.player_level : 'N/A'} (XP: ${headerData.player_xp !== undefined ? headerData.player_xp : 'N/A'}/${headerData.player_xp_to_next_level !== undefined ? headerData.player_xp_to_next_level : 'N/A'}) - Coins: ${formatGSBCurrency(headerData.player_coins)} - Diamond: 0💎`;
}

function handleUnequipDoubleClick(event) {
    event.preventDefault(); 
    const itemId = this.getAttribute('data-item-id');
    console.log(`Double-clicked equipped item ID: ${itemId}`);
    if (itemId) performAction(`unequip ${itemId}`);
}

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
        neck: document.getElementById('char-panel-equip-neck'),
        back: document.getElementById('char-panel-equip-back'),
        trinket1: document.getElementById('char-panel-equip-trinket1'),
        trinket2: document.getElementById('char-panel-equip-trinket2')
    };
    const equipSlotPrefixes = {
        head: "H", shoulders: "S", chest: "C", hands: "G", legs: "L", feet: "F", 
        main_hand: "MH", off_hand: "OH", neck: "N", back: "B", 
        trinket1: "T1", trinket2: "T2"
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
    if (equipGrid) {
        equipGrid.querySelectorAll('.equip-slot[data-item-id]').forEach(slotElement => {
            slotElement.removeEventListener('dblclick', handleUnequipDoubleClick); 
            slotElement.addEventListener('dblclick', handleUnequipDoubleClick);
        });
    }
}

function renderOrUpdateModalBackpackGrid(itemsToDisplay) {
    const modalGridContainer = document.getElementById('modal-backpack-grid');
    if (!modalGridContainer) return; 
    
    itemsToDisplay = itemsToDisplay || []; // Ensure itemsToDisplay is an array
    let gridHTML = '';
    const MIN_BACKPACK_SLOTS = 24; // e.g., 3 rows of 8
    const EXTRA_EMPTY_SLOTS_IN_BACKPACK = 8; // e.g., one extra row for spacing
    const totalSlots = Math.max(MIN_BACKPACK_SLOTS, itemsToDisplay.length + EXTRA_EMPTY_SLOTS_IN_BACKPACK);

    for (let i = 0; i < totalSlots; i++) {
        if (i < itemsToDisplay.length) {
            const item = itemsToDisplay[i]; 
            let slotHTML = `<div class="inventory-slot" title="${item.name}" data-item-id="${item.id}"`;
            if (item.equip_slot) { 
                slotHTML += ` style="border-color: #007bff;"`; 
            }
            slotHTML += `>${item.name}</div>`;
            gridHTML += slotHTML;
        } else {
            gridHTML += `<div class="inventory-slot">&nbsp;</div>`; 
        }
    }
    modalGridContainer.innerHTML = gridHTML;

    modalGridContainer.querySelectorAll('.inventory-slot[data-item-id]').forEach(slotElement => {
        slotElement.addEventListener('dblclick', function(event) {
            event.preventDefault(); 
            const itemId = this.getAttribute('data-item-id');
            performAction(`equip ${itemId}`);
            //closeModal(); 
        });
    });
}
function updateActionButtonsComponent(availableActions) {
    const actionsPanel = document.getElementById('general-actions-panel'); // Assuming you have a panel for these
    const buttonsContainer = setupPanel('general-actions-panel', 'action-panels-container', 'Actions'); // Using your setupPanel helper

    if (!buttonsContainer || !actionsPanel) {
        console.error("Actions panel or buttons container not found for updateActionButtonsComponent.");
        return;
    }

    if (availableActions && availableActions.length > 0) {
        availableActions.forEach(actionString => {
            const actionButton = document.createElement('button');
            let buttonText = actionString.charAt(0).toUpperCase() + actionString.slice(1); // Capitalize first letter

            // You can customize button text for specific actions
            if (actionString === "enter city") {
                buttonText = "Enter City";
            } else if (actionString === "exit city") {
                buttonText = "Exit City";
            }
            // Add more custom texts if needed

            actionButton.textContent = buttonText;
            actionButton.onclick = () => performAction(actionString);
            buttonsContainer.appendChild(actionButton);
        });
        actionsPanel.style.display = 'block';
    } else {
        actionsPanel.style.display = 'none';
    }
}


function updateInventoryModalComponent(data, actionStringEcho) {
    if (actionStringEcho === 'inventory') {
        let controlsHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <div>
                    <input type="checkbox" id="autoEquipInventoryCheckbox" name="autoEquipInventory">
                    <label for="autoEquipInventoryCheckbox" style="font-size: 0.9em;">Auto-Equip (on check)</label>
                </div>
                <button onclick="performAction('sort_inventory_by_id_action')">Sort by ID</button>
            </div>`;

        let inventoryGridHTML = '<div id="modal-backpack-grid" style="display: grid; grid-template-columns: repeat(8, 1fr); grid-auto-rows: minmax(60px, auto); gap: 5px; padding: 10px; max-height: 400px; overflow-y: auto;">';

        if (data.inventory_list && data.inventory_list.length > 0) {
            inventoryGridHTML += '</div>'; 
        } else {
            inventoryGridHTML = "<p>Your inventory is empty.</p>"; 
        }
        
        let modalDisplayContent = controlsHTML + inventoryGridHTML;
        showMenuModal("Backpack", modalDisplayContent, [{text: "Close", action: () => {}}]);
        
        if (data.inventory_list && data.inventory_list.length > 0) {
            renderOrUpdateModalBackpackGrid(data.inventory_list);
        }

        // Add event listener for the new auto-equip checkbox
        const autoEquipCheckbox = document.getElementById('autoEquipInventoryCheckbox');
        if (autoEquipCheckbox) {
            // Set initial state from player data received from backend
            // Assuming the backend sends this as: data.player_preferences.auto_equip_from_inventory_panel_enabled
            autoEquipCheckbox.checked = (data.player_preferences && data.player_preferences.auto_equip_from_inventory_panel_enabled === true);

            autoEquipCheckbox.addEventListener('change', function() {
                const isChecked = this.checked;
                // Send action to backend to update the persistent player setting
                // Example action: "set_player_preference <preference_name> <value>"
                performAction(`set_player_preference auto_equip_from_inventory_panel_enabled ${isChecked}`);

                if (isChecked) {
                    // If now checked, also perform the immediate auto-equip attempt from current inventory

                    console.log("Auto-equip checkbox checked. Sending 'auto_equip_inventory' action.");
                    performAction('auto_equip_inventory');
                }
            });
        }

        if (document.getElementById('game-output') && data.message === "Your inventory is empty.") {
            data.message = ""; 
        }
    } else if (actionStringEcho === 'sort_inventory_by_id_action' && data.inventory_list) {
        const modalGrid = document.getElementById('modal-backpack-grid');
        if (modalGrid && document.getElementById('custom-modal-overlay')) {
            renderOrUpdateModalBackpackGrid(data.inventory_list);
        }
    }
}

function updateNPCInteractionPanelComponent(npcsData) {
    const npcPanel = document.getElementById('npc-interactions-panel');
    const npcButtonsContainer = setupPanel('npc-interactions-panel', 'action-panels-container', 'People to talk to');
    if (!npcButtonsContainer || !npcPanel) return;

    if (npcsData && npcsData.length > 0) {
        npcsData.forEach(npc => {
            const npcButton = document.createElement('button');
            npcButton.textContent = `Talk to ${npc.name}`;
            npcButton.onclick = () => performAction(`talk ${npc.id}`); 
            npcButtonsContainer.appendChild(npcButton);
        });
        npcPanel.style.display = 'block';
    } else {
        npcPanel.style.display = 'none';
    }
}

function updateExitButtonsComponent(exitDirections) {
    const exitPanel = document.getElementById('exit-buttons-panel');
    const buttonsContainer = setupPanel('exit-buttons-panel', 'action-panels-container', 'Go');
    if (!buttonsContainer || !exitPanel) return;

    if (exitDirections && exitDirections.length > 0) {
        exitDirections.forEach(direction => {
            const exitButton = document.createElement('button');
            const displayText = direction.charAt(0).toUpperCase() + direction.slice(1);
            exitButton.textContent = `Go ${displayText}`;
            exitButton.onclick = () => performAction(`go ${direction}`);
            buttonsContainer.appendChild(exitButton);
        });
        exitPanel.style.display = 'block';
    } else {
        exitPanel.style.display = 'none';
    }
}

function updateZoneMapSidePanel(zoneMapData) {
    const panel = document.getElementById('zone-map-side-panel');
    if (!panel) {
        console.error("Zone map side panel not found!");
        return;
    }

    if (!zoneMapData || !zoneMapData.locations || zoneMapData.locations.length === 0) {
        panel.innerHTML = '<p style="text-align: center; margin-bottom: 5px;"><strong>Zone Map</strong></p><p style="text-align:center;">No map data for this zone.</p>';
        return;
    }

    const locations = zoneMapData.locations;
    const currentLocationId = zoneMapData.current_location_id;
    const zoneName = zoneMapData.zone_name || "Current Zone";

    // Determine map dimensions dynamically based on min/max coordinates for THIS zone's locations
    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;
    locations.forEach(loc => {
        minX = Math.min(minX, loc.x);
        maxX = Math.max(maxX, loc.x);
        minY = Math.min(minY, loc.y);
        maxY = Math.max(maxY, loc.y);
    });

    // If locations array was empty or had no valid coords, min/max might still be Infinity/-Infinity
    if (minX === Infinity || locations.length === 0) { // Handle case with no locations or no valid coords
        panel.innerHTML = `<p style="text-align: center; margin-bottom: 5px;"><strong>Zone: ${zoneName}</strong></p><p style="text-align:center;">No map data for this zone.</p>`;
        return;
    }

    const gridWidth = maxX - minX + 1;
    const gridHeight = maxY - minY + 1;

    const EMOJI_CURRENT = '📍';
    const EMOJI_VISITED = '🟩';
    const EMOJI_UNVISITED_KNOWN = '🟨';
    const EMOJI_EMPTY = '⬜';
    const OUTER_BORDER_COLOR = '#777';
    const NO_BORDER_STYLE = 'none';

    let mapHTML = `<p style="text-align: center; margin-bottom: 5px; font-weight: bold;">Zone: ${zoneName}</p>`;
    mapHTML += `<table style="margin: 0 auto; border-collapse: collapse; font-size: 1.1em; line-height: 1;">`; // Adjusted font size

    for (let y = 0; y < gridHeight; y++) {
        mapHTML += '<tr>';
        for (let x = 0; x < gridWidth; x++) {
            const locationAtCell = locations.find(loc => loc.x === x + minX && loc.y === y + minY);
            let cellEmoji = EMOJI_EMPTY;
            let cellTitle = `(${(x + minX)},${(y + minY)})`; // Display actual coordinates
            let borderStyles = { top: NO_BORDER_STYLE, right: NO_BORDER_STYLE, bottom: NO_BORDER_STYLE, left: NO_BORDER_STYLE };

            if (locationAtCell) {
                cellTitle = `${locationAtCell.name} (${locationAtCell.x},${locationAtCell.y})`; // Use actual loc.x, loc.y
                if (locationAtCell.exits && Object.keys(locationAtCell.exits).length > 0) { /* ... tooltip ... */ }
                if (locationAtCell.id === currentLocationId) cellEmoji = EMOJI_CURRENT;
                else if (locationAtCell.visited) cellEmoji = EMOJI_VISITED;
                else cellEmoji = EMOJI_UNVISITED_KNOWN;

                if (locationAtCell.visited || locationAtCell.id === currentLocationId) {
                    if (discoveredDeadEnds[`${locationAtCell.id}_north`]) borderStyles.top = `1px solid ${OUTER_BORDER_COLOR}`;
                    if (discoveredDeadEnds[`${locationAtCell.id}_east`]) borderStyles.right = `1px solid ${OUTER_BORDER_COLOR}`;
                    if (discoveredDeadEnds[`${locationAtCell.id}_south`]) borderStyles.bottom = `1px solid ${OUTER_BORDER_COLOR}`;
                    if (discoveredDeadEnds[`${locationAtCell.id}_west`]) borderStyles.left = `1px solid ${OUTER_BORDER_COLOR}`;
                } else if (cellEmoji === EMOJI_EMPTY) { 
                    const faintGrid = '1px solid #f0f0f0'; // Lighter faint grid
                    borderStyles = { top: faintGrid, right: faintGrid, bottom: faintGrid, left: faintGrid };
                }
            }
            const cellStyle = `padding: 0px; border-top: ${borderStyles.top}; border-right: ${borderStyles.right}; border-bottom: ${borderStyles.bottom}; border-left: ${borderStyles.left}; width: 1.3em; height: 1.3em; text-align: center; vertical-align: middle;`; // Adjusted cell size
            mapHTML += `<td title="${cellTitle}" style="${cellStyle}">${cellEmoji}</td>`;
        }
        mapHTML += '</tr>';
    }
    mapHTML += `</table>`;
    panel.innerHTML = mapHTML;
}
// --- Command Nexus Setup ---
function setupCommandNexus() {
    // Ensure this runs only once
    if (commandNexusSetup) {
        return;
    }
    
    const backpackButton = document.getElementById('action-slot-backpack-button'); 
    if (backpackButton) {
        backpackButton.onclick = function() { 
            performAction('inventory'); // Action to open the inventory modal
        }
    }
    const worldMapButton = document.getElementById('action-slot-worldmap-button');
    if (worldMapButton) {
        worldMapButton.onclick = function() { 
            toggleWorldMapModal();
        };
    }

    // Mark as setup if at least one button was found and configured
    // const saveButton = document.getElementById('action-slot-save-button'); // OLD ID
    const saveButton = document.getElementById('dedicated-save-button'); // NEW ID
    if (saveButton) {
        saveButton.onclick = function() {
            performAction('!save'); // Action to save the game
        };
    }

    // Mark as setup if at least one of the core buttons was found and configured
    // (Adjust if more buttons become essential for setup)
    if (backpackButton || worldMapButton || saveButton) commandNexusSetup = true;


}


// --- End of Top-Level Component Update Functions ---

function displaySceneData(data, actionStringEcho = null) {
    console.trace("displaySceneData called");
    // Deep clone for logging to avoid issues if data is modified elsewhere by reference
    console.log("Data received by displaySceneData:", JSON.parse(JSON.stringify(data))); 
    const outputElement = document.getElementById('game-output');

    // Call the core component update functions
    updateGameOutputComponent(data, actionStringEcho);

    // If the inventory modal ("Backpack") is already open, refresh its grid content
    // This logic is already present, ensuring it uses the latest data.
    const inventoryModal = document.getElementById('custom-modal-overlay');
    if (inventoryModal) {
        const modalTitleElement = inventoryModal.querySelector('#custom-modal-content h3');
        // Check if the modal is the Backpack modal AND if inventory_list data is available
        if (modalTitleElement && modalTitleElement.textContent === "Backpack" && data.inventory_list) {
            console.log("Inventory modal is open. Refreshing grid.");
            renderOrUpdateModalBackpackGrid(data.inventory_list);
        }
    }

    // Call the component function to update the Dynamic Header
    updateDynamicHeaderComponent(data); // Pass the whole data object, component will pick what it needs

    // Call the component function to update the Character Panel
    updateCharacterPanelComponent(data); 

    // Call the component functions to update Feature and Item panels
    updateFeatureInteractionsComponent(data.interactable_features);
    updateRoomItemsComponent(data.room_items);

    // Call component functions for action panels in desired visual order (top to bottom)
    updateExitButtonsComponent(data.available_exits); // Handles dynamic "Go" buttons
    updateActionButtonsComponent(data.available_actions); // For general actions like "Enter City", called AFTER exit buttons

    updateNPCInteractionPanelComponent(data.npcs_in_room); // Handles people to talk to
    updateVPadComponent(data); // Update VPad based on new data

    // Update the Inventory Modal Component (handles opening if action was 'inventory')
    updateInventoryModalComponent(data, actionStringEcho);

    // Control visibility of the Save Game button in Command Nexus
    console.log("[SaveButtonDebug] Checking save button visibility. data.can_save_in_city:", data.can_save_in_city);
    const commandNexusSaveButton = document.getElementById('action-slot-save-button');
    console.log("[SaveButtonDebug] commandNexusSaveButton element:", commandNexusSaveButton);

    if (commandNexusSaveButton) {
        if (data.can_save_in_city) {
            console.log("[SaveButtonDebug] Setting save button to visible.");
            commandNexusSaveButton.style.display = 'inline-block'; // Or 'block', 'flex' etc.
        } else {
            console.log("[SaveButtonDebug] Setting save button to hidden.");
            commandNexusSaveButton.style.display = 'none';
        }
    }

    const dedicatedSaveButton = document.getElementById('dedicated-save-button'); // NEW ID
    
    if (dedicatedSaveButton) {
        if (data.can_save_in_city) {
            dedicatedSaveButton.style.display = 'inline-block'; // Or 'block', 'flex' etc.
        } else {
            dedicatedSaveButton.style.display = 'none';
        }
    }


    // --- Conditional Map Display ---
    const primaryMapDisplayElement = document.getElementById('zone-map-side-panel'); // This is now the single map display area

    if (data.map_type === "city" && data.city_map_data) {
        if (primaryMapDisplayElement) {
            renderCityMap(data.city_map_data, data.player_city_x, data.player_city_y); // renderCityMap will now target zone-map-side-panel
            primaryMapDisplayElement.style.display = 'block';
        } else {
            console.error("Primary map display element ('zone-map-side-panel') not found!");
        }
    } else { // Default to zone map view or if map_type is "zone"
        if (primaryMapDisplayElement && data.current_zone_map_data) {
            updateZoneMapSidePanel(data.current_zone_map_data);
            primaryMapDisplayElement.style.display = 'block';
        } else if (primaryMapDisplayElement) {
            primaryMapDisplayElement.innerHTML = '<p style="text-align:center;">Map data unavailable.</p>'; // Clear or show placeholder
            primaryMapDisplayElement.style.display = 'block';
        }
    }
}

function renderCityMap(cityMapData, playerCityX, playerCityY) {
    const mapVisualArea = document.getElementById('zone-map-side-panel'); // Changed target to zone-map-side-panel
    if (!mapVisualArea) {
        console.error("HTML element with ID 'zone-map-side-panel' not found for renderCityMap!");
        return;
    }
    if (!cityMapData || !cityMapData.cells || !cityMapData.grid_size) {
        mapVisualArea.innerHTML = "<p>City map data is incomplete or missing.</p>";
        mapVisualArea.style.display = 'block'; // Ensure it's visible even for error
        return;
    }

    let gridHTML = `<h4 style="margin-bottom: 5px;">${cityMapData.name || 'City Map'}</h4>`;
    // Enhanced table style for a more "beautiful visual"
    gridHTML += '<table class="city-grid" style="margin: 10px auto; border-collapse: collapse; font-size: 1.2em; line-height: 1; box-shadow: 0 0 8px rgba(0,0,0,0.2); border: 2px solid #777;">';
    const cells = cityMapData.cells;
    const legend = cityMapData.legend || {}; // Ensure legend exists
    const PLAYER_SYMBOL = '🧍'; // Using a person emoji for the player

    // Define some background colors for cell types (customize these as you like)
    const cellTypeColors = {
        "path": "#f0f0f0", // Light gray for paths
        "wall_city_edge": "#8B4513", // Brown for walls
        "building_house_large": "#d2b48c", // Tan for large houses
        "building_house_small": "#deb887", // Lighter tan for small houses
        "market_main_area": "#90ee90", // Light green for market
        "market_stall_goods": "#add8e6", // Light blue for goods stalls
        "market_stall_food": "#ffdab9", // Peach for food stalls
        "square_main_area": "#e6e6fa", // Lavender for square
        "square_fountain": "#afeeee", // Pale turquoise for fountain
        // Add more types and their colors from your eldoria_city_map.json legend
    };

    for (let y = 0; y < cityMapData.grid_size.height; y++) {
        gridHTML += '<tr>';
        for (let x = 0; x < cityMapData.grid_size.width; x++) {
            const cell = cells[y] && cells[y][x] ? cells[y][x] : { type: 'unknown', description: 'Unknown' }; // Graceful handling of sparse cells
            const cellTypeData = legend[cell.type] || { symbol: '?', description: 'Unknown Type' }; // Fallback for legend
            let displaySymbol = cellTypeData.symbol;
            let cellClass = `map-cell type-${cell.type.replace(/_/g, '-')}`; // CSS-friendly class name
            let cellBackgroundColor = cellTypeColors[cell.type] || '#ffffff'; // Default to white

            if (x === playerCityX && y === playerCityY) {
                displaySymbol = PLAYER_SYMBOL;
                cellClass += ' player-location';
                cellBackgroundColor = cellTypeColors[cell.type] || '#ffff99'; // Highlight player cell, fallback to light yellow
            }
            
            const tooltip = cell.name ? `${cell.name} (${cell.type}) - ${cell.description}` : `${cell.type} - ${cell.description}`;
            // Enhanced cell style with background color and slightly more padding for symbols
            gridHTML += `<td class="${cellClass}" title="${tooltip}" style="width: 1.5em; height: 1.5em; padding: 2px; border: 1px solid #ccc; text-align: center; vertical-align: middle; background-color: ${cellBackgroundColor}; cursor: default;">${displaySymbol}</td>`;
        }
        gridHTML += '</tr>';
    }
    gridHTML += '</table>';

    // Add legend display
    // Improved legend styling
    if (Object.keys(legend).length > 0) {
        gridHTML += '<div class="city-legend" style="margin-top: 15px; padding: 10px; border: 1px solid #ddd; border-radius: 5px; background-color: #f9f9f9; font-size: 0.9em; text-align: left; max-width: 350px; margin-left: auto; margin-right: auto;"><strong>Legend:</strong><ul style="list-style-type: none; padding-left: 0; margin-top: 5px;">';
        for (const type in legend) {
            const legendItemColor = cellTypeColors[type] || 'transparent';
            gridHTML += `<li style="margin-bottom: 3px;"><span style="display: inline-block; width: 1.2em; height: 1.2em; text-align:center; margin-right: 5px; border: 1px solid #ccc; background-color: ${legendItemColor}; vertical-align: middle;">${legend[type].symbol}</span> ${legend[type].description}</li>`;
        }
        gridHTML += `<li style="margin-bottom: 3px;"><span style="display: inline-block; width: 1.2em; height: 1.2em; text-align:center; margin-right: 5px; border: 1px solid #ccc; background-color: #ffff99; vertical-align: middle;">${PLAYER_SYMBOL}</span> You are here</li></ul></div>`;
    }

    mapVisualArea.innerHTML = gridHTML;
    mapVisualArea.style.display = 'block'; // Make sure the area is visible
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
            commandNexusSetup = false; // Reset flag if returning to character screen
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

function appendMessageToOutput(messageText, className = null) {
    const outputElement = document.getElementById('game-output');
    const p_msg = document.createElement('p');
    p_msg.textContent = messageText;
    if (className) p_msg.classList.add(className);
    outputElement.appendChild(p_msg);
    outputElement.scrollTop = outputElement.scrollHeight;
}

// Add a flag for vpad setup, similar to commandNexusSetup
let vpadSetup = false;

// ... (near your other setup functions like setupCommandNexus) ...

function setupVPad() {
    if (vpadSetup) return;

    const vpadNorth = document.getElementById('vpad-north');
    const vpadSouth = document.getElementById('vpad-south');
    const vpadEast = document.getElementById('vpad-east');
    const vpadWest = document.getElementById('vpad-west');
    const vpadCenter = document.getElementById('vpad-center-action');

    if (vpadNorth) vpadNorth.onclick = () => performAction('go north');
    if (vpadSouth) vpadSouth.onclick = () => performAction('go south');
    if (vpadEast) vpadEast.onclick = () => performAction('go east');
    if (vpadWest) vpadWest.onclick = () => performAction('go west');
    if (vpadCenter) vpadCenter.onclick = () => performAction('enter city'); // Or whatever action it's for

    if (vpadNorth || vpadSouth || vpadEast || vpadWest || vpadCenter) {
        vpadSetup = true;
    }
}

function updateVPadComponent(data) {
    const vpadNorth = document.getElementById('vpad-north');
    const vpadSouth = document.getElementById('vpad-south');
    const vpadEast = document.getElementById('vpad-east');
    const vpadWest = document.getElementById('vpad-west');
    const vpadCenter = document.getElementById('vpad-center-action');

    const availableExits = data.available_exits || [];
    const availableActions = data.available_actions || [];

    if (vpadNorth) vpadNorth.style.display = availableExits.includes('north') ? 'flex' : 'none';
    if (vpadSouth) vpadSouth.style.display = availableExits.includes('south') ? 'flex' : 'none';
    if (vpadEast) vpadEast.style.display = availableExits.includes('east') ? 'flex' : 'none';
    if (vpadWest) vpadWest.style.display = availableExits.includes('west') ? 'flex' : 'none';
    
    // Assuming "enter city" is the action for the center button
    if (vpadCenter) vpadCenter.style.display = availableActions.includes('enter city') ? 'flex' : 'none';
}
