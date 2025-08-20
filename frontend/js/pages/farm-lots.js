async function loadLotsData() {
    const container = document.getElementById('lots-list-grid');
    if (!container) {
        console.error("Lots grid element not found!");
        return;
    }
    if (!selectedFarmId) {
        container.innerHTML = `<p>${getTranslation('select_farm_to_view_data')}</p>`;
        return;
    }

    try {
        const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/lots/summary`);
        if (!response.ok) throw new Error('Failed to fetch lots summary');
        const lots = await response.json();
        createLotsListGrid(lots);
    } catch (error) {
        console.error("Error loading lots summary:", error);
        container.innerHTML = `<p style="color: red;">${getTranslation('error_loading_data')}</p>`;
    }
}

function createLotsListGrid(lots) {
    const gridDiv = document.getElementById('lots-list-grid');
    if (!gridDiv) return;

    const columnDefs = [
        { headerName: getTranslation("lot"), field: "lot_number", width: 150, onCellClicked: (params) => showConsultView(params.data) },
        { headerName: getTranslation("animal_count"), field: "animal_count", width: 150, onCellClicked: (params) => showConsultView(params.data) },
        { headerName: getTranslation("males"), field: "male_count", width: 120, onCellClicked: (params) => showConsultView(params.data) },
        { headerName: getTranslation("females"), field: "female_count", width: 120, onCellClicked: (params) => showConsultView(params.data) },
        { headerName: `${getTranslation('average_age')} (${getTranslation('months')})`, field: "average_age_months", valueFormatter: p => p.value.toFixed(2), width: 180, onCellClicked: (params) => showConsultView(params.data) },
        { headerName: `${getTranslation('average_gmd')} (kg)`, field: "average_gmd_kg", valueFormatter: p => p.value.toFixed(3), width: 180, onCellClicked: (params) => showConsultView(params.data) },
        { headerName: `${getTranslation('forecasted_weight')} (kg)`, field: "average_weight_kg", valueFormatter: p => p.value.toFixed(2), width: 200, onCellClicked: (params) => showConsultView(params.data) },
    ];

    const gridOptions = {
        columnDefs: columnDefs,
        rowData: lots,
        defaultColDef: {
            sortable: true,
            filter: true,
            resizable: true,
            cellStyle: { 'text-align': 'center', 'cursor': 'pointer' }
        },
        onGridReady: (params) => params.api.sizeColumnsToFit(),
    };
    gridDiv.innerHTML = '';
    createGrid(gridDiv, gridOptions);
}

function renderLotSummaryKPIs(lotData, container) {
    if (!container) return;
    container.innerHTML = `
        <div class="kpi-item">
            <span class="kpi-value">${lotData.animal_count}</span>
            <span class="kpi-label">${getTranslation('animal_count')}</span>
        </div>
        <div class="kpi-item">
            <span class="kpi-value">${lotData.male_count} / ${lotData.female_count}</span>
            <span class="kpi-label">${getTranslation('males')} / ${getTranslation('females')}</span>
        </div>
        <div class="kpi-item">
            <span class="kpi-value">${lotData.average_age_months.toFixed(2)}</span>
            <span class="kpi-label">${getTranslation('average_age')} (${getTranslation('months')})</span>
        </div>
        <div class="kpi-item">
            <span class="kpi-value">${lotData.average_gmd_kg.toFixed(3)}</span>
            <span class="kpi-label">${getTranslation('average_gmd')} (kg)</span>
        </div>
        <div class="kpi-item">
            <span class="kpi-value">${lotData.average_weight_kg.toFixed(2)}</span>
            <span class="kpi-label">${getTranslation('forecasted_weight')} (kg)</span>
        </div>
    `;
}

function createLotAnimalsGrid(animals) {
    const gridDiv = document.getElementById('lot-animals-grid');
    if (!gridDiv) return;

    const columnDefs = [
        { headerName: getTranslation("ear_tag"), field: "ear_tag", width: 120 },
        { headerName: getTranslation("sex"), field: "sex", width: 100 },
        { headerName: `${getTranslation('age')} (${getTranslation('months')})`, field: "kpis.current_age_months", valueFormatter: p => p.value.toFixed(2), width: 150 },
        { headerName: getTranslation("last_wt_kg"), field: "kpis.last_weight_kg", valueFormatter: p => p.value.toFixed(2), width: 150 },
        { headerName: getTranslation("avg_daily_gain_kg"), field: "kpis.average_daily_gain_kg", valueFormatter: p => p.value.toFixed(3), width: 180 },
        { headerName: getTranslation("forecasted_weight"), field: "kpis.forecasted_current_weight_kg", valueFormatter: p => p.value.toFixed(2), width: 180 },
        { headerName: getTranslation("current_location"), field: "kpis.current_location_name" },
        { headerName: getTranslation("diet_type"), field: "kpis.current_diet_type" },
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


function initLotsPage() {
    console.log("Initializing Lots Page...");
    
    const lotsListView = document.getElementById('lots-list-view');
    const lotConsultView = document.getElementById('lot-consult-view');
    const backBtn = document.getElementById('back-to-lots-list-btn');
    const consultTitle = document.getElementById('lot-consult-title');
    const summaryContainer = document.getElementById('lot-summary-kpis');
    const gridContainer = document.getElementById('lot-animals-grid');

    if (!lotsListView || !lotConsultView || !backBtn) {
        console.error("Essential elements for Lots page are missing. Aborting initialization.");
        return; 
    }

    const showListView = () => {
        lotConsultView.classList.add('hidden');
        lotsListView.classList.remove('hidden');
        loadLotsData(); 
    };

    window.showConsultView = async (lotData) => {
        lotsListView.classList.add('hidden');
        lotConsultView.classList.remove('hidden');

        const lotNumber = lotData.lot_number;
        consultTitle.textContent = `${getTranslation('lot_summary')}: ${lotNumber}`;
        summaryContainer.innerHTML = `<p>${getTranslation('loading_summary')}...</p>`;
        if (gridContainer) gridContainer.innerHTML = `<p>${getTranslation('loading_animals')}...</p>`;
        
        // Render the summary KPIs immediately from the data we already have from the list view
        renderLotSummaryKPIs(lotData, summaryContainer);

        try {
            // Fetch the detailed list of animals for this lot
            const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/lot/${lotNumber}?status=active`);
            if (!response.ok) throw new Error('Failed to fetch lot details');
            const animals = await response.json();
            
            createLotAnimalsGrid(animals);

        } catch (error) {
            console.error("Error loading lot details:", error);
            if (gridContainer) gridContainer.innerHTML = `<p style="color: red;">${getTranslation('could_not_load_animal_list')}</p>`;
        }
    };
    
    backBtn.onclick = showListView;
    
    loadLotsData();
}