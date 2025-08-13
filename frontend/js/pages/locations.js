// This function is defined globally in this file so main-renderer.js can call it
async function loadLocationsData() {
    const gridDiv = document.getElementById('locations-grid');
    if (!gridDiv) {
        console.error("Locations grid element not found!");
        return;
    }

    if (!selectedFarmId) {
        gridDiv.innerHTML = `<p>${getTranslation('select_farm_to_view_locations')}</p>`;
        return;
    }

    try {
        const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/locations`);
        if (!response.ok) throw new Error('Failed to fetch locations');
        const locations = await response.json();
        createLocationsGrid(locations);
    } catch (error) {
        console.error("Error loading locations:", error);
        gridDiv.innerHTML = `<p style="color: red;">${getTranslation('error_loading_locations_history')}</p>`;
    }
}

function createLocationsGrid(data) {
    const gridDiv = document.getElementById('locations-grid');
    if (!gridDiv) return;

    const columnDefs = [
        { headerName: getTranslation("location_name"), field: "name", flex: 2 },
        { headerName: getTranslation("area_hectares"), field: "area_hectares", flex: 1, valueFormatter: p => p.value ? p.value.toFixed(2) : 'N/A' },
        { headerName: getTranslation("location_type"), field: "location_type", flex: 1 },
        { headerName: getTranslation("grass_type"), field: "grass_type", flex: 1 },
        { headerName: getTranslation("animal_count"), field: "kpis.animal_count", flex: 1 },
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

    gridDiv.innerHTML = ''; // Clear previous grid
    createGrid(gridDiv, gridOptions);
}

// This is the main "controller" for the Locations page.
function initLocationsPage() {
    console.log("Initializing Locations Page...");

    // --- Element References for the Modal ---
    const showModalBtn = document.getElementById('show-add-location-modal-btn');
    const addLocationModal = document.getElementById('add-location-modal');
    const cancelAddLocationBtn = document.getElementById('cancel-add-location');
    const addLocationForm = document.getElementById('add-location-form');

    // --- Event Listeners (using .onclick to prevent duplicates) ---
    showModalBtn.onclick = () => {
        addLocationForm.reset();
        addLocationModal.classList.remove('hidden');
    };

    cancelAddLocationBtn.onclick = () => {
        addLocationModal.classList.add('hidden');
    };

    addLocationForm.onsubmit = async (event) => {
        event.preventDefault();

        const locationData = {
            name: document.getElementById('location-name-input').value.trim(),
            area_hectares: document.getElementById('location-area-input').value,
            location_type: document.getElementById('location-type-input').value.trim(),
            grass_type: document.getElementById('location-grass-input').value.trim(),
        };

        try {
            const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/location/add`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(locationData)
            });

            const result = await response.json();
            if (!response.ok) throw new Error(result.error);

            showToast(getTranslation('location_saved_successfully', { name: locationData.name }), 'success');
            addLocationModal.classList.add('hidden');
            loadLocationsData(); // Refresh the grid to show the new location

        } catch (error) {
            showToast(`${getTranslation('error_saving_location')}: ${error.message}`, 'error');
        }
    };

    // Initial data load for the page
    loadLocationsData();
}