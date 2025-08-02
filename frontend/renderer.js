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
let allFarms = []; // This will hold the complete list of farm objects

// --- 3. ELEMENT REFERENCES ---
// Main Page Elements
const summaryDiv = document.getElementById('summary-kpis');
const gridDiv = document.getElementById('animal-grid');
const farmSelect = document.getElementById('farm-select');

// Farm Management Buttons
const addFarmBtn = document.getElementById('add-farm-btn');
const renameFarmBtn = document.getElementById('rename-farm-btn');
const deleteFarmBtn = document.getElementById('delete-farm-btn');

// Add Farm Modal Elements
const addFarmModal = document.getElementById('add-farm-modal');
const addFarmForm = document.getElementById('add-farm-form');
const cancelAddFarmBtn = document.getElementById('cancel-add-farm');
const newFarmNameInput = document.getElementById('new-farm-name');

// Rename Farm Modal Elements
const renameFarmModal = document.getElementById('rename-farm-modal');
const renameFarmForm = document.getElementById('rename-farm-form');
const cancelRenameFarmBtn = document.getElementById('cancel-rename-farm');
const renameFarmNameInput = document.getElementById('rename-farm-name');

// Delete Farm Modal Elements
const deleteFarmModal = document.getElementById('delete-farm-modal');
const deleteFarmForm = document.getElementById('delete-farm-form');
const cancelDeleteFarmBtn = document.getElementById('cancel-delete-farm');
const farmNameToDeleteSpan = document.getElementById('farm-name-to-delete');


// --- Main App Initialization ---
// This line says: "When the entire HTML document has been fully loaded and is ready..."
document.addEventListener('DOMContentLoaded', initializeApp);

// An "async function" is a special function that can perform long-running tasks
// (like network requests) without freezing the whole application.
// This is our main "controller" that runs when the app is ready.
async function initializeApp() {
    console.log("Initializing App...");
    await loadFarms();
    setupEventListeners();
}

function setupEventListeners() {
    const mainNav = document.querySelector('.main-nav');

    // Farm selection
    farmSelect.addEventListener('change', handleFarmSelection);
    // Add Farm
    addFarmBtn.addEventListener('click', () => addFarmModal.classList.remove('hidden'));
    cancelAddFarmBtn.addEventListener('click', () => addFarmModal.classList.add('hidden'));
    addFarmForm.addEventListener('submit', handleAddFarmSubmit);
    // Rename Farm
    renameFarmBtn.addEventListener('click', openRenameModal);
    renameFarmForm.addEventListener('submit', handleRenameFarmSubmit);
    cancelRenameFarmBtn.addEventListener('click', () => renameFarmModal.classList.add('hidden'));
    // Delete Farm
    deleteFarmBtn.addEventListener('click', openDeleteModal);
    deleteFarmForm.addEventListener('submit', handleDeleteFarmSubmit);
    cancelDeleteFarmBtn.addEventListener('click', () => deleteFarmModal.classList.add('hidden'));
    // Page Navigation
    mainNav.addEventListener('click', (event) => {
        const link = event.target.closest('a');
        if (!link) return;

        event.preventDefault();

        if (link.classList.contains('nav-link')) {
            handlePageNavigation(link);
            event.stopPropagation();
        } else if (link.parentElement.classList.contains('has-dropdown')) {
            handleDropdownToggle(link.parentElement);
            event.stopPropagation();
        }
    });

    window.addEventListener('click', (event) => {
        if (!mainNav.contains(event.target)) {
            closeAllDropdowns();
        }
    });
}

// --- Farm Management Functions ---

async function loadFarms() {
    try {
        const response = await fetch(`${API_URL}/api/farms`);
        if (!response.ok) throw new Error('Failed to fetch farms');
        
        // THIS IS THE FIX. We assign the fetched data to our global variable.
        allFarms = await response.json(); 
        
        console.log('Farms loaded into global allFarms:', allFarms);

        if (allFarms.length === 0) {
            farmSelect.innerHTML = '<option>No farms found</option>';
            selectedFarmId = null;
            addFarmModal.classList.remove('hidden');
            renameFarmBtn.disabled = true;
            deleteFarmBtn.disabled = true;
            loadDashboardData();
        } else {
            // We now pass the global variable to the populator function
            populateFarmSelector(allFarms);
            selectedFarmId = farmSelect.value;
            renameFarmBtn.disabled = false;
            deleteFarmBtn.disabled = false;
            await loadDashboardData();
        }
    } catch (error) {
        console.error("Error loading farms:", error);
        alert("Could not connect to the backend to load farm data.");
    }
}

function populateFarmSelector(farms) {
    const previouslySelected = farmSelect.value; // Move this line to the top
    farmSelect.innerHTML = ''; // Now clear the options
    farms.forEach(farm => {
        const option = document.createElement('option');
        option.value = farm.id;
        option.textContent = farm.name;
        farmSelect.appendChild(option);
    });
    // Now this check will work correctly
    if (farms.some(f => f.id == previouslySelected)) {
        farmSelect.value = previouslySelected;
    }
}

async function handleFarmSelection() {
    selectedFarmId = farmSelect.value;
    console.log(`Farm changed to: ${selectedFarmId}`);
    // When the farm changes, reload the dashboard data
    await loadDashboardData();
}

async function handleAddFarmSubmit(event) {
    event.preventDefault();
    const farmName = newFarmNameInput.value.trim();
    if (!farmName) return;

    try {
        const response = await fetch(`${API_URL}/api/farm/add`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: farmName })
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'Failed to create farm');
        
        addFarmModal.classList.add('hidden');
        newFarmNameInput.value = '';
        await loadFarms();
    } catch (error) {
        console.error("Error creating farm:", error);
        alert(`Error: ${error.message}`);
    }
}

function openRenameModal() {
    if (!selectedFarmId) return;
    // This will now work correctly because allFarms is populated.
    const selectedFarm = allFarms.find(f => f.id == selectedFarmId);
    if (selectedFarm) {
        renameFarmNameInput.value = selectedFarm.name;
        renameFarmModal.classList.remove('hidden');
    }
}

async function handleRenameFarmSubmit(event) {
    event.preventDefault();
    const newName = renameFarmNameInput.value.trim();
    if (!newName || !selectedFarmId) return;

    try {
        const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/rename`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: newName })
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error);
        
        renameFarmModal.classList.add('hidden');
        await loadFarms(); // Reload the list to show the new name
    } catch (error) {
        console.error("Error renaming farm:", error);
        alert(`Error: ${error.message}`);
    }
}

function openDeleteModal() {
    if (!selectedFarmId) return;
    // This will now work correctly.
    const selectedFarm = allFarms.find(f => f.id == selectedFarmId);
    if (selectedFarm) {
        farmNameToDeleteSpan.textContent = selectedFarm.name;
        deleteFarmModal.classList.remove('hidden');
    }
}

async function handleDeleteFarmSubmit(event) {
    event.preventDefault();
    if (!selectedFarmId) return;
    
    try {
        const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/delete`, {
            method: 'DELETE'
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error);

        deleteFarmModal.classList.add('hidden');
        await loadFarms(); // Reload farm list, which will either select the next farm or show the "add" modal
    } catch (error) {
        console.error("Error deleting farm:", error);
        alert(`Error: ${error.message}`);
    }
}

function handleDropdownToggle(dropdownLi) {
    const wasActive = dropdownLi.classList.contains('dropdown-is-active');
    closeAllDropdowns();
    if (!wasActive) {
        dropdownLi.classList.add('dropdown-is-active');
    }
}

function handlePageNavigation(navLink) {
    const pageId = navLink.dataset.page;
    if (pageId) {
        showPage(pageId);
        document.querySelectorAll('.nav-link').forEach(link => link.classList.remove('active'));
        navLink.classList.add('active');
        closeAllDropdowns();
    }
}

function closeAllDropdowns() {
    document.querySelectorAll('.has-dropdown.dropdown-is-active').forEach(item => {
        item.classList.remove('dropdown-is-active');
    });
}

// This function is now only for switching the page content.
function handleNavigation(event) {
    // This function's logic is now inside handleNavClick.
    // We can keep it here empty or remove it, but for now we'll leave it
    // to avoid breaking anything else that might call it, just in case.
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
        { headerName: "Entry Date", field: "entry_date", width: 150 },
        { headerName: "Sex", field: "sex", width: 120 },
        { headerName: "Age (Months)", field: "kpis.current_age_months", valueFormatter: p => p.value.toFixed(2), width: 150 },
        { headerName: "Last Wt (kg)", field: "kpis.last_weight_kg", valueFormatter: p => p.value.toFixed(2), width: 150 },
        { headerName: "Last Wt Date", field: "kpis.last_weighting_date", width: 150 },
        { headerName: "Avg Daily Gain (kg)", field: "kpis.average_daily_gain_kg", valueFormatter: p => p.value.toFixed(3), width: 180 },
        { headerName: "Forecasted Weight", field: "kpis.forecasted_current_weight_kg", valueFormatter: p => p.value.toFixed(2), width: 180 },
        { headerName: "Current Location", field: "kpis.current_location_name" },
        { headerName: "Diet Type", field: "kpis.current_diet_type" },
        { headerName: "Diet Intake (%)", field: "kpis.current_diet_intake", valueFormatter: p => p.value ? `${p.value}%` : 'N/A', width: 150 },
    ];
    const gridOptions = {
        columnDefs: columnDefs,
        rowData: animals,
        defaultColDef: { sortable: true, filter: true, resizable: true, cellStyle: { 'text-align': 'center' } },
        onGridReady: (params) => params.api.sizeColumnsToFit(),
    };
    gridDiv.innerHTML = '';
    createGrid(gridDiv, gridOptions);
}

// --- Page Navigation Logic ---

function showPage(pageId) {
    // 1. Get all the page containers
    const pages = document.querySelectorAll('.page');
    // 2. Hide all of them
    pages.forEach(page => {
        page.classList.add('hidden');
    });
    // 3. Find the one page we want to show
    const pageToShow = document.getElementById(pageId);
    // 4. Show it (if it exists)
    if (pageToShow) {
        pageToShow.classList.remove('hidden');
    } else {
        console.error(`Page with ID "${pageId}" not found.`);
    }
}


