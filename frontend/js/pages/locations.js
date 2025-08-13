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
                        <li>
                            <span>${sub.name}</span>
                            <span>${sub.area_hectares ? sub.area_hectares.toFixed(2) + ' ha' : ''}</span>
                        </li>
                    `).join('')}
                </ul>
            `;
        }

        // --- THE UPGRADE ---
        // Assemble the full card HTML, now including the new KPI section
        locationCard.innerHTML = `
            <div class="location-card-header">
                <h3>${location.name}</h3>
                <div class="location-card-actions">
                    <button class="button-secondary add-subdivision-btn" 
                            data-location-id="${location.id}" 
                            data-location-name="${location.name}">
                        ${getTranslation('add_new_subdivision')}
                    </button>
                </div>
            </div>
            
            <!-- NEW KPI Section -->
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

function initLocationsPage() {
    console.log("Initializing Locations Page...");
    
    // --- Element References ---
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

    // --- THE FIX: Guard Clause ---
    // Before we do anything else, we check if our core elements were found.
    // If not, it means the HTML didn't load correctly, and we stop execution.
    if (!showAddLocationModalBtn || !locationsContainer || !addSublocationModal) {
        console.error("Essential elements for Locations page are missing. Aborting initialization.");
        return; 
    }
    // --- END OF FIX ---

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
        const target = event.target.closest('.add-subdivision-btn');
        if (target) {
            currentParentLocationId = target.dataset.locationId;
            const locationName = target.dataset.locationName;
            
            addSublocationForm.reset();
            parentLocationNameSpan.textContent = locationName;
            addSublocationModal.classList.remove('hidden');
        }
    };
    
    // --- Form Handlers ---
    async function handleAddLocationSubmit(event) {
        event.preventDefault();
        const locationData = { name: document.getElementById('location-name-input').value.trim(), area_hectares: document.getElementById('location-area-input').value, location_type: document.getElementById('location-type-input').value.trim(), grass_type: document.getElementById('location-grass-input').value.trim(), };
        try {
            const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/location/add`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(locationData) });
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
            const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/location/${currentParentLocationId}/sublocation/add`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(sublocationData) });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);
            showToast(getTranslation('subdivision_saved_successfully', { name: sublocationData.name }), 'success');
            addSublocationModal.classList.add('hidden');
            loadLocationsData();
        } catch (error) {
            showToast(`${getTranslation('error_saving_subdivision')}: ${error.message}`, 'error');
        }
    }

    // Initial data load for the page
    loadLocationsData();
}