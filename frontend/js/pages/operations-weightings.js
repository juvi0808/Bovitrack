// This is the "controller" for the Weighting History page.
function initHistoryWeightingsPage() {
    console.log("Initializing Weighting History Page...");

    // --- Element References ---
    const showModalBtn = document.getElementById('show-add-weighting-modal-btn');
    const addWeightingModal = document.getElementById('add-weighting-modal');
    const cancelAddWeightingBtn = document.getElementById('cancel-add-weighting');
    const addWeightingForm = document.getElementById('add-weighting-form');
    const animalSearchInput = document.getElementById('weighting-animal-search-eartag');
    const animalSearchBtn = document.getElementById('weighting-search-animal-btn');
    const searchResultDiv = document.getElementById('weighting-search-animal-result');
    
    let activeAnimalForWeighting = null; // This will store the data of the animal we find.

    // --- Event Listeners ---
    showModalBtn.addEventListener('click', openAddWeightingModal);
    cancelAddWeightingBtn.addEventListener('click', () => {
        addWeightingModal.classList.add('hidden');
    });
    
    addWeightingForm.onsubmit = handleAddWeightingSubmit;
    animalSearchBtn.addEventListener('click', searchForAnimal);

    // Event delegation for selecting an animal from the search results
    searchResultDiv.addEventListener('change', (event) => {
        if (event.target.name === 'selectedAnimalForWeighting') {
            activeAnimalForWeighting = JSON.parse(event.target.value);
            console.log("Animal selected for weighting:", activeAnimalForWeighting);
        }
    });

    // --- Functions ---
    async function searchForAnimal() {
        const earTag = animalSearchInput.value.trim();
        if (!earTag) return;

        activeAnimalForWeighting = null;
        searchResultDiv.innerHTML = `<p>${getTranslation('loading_animals')}...</p>`;

        try {
            const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/animal/search?eartag=${earTag}`);
            const animals = await response.json();

            searchResultDiv.innerHTML = ''; 

            if (animals.length > 0) {
                animals.forEach(animal => {
                    const itemDiv = document.createElement('div');
                    itemDiv.className = 'search-result-item';
                    const animalDataString = JSON.stringify(animal);

                    itemDiv.innerHTML = `
                        <input type="radio" name="selectedAnimalForWeighting" id="animal-weighting-${animal.id}" value='${animalDataString}'>
                        <label for="animal-weighting-${animal.id}">
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

    function openAddWeightingModal() {
        addWeightingForm.reset();
        activeAnimalForWeighting = null;
        searchResultDiv.innerHTML = '';
        
        const weightingDateInput = document.getElementById('weighting-date');
        const today = new Date().toISOString().split('T')[0];
        weightingDateInput.max = today;
        weightingDateInput.value = today;

        addWeightingModal.classList.remove('hidden');
        animalSearchInput.focus();
    }

    async function handleAddWeightingSubmit(event) {
        event.preventDefault();

        if (!activeAnimalForWeighting) {
            showToast(getTranslation('error_no_animal_selected_for_weighting'), 'error');
            return;
        }

        const weightingData = {
            date: document.getElementById('weighting-date').value,
            weight_kg: document.getElementById('weighting-weight-kg').value,
        };

        try {
            const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/purchase/${activeAnimalForWeighting.id}/weighting/add`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(weightingData)
            });

            const result = await response.json();
            if (!response.ok) throw new Error(result.error);

            showToast(getTranslation('weighting_recorded_successfully', { earTag: activeAnimalForWeighting.ear_tag }), 'success');
            loadWeightingHistoryData(); // Refresh the grid

            activeAnimalForWeighting = null;
            searchResultDiv.innerHTML = '';
            animalSearchInput.value = '';
            document.getElementById('weighting-weight-kg').value = '';
            animalSearchInput.focus(); // Set focus for the next search

        } catch (error) {
            showToast(`${getTranslation('error_recording_weighting')}: ${error.message}`, 'error');
        }
    }

    // Initial data load for the page
    loadWeightingHistoryData();
}

// Fetches weighting data from the API and populates the grid.
async function loadWeightingHistoryData() {
    const gridDiv = document.getElementById('weighting-history-grid');
    if (!gridDiv) return;

    if (!selectedFarmId) {
        gridDiv.innerHTML = `<p>${getTranslation('select_farm_to_view_data')}</p>`;
        return;
    }

    try {
        const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/weightings`);
        if (!response.ok) throw new Error('Failed to fetch weighting history');
        const weightings = await response.json();
        createWeightingHistoryGrid(weightings);

    } catch (error) {
        console.error("Error loading weighting history:", error);
        gridDiv.innerHTML = `<p style="color: red;">${getTranslation('error_loading_data')}</p>`;
    }
}

// Sets up and creates the AG Grid for weighting history.
function createWeightingHistoryGrid(data) {
    const gridDiv = document.getElementById('weighting-history-grid');
    if (!gridDiv) return;

    const columnDefs = [
        { headerName: getTranslation("date"), field: "date" },
        { 
            headerName: getTranslation("ear_tag"), 
            field: "ear_tag", 
            width: 120,
            onCellClicked: (params) => window.navigateToConsultAnimal(params.data.animal_id,'page-operations-weightings'),
            cellClass: 'clickable-cell'
        },
        { 
            headerName: getTranslation("lot"), 
            field: "lot", 
            width: 100, 
            filter: 'agNumberColumnFilter',
            onCellClicked: (params) => window.navigateToConsultLot(params.value,'page-operations-weightings'),
            cellClass: 'clickable-cell'
        },
        { headerName: getTranslation("weightings"), field: "weight_kg", valueFormatter: p => p.value.toFixed(2) },
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