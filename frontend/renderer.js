// --- RENDERER WITH NODE.JS POWERS & APP STATE ---
// This is where all the logic, interactivity, and intelligence of your application lives. 
// It's written in JavaScript. 
// It acts as the coordinator, responding to user actions, 
// talking to the backend API, and manipulating the HTML and CSS.




console.log('Renderer.js script loaded!');

// Set up AG Grid
const { ModuleRegistry, AllCommunityModule, createGrid } = require('ag-grid-community');
ModuleRegistry.registerModules([AllCommunityModule]);

// --- Global State ---
const API_URL = 'http://127.0.0.1:5000'; // This is the base URL for our backend API
let selectedFarmId = null; // This will hold the ID of the currently selected farm

// --- Element References ---
// --- A block of code to get "references" to the important HTML elements. ---
// We use getElementById() to find the elements we named in the HTML
// and store them in variables so we can easily interact with them later.
const summaryDiv = document.getElementById('summary-kpis');
const gridDiv = document.getElementById('animal-grid');
const farmSelect = document.getElementById('farm-select');
const addFarmBtn = document.getElementById('add-farm-btn');
const addFarmModal = document.getElementById('add-farm-modal');
const addFarmForm = document.getElementById('add-farm-form');
const cancelAddFarmBtn = document.getElementById('cancel-add-farm');
const newFarmNameInput = document.getElementById('new-farm-name');

// --- Main App Initialization ---
// This line says: "When the entire HTML document has been fully loaded and is ready..."
document.addEventListener('DOMContentLoaded', initializeApp);

// An "async function" is a special function that can perform long-running tasks
// (like network requests) without freezing the whole application.
async function initializeApp() {
    console.log("Initializing App...");
    await loadFarms();

    // Attach event listeners after initial setup
    farmSelect.addEventListener('change', handleFarmSelection);
    addFarmBtn.addEventListener('click', () => addFarmModal.classList.remove('hidden'));
    cancelAddFarmBtn.addEventListener('click', () => addFarmModal.classList.add('hidden'));
    addFarmForm.addEventListener('submit', handleAddFarmSubmit);
}

// --- Farm Management Functions ---

async function loadFarms() {
    try {
        // 'fetch' is the built-in JavaScript command to make a network request (an API call).
        // It's 'await'ed because it takes time.
        const response = await fetch(`${API_URL}/api/farms`);
        if (!response.ok) throw new Error('Failed to fetch farms');
        const farms = await response.json(); // If it was successful, we tell it to parse the body text as JSON.
        console.log('Farms loaded:', farms);

        if (farms.length === 0) { 
            // No farms exist, force user to create one
            farmSelect.innerHTML = '<option>No farms found</option>';
            addFarmModal.classList.remove('hidden'); // Show the 'Add Farm' modal
        } else {  // Logic for when farms ARE returned. We call other functions to do the work.
            // Farms exist, populate the dropdown
            populateFarmSelector(farms);
            // Set the global state to the first farm and load its data
            selectedFarmId = farmSelect.value;
            await loadDashboardData();
        }
    } catch (error) {
        console.error("Error loading farms:", error);
        alert("Could not connect to the backend to load farm data.");
    }
}

function populateFarmSelector(farms) {
     // We directly manipulate the HTML of the <select> element.
    farmSelect.innerHTML = ''; // Clear existing options
    farms.forEach(farm => {
        const option = document.createElement('option');
        option.value = farm.id; // Set its 'value' attribute.
        option.textContent = farm.name; // Set the visible text.
        farmSelect.appendChild(option); // Add the newly created element inside the <select> element.
    });
}

async function handleFarmSelection() {
    selectedFarmId = farmSelect.value;
    console.log(`Farm changed to: ${selectedFarmId}`);
    // When the farm changes, reload the dashboard data
    await loadDashboardData();
}

async function handleAddFarmSubmit(event) {
    event.preventDefault(); // Prevent default form submission
    const farmName = newFarmNameInput.value.trim();
    if (!farmName) return;

    try {
        const response = await fetch(`${API_URL}/api/farm/add`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: farmName })
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || 'Failed to create farm');
        }

        console.log('Farm created:', result.farm);
        addFarmModal.classList.add('hidden');
        newFarmNameInput.value = '';
        await loadFarms(); // Reload the farm list to include the new one
    } catch (error) {
        console.error("Error creating farm:", error);
        alert(`Error: ${error.message}`);
    }
}

// --- Data Loading & Display Functions ---

async function loadDashboardData() {
    // Check if a farm is selected
    if (!selectedFarmId) {
        console.log("No farm selected. Skipping data load.");
        summaryDiv.innerHTML = 'Please select a farm to view data.';
        gridDiv.innerHTML = '';
        return;
    }
    console.log(`Fetching data for farm ID: ${selectedFarmId}`);

    // Show loading state
    summaryDiv.innerHTML = 'Loading summary...';
    gridDiv.innerHTML = ''; // Clear grid

    try {
        const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/stock/active_summary`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        displaySummary(data.summary_kpis);
        createAnimalGrid(data.animals);
    } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
        summaryDiv.innerHTML = 'Error: Could not load summary data.';
        gridDiv.innerHTML = 'Error: Could not load animal list.';
    }
}

function displaySummary(kpis) {
    // This function is the same as before
    summaryDiv.innerHTML = `
        <p><strong>Total Active Animals:</strong> ${kpis.total_active_animals}</p>
        <p><strong>Males:</strong> ${kpis.number_of_males} | <strong>Females:</strong> ${kpis.number_of_females}</p>
        <p><strong>Average Age:</strong> ${kpis.average_age_months.toFixed(2)} months</p>
        <p><strong>Average GMD:</strong> ${kpis.average_gmd_kg_day.toFixed(3)} kg/day</p>
    `;
}

function createAnimalGrid(animals) {
    // This function is the same as before
    const columnDefs = [
        { headerName: "Ear Tag", field: "ear_tag", width: 120 },
        { headerName: "Lot", field: "lot", width: 100 },
        { headerName: "Status", field: "kpis.status", width: 120 },
        { headerName: "Age (Months)", field: "kpis.current_age_months", valueFormatter: p => p.value.toFixed(2), width: 150 },
        { headerName: "Last Wt (kg)", field: "kpis.last_weight_kg", valueFormatter: p => p.value.toFixed(2), width: 150 },
        { headerName: "Avg Daily Gain (kg)", field: "kpis.average_daily_gain_kg", valueFormatter: p => p.value.toFixed(3), width: 180 },
        { headerName: "Current Location", field: "kpis.current_location_name" }
    ];
    const gridOptions = {
        columnDefs: columnDefs,
        rowData: animals,
        defaultColDef: { sortable: true, filter: true, resizable: true },
        onGridReady: (params) => params.api.sizeColumnsToFit(),
    };
    gridDiv.innerHTML = '';
    createGrid(gridDiv, gridOptions);
}
