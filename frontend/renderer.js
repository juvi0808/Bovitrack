console.log('Renderer.js script loaded!');

// STEP 1: We can now use 'require' directly in the renderer!
const { ModuleRegistry, AllCommunityModule, createGrid } = require('ag-grid-community');

// STEP 2: Register the modules right here.
ModuleRegistry.registerModules([AllCommunityModule]);


const API_URL = 'http://127.0.0.1:5000';
const summaryDiv = document.getElementById('summary-kpis');
const gridDiv = document.getElementById('animal-grid');


async function fetchActiveStock() {
    const farmId = 1;
    try {
        const response = await fetch(`${API_URL}/api/farm/${farmId}/stock/active_summary`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        displaySummary(data.summary_kpis);
        createAnimalGrid(data.animals);
    } catch (error) {
        console.error('Failed to fetch active stock:', error);
        summaryDiv.innerHTML = 'Error: Could not load summary data.';
        gridDiv.innerHTML = 'Error: Could not load animal list.';
    }
}

function displaySummary(kpis) {
    summaryDiv.innerHTML = `
        <p><strong>Total Active Animals:</strong> ${kpis.total_active_animals}</p>
        <p><strong>Males:</strong> ${kpis.number_of_males} | <strong>Females:</strong> ${kpis.number_of_females}</p>
        <p><strong>Average Age:</strong> ${kpis.average_age_months.toFixed(2)} months</p>
        <p><strong>Average GMD:</strong> ${kpis.average_gmd_kg_day.toFixed(3)} kg/day</p>
        <p><strong>Average Forecasted Weigth:</strong> ${kpis.average_forecasted_weight_kg.toFixed(2)} kg</p>
    `;
}

function createAnimalGrid(animals) {
    const columnDefs = [
        { headerName: "Ear Tag", field: "ear_tag", width: 120 },
        { headerName: "Lot", field: "lot", width: 100 },
        { headerName: "Age (Months)", field: "kpis.current_age_months", valueFormatter: p => p.value.toFixed(2), width: 150 },
        { headerName: "Sex", field: "sex", width: 100 },
        { headerName: "Current Location", field: "kpis.current_location_name" },
        { headerName: "Last Weitgh (kg)", field: "kpis.last_weight_kg", valueFormatter: p => p.value.toFixed(2), width: 150 },
        { headerName: "Last Weight Date", field: "kpis.last_weighting_date", width: 180 },
        { headerName: "Avg Daily Gain (kg)", field: "kpis.average_daily_gain_kg", valueFormatter: p => p.value.toFixed(3), width: 180 },
        { headerName: "forecasted_current_weight_kg", field: "kpis.forecasted_current_weight_kg", valueFormatter: p => p.value.toFixed(2), width: 180 },
        
    ];

    const gridOptions = {
        columnDefs: columnDefs,
        rowData: animals, // Pass the data directly
        defaultColDef: {
            sortable: true,
            filter: true,
            resizable: true,
        },
        onGridReady: (params) => {
            params.api.sizeColumnsToFit();
        },
    };

    // Clean out the div before creating the grid
    gridDiv.innerHTML = '';
    // Call the createGrid function we required at the top of the file.
    createGrid(gridDiv, gridOptions);
}

// Call our main function to start the process
fetchActiveStock();