// This function is now at the top level, so main-renderer.js can call it.
async function loadDashboardData() {
    // Find elements just-in-time. This is the safest way.
    const summaryDiv = document.getElementById('summary-kpis');
    const gridDiv = document.getElementById('animal-grid');

    if (!summaryDiv || !gridDiv) {
        console.error("Dashboard elements not found on the page!");
        return;
    }

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
       { headerName: getTranslation("ear_tag"), field: "ear_tag", width: 120 },
        { headerName: getTranslation("lot"), field: "lot", width: 100 },
        { headerName: getTranslation("entry_date"), field: "entry_date", width: 150 },
        { headerName: getTranslation("sex"), field: "sex", width: 120 },
        { headerName: `${getTranslation('age')} (${getTranslation('months')})`, field: "kpis.current_age_months", valueFormatter: p => p.value.toFixed(2), width: 150 },
        { headerName: `${getTranslation('last_wt_kg')}`, field: "kpis.last_weight_kg", valueFormatter: p => p.value.toFixed(2), width: 150 },
        { headerName: getTranslation("last_wt_date"), field: "kpis.last_weighting_date", width: 150 },
        { headerName: getTranslation("avg_daily_gain_kg"), field: "kpis.average_daily_gain_kg", valueFormatter: p => p.value.toFixed(3), width: 180 },
        { headerName: getTranslation("forecasted_weight"), field: "kpis.forecasted_current_weight_kg", valueFormatter: p => p.value.toFixed(2), width: 180 },
        { headerName: getTranslation("current_location"), field: "kpis.current_location_name" },
        { headerName: getTranslation("diet_type"), field: "kpis.current_diet_type" },
        { headerName: `${getTranslation('diet_intake')} (%)`, field: "kpis.current_diet_intake", valueFormatter: p => p.value ? `${p.value}%` : 'N/A', width: 150 },
    ];const gridOptions = {
            columnDefs: columnDefs,
            rowData: animals,
            defaultColDet: {
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

// The init function is now very simple. It just calls the main data loader.
function initActiveStockPage() {
    console.log("Initializing Active Stock Page...");
    loadDashboardData();
}