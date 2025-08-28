// --- RENDERER WITH NODE.JS POWERS & APP STATE ---
// This is where all the logic, interactivity, and intelligence of your application lives. 
// It's written in JavaScript. 
// It acts as the coordinator, responding to user actions, 
// talking to the backend API, and manipulating the HTML and CSS.




console.log('Renderer.js script loaded!');

// Set up AG Grid
const { ModuleRegistry, AllCommunityModules, createGrid } = require('ag-grid-community');
// 2. Pass AllCommunityModules directly (it's already an array)
ModuleRegistry.registerModules(AllCommunityModules);

// --- Global State & Constants ---
const API_URL = 'http://127.0.0.1:8000';
const LAST_FARM_ID_KEY = 'bovitrack-last-farm-id';
const LANGUAGE_KEY = 'bovitrack-language'; // Moved to the top for safety

let selectedFarmId = null;
let allFarms = [];
let currentLanguage = 'en';

window.animalIdToConsult = null; // Global variable to hold the ID
window.consultAnimalReturnPage = null; // Global variable for the back button logic
window.lotToConsult = null;
window.consultLotReturnPage = null;
window.locationToConsult = null;
window.consultLocationReturnPage = null;

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

    // 3. Manually set our global state variable from the dropdown's current value.
    //    This is the key step that avoids firing an unnecessary event.
    selectedFarmId = farmSelect.value;
    
    // 4. If there is a selected farm, ensure it's saved back to storage.
    if (selectedFarmId) {
        localStorage.setItem(LAST_FARM_ID_KEY, selectedFarmId);
    }
    
    // 5. Now, load the default page. This will call its own data-loading function,
    //    which will correctly use the 'selectedFarmId' we just set.
    await showPage('page-active-stock');

    // 6. Set the active class on the navigation link.
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
        const response = await fetch(`${API_URL}/api/farms/`);
        if (!response.ok) throw new Error('Failed to fetch farms');
        
        //We assign the fetched data to our global variable.
        allFarms = await response.json(); 
        
        console.log('Farms loaded into global allFarms:', allFarms);

        if (allFarms.length === 0) {
            farmSelect.innerHTML = '<option>No farms found</option>';
            selectedFarmId = null;
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
        const response = await fetch(`${API_URL}/api/farms/`, {
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
        const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/`, { // New url will be /api/farm/${selectedFarmId}/
            method: 'PUT', // Will have to change to PUT once we migrate to the django backend
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
    
    const submitButton = event.submitter; // Get the button that was clicked
    if (!selectedFarmId || !submitButton) return;

    const originalButtonText = submitButton.textContent;
    submitButton.disabled = true;
    submitButton.textContent = getTranslation('deleting'); // Show loading state

    try {
        // NOTE: The URL points to the resource itself, not a special /delete endpoint.
        const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/`, {
            method: 'DELETE'
        });

        // Check if the response was successful (status 200-299).
        // This correctly handles the 204 No Content status.
        if (response.ok) {
            // If the delete was successful, we don't try to parse a body.
            // We just proceed with the success actions.
            showToast(getTranslation('farm_deleted'), 'success');
            deleteFarmModal.classList.add('hidden');
            
            await loadFarms(); // Reload the farm list
            
            // This logic correctly handles what to display after deletion
            const activeLink = document.querySelector('.nav-link.active');
            const currentPageId = activeLink ? activeLink.dataset.page : null;
            if (allFarms.length === 0 && currentPageId === 'page-active-stock') {
                initActiveStockPage();
            } else {
                await handleFarmSelection();
            }

        } else {
            // If the response is not ok (e.g., 404, 500), THEN we try to get an error message.
            const errorData = await response.json().catch(() => ({ error: 'An unknown error occurred.' }));
            throw new Error(errorData.error);
        }


    } catch (error) {
        console.error("Error deleting farm:", error);
        showToast(`Error: ${error.message}`, 'error');
    } finally {
        // This block will run regardless of success or failure
        submitButton.disabled = false;
        submitButton.textContent = originalButtonText; // Restore original text
    }


}

// The global function called from the grids now accepts the return page ID.
window.navigateToConsultAnimal = function(animalId, returnPageId) {
    if (!animalId) return;
    console.log(`Navigating to consult page for animal ID: ${animalId} from ${returnPageId}`);
    window.animalIdToConsult = animalId;
    window.consultAnimalReturnPage = returnPageId; // Store where to go back to
    navigateToPage('page-lookup-consult-animal');
}

// ... after window.navigateToConsultAnimal function
window.navigateToConsultLot = function(lotNumber, returnPageId) {
    if (!lotNumber) return;
    console.log(`Navigating to consult page for lot: ${lotNumber} from ${returnPageId}`);
    window.lotToConsult = lotNumber;
    window.consultLotReturnPage = returnPageId; // Store where to go back to
    navigateToPage('page-farm-lots');
}

window.navigateToConsultLocation = function(locationId, locationName, returnPageId) {
    if (!locationId || !locationName) return;
    console.log(`Navigating to consult page for location ID: ${locationId} from ${returnPageId}`);
    window.locationToConsult = { id: locationId, name: locationName };
    window.consultLocationReturnPage = returnPageId; // Store where to go back to
    navigateToPage('page-farm-locations');
}

function handleDropdownToggle(dropdownLi) {
    const wasActive = dropdownLi.classList.contains('dropdown-is-active');
    closeAllDropdowns();
    if (!wasActive) {
        dropdownLi.classList.add('dropdown-is-active');
    }
}

// This is our central navigation controller.
function navigateToPage(pageId) {
    if (!pageId) return;

    // 1. Fetch and display the new page's HTML content.
    showPage(pageId);

    // 2. Update the visual state of the navigation menu.
    // Deactivate all links first to ensure a clean slate.
    document.querySelectorAll('.main-nav a').forEach(link => link.classList.remove('active'));

    // Find the specific link that corresponds to the page we are navigating to.
    const targetLink = document.querySelector(`.nav-link[data-page="${pageId}"]`);
    if (targetLink) {
        // Activate the target link (e.g., "Search Animal").
        targetLink.classList.add('active');

        // If it's in a dropdown, activate its parent menu item too (e.g., "Lookup").
        const parentDropdown = targetLink.closest('.has-dropdown');
        if (parentDropdown) {
            const parentMenuLink = parentDropdown.querySelector('a');
            if (parentMenuLink) {
                parentMenuLink.classList.add('active');
            }
        }
    }
    closeAllDropdowns();
}

// It just determines the pageId and calls our new central controller.
function handlePageNavigation(navLink) {
    const pageId = navLink.dataset.page;
    navigateToPage(pageId);
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

function renderPaginationControls(paginationData, container, callback, currentPage) {
    if (!container || !paginationData || typeof paginationData.count === 'undefined') {
        if(container) container.innerHTML = ''; // Ensure old controls are cleared
        return;
    }

    container.innerHTML = '';

    // Calculate total pages. The page size is 100 as set in the backend views.
    const pageSize = 100;
    const totalPages = Math.ceil(paginationData.count / pageSize);

    if (totalPages <= 1) return; // Don't show controls if there's only one page

    const prevButton = document.createElement('button');
    prevButton.textContent = `<< ${getTranslation('previous')}`;
    prevButton.disabled = !paginationData.previous; // Use 'previous' link from API
    prevButton.className = 'button-secondary';
    prevButton.onclick = () => callback(currentPage - 1);

    const pageIndicator = document.createElement('span');
    // Use the currentPage and calculated totalPages
    pageIndicator.textContent = `${getTranslation('page')} ${currentPage} ${getTranslation('of')} ${totalPages}`;
    pageIndicator.style.margin = '0 15px';
    pageIndicator.style.fontWeight = 'bold';

    const nextButton = document.createElement('button');
    nextButton.textContent = `${getTranslation('next')} >>`;
    nextButton.disabled = !paginationData.next; // Use 'next' link from API
    nextButton.className = 'button-secondary';
    nextButton.onclick = () => callback(currentPage + 1);

    container.appendChild(prevButton);
    container.appendChild(pageIndicator);
    container.appendChild(nextButton);
}

function showCustomConfirm(message) {
    return new Promise(resolve => {
        const confirmModal = document.getElementById('custom-confirm-modal');
        const msgElement = document.getElementById('custom-confirm-msg');
        const okBtn = document.getElementById('custom-confirm-ok-btn');
        const cancelBtn = document.getElementById('custom-confirm-cancel-btn');

        if (!confirmModal || !msgElement || !okBtn || !cancelBtn) {
            console.error("Custom confirmation modal elements not found in index.html!");
            resolve(false); // Resolve as false if the modal isn't set up
            return;
        }

        msgElement.textContent = message;
        confirmModal.classList.remove('hidden');

        // We use .onclick here to easily overwrite the listener each time
        okBtn.onclick = () => {
            confirmModal.classList.add('hidden');
            resolve(true); // User confirmed
        };

        cancelBtn.onclick = () => {
            confirmModal.classList.add('hidden');
            resolve(false); // User canceled
        };
    });
}


