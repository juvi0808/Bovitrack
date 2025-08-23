// This function is now at the top level, so main-renderer.js can call it.
async function loadDashboardData(page = 1) {
    const summaryDiv = document.getElementById('summary-kpis');
    const gridDiv = document.getElementById('animal-grid');
    const pageContent = document.getElementById('active-stock-content');
    
    if (!summaryDiv || !gridDiv) {
        console.error("Dashboard elements not found on the page!");
        return;
    }

    // Unhide the main content if it was hidden
    pageContent.classList.remove('hidden');

    if (!selectedFarmId) {
        summaryDiv.innerHTML = getTranslation('select_farm_to_view_data');
        gridDiv.innerHTML = '';
        return;
    }

    summaryDiv.innerHTML = getTranslation('loading_summary');
    gridDiv.innerHTML = getTranslation('loading_animals');

    try {
        const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/stock/active_summary`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        
        displaySummary(data.summary_kpis);
        createAnimalGrid(data.animals);

    } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
        summaryDiv.innerHTML = `Error: ${getTranslation('could_not_load_summary_data')}`;
        gridDiv.innerHTML = `Error: ${getTranslation('could_not_load_animal_list')}`;
    }
}

function displaySummary(kpis) {
    const summaryDiv = document.getElementById('summary-kpis');
    if (summaryDiv) {
        summaryDiv.innerHTML = `
            <p><strong>${getTranslation('total_active_animals')}:</strong> ${kpis.total_active_animals}</p>
            <p><strong>${getTranslation('males')}:</strong> ${kpis.number_of_males} | <strong>${getTranslation('females')}:</strong> ${kpis.number_of_females}</p>
            <p><strong>${getTranslation('average_age')}:</strong> ${kpis.average_age_months.toFixed(2)} ${getTranslation('months')}</p>
            <p><strong>${getTranslation('average_gmd')}:</strong> ${kpis.average_gmd_kg_day.toFixed(3)} kg/day</p>
        `;
    }
}

function createAnimalGrid(animals) {
    const gridDiv = document.getElementById('animal-grid');
    if (gridDiv) {
        const columnDefs = [       
        { 
            headerName: getTranslation("ear_tag"), 
            field: "ear_tag", 
            width: 120,
            onCellClicked: (params) => window.navigateToConsultAnimal(params.data.id,'page-active-stock'),
            cellClass: 'clickable-cell'
        },
        { 
            headerName: getTranslation("lot"), 
            field: "lot", 
            width: 100, 
            filter: 'agNumberColumnFilter',
            onCellClicked: (params) => window.navigateToConsultLot(params.value,'page-active-stock'),
            cellClass: 'clickable-cell'
        },
        { headerName: getTranslation("entry_date"), field: "entry_date", width: 150 },
        { headerName: getTranslation("sex"), field: "sex", width: 120 },
        { headerName: `${getTranslation('age')} (${getTranslation('months')})`, field: "kpis.current_age_months", valueFormatter: p => p.value.toFixed(2), width: 150 },
        { headerName: `${getTranslation('last_wt_kg')}`, field: "kpis.last_weight_kg", valueFormatter: p => p.value.toFixed(2), width: 150 },
        { headerName: getTranslation("last_wt_date"), field: "kpis.last_weighting_date", width: 150 },
        { headerName: getTranslation("avg_daily_gain_kg"), field: "kpis.average_daily_gain_kg", valueFormatter: p => p.value.toFixed(3), width: 180 },
        { headerName: getTranslation("forecasted_weight"), field: "kpis.forecasted_current_weight_kg", valueFormatter: p => p.value.toFixed(2), width: 180 },
        { 
            headerName: getTranslation("current_location"), 
            field: "kpis.current_location_name",
            onCellClicked: (params) => window.navigateToConsultLocation(params.data.kpis.current_location_id, params.value,'page-active-stock'),
            cellClass: (params) => params.value ? 'clickable-cell' : ''
        },
        { headerName: getTranslation("diet_type"), field: "kpis.current_diet_type" },
        { headerName: `${getTranslation('diet_intake')} (%)`, field: "kpis.current_diet_intake", valueFormatter: p => p.value ? `${p.value}%` : 'N/A', width: 150 },
    ];const gridOptions = {
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
}

function showNoFarmsModal() {
    const noFarmsModal = document.getElementById('no-farms-modal');
    const createNewBtn = document.getElementById('no-farms-create-new-btn');
    const loadDemoBtn = document.getElementById('no-farms-load-demo-btn');
    const addFarmModal = document.getElementById('add-farm-modal');
    const pageContent = document.getElementById('active-stock-content');


    // Hide the main page content
    if(pageContent) pageContent.classList.add('hidden');

    if (!noFarmsModal || !createNewBtn || !loadDemoBtn || !addFarmModal) {
        console.error("Welcome modal elements not found!");
        return;
    }

    noFarmsModal.classList.remove('hidden');

    // Button to open the regular "Add Farm" modal
    createNewBtn.onclick = () => {
        noFarmsModal.classList.add('hidden');
        addFarmModal.classList.remove('hidden');
    };

    // Button to load the demo farm
    loadDemoBtn.onclick = async () => {
        const originalButtonText = loadDemoBtn.textContent;
        loadDemoBtn.disabled = true;
        loadDemoBtn.textContent = getTranslation('loading_demo_farm');

        const demoPayload = {
          "farm_name": "BoviTrack Demo Farm",
          "years": 5,
          "end_date":"2025-08-22",
          "total_farm_area_ha": 100,
          "total_animal_purchases_per_year": 500,
          "monthly_concentration": {
            "1": 0.05, "2": 0.05, "3": 0.1, "4": 0.2, "5": 0.2, "6": 0.1,
            "7": 0.05, "8": 0.05, "9": 0.05, "10": 0.05, "11": 0.05, "12": 0.05
          },
          "weighting_frequency_days": 90,
          "sell_after_days": 390,
          "assumed_gmd_kg": 0.95,
          "sanitary_protocols": [
            { "protocol_type": "Vaccine A", "product_name": "Product X", "frequency_days": 180 },
            { "protocol_type": "Vaccine B", "product_name": "Product Y", "frequency_days": 180 },
            { "protocol_type": "Dewormer", "product_name": "Product Z", "frequency_days": 120 }
          ],
          "initial_diet": { "diet_type": "PE", "daily_intake_percentage": 0.3 },
          "diet_change": {
            "days_after_purchase": 365,
            "new_diet": { "diet_type": "TIP", "daily_intake_percentage": 2.0 }
          },
          "num_locations": 5,
          "num_sublocations_per_location": 4
        };

        try {
            const response = await fetch(`${API_URL}/api/dev/seed-test-farm`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(demoPayload)
            });

            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || 'Failed to seed demo farm');
            }

            showToast(getTranslation('demo_farm_loaded_successfully'), 'success');
            noFarmsModal.classList.add('hidden');
            
            // --- CRITICAL REFRESH SEQUENCE ---
            // 1. Reload the farm list. This will update 'allFarms' and populate the dropdown.
            await loadFarms(); 
            // 2. Trigger the farm selection logic. This will set 'selectedFarmId' and call 'loadDashboardData'.
            await handleFarmSelection();

        } catch (error) {
            console.error("Error loading demo farm:", error);
            showToast(`Error: ${error.message}`, 'error');
        } finally {
            loadDemoBtn.disabled = false;
            loadDemoBtn.textContent = originalButtonText;
        }
    };
}

// The init function is now very simple. It just calls the main data loader.
function initActiveStockPage() {
    console.log("Initializing Active Stock Page...");

    // Check if there are no farms. 'allFarms' is a global from main-renderer.js
    if (!allFarms || allFarms.length === 0) {
        showNoFarmsModal();
    } else {
        // If there are farms, proceed with the normal data loading.
        loadDashboardData();
    }
}