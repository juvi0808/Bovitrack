// This function is now at the top level, so main-renderer.js can call it.
async function loadDashboardData() {
    const summaryDiv = document.getElementById('summary-kpis');
    const gridDiv = document.getElementById('animal-grid');
    const pageContent = document.getElementById('active-stock-content');
    
    // NOTE: paginationControlsDiv is no longer needed here
    if (!summaryDiv || !gridDiv) {
        console.error("Dashboard elements not found on the page!");
        return;
    }

    pageContent.classList.remove('hidden');

    if (!selectedFarmId) {
        summaryDiv.innerHTML = getTranslation('select_farm_to_view_data');
        gridDiv.innerHTML = '';
        return;
    }

    summaryDiv.innerHTML = getTranslation('loading_summary');
    gridDiv.innerHTML = getTranslation('loading_animals');
    
    try {
        // The URL no longer needs a page parameter
        const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/stock/active_summary/`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        
        displaySummary(data.summary_kpis);
        // We now get the data from the 'animals' key, not 'results'
        createAnimalGrid(data.animals);
        // The call to displayPaginationControls is removed

    } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
        summaryDiv.innerHTML = `Error: ${getTranslation('could_not_load_summary_data')}`;
        gridDiv.innerHTML = `Error: ${getTranslation('could_not_load_animal_list')}`;
    }
}

function displayPaginationControls(data, currentPage) {
    const container = document.getElementById('pagination-controls');
    if (!container) return;

    container.innerHTML = ''; // Clear previous controls

    if (data.count === 0 || !data.results || data.results.length === 0) {
        return;
    }
    
    // This calculation is a bit tricky since the API doesn't give us total_pages,
    // so we derive it.
    const pageSize = 100; // As set in your backend view
    const totalPages = Math.ceil(data.count / pageSize);

    if (totalPages <= 1) return; // Don't show controls for a single page

    // Previous Button
    const prevButton = document.createElement('button');
    prevButton.textContent = getTranslation('previous'); // <-- FIX
    prevButton.disabled = !data.previous;
    prevButton.className = 'button-secondary';
    prevButton.onclick = () => loadDashboardData(currentPage - 1);

    // Page Info Span
    const pageInfo = document.createElement('span');
    pageInfo.textContent = `${getTranslation('page')} ${currentPage} ${getTranslation('of')} ${totalPages}`; // <-- FIX
    pageInfo.style.margin = '0 15px';


    // Next Button
    const nextButton = document.createElement('button');
    nextButton.textContent = getTranslation('next'); // <-- FIX
    nextButton.disabled = !data.next;
    nextButton.className = 'button-secondary';
    nextButton.onclick = () => loadDashboardData(currentPage + 1);

    container.append(prevButton, pageInfo, nextButton);
}

function displaySummary(kpis) {
    const summaryDiv = document.getElementById('summary-kpis');
    if (summaryDiv) {
        // THE FIX: Use the '|| 0' trick to provide a default value if a kpi is null.
        const totalAnimals = kpis.total_active_animals || 0;
        const males = kpis.number_of_males || 0;
        const females = kpis.number_of_females || 0;
        const avgAge = kpis.average_age_months || 0;
        const avgGmd = kpis.average_gmd_kg_day || 0;

        summaryDiv.innerHTML = `
            <div class="kpi-card">
                <span class="kpi-card-value">${totalAnimals}</span>
                <span class="kpi-card-label">${getTranslation('total_active_animals')}</span>
            </div>
            <div class="kpi-card">
                <span class="kpi-card-value">${males} / ${females}</span>
                <span class="kpi-card-label">${getTranslation('males')} / ${getTranslation('females')}</span>
            </div>
            <div class="kpi-card">
                <span class="kpi-card-value">${avgAge.toFixed(2)}</span>
                <span class="kpi-card-label">${getTranslation('average_age')} (${getTranslation('months')})</span>
            </div>
            <div class="kpi-card">
                <span class="kpi-card-value">${avgGmd.toFixed(3)} kg/day</span>
                <span class="kpi-card-label">${getTranslation('average_gmd')}</span>
            </div>
        `;
    }
}
function createAnimalGrid(animals) {
    const gridDiv = document.getElementById('animal-grid');
    if (gridDiv) {

        gridDiv.className = 'ag-theme-quartz full-height-grid';
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
            { 
                headerName: `${getTranslation('age')} (${getTranslation('months')})`, 
                field: "kpis.current_age_months", 
                valueFormatter: p => p.value != null ? p.value.toFixed(2) : '', 
                width: 150 
            },
            { 
                headerName: `${getTranslation('last_wt_kg')}`, 
                field: "kpis.last_weight_kg", 
                valueFormatter: p => p.value != null ? p.value.toFixed(2) : '', 
                width: 150 
            },
            { headerName: getTranslation("last_wt_date"), field: "kpis.last_weighting_date", width: 150 },
            { 
                headerName: getTranslation("avg_daily_gain_kg"), 
                field: "kpis.average_daily_gain_kg", 
                valueFormatter: p => p.value != null ? p.value.toFixed(3) : '', 
                width: 180 
            },
            { 
                headerName: getTranslation("forecasted_weight"), 
                field: "kpis.forecasted_current_weight_kg", 
                valueFormatter: p => p.value != null ? p.value.toFixed(2) : '', 
                width: 180 
            },
            { 
                headerName: getTranslation("current_location"), 
                field: "kpis.current_location_name",
                onCellClicked: (params) => window.navigateToConsultLocation(params.data.kpis.current_location_id, params.value,'page-active-stock'),
                cellClass: (params) => params.value ? 'clickable-cell' : ''
            },
            { headerName: getTranslation("diet_type"), field: "kpis.current_diet_type" },
            { headerName: `${getTranslation('diet_intake')} (%)`, field: "kpis.current_diet_intake", valueFormatter: p => p.value ? `${p.value}%` : 'N/A', width: 150 },
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
            const response = await fetch(`${API_URL}/api/dev/seed-test-farm/`, {
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