async function loadLocationsData() {
    const container = document.getElementById('locations-container');
    if (!container) {
        console.error("Locations container element not found!");
        return;
    }
    if (!selectedFarmId) {
        container.innerHTML = `<p>${getTranslation('select_farm_to_view_locations')}</p>`;
        return;
    }

    try {
        const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/locations`);
        if (!response.ok) throw new Error('Failed to fetch locations');
        const locations = await response.json();
        renderLocationsList(locations);
    } catch (error) {
        console.error("Error loading locations:", error);
        container.innerHTML = `<p style="color: red;">${getTranslation('error_loading_locations_history')}</p>`;
    }
}

function renderLocationsList(locations) {
    const container = document.getElementById('locations-container');
    if (!container) return;

    container.innerHTML = ''; 

    if (locations.length === 0) {
        container.innerHTML = `<p>${getTranslation('no_locations_found')}</p>`;
        return;
    }

    locations.forEach(location => {
        const locationCard = document.createElement('div');
        locationCard.className = 'location-card';

        // Create the list of sublocations
        let sublocationsHtml = `<p>${getTranslation('no_subdivisions_yet')}</p>`;
        if (location.sublocations && location.sublocations.length > 0) {
            sublocationsHtml = `
                <ul class="sublocation-list">
                    ${location.sublocations.map(sub => `
                        <li class="${sub.animal_count > 0 ? 'occupied' : ''}">
                            <div class="sublocation-info">
                                <span>${sub.name}</span>
                                <span class="sublocation-area">${sub.area_hectares ? sub.area_hectares.toFixed(2) + ' ha' : ''}</span>
                            </div>

                            ${sub.animal_count > 0 ? `<span class="occupied-animal-count">${getTranslation('animal_occupation')}: ${sub.animal_count}</span>` : ''}

                            <div class="sublocation-actions">
                                <button class="button-secondary assign-herd-btn" 
                                        data-location-id="${location.id}"
                                        data-location-name="${location.name}"
                                        data-sublocation-id="${sub.id}"
                                        data-sublocation-name="${sub.name}"
                                        title="Assign all unassigned animals in ${location.name} to this subdivision">
                                    ${getTranslation('assign_herd')}
                                </button>
                            </div>
                        </li>
                    `).join('')}
                </ul>
            `;
        }

        // Assemble the full card HTML, now including the new KPI section
        locationCard.innerHTML = `
            <div class="location-card-header">
                <h3>${location.name}</h3>
                <div class="location-card-actions">
                    <button class="button-primary see-details-btn" 
                            data-location-id="${location.id}" 
                            data-location-name="${location.name}">
                        ${getTranslation('see_details')}
                    </button>
                    <button class="button-secondary add-subdivision-btn" 
                            data-location-id="${location.id}" 
                            data-location-name="${location.name}">
                        ${getTranslation('add_new_subdivision')}
                    </button>
                </div>
            </div>
            
            <div class="location-card-kpis">
                <div class="kpi-item">
                    <span class="kpi-value">${location.kpis.animal_count}</span>
                    <span class="kpi-label">${getTranslation('animal_count')}</span>
                </div>
                <div class="kpi-item">
                    <span class="kpi-value">${location.area_hectares ? location.area_hectares.toFixed(2) + ' ha' : 'N/A'}</span>
                    <span class="kpi-label">${getTranslation('area_hectares')}</span>
                </div>
                <div class="kpi-item">
                    <span class="kpi-value">${location.grass_type || 'N/A'}</span>
                    <span class="kpi-label">${getTranslation('grass_type')}</span>
                </div>
                <div class="kpi-item">
                    <span class="kpi-value">${location.kpis.capacity_rate_actual_ua_ha || 'N/A'}</span>
                    <span class="kpi-label">${getTranslation('capacity_rate_actual_ua_ha')}</span>
                </div>
                <div class="kpi-item">
                    <span class="kpi-value">${location.kpis.capacity_rate_forecasted_ua_ha || 'N/A'}</span>
                    <span class="kpi-label">${getTranslation('capacity_rate_forecasted_ua_ha')}</span>
                </div>
            </div>

            <div class="location-card-body">
                <h4 class="subdivision-header">${getTranslation('subdivisions')}</h4>
                ${sublocationsHtml}
            </div>
        `;
        container.appendChild(locationCard);
    });
}

// Renders the summary KPIs for the consult view.
function renderLocationSummary(location, container) {
    if (!container) return;
    container.innerHTML = `
        <div class="kpi-item">
            <span class="kpi-value">${location.kpis.animal_count}</span>
            <span class="kpi-label">${getTranslation('animal_count')}</span>
        </div>
        <div class="kpi-item">
            <span class="kpi-value">${location.area_hectares ? location.area_hectares.toFixed(2) + ' ha' : 'N/A'}</span>
            <span class="kpi-label">${getTranslation('area_hectares')}</span>
        </div>
        <div class="kpi-item">
            <span class="kpi-value">${location.grass_type || 'N/A'}</span>
            <span class="kpi-label">${getTranslation('grass_type')}</span>
        </div>
        <div class="kpi-item">
            <span class="kpi-value">${location.kpis.capacity_rate_actual_ua_ha || 'N/A'}</span>
            <span class="kpi-label">${getTranslation('capacity_rate_actual_ua_ha')}</span>
        </div>
        <div class="kpi-item">
            <span class="kpi-value">${location.kpis.capacity_rate_forecasted_ua_ha || 'N/A'}</span>
            <span class="kpi-label">${getTranslation('capacity_rate_forecasted_ua_ha')}</span>
        </div>
    `;
}

// Creates the AG Grid for animals in the selected location.
function createLocationAnimalsGrid(animals) {
    const gridDiv = document.getElementById('location-animals-grid');
    if (!gridDiv) return;

    gridDiv.className = 'ag-theme-quartz full-height-grid';
    const columnDefs = [
        { headerName: getTranslation("ear_tag"), field: "ear_tag", width: 120, onCellClicked: (params) => window.navigateToConsultAnimal(params.data.id,'page-farm-locations'), cellClass: 'clickable-cell' },
        { 
            headerName: getTranslation("lot"), 
            field: "lot", 
            width: 100, 
            filter: 'agNumberColumnFilter',
            onCellClicked: (params) => window.navigateToConsultLot(params.value, 'page-farm-locations'),
            cellClass: 'clickable-cell'
        },
        { headerName: getTranslation("sex"), field: "sex", width: 100 },
        { headerName: `${getTranslation('age')} (${getTranslation('months')})`, field: "kpis.current_age_months", valueFormatter: p => p.value.toFixed(2), width: 150 },
        { headerName: getTranslation("last_wt_kg"), field: "kpis.last_weight_kg", valueFormatter: p => p.value.toFixed(2), width: 150 },
        { headerName: getTranslation("avg_daily_gain_kg"), field: "kpis.average_daily_gain_kg", valueFormatter: p => p.value.toFixed(3), width: 180 },
        { headerName: getTranslation("forecasted_weight"), field: "kpis.forecasted_current_weight_kg", valueFormatter: p => p.value.toFixed(2), width: 180 },
        { headerName: getTranslation("diet_type"), field: "kpis.current_diet_type" },
        { headerName: getTranslation("sublocation_name"), field: "kpis.current_sublocation_name" },
    ];

    const gridOptions = {
        columnDefs: columnDefs,
        rowData: animals,
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

function initLocationsPage() {
    console.log("Initializing Locations Page...");
    
    // --- Element References for BOTH views ---
    const locationsListView = document.getElementById('locations-list-view');
    const locationConsultView = document.getElementById('location-consult-view');

    // We get all references up front.
    const showAddLocationModalBtn = document.getElementById('show-add-location-modal-btn');
    const addLocationModal = document.getElementById('add-location-modal');
    const cancelAddLocationBtn = document.getElementById('cancel-add-location');
    const addLocationForm = document.getElementById('add-location-form');
    const addSublocationModal = document.getElementById('add-sublocation-modal');
    const cancelAddSublocationBtn = document.getElementById('cancel-add-sublocation');
    const addSublocationForm = document.getElementById('add-sublocation-form');
    const parentLocationNameSpan = document.getElementById('parent-location-name');
    const locationsContainer = document.getElementById('locations-container');

    const backBtn = document.getElementById('back-to-locations-list-btn');
    const consultTitle = document.getElementById('location-consult-title');
    const summaryContainer = document.getElementById('location-summary-kpis');
    const gridContainer = document.getElementById('location-animals-grid');

    // --- View Switching Logic ---
    const showListView = () => {
        locationConsultView.classList.add('hidden');
        locationsListView.classList.remove('hidden');
        loadLocationsData(); // Refresh list data in case of changes
    };

    const showConsultView = async (locationId, locationName) => {
        locationsListView.classList.add('hidden');
        locationConsultView.classList.remove('hidden');

        consultTitle.textContent = `${getTranslation('location_occupancy')}: ${locationName}`;
        summaryContainer.innerHTML = `<p>${getTranslation('loading_summary')}...</p>`;
        if (gridContainer) gridContainer.innerHTML = `<p>${getTranslation('loading_animals')}...</p>`;

        try {
            const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/location/${locationId}/summary`); // New URL will be /api/farm/${selectedFarmId}/location/${locationId}/
            if (!response.ok) throw new Error('Failed to fetch location summary');
            const data = await response.json();
            
            renderLocationSummary(data.location_details, summaryContainer);
            createLocationAnimalsGrid(data.animals);

        } catch (error) {
            console.error("Error loading location summary:", error);
            summaryContainer.innerHTML = `<p style="color: red;">${getTranslation('could_not_load_summary_data')}</p>`;
            if (gridContainer) gridContainer.innerHTML = '';
        }
    };

    showAddLocationModalBtn.onclick = () => { /* ... */ };
    cancelAddLocationBtn.onclick = () => { /* ... */ };
    addLocationForm.onsubmit = handleAddLocationSubmit;
    cancelAddSublocationBtn.onclick = () => { /* ... */ };
    addSublocationForm.onsubmit = handleAddSublocationSubmit;
    
    locationsContainer.onclick = (event) => {
        const detailsBtn = event.target.closest('.see-details-btn');
        if (detailsBtn) {
            // --- START OF FIX: When navigating internally, clear the return page flag ---
            window.consultLocationReturnPage = null; 
            // --- END OF FIX ---
            const locationId = detailsBtn.dataset.locationId;
            const locationName = detailsBtn.dataset.locationName;
            showConsultView(locationId, locationName);
        }
        // ... (rest of the click handling logic for other buttons)
    };

    // --- Page Load & Back Button Logic (Corrected Structure) ---

    // 1. Determine the back button's behavior FIRST.
    if (window.consultLocationReturnPage) {
        // Came from an external grid click
        backBtn.textContent = getTranslation('back_to_list');
        backBtn.onclick = () => {
            navigateToPage(window.consultLocationReturnPage);
            window.consultLocationReturnPage = null;
            window.locationToConsult = null;
        };
    } else {
        // Normal flow within the locations page
        backBtn.textContent = getTranslation('back_to_locations_list'); // Use correct translation key
        backBtn.onclick = showListView;
    }

    // 2. NOW, determine which view to show.
    if (window.locationToConsult) {
        // Came here to see a specific location
        const { id, name } = window.locationToConsult;
        window.locationToConsult = null; // Clear the flag
        showConsultView(id, name);
    } else {
        // Standard page load
        showListView();
    }
    // Before we do anything else, we check if our core elements were found.
    // If not, it means the HTML didn't load correctly, and we stop execution.
    if (!showAddLocationModalBtn || !locationsContainer || !addSublocationModal) {
        console.error("Essential elements for Locations page are missing. Aborting initialization.");
        return; 
    }

    let currentParentLocationId = null; 



    // --- Event Listeners ---
    showAddLocationModalBtn.onclick = () => {
        addLocationForm.reset();
        addLocationModal.classList.remove('hidden');
    };
    cancelAddLocationBtn.onclick = () => addLocationModal.classList.add('hidden');
    addLocationForm.onsubmit = handleAddLocationSubmit;
    
    cancelAddSublocationBtn.onclick = () => addSublocationModal.classList.add('hidden');
    addSublocationForm.onsubmit = handleAddSublocationSubmit;

    locationsContainer.onclick = (event) => {
        const addBtn = event.target.closest('.add-subdivision-btn');
        const assignBtn = event.target.closest('.assign-herd-btn');

        const detailsBtn = event.target.closest('.see-details-btn');

        if (detailsBtn) {
            const locationId = detailsBtn.dataset.locationId;
            const locationName = detailsBtn.dataset.locationName;
            showConsultView(locationId, locationName);
        } else if (addBtn) {
            currentParentLocationId = addBtn.dataset.locationId;
            const locationName = addBtn.dataset.locationName;
            
            addSublocationForm.reset();
            parentLocationNameSpan.textContent = locationName;
            addSublocationModal.classList.remove('hidden');
        } else if (assignBtn) {
            handleAssignAnimalsToSublocation(assignBtn.dataset);
        }
    };
    
    // --- Form Handlers ---
    async function handleAddLocationSubmit(event) {
        event.preventDefault();
        const locationData = { name: document.getElementById('location-name-input').value.trim(), area_hectares: document.getElementById('location-area-input').value, location_type: document.getElementById('location-type-input').value.trim(), grass_type: document.getElementById('location-grass-input').value.trim(), };
        try {
            const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/location/add`, { // New url will be /api/farm/${selectedFarmId}/location
                method: 'POST',  
                headers: { 'Content-Type': 'application/json' }, 
                body: JSON.stringify(locationData) 
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);
            showToast(getTranslation('location_saved_successfully', { name: locationData.name }), 'success');
            addLocationModal.classList.add('hidden');
            loadLocationsData();
        } catch (error) {
            showToast(`${getTranslation('error_saving_location')}: ${error.message}`, 'error');
        }
    }

    async function handleAddSublocationSubmit(event) {
        event.preventDefault();
        if (!currentParentLocationId) {
            console.error("No parent location ID set for sublocation.");
            return;
        }
        const sublocationData = { name: document.getElementById('sublocation-name-input').value.trim(), area_hectares: document.getElementById('sublocation-area-input').value };
        try {
            const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/location/${currentParentLocationId}/sublocation/add`, { //New URL will be /api/farm/${selectedFarmId}/location/${currentParentLocationId}/sublocations/
                method: 'POST', 
                headers: { 'Content-Type': 'application/json' }, 
                body: JSON.stringify(sublocationData) 
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);
            showToast(getTranslation('subdivision_saved_successfully', { name: sublocationData.name }), 'success');
            addSublocationModal.classList.add('hidden');
            loadLocationsData();
        } catch (error) {
            showToast(`${getTranslation('error_saving_subdivision')}: ${error.message}`, 'error');
        }
    }

    // --- Function to handle the Bulk Assign action (REVISED) ---
    async function handleAssignAnimalsToSublocation(dataset) {
        const { locationId, locationName, sublocationId, sublocationName } = dataset;

        const confirmationMessage = getTranslation('confirm_bulk_assign', {
            parentName: locationName,
            subName: sublocationName
        });

        // Use a non-blocking, promise-based confirmation
        const userConfirmed = await showCustomConfirm(confirmationMessage);

        if (userConfirmed) {
            const today = new Date().toISOString().split('T')[0];
            const payload = {
                date: today,
                destination_sublocation_id: sublocationId
            };

            try {
                const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/location/${locationId}/bulk_assign_sublocation`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const result = await response.json();
                if (!response.ok) throw new Error(result.error);
                
                showToast(result.message, 'success');
                loadLocationsData(); // Refresh the page to update animal counts

            } catch (error) {
                showToast(`Error: ${error.message}`, 'error');
            }
        }
        // If userConfirmed is false, do nothing.
    }


    // Initial data load for the page
    loadLocationsData();
}