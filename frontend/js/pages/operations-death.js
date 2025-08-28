// This is the "controller" for the Death History page.
function initHistoryDeathsPage() {
    console.log("Initializing Death History Page...");

    // --- Element References ---
    const showModalBtn = document.getElementById('show-add-death-modal-btn');
    const addDeathModal = document.getElementById('add-death-modal');
    const cancelAddDeathBtn = document.getElementById('cancel-add-death');
    const addDeathForm = document.getElementById('add-death-form');
    const animalSearchInput = document.getElementById('death-animal-search-eartag');
    const animalSearchBtn = document.getElementById('death-search-animal-btn');
    const searchResultDiv = document.getElementById('death-search-animal-result');
    
    let activeAnimalForDeath = null;

    // --- Event Listeners ---
    showModalBtn.addEventListener('click', openAddDeathModal);
    cancelAddDeathBtn.addEventListener('click', () => {
        addDeathModal.classList.add('hidden');
    });
    
    addDeathForm.onsubmit = handleAddDeathSubmit; // Assign directly to prevent duplicates
    animalSearchBtn.addEventListener('click', searchForAnimal);

    searchResultDiv.addEventListener('change', (event) => {
        if (event.target.name === 'selectedAnimalForDeath') {
            activeAnimalForDeath = JSON.parse(event.target.value);
            console.log("Animal selected for death record:", activeAnimalForDeath);
        }
    });

    // --- Functions ---
    async function searchForAnimal() {
        const earTag = animalSearchInput.value.trim();
        if (!earTag) return;

        activeAnimalForDeath = null;
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
                        <input type="radio" name="selectedAnimalForDeath" id="animal-death-${animal.id}" value='${animalDataString}'>
                        <label for="animal-death-${animal.id}">
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

    function openAddDeathModal() {
        addDeathForm.reset();
        activeAnimalForDeath = null;
        searchResultDiv.innerHTML = '';
        
        const dateInput = document.getElementById('death-date');
        const today = new Date().toISOString().split('T')[0];
        dateInput.max = today;
        dateInput.value = today;

        addDeathModal.classList.remove('hidden');
        animalSearchInput.focus();
    }

    async function handleAddDeathSubmit(event) {
        event.preventDefault();

        if (!activeAnimalForDeath) {
            showToast(getTranslation('error_no_animal_selected_for_death'), 'error');
            return;
        }

        const payload = {
            date: document.getElementById('death-date').value,
            cause: document.getElementById('death-cause').value
        };
        
        try {
            const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/purchase/${activeAnimalForDeath.id}/death/add/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || 'An unknown error occurred');
            }

            showToast(getTranslation('death_recorded_successfully', { earTag: activeAnimalForDeath.ear_tag }), 'success');
            loadDeathHistoryData(); // Refresh the grid

            // Reset the form for the next entry
            activeAnimalForDeath = null;
            searchResultDiv.innerHTML = '';
            animalSearchInput.value = '';
            document.getElementById('death-cause').value = '';
            animalSearchInput.focus();

        } catch (error) {
            showToast(`${getTranslation('error_recording_death')}: ${error.message}`, 'error');
        }
    }

    loadDeathHistoryData();
}

async function loadDeathHistoryData(page = 1) {
    const gridDiv = document.getElementById('death-history-grid');
    if (!gridDiv) return;

    if (!selectedFarmId) {
        gridDiv.innerHTML = `<p>${getTranslation('select_farm_to_view_data')}</p>`;
        return;
    }

    try {
        const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/deaths/?page=${page}`);
        if (!response.ok) throw new Error('Failed to fetch death history');
        const data = await response.json(); // This is now a paginated response
        
        createDeathHistoryGrid(data.results); // Use the .results property for the grid

        // Render pagination controls
        const paginationContainer = document.getElementById('pagination-controls');
        renderPaginationControls(data, paginationContainer, loadDeathHistoryData, page);

    } catch (error) {
        console.error("Error loading death history:", error);
        gridDiv.innerHTML = `<p style="color: red;">${getTranslation('error_loading_data')}</p>`;
    }
}
function createDeathHistoryGrid(data) {
    const gridDiv = document.getElementById('death-history-grid');
    if (!gridDiv) return;

    const columnDefs = [
        { headerName: getTranslation("date"), field: "date" },
        { 
            headerName: getTranslation("ear_tag"), 
            field: "ear_tag", 
            width: 120,
            onCellClicked: (params) => window.navigateToConsultAnimal(params.data.animal_id,'page-operations-death'),
            cellClass: 'clickable-cell'
        },
        { 
            headerName: getTranslation("lot"), 
            field: "lot", 
            width: 100, 
            filter: 'agNumberColumnFilter',
            onCellClicked: (params) => window.navigateToConsultLot(params.value,'page-operations-death'),
            cellClass: 'clickable-cell'
        },
        { headerName: getTranslation("cause_of_death"), field: "cause" },
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