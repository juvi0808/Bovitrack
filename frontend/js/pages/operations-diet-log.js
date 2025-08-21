// This is the "controller" for the Diet Log History page.
function initHistoryDietLogsPage() {
    console.log("Initializing Diet Log History Page...");

    // --- Element References ---
    const showModalBtn = document.getElementById('show-add-diet-log-modal-btn');
    const addDietLogModal = document.getElementById('add-diet-log-modal');
    const cancelAddDietLogBtn = document.getElementById('cancel-add-diet-log');
    const addDietLogForm = document.getElementById('add-diet-log-form');
    const animalSearchInput = document.getElementById('diet-log-animal-search-eartag');
    const animalSearchBtn = document.getElementById('diet-log-search-animal-btn');
    const searchResultDiv = document.getElementById('diet-log-search-animal-result');
    
    let activeAnimalForDietLog = null;

    // --- Event Listeners ---
    showModalBtn.addEventListener('click', openAddDietLogModal);
    cancelAddDietLogBtn.addEventListener('click', () => {
        addDietLogModal.classList.add('hidden');
    });
    
    addDietLogForm.onsubmit = handleAddDietLogSubmit; // Assign directly to prevent duplicates
    animalSearchBtn.addEventListener('click', searchForAnimal);

    searchResultDiv.addEventListener('change', (event) => {
        if (event.target.name === 'selectedAnimalForDietLog') {
            activeAnimalForDietLog = JSON.parse(event.target.value);
            console.log("Animal selected for diet log:", activeAnimalForDietLog);
        }
    });

    // --- Functions ---
    async function searchForAnimal() {
        const earTag = animalSearchInput.value.trim();
        if (!earTag) return;

        activeAnimalForDietLog = null;
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
                        <input type="radio" name="selectedAnimalForDietLog" id="animal-diet-log-${animal.id}" value='${animalDataString}'>
                        <label for="animal-diet-log-${animal.id}">
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

    function openAddDietLogModal() {
        addDietLogForm.reset();
        activeAnimalForDietLog = null;
        searchResultDiv.innerHTML = '';
        
        const dateInput = document.getElementById('diet-log-date');
        const today = new Date().toISOString().split('T')[0];
        dateInput.max = today;
        dateInput.value = today;

        addDietLogModal.classList.remove('hidden');
        animalSearchInput.focus();
    }

    async function handleAddDietLogSubmit(event) {
        event.preventDefault();

        if (!activeAnimalForDietLog) {
            showToast(getTranslation('error_no_animal_selected_for_diet_log'), 'error');
            return;
        }

        const payload = {
            date: document.getElementById('diet-log-date').value,
            diet_type: document.getElementById('new-diet-type').value,
            daily_intake_percentage: document.getElementById('new-diet-intake').value,
            weight_kg: document.getElementById('diet-log-weight-kg').value
        };
        
        try {
            const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/purchase/${activeAnimalForDietLog.id}/diet/add`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || 'An unknown error occurred');
            }

            showToast(result.message, 'success');
            loadDietLogHistoryData(); // Refresh the grid

            activeAnimalForDietLog = null;
            searchResultDiv.innerHTML = '';
            animalSearchInput.value = '';
            document.getElementById('new-diet-type').value = '';
            document.getElementById('new-diet-intake').value = '';
            document.getElementById('diet-log-weight-kg').value = '';
            animalSearchInput.focus(); // Set focus for the next search

        } catch (error) {
            showToast(`${getTranslation('error_recording_diet_log')}: ${error.message}`, 'error');
        }
    }

    loadDietLogHistoryData();
}

// Fetches diet log history data and populates the grid.
async function loadDietLogHistoryData() {
    const gridDiv = document.getElementById('diet-log-history-grid');
    if (!gridDiv) return;

    if (!selectedFarmId) {
        gridDiv.innerHTML = `<p>${getTranslation('select_farm_to_view_data')}</p>`;
        return;
    }

    try {
        const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/diets`);
        if (!response.ok) throw new Error('Failed to fetch diet log history');
        const history = await response.json();
        createDietLogHistoryGrid(history);

    } catch (error) {
        console.error("Error loading diet log history:", error);
        gridDiv.innerHTML = `<p style="color: red;">${getTranslation('error_loading_data')}</p>`;
    }
}

// Sets up and creates the AG Grid.
function createDietLogHistoryGrid(data) {
    const gridDiv = document.getElementById('diet-log-history-grid');
    if (!gridDiv) return;

    const columnDefs = [
        { headerName: getTranslation("date"), field: "date" },
        { 
            headerName: getTranslation("ear_tag"), 
            field: "ear_tag", 
            width: 120,
            onCellClicked: (params) => window.navigateToConsultAnimal(params.data.animal_id,'page-operations-diet-log'),
            cellClass: 'clickable-cell'
        },
        { headerName: getTranslation("lot"), field: "lot" },
        { headerName: getTranslation("diet_type"), field: "diet_type" },
        { headerName: getTranslation("diet_intake"), field: "daily_intake_percentage", valueFormatter: p => p.value ? `${p.value.toFixed(1)}%` : 'N/A' },
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