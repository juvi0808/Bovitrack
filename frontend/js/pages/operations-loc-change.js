// This is the "controller" for the Location Change History page.
function initHistoryLocationChangesPage() {
    console.log("Initializing Location Change History Page...");

    // --- Element References ---
    const showModalBtn = document.getElementById('show-add-loc-change-modal-btn');
    const addLocChangeModal = document.getElementById('add-location-change-modal');
    const cancelAddLocChangeBtn = document.getElementById('cancel-add-location-change');
    const addLocChangeForm = document.getElementById('add-location-change-form');
    const animalSearchInput = document.getElementById('location-change-animal-search-eartag');
    const animalSearchBtn = document.getElementById('location-change-search-animal-btn');
    const searchResultDiv = document.getElementById('location-change-search-animal-result');
    const locationSelect = document.getElementById('new-location-select');
    const sublocationSelect = document.getElementById('new-sublocation-select');
    
    let activeAnimalForLocationChange = null;

    // --- Event Listeners ---
    showModalBtn.addEventListener('click', openAddLocationChangeModal);
    cancelAddLocChangeBtn.addEventListener('click', () => {
        addLocChangeModal.classList.add('hidden');
    });
    
    addLocChangeForm.onsubmit = handleAddLocationChangeSubmit; // Assign directly to prevent duplicates
    animalSearchBtn.addEventListener('click', searchForAnimal);

    searchResultDiv.addEventListener('change', (event) => {
        if (event.target.name === 'selectedAnimalForLocChange') {
            activeAnimalForLocationChange = JSON.parse(event.target.value);
            console.log("Animal selected for location change:", activeAnimalForLocationChange);
        }
    });

    // Listen for changes on the main location dropdown.
    locationSelect.onchange = () => {
        const selectedLocationId = locationSelect.value;
        populateSublocations(selectedLocationId);
    };

    // --- Functions ---
    async function searchForAnimal() {
        const earTag = animalSearchInput.value.trim();
        if (!earTag) return;

        activeAnimalForLocationChange = null;
        searchResultDiv.innerHTML = `<p>${getTranslation('loading_animals')}...</p>`;

        try {
            const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/animal/search/?eartag=${earTag}`);
            const animals = await response.json();
            searchResultDiv.innerHTML = ''; 

            if (animals.length > 0) {
                animals.forEach(animal => {
                    const itemDiv = document.createElement('div');
                    itemDiv.className = 'search-result-item';
                    const animalDataString = JSON.stringify(animal);

                    itemDiv.innerHTML = `
                        <input type="radio" name="selectedAnimalForLocChange" id="animal-loc-change-${animal.id}" value='${animalDataString}'>
                        <label for="animal-loc-change-${animal.id}">
                            <div class="search-result-details-grid"> 
                                <div class="detail-row">
                                    <span><b>${getTranslation('lot')}:</b> ${animal.lot}</span>
                                    <span><b>${getTranslation('race')}:</b> ${animal.race || 'N/A'}</span>
                                    <span><b>${getTranslation('age')}:</b> ${animal.kpis.current_age_months.toFixed(1)} ${getTranslation('months')}</span>
                                </div>
                                <div class="detail-row">
                                    <span><b>${getTranslation('entry_date')}:</b> ${animal.entry_date}</span>
                                    <span><b>${getTranslation('location')}:</b> ${animal.kpis.current_location_name || 'N/A'}</span>
                                    <span><b>${getTranslation('diet_type')}:</b> ${animal.kpis.current_diet_type || 'N/A'}</span>
                                    <span><b>${getTranslation('sublocation')}:</b> ${animal.kpis.current_sublocation_name || 'N/A'}</span>
                                </div>
                            </div>
                       </label>
                    `;
                    searchResultDiv.appendChild(itemDiv);
                });
            } else {
                searchResultDiv.innerHTML = `<p style="padding: 10px;">${getTranslation('no_active_animal_found')}</p>`;
            }
        } catch (error) {
            console.error('Error searching for animal:', error);
            searchResultDiv.innerHTML = `<p style="color: red; padding: 10px;">${getTranslation('error_searching_animal')}</p>`;
        }
    }

    async function openAddLocationChangeModal() {
        addLocChangeForm.reset();
        activeAnimalForLocationChange = null;
        searchResultDiv.innerHTML = '';
        
        const dateInput = document.getElementById('location-change-date');
        const today = new Date().toISOString().split('T')[0];
        dateInput.max = today;
        dateInput.value = today;

        addLocChangeModal.classList.remove('hidden');
        animalSearchInput.focus();

        // Dynamically populate the locations dropdown
        const locationSelect = document.getElementById('new-location-select');
        locationSelect.innerHTML = `<option>${getTranslation('loading_locations')}...</option>`;
        locationSelect.disabled = true;

        const sublocationSelect = document.getElementById('new-sublocation-select');
        sublocationSelect.innerHTML = `<option>${getTranslation('loading_sublocations')}...</option>`;
        sublocationSelect.disabled = true;

        try {
            const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/locations/`);
            if (!response.ok) throw new Error('Could not fetch locations');
            
            // Store the full data in our variable
            locationsWithSublocations = await response.json();
            
            locationSelect.innerHTML = ''; // Clear "Loading..."
            if (locationsWithSublocations.length === 0) {
                locationSelect.innerHTML = `<option value="">${getTranslation('no_locations_found')}</option>`;
            } else {
                // Add a default "Select..." option
                locationSelect.innerHTML = `<option value="">${getTranslation('select_one_placeholder')}</option>`;
                
                locationsWithSublocations.forEach(loc => {
                    const option = document.createElement('option');
                    option.value = loc.id;
                    option.textContent = loc.name;
                    locationSelect.appendChild(option);
                });
                locationSelect.disabled = false;
            }
        } catch (error) {
            console.error(error);
            locationSelect.innerHTML = `<option value="">${getTranslation('error_loading_locations')}</option>`;
        }
    }
    
    // --- Step 2: Create a function to populate sublocations based on parent ID ---
    function populateSublocations(locationId) {
        // Find the selected location from our stored data
        const selectedLocation = locationsWithSublocations.find(loc => loc.id == locationId);

        sublocationSelect.innerHTML = ''; // Clear previous options

        if (selectedLocation && selectedLocation.sublocations.length > 0) {
            // If there are sublocations, enable the dropdown and populate it
            sublocationSelect.disabled = false;
            sublocationSelect.innerHTML = `<option value="">${getTranslation('select_one_placeholder_optional')}</option>`;
            selectedLocation.sublocations.forEach(sub => {
                const option = document.createElement('option');
                option.value = sub.id;
                option.textContent = sub.name;
                sublocationSelect.appendChild(option);
            });
        } else {
            // If there are no sublocations, disable it and show a message
            sublocationSelect.disabled = true;
            sublocationSelect.innerHTML = `<option value="">${getTranslation('no_subdivisions_available')}</option>`;
        }
    }

    async function handleAddLocationChangeSubmit(event) {
        event.preventDefault();

        if (!activeAnimalForLocationChange) {
            showToast(getTranslation('error_no_animal_selected_for_loc_change'), 'error');
            return;
        }

        // Create a single payload with all the data
        const payload = {
            date: document.getElementById('location-change-date').value,
            location_id: document.getElementById('new-location-select').value,
            weight_kg: document.getElementById('location-change-weight-kg').value || null,
            sublocation_id: sublocationSelect.value || null, // Send null if empty
        };

        try {
            // Make a single, combined API call
            const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/purchase/${activeAnimalForLocationChange.id}/location/add/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || 'An unknown error occurred');
            }

            // The backend now provides the correct success message
            showToast(getTranslation('success_location_change_added'), 'success');
            loadLocationChangeHistoryData(); // Refresh the grid

            activeAnimalForLocationChange = null;
            searchResultDiv.innerHTML = '';
            animalSearchInput.value = '';
            document.getElementById('location-change-weight-kg').value = '';
            locationSelect.selectedIndex = 0;
            populateSublocations(null); // Reset sublocations
            animalSearchInput.focus(); // Set focus for the next search

        } catch (error) {
            showToast(`${getTranslation('error_recording_loc_change')}: ${error.message}`, 'error');
        }
    }

    // Initial data load for the page
    loadLocationChangeHistoryData();
}

// Fetches location change data and populates the grid.
async function loadLocationChangeHistoryData() {
    const gridDiv = document.getElementById('location-change-history-grid');
    if (!gridDiv) return;

    if (!selectedFarmId) {
        gridDiv.innerHTML = `<p>${getTranslation('select_farm_to_view_data')}</p>`;
        return;
    }

    try {
        const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/location_log/`);
        if (!response.ok) throw new Error('Failed to fetch location history');
        const history = await response.json();
        createLocationChangeHistoryGrid(history);

    } catch (error) {
        console.error("Error loading location history:", error);
        gridDiv.innerHTML = `<p style="color: red;">${getTranslation('error_loading_data')}</p>`;
    }
}

// Sets up and creates the AG Grid.
function createLocationChangeHistoryGrid(data) {
    const gridDiv = document.getElementById('location-change-history-grid');
    if (!gridDiv) return;

    const columnDefs = [
        { headerName: getTranslation("date"), field: "date" },
        { 
            headerName: getTranslation("ear_tag"), 
            field: "ear_tag", 
            width: 120,
            onCellClicked: (params) => window.navigateToConsultAnimal(params.data.animal_id,'page-operations-loc-change'),
            cellClass: 'clickable-cell'
        },
        { 
            headerName: getTranslation("lot"), 
            field: "lot", 
            width: 100, 
            filter: 'agNumberColumnFilter',
            onCellClicked: (params) => window.navigateToConsultLot(params.value,'page-operations-loc-change'),
            cellClass: 'clickable-cell'
        },
        { 
            headerName: getTranslation("location_name"), 
            field: "location_name",
            onCellClicked: (params) => window.navigateToConsultLocation(params.data.location_id, params.value,'page-operations-loc-change'),
            cellClass: 'clickable-cell'
        },
        { headerName: getTranslation("sublocation_name"), field: "sublocation_name" },
    ];

    const gridOptions = {
        columnDefs: columnDefs,
        rowData: data,
        defaultColDef: { 
            sortable: true, 
            filter: true, 
            resizable: true, 
            cellStyle: { 'text-align': 'center' } 
        },
        onGridReady: (params) => params.api.sizeColumnsToFit(),
    };

    gridDiv.innerHTML = '';
    createGrid(gridDiv, gridOptions);
}