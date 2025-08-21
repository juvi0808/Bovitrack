// --- RENDERER WITH NODE.JS POWERS & APP STATE ---
// This is where all the logic, interactivity, and intelligence of your application lives. 
// It's written in JavaScript. 
// It acts as the coordinator, responding to user actions, 
// talking to the backend API, and manipulating the HTML and CSS.




console.log('Renderer.js script loaded!');

// Set up AG Grid
const { ModuleRegistry, AllCommunityModule, createGrid } = require('ag-grid-community');
ModuleRegistry.registerModules([AllCommunityModule]);

// --- Global State & Constants ---
const API_URL = 'http://127.0.0.1:5000';
const LAST_FARM_ID_KEY = 'bovitrack-last-farm-id';
const LANGUAGE_KEY = 'bovitrack-language'; // Moved to the top for safety

let selectedFarmId = null;
let allFarms = [];
let currentLanguage = 'en';

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
    // Load the saved language preference or default to English
    currentLanguage = localStorage.getItem(LANGUAGE_KEY) || 'en';
    applyTranslations();

    await loadFarms(); 
    setupEventListeners(); 

    // Try to load the last selected farm ID from storage.
    const lastSelectedId = localStorage.getItem(LAST_FARM_ID_KEY);

    // Check if the loaded ID is actually a valid farm that we have.
    if (lastSelectedId && allFarms.some(farm => farm.id == lastSelectedId)) {
        // If it's valid, set the dropdown to that value.
        farmSelect.value = lastSelectedId;
    }

    // Manually trigger the 'change' event to ensure the page loads the correct data.
    // This will update the selectedFarmId global variable and load the dashboard.
    farmSelect.dispatchEvent(new Event('change'));

    // Go to the default page.
    await showPage('page-active-stock');

    // FIX: Find the correct link now and handle the case where it might not exist.
    const activeLink = document.querySelector('.nav-link[data-page="page-active-stock"]');
    if (activeLink) {
        activeLink.classList.add('active');
    }
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

// --- Language Functions  ---
function setLanguage(lang) {
    currentLanguage = lang;
    localStorage.setItem(LANGUAGE_KEY, lang);
    applyTranslations(); // Apply to currently visible content

    // Refresh the data on the current page to update dynamic elements like grid headers
    const activeLink = document.querySelector('.nav-link.active');
    if (activeLink) {
        const pageId = activeLink.dataset.page;
        // Re-run the data loading function for the current page
        if (pageId === 'page-active-stock') {
            loadDashboardData();} 
        else if (pageId === 'page-operations-purchases') {
            loadPurchaseHistoryData();}
        else if (pageId === 'page-operations-sales') {
            loadSalesHistoryData();}
    }
}

function applyTranslations() {
    document.querySelectorAll('[data-translate]').forEach(element => {
        const key = element.getAttribute('data-translate');
        element.textContent = getTranslation(key);
    });
    // Also translate placeholder text
    document.querySelectorAll('[data-translate-placeholder]').forEach(element => {
        const key = element.getAttribute('data-translate-placeholder');
        element.placeholder = getTranslation(key);
    });
}

function getTranslation(key, replacements = {}) {
    let translation = translations[currentLanguage]?.[key] || key;
    for (const placeholder in replacements) {
        translation = translation.replace(`{${placeholder}}`, replacements[placeholder]);
    }
    return translation;
}
// --- Farm Management Functions ---

async function loadFarms() {
    try {
        const response = await fetch(`${API_URL}/api/farms`);
        if (!response.ok) throw new Error('Failed to fetch farms');
        
        //We assign the fetched data to our global variable.
        allFarms = await response.json(); 
        
        console.log('Farms loaded into global allFarms:', allFarms);

        if (allFarms.length === 0) {
            farmSelect.innerHTML = '<option>No farms found</option>';
            selectedFarmId = null;
            addFarmModal.classList.remove('hidden');
            renameFarmBtn.disabled = true;
            deleteFarmBtn.disabled = true;
        } else {
            // We now pass the global variable to the populator function
            populateFarmSelector(allFarms);
            selectedFarmId = farmSelect.value;
            renameFarmBtn.disabled = false;
            deleteFarmBtn.disabled = false;
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

    // Save the newly selected ID to localStorage for next time.
    localStorage.setItem(LAST_FARM_ID_KEY, selectedFarmId);
    
    // Find the currently active page to know which data to refresh
    const activeLink = document.querySelector('.nav-link.active');
    if (!activeLink) return;

    const pageId = activeLink.dataset.page;

    // Simple router to call the correct data-loading function
    // This is much more efficient than reloading the whole page HTML.
    if (pageId === 'page-active-stock') {
        // Since loadDashboardData is now a top-level function in active-stock.js,
        // we can call it directly from here.
        await loadDashboardData();}
    else if (pageId === 'page-operations-purchases') {
        await loadPurchaseHistoryData(); }
    else if (pageId === 'page-operations-sales') {
        await loadSalesHistoryData();}
    else if (pageId === 'page-operations-weightings') {
        await loadWeightingHistoryData();}
    else if (pageId === 'page-operations-loc-change') {
        await loadLocationChangeHistoryData();}
    else if (pageId === 'page-operations-diet-log') {
        await loadDietLogHistoryData();}
    else if (pageId === 'page-operations-sanitary') {
        await loadSanitaryProtocolHistoryData();}
    else if (pageId === 'page-operations-death') {
        await loadDeathHistoryData();}  
    else if (pageId === 'page-farm-locations') { 
        await loadLocationsData();}      
    else if (pageId === 'page-farm-lots') { 
        await loadLotsData();
    }     
    else if (pageId === 'page-lookup-consult-animal') { 
        await loadConsultAnimalData();
    }     
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

// --- Page Navigation Logic ---

async function showPage(pageId) {
    const appContent = document.getElementById('app-content');

    // 1. Construct the path to the HTML partial.
    //    e.g., if pageId is 'page-dashboard', the path will be './pages/dashboard.html'
    const pageName = pageId.replace('page-', '');
    const pagePath = `./pages/${pageName}.html`;

    try {
        // 2. Fetch the content of the HTML file.
        const response = await fetch(pagePath);
        if (!response.ok) {
            throw new Error(`Could not load page: ${pagePath}`);
        }
        const htmlContent = await response.text();

        // 3. Inject the new HTML into our main content area.
        appContent.innerHTML = htmlContent;

        // Apply translations to the newly loaded static elements.
        applyTranslations();

        // ROUTER LOGIC: Call the correct init function for the page we just loaded.
        console.log(`Page ${pageName} loaded. Initializing...`);
        if (pageName === 'active-stock') {
            initActiveStockPage();
        } else if (pageName === 'operations-purchases') {
            initHistoryPurchasesPage();
        } else if (pageName === 'operations-sales') {
            initHistorySalesPage();
        } else if (pageId === 'page-operations-weightings') {
            initHistoryWeightingsPage();  
        } else if (pageId === 'page-operations-loc-change') {
            initHistoryLocationChangesPage();    
        } else if (pageId === 'page-operations-diet-log') {
            initHistoryDietLogsPage();
        } else if (pageId === 'page-operations-sanitary') {
            initHistorySanitaryProtocolsPage();   
        } else if (pageId === 'page-operations-death') {
            initHistoryDeathsPage(); 
        } else if (pageName === 'farm-locations') { 
            initLocationsPage();
        } else if (pageName === 'farm-lots') { 
            initLotsPage();
        } else if (pageName === 'lookup-consult-animal') {
            initConsultAnimalPage();
        } else if (pageName === 'settings') {
            initSettingsPage();
        }



    } catch (error) {
        console.error("Error loading page:", error);
        appContent.innerHTML = `<p style="color: red; padding: 20px;">Error: Could not load the requested page.</p>`;
    }
}

// A global timer for the toast to prevent overlaps ---
let toastTimer;

// The Toast Notification Function ---
function showToast(message, type = 'success') {
    const notification = document.getElementById('toast-notification');
    if (!notification) return;

    // Clear any existing timer to reset the fade-out
    clearTimeout(toastTimer);

    notification.textContent = message;
    // Set class for styling (success or error)
    notification.className = 'show ' + type;

    // Set a timer to automatically hide the toast after 3 seconds
    toastTimer = setTimeout(() => {
        notification.className = notification.className.replace('show', '');
    }, 3000);
}


