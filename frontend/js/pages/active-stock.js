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
        summaryDiv.innerHTML = 'Please select a farm to view data.';
        gridDiv.innerHTML = '';
        return;
    }
    summaryDiv.innerHTML = 'Loading summary...';
    gridDiv.innerHTML = 'Loading animals...';

    try {
        const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/stock/active_summary`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        
        displaySummary(data.summary_kpis);
        createAnimalGrid(data.animals);
    } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
        summaryDiv.innerHTML = 'Error: Could not load summary data.';
        gridDiv.innerHTML = 'Error: Could not load animal list.';
    }
}

function displaySummary(kpis) {
    const summaryDiv = document.getElementById('summary-kpis');
    if (summaryDiv) {
        summaryDiv.innerHTML = `
            <p><strong>Total Active Animals:</strong> ${kpis.total_active_animals}</p>
            <p><strong>Males:</strong> ${kpis.number_of_males} | <strong>Females:</strong> ${kpis.number_of_females}</p>
            <p><strong>Average Age:</strong> ${kpis.average_age_months.toFixed(2)} months</p>
            <p><strong>Average GMD:</strong> ${kpis.average_gmd_kg_day.toFixed(3)} kg/day</p>
        `;
    }
}

function createAnimalGrid(animals) {
    const gridDiv = document.getElementById('animal-grid');
    if (gridDiv) {
        const columnDefs = [
        { headerName: "Ear Tag", field: "ear_tag", width: 120 },
        { headerName: "Lot", field: "lot", width: 100 },
        { headername: "Entry Date", field: "entry_date", width: 150 },
        { headerName: "Sex", field: "sex", width: 120 },
        { headerName: "Age (Months)", field: "kpis.current_age_months", valueFormatter: p => p.value.toFixed(2), width: 150 },
        { headerName: "Last Wt (kg)", field: "kpis.last_weight_kg", valueFormatter: p => p.value.toFixed(2), width: 150 },
        { headerName: "Last Wt Date", field: "kpis.last_weighting_date", width: 150 },
        { headerName: "Avg Daily Gain (kg)", field: "kpis.average_daily_gain_kg", valueFormatter: p => p.value.toFixed(3), width: 180 },
        { headerName: "Forecasted Weight", field: "kpis.forecasted_current_weight_kg", valueFormatter: p => p.value.toFixed(2), width: 180 },
        { headerName: "Current Location", field: "kpis.current_location_name" },
        { headerName: "Diet Type", field: "kpis.current_diet_type" },
        { headerName: "Diet Intake (%)", field: "kpis.current_diet_intake", valueFormatter: p => p.value ? `${p.value}%` : 'N/A', width: 150 },
    ];
        const gridOptions = {
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