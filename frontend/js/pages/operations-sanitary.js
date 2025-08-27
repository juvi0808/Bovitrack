// This is the "controller" for the Sanitary Protocol History page.
function initHistorySanitaryProtocolsPage() {
    console.log("Initializing Sanitary Protocol History Page...");

    let protocolsForSubmission = [];
    let lastSavedProtocols = []; // Cache for the last successful save
    let activeAnimalForProtocol = null;

    // --- Element References ---
    const showModalBtn = document.getElementById('show-add-sanitary-protocol-modal-btn');
    const addProtocolModal = document.getElementById('add-sanitary-protocol-modal');
    const cancelAddProtocolBtn = document.getElementById('cancel-add-sanitary-protocol');
    const addProtocolForm = document.getElementById('add-sanitary-protocol-form');
    
    // Animal Search elements
    const animalSearchInput = document.getElementById('sp-animal-search-eartag');
    const animalSearchBtn = document.getElementById('sp-search-animal-btn');
    const searchResultDiv = document.getElementById('sp-search-animal-result');

    // Protocol Sub-form elements
    const addProtocolBtn = document.getElementById('sp-add-protocol-btn');
    const clearProtocolsBtn = document.getElementById('sp-clear-protocols-btn');
    const protocolsListUl = document.getElementById('sp-protocols-list');
    const protocolDateInput = document.getElementById('sp-protocol-date');

    // --- Event Listeners ---
    showModalBtn.addEventListener('click', openAddSanitaryProtocolModal);
    cancelAddProtocolBtn.addEventListener('click', () => addProtocolModal.classList.add('hidden'));
    
    addProtocolForm.onsubmit = handleAddSanitaryProtocolSubmit;
    animalSearchBtn.addEventListener('click', searchForAnimal);
    
    searchResultDiv.addEventListener('change', (event) => {
        if (event.target.name === 'selectedAnimalForProtocol') {
            activeAnimalForProtocol = JSON.parse(event.target.value);
            console.log("Animal selected for protocol:", activeAnimalForProtocol);
        }
    });

    addProtocolBtn.addEventListener('click', handleAddProtocol);
    clearProtocolsBtn.addEventListener('click', () => {
        protocolsForSubmission = [];
        renderProtocolsList();
    });
    
    protocolsListUl.addEventListener('click', (event) => {
        if (event.target.classList.contains('remove-item-btn')) {
            const indexToRemove = parseInt(event.target.dataset.index, 10);
            protocolsForSubmission.splice(index, 1);
            renderProtocolsList();
        }
    });

    // --- Functions ---
    function openAddSanitaryProtocolModal() {
        // Restore the last saved protocols list
        protocolsForSubmission = [...lastSavedProtocols];
        renderProtocolsList();
        
        // Reset only the animal-specific parts
        addProtocolForm.reset();
        activeAnimalForProtocol = null;
        searchResultDiv.innerHTML = '';
        
        const today = new Date().toISOString().split('T')[0];
        protocolDateInput.value = today;

        addProtocolModal.classList.remove('hidden');
        animalSearchInput.focus();
    }

    async function searchForAnimal() {
        const earTag = animalSearchInput.value.trim();
        if (!earTag) return;

        activeAnimalForProtocol = null;
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
                        <input type="radio" name="selectedAnimalForProtocol" id="animal-protocol-${animal.id}" value='${animalDataString}'>
                        <label for="animal-protocol-${animal.id}">
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
    
    function handleAddProtocol() {
        const typeInput = document.getElementById('sp-protocol-type');
        const productInput = document.getElementById('sp-protocol-product');
        const dosageInput = document.getElementById('sp-protocol-dosage');
        const invoiceInput = document.getElementById('sp-protocol-invoice');

        if (!protocolDateInput.value || !typeInput.value.trim()) {
            alert('Protocol Date and Type are required.');
            return;
        }

        protocolsForSubmission.push({
            date: protocolDateInput.value,
            protocol_type: typeInput.value.trim(),
            product_name: productInput.value.trim(),
            dosage: dosageInput.value.trim(),
            invoice_number: invoiceInput.value.trim()
        });

        typeInput.value = '';
        productInput.value = '';
        dosageInput.value = '';
        invoiceInput.value = '';
        renderProtocolsList();
    }
    
    function renderProtocolsList() {
        protocolsListUl.innerHTML = '';
        if (protocolsForSubmission.length === 0) {
            protocolsListUl.innerHTML = `<li class="no-items">${getTranslation('no_protocols_added')}</li>`;
            return;                     
        }

        protocolsForSubmission.forEach((protocol, index) => {
            const li = document.createElement('li');
            const dosageText = protocol.dosage ? ` - ${protocol.dosage}` : '';
            li.innerHTML = `
                <span>${protocol.date} - ${protocol.protocol_type} (${protocol.product_name || 'N/A'})${dosageText}</span>
                <button type="button" class="remove-item-btn" data-index="${index}">×</button>
            `;
            protocolsListUl.appendChild(li);
        });
    }

    async function handleAddSanitaryProtocolSubmit(event) {
        event.preventDefault();

        if (!activeAnimalForProtocol) {
            showToast(getTranslation('error_no_animal_selected_for_protocol'), 'error');
            return;
        }
        if (protocolsForSubmission.length === 0) {
            showToast(getTranslation('error_no_protocols_added'), 'error');
            return;
        }

        const payload = {
            protocols: protocolsForSubmission,
            weight_kg: document.getElementById('sp-weight-kg').value // Read the optional weight
        };
        
        try {
            const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/purchase/${activeAnimalForProtocol.id}/sanitary/add/`, { // Will become ${API_URL}/api/farm/${selectedFarmId}/purchase/${activeAnimalForProtocol.id}/sanitary/add 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);

            // SUCCESS!
            showToast(result.message, 'success'); 
            
            // Fulfill the main requirement: keep the protocol list for the next animal
            lastSavedProtocols = [...protocolsForSubmission];
            
            // Reset only the animal-specific parts of the form
            activeAnimalForProtocol = null;
            searchResultDiv.innerHTML = '';
            animalSearchInput.value = '';
            document.getElementById('sp-weight-kg').value = '';
            animalSearchInput.focus();

            loadSanitaryProtocolHistoryData(); // Refresh the grid in the background

        } catch (error) {
            showToast(`${getTranslation('error_recording_protocols')}: ${error.message}`, 'error');
        }
    }

    loadSanitaryProtocolHistoryData();
}

async function loadSanitaryProtocolHistoryData() {
    const gridDiv = document.getElementById('sanitary-protocol-history-grid');
    if (!gridDiv) return;

    if (!selectedFarmId) {
        gridDiv.innerHTML = `<p>${getTranslation('select_farm_to_view_data')}</p>`;
        return;
    }

    try {
        const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/sanitary/`);
        if (!response.ok) throw new Error('Failed to fetch sanitary protocol history');
        const history = await response.json();
        createSanitaryProtocolHistoryGrid(history);

    } catch (error) {
        console.error("Error loading sanitary protocol history:", error);
        gridDiv.innerHTML = `<p style="color: red;">${getTranslation('error_loading_data')}</p>`;
    }
}

function createSanitaryProtocolHistoryGrid(data) {
    const gridDiv = document.getElementById('sanitary-protocol-history-grid');
    if (!gridDiv) return;

    const columnDefs = [
        { headerName: getTranslation("date"), field: "date" },
        { 
            headerName: getTranslation("ear_tag"), 
            field: "ear_tag", 
            width: 120,
            onCellClicked: (params) => window.navigateToConsultAnimal(params.data.animal_id,'page-operations-sanitary'),
            cellClass: 'clickable-cell'
        },
        { 
            headerName: getTranslation("lot"), 
            field: "lot", 
            width: 100, 
            filter: 'agNumberColumnFilter',
            onCellClicked: (params) => window.navigateToConsultLot(params.value,'page-operations-sanitary'),
            cellClass: 'clickable-cell'
        },
        { headerName: getTranslation("protocol_type_placeholder"), field: "protocol_type" },
        { headerName: getTranslation("product_name_placeholder"), field: "product_name" },
        { headerName: getTranslation("dosage_placeholder"), field: "dosage" },
        { headerName: getTranslation("invoice_number_placeholder"), field: "invoice_number" },
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