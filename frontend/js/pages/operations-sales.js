// This is the "controller" for the Sales History page.
function initHistorySalesPage() {
    console.log("Initializing Sales History Page...");

    // --- Element References ---
    const showModalBtn = document.getElementById('show-add-sale-modal-btn');
    const addSaleModal = document.getElementById('add-sale-modal');
    const cancelAddSaleBtn = document.getElementById('cancel-add-sale');
    const addSaleForm = document.getElementById('add-sale-form');
    const animalSearchInput = document.getElementById('sale-animal-search-eartag');
    const animalSearchBtn = document.getElementById('search-animal-btn');
    const searchResultDiv = document.getElementById('search-animal-result');
    
    let activeAnimalForSale = null; // This will store the data of the animal we find.

    // --- Event Listeners ---
    showModalBtn.addEventListener('click', openAddSaleModal);
    cancelAddSaleBtn.addEventListener('click', () => {
        addSaleModal.classList.add('hidden');
    });
    
    // Assign directly to onsubmit. This prevents duplicate listeners
    addSaleForm.onsubmit = handleAddSaleSubmit;

    // Listen for clicks on the animal search button
    animalSearchBtn.addEventListener('click', searchForAnimal);
    searchResultDiv.addEventListener('change', (event) => {
        // Check if the thing that was changed was a radio button named 'selectedAnimal'
        if (event.target.name === 'selectedAnimal') {
            // The full animal data object was stored as a JSON string in the radio button's value.
            // We parse it back into an object here.
            activeAnimalForSale = JSON.parse(event.target.value);
            console.log("Animal selected for sale:", activeAnimalForSale);
        }
    });

    // --- Functions ---

    function openAddSaleModal() {
        // Reset the form every time we open it
        addSaleForm.reset();
        activeAnimalForSale = null;
        searchResultDiv.innerHTML = '';
        searchResultDiv.className = '';
        // Set the sale date to today by default
        document.getElementById('sale-date').value = new Date().toISOString().split('T')[0];
        addSaleModal.classList.remove('hidden');
        animalSearchInput.focus();
    }

    async function searchForAnimal() {    
        const earTag = animalSearchInput.value.trim();
        if (!earTag) return;

        // Reset state before new search
        activeAnimalForSale = null;
        searchResultDiv.innerHTML = `<p>${getTranslation('loading_animals')}...</p>`;

        try {
            const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/animal/search?eartag=${earTag}`);
            const animals = await response.json();

            searchResultDiv.innerHTML = ''; // Clear "Loading..."

            if (animals.length > 0) {
                // We found animals! Let's build the list.
                animals.forEach(animal => {
                    const itemDiv = document.createElement('div');
                    itemDiv.className = 'search-result-item';

                    // We store the ENTIRE animal object as a string in the radio's value.
                    // This is the easiest way to get all the data back when the user selects it.
                    const animalDataString = JSON.stringify(animal);

                    itemDiv.innerHTML = `
                        <input type="radio" name="selectedAnimal" id="animal-${animal.id}" value='${animalDataString}'>
                        <label for="animal-${animal.id}">
                            <div class="search-result-details-grid">
                                <div class="detail-row">
                                    <span><b>Lot:</b> ${animal.lot}</span>
                                    <span><b>Race:</b> ${animal.race || 'N/A'}</span>
                                    <span><b>${getTranslation('age')}:</b> ${animal.kpis.current_age_months.toFixed(1)} ${getTranslation('months')}</span>
                                </div>
                                <div class="detail-row">
                                    <span><b>Entry:</b> ${animal.entry_date}</span>
                                    <span><b>Location:</b> ${animal.kpis.current_location_name || 'N/A'}</span>
                                    <span><b>Diet:</b> ${animal.kpis.current_diet_type || 'N/A'}</span>
                                    <span></span> <!-- Empty span for alignment -->
                                </div>
                            </div>
                        </label>
                    `;
                    searchResultDiv.appendChild(itemDiv);
                });
            } else {
                // No active animal found.
                searchResultDiv.innerHTML = `<p style="padding: 10px;">${getTranslation('no_active_animal_found')}</p>`;
                }

        } catch (error) {
            console.error('Error searching for animal:', error);
            searchResultDiv.innerHTML = `<p style="color: red; padding: 10px;">${getTranslation('error_searching_animal')}</p>`;
        }
    }

    async function handleAddSaleSubmit(event) {
        event.preventDefault();

        // VALIDATION: Make sure we've successfully found an animal first.
        if (!activeAnimalForSale) {
            showToast(getTranslation('error_no_animal_selected_for_sale'), 'error');
            return;
        }

        const saleData = {
            date: document.getElementById('sale-date').value,
            sale_price: document.getElementById('sale-price').value,
            exit_weight: document.getElementById('sale-exit-weight').value,
        };

        try {
            // The endpoint needs the farm_id and the unique purchase_id of the animal.
            const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/purchase/${activeAnimalForSale.id}/sale/add`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(saleData)
            });

            const result = await response.json();
            if (!response.ok) throw new Error(result.error);

            showToast(getTranslation('sale_recorded_successfully', { earTag: activeAnimalForSale.ear_tag }), 'success');
            loadSalesHistoryData(); // Refresh the grid to show the new sale

            activeAnimalForSale = null;
            searchResultDiv.innerHTML = '';
            animalSearchInput.value = '';
            document.getElementById('sale-exit-weight').value = '';
            document.getElementById('sale-price').value = '';
            animalSearchInput.focus();

        } catch (error) {
            showToast(`${getTranslation('error_recording_sale')}: ${error.message}`, 'error');
        }
    }

    // Initial data load for the page
    loadSalesHistoryData();
}

// Fetches sales data from the API and populates the grid.
async function loadSalesHistoryData() {
    const gridDiv = document.getElementById('sales-history-grid');
    if (!gridDiv) return;

    if (!selectedFarmId) {
        gridDiv.innerHTML = `<p>${getTranslation('select_farm_to_view_sales_history')}</p>`;
        return;
    }

    try {
        const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/sales`);
        if (!response.ok) throw new Error('Failed to fetch sales history');
        const sales = await response.json();
        createSalesHistoryGrid(sales);

    } catch (error) {
        console.error("Error loading sales history:", error);
        gridDiv.innerHTML = `<p style="color: red;">${getTranslation('error_loading_sales_history')}</p>`;
    }
}

// Sets up and creates the AG Grid for sales history.
function createSalesHistoryGrid(data) {
    const gridDiv = document.getElementById('sales-history-grid');
    if (!gridDiv) return;

    const columnDefs = [
        { 
            headerName: getTranslation("ear_tag"), 
            field: "ear_tag", 
            width: 120,
            onCellClicked: (params) => window.navigateToConsultAnimal(params.data.animal_id,'page-operations-sales'),
            cellClass: 'clickable-cell'
        },
        { 
            headerName: getTranslation("lot"), 
            field: "lot", 
            width: 100, 
            filter: 'agNumberColumnFilter',
            onCellClicked: (params) => window.navigateToConsultLot(params.value,'page-operations-sales'),
            cellClass: 'clickable-cell'
        },
        { headerName: getTranslation("entry_date"), field: "entry_date" },
        { headerName: getTranslation("exit_date"), field: "exit_date" },
        { headerName: getTranslation("days_on_farm"), field: "days_on_farm" },
        { headerName: getTranslation("entry_weight_kg"), field: "entry_weight", valueFormatter: p => p.value.toFixed(2) },
        { headerName: getTranslation("exit_weight_kg"), field: "exit_weight", valueFormatter: p => p.value.toFixed(2) },
        { headerName: getTranslation("avg_daily_gain_kg"), field: "gmd_kg_day", valueFormatter: p => p.value.toFixed(3) },
        { headerName: getTranslation("purchase_price"), field: "entry_price", valueFormatter: p => p.value ? `$${p.value.toFixed(2)}` : 'N/A' },
        { headerName: getTranslation("sale_price"), field: "exit_price", valueFormatter: p => p.value ? `$${p.value.toFixed(2)}` : 'N/A' },
        { headerName: getTranslation("race"), field: "race" },
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