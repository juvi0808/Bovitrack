async function loadPurchaseHistoryData() {
    // We get the gridDiv reference just-in-time inside the function.
    const gridDiv = document.getElementById('purchase-history-grid');
    if (!gridDiv) {
        console.error("Purchase history grid element not found!");
        return;
    }

    if (!selectedFarmId) {
        gridDiv.innerHTML = `<p>${getTranslation('select_farm_to_view_purchase_history')}</p>`;
        return;
    }

    try {
        const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/purchases`);
        if (!response.ok) throw new Error('Failed to fetch purchase history');
        const purchases = await response.json();
        
        // We still need a helper function to create the grid, but it can live inside this function's scope.
        function createPurchaseHistoryGrid(data) {
            const columnDefs = [
                { headerName: getTranslation("ear_tag"), field: "ear_tag" },
                { headerName: getTranslation("lot"), field: "lot" },
                { headerName: getTranslation("entry_date"), field: "entry_date" },
                { headerName: getTranslation("entry_weight_kg"), field: "entry_weight", valueFormatter: p => p.value.toFixed(2) },
                { headerName: getTranslation("sex"), field: "sex" },
                { headerName: getTranslation("race"), field: "race" },
                { headerName: getTranslation("purchase_price"), field: "purchase_price", valueFormatter: p => p.value ? `$${p.value.toFixed(2)}` : 'N/A' },
            ];
            const gridOptions = {
                columnDefs: columnDefs,
                rowData: data,
                defaultColDef: { sortable: true, filter: true, resizable: true, cellStyle: { 'text-align': 'center' } },
                onGridReady: (params) => params.api.sizeColumnsToFit(),
            };
            gridDiv.innerHTML = '';
            createGrid(gridDiv, gridOptions);
        }

        createPurchaseHistoryGrid(purchases);

    } catch (error) {
        console.error("Error loading purchase history:", error);
        gridDiv.innerHTML = `<p style="color: red;">${getTranslation('error_loading_purchase_history')}</p>`;
    }
}

// This is the main "controller" for the Purchase History page.
function initHistoryPurchasesPage() {
    console.log("Initializing Purchase History Page...");
    let protocolsForCurrentPurchase = [];
    let lastSavedProtocols = []; // Our new cache for the last successful save


    
    // --- Element References ---
    // We get these just-in-time, now that we know the HTML is loaded.
    const gridDiv = document.getElementById('purchase-history-grid');
    const showModalBtn = document.getElementById('show-add-purchase-modal-btn');
    
    // Modal elements
    const addPurchaseModal = document.getElementById('add-purchase-modal');
    const addPurchaseForm = document.getElementById('add-purchase-form');
    const cancelAddPurchaseBtn = document.getElementById('cancel-add-purchase');
    const addProtocolBtn = document.getElementById('add-protocol-btn');
    const clearProtocolsBtn = document.getElementById('clear-protocols-btn');
    const protocolsListUl = document.getElementById('protocols-list');
    const purchaseEntryDateInput = document.getElementById('purchase-entry-date');
    const protocolDateInput = document.getElementById('protocol-date');

    // --- Event Listeners ---
    showModalBtn.addEventListener('click', openAddPurchaseModal);
    cancelAddPurchaseBtn.addEventListener('click', () => addPurchaseModal.classList.add('hidden'));
    addPurchaseForm.onsubmit = handleAddPurchaseSubmit;
    addProtocolBtn.addEventListener('click', handleAddProtocol);
    clearProtocolsBtn.addEventListener('click', () => {
        protocolsForCurrentPurchase.length = 0; // Clear the live array
        renderProtocolsList(); // Update the UI
    });
    protocolsListUl.addEventListener('click', (event) => {
        if (event.target.classList.contains('remove-item-btn')) {
            const indexToRemove = parseInt(event.target.dataset.index, 10);
            handleRemoveProtocol(indexToRemove);
        }
    });

    // When the main purchase date changes, automatically update the protocol date.
    purchaseEntryDateInput.addEventListener('change', () => {
        protocolDateInput.value = purchaseEntryDateInput.value;
    });

    // --- Modal Logic ---
async function openAddPurchaseModal() {
    // First, clear any old data from the form and reset the protocol list.
    addPurchaseForm.reset();
    pprotocolsForCurrentPurchase = [...lastSavedProtocols];
    renderProtocolsList();

    // Set default dates when modal opens ***
    const today = new Date().toISOString().split('T')[0];
    purchaseEntryDateInput.value = today; // Default purchase date to today
    protocolDateInput.value = today;      // Sync protocol date immediately

    // Show the modal immediately so the user sees something happening.
    addPurchaseModal.classList.remove('hidden');

    // --- Now, populate the locations dropdown ---
    const locationSelect = document.getElementById('purchase-location');
    locationSelect.innerHTML = `<option>${getTranslation('loading_locations')}</option>`;
    locationSelect.disabled = true; // Disable it while loading

    try {
        const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/locations`);
        if (!response.ok) throw new Error('Could not fetch locations');
        const locations = await response.json();

        // Let's see what is ACTUALLY in the 'locations' variable
        console.log("Parsed locations data:", locations);
        
        locationSelect.innerHTML = ''; // Clear "Loading..." message
        if (locations.length === 0) {
            locationSelect.innerHTML = `<option value="">${getTranslation('no_locations_found')}</option>`;
            // Keep it disabled
        } else {
            locations.forEach(loc => {
                const option = document.createElement('option');
                option.value = loc.id;
                option.textContent = loc.name;
                locationSelect.appendChild(option);
            });
            locationSelect.disabled = false; // Re-enable the dropdown
        }
    } catch (error) {
        console.error(error);
        locationSelect.innerHTML = '<option value="">Error loading locations.</option>';
    }
}
    
    function handleAddProtocol() {
        // Get values from the sub-form
        // const dateInput = document.getElementById('protocol-date');
        const typeInput = document.getElementById('protocol-type');
        const productInput = document.getElementById('protocol-product');
        const dosageInput = document.getElementById('protocol-dosage');
        const invoiceInput = document.getElementById('protocol-invoice');

        if (!protocolDateInput.value || !typeInput.value.trim()) {
            alert('Protocol Date and Type are required.');
            return;
        }

        // Add the new protocol to our temporary array
        protocolsForCurrentPurchase.push({
            date: protocolDateInput.value,
            protocol_type: typeInput.value.trim(),
            product_name: productInput.value.trim(),
            dosage: dosageInput.value.trim(),
            invoice_number: invoiceInput.value.trim()
        });

        // Clear the inputs for the next entry
        typeInput.value = '';
        productInput.value = '';
        dosageInput.value = '';
        invoiceInput.value = '';
        
        // Update the visual list on the screen
        renderProtocolsList();
    }

    function handleRemoveProtocol(index) {
        // Remove the item from the array by its index
        protocolsForCurrentPurchase.splice(index, 1);
        // Re-render the list to reflect the change
        renderProtocolsList();
    }

    function renderProtocolsList() {
        protocolsListUl.innerHTML = ''; // Clear the list
        if (protocolsForCurrentPurchase.length === 0) {
            protocolsListUl.innerHTML = `<li class="no-items">${getTranslation('no_protocols_added')}</li>`;
            return;                     
        }

        protocolsForCurrentPurchase.forEach((protocol, index) => {
            const li = document.createElement('li');
            const dosageText = protocol.dosage ? ` - ${protocol.dosage}` : '';
            li.innerHTML = `
                <span>${protocol.date} - ${protocol.protocol_type} (${protocol.product_name || 'N/A'})${dosageText}</span>
                <button type="button" class="remove-item-btn" data-index="${index}">×</button>
            `;
            protocolsListUl.appendChild(li);
        });
    }

    async function handleAddPurchaseSubmit(event) {
        event.preventDefault();
        
        // Gather data from the form into an object
        const formData = {
            ear_tag: document.getElementById('purchase-ear-tag').value,
            lot: document.getElementById('purchase-lot').value,
            entry_date: document.getElementById('purchase-entry-date').value,
            entry_age: document.getElementById('purchase-entry-age').value,
            entry_weight: document.getElementById('purchase-entry-weight').value,
            sex: document.getElementById('purchase-sex').value,
            race: document.getElementById('purchase-race').value,
            purchase_price: document.getElementById('purchase-price').value,
            location_id: document.getElementById('purchase-location').value,
            sanitary_protocols: protocolsForCurrentPurchase,
            diet_type: document.getElementById('purchase-diet-type').value,
            daily_intake_percentage: document.getElementById('purchase-diet-intake').value, 
        };

        try {
            const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/purchase/add`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || 'An unknown error occurred.');
            
            // 1. Update the cache with the protocols from the successful save.
            lastSavedProtocols = [...protocolsForCurrentPurchase];

            // 2. Give the user clear feedback.
            const successMessage = getTranslation('animal_saved_successfully', { earTag: formData.ear_tag });
            showToast(`${successMessage} ${getTranslation('form_ready_for_next_entry')}`, 'success');
            // 3. Refresh the data grid in the background so the user sees the new entry.
            loadPurchaseHistoryData(); 

            // 4. Reset only the fields unique to each animal.
            document.getElementById('purchase-ear-tag').value = '';
            document.getElementById('purchase-entry-weight').value = '';
            document.getElementById('purchase-entry-age').value = '';
            // 5. (UX) Automatically focus the cursor on the next ear tag field.
            document.getElementById('purchase-ear-tag').focus();
            }
        catch (error) {
            showToast(`${getTranslation('error_saving_animal')}: ${error.message}`, 'error');
            }
        }
    

    // Initial data load for the page
    loadPurchaseHistoryData();
}