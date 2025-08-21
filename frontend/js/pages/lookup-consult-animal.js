function initConsultAnimalPage() {
    console.log("Initializing Consult Animal Page...");

    let weightChartInstance = null;

    // --- Element References ---
    const searchView = document.getElementById('animal-search-view');
    const masterRecordView = document.getElementById('animal-master-record-view');
    
    const searchInput = document.getElementById('consult-animal-search-eartag');
    const searchBtn = document.getElementById('consult-search-animal-btn');
    const searchResultDiv = document.getElementById('consult-search-animal-result');
    const backBtn = document.getElementById('back-to-search-btn');

    // Smart Back Button Logic
    if (window.consultAnimalReturnPage) {
        // Came from a grid click
        backBtn.textContent = getTranslation('back_to_list');
        backBtn.onclick = () => {
            navigateToPage(window.consultAnimalReturnPage);
            // Clean up global state after use
            window.consultAnimalReturnPage = null;
            window.animalIdToConsult = null;
        };
    } else {
        // Normal search flow
        backBtn.textContent = getTranslation('back_to_search');
        backBtn.onclick = () => {
            masterRecordView.classList.add('hidden');
            searchView.classList.remove('hidden');
            searchInput.value = '';
            searchResultDiv.innerHTML = '';
        };
    }
    
    // Check if we navigated here with a specific animal ID
    if (window.animalIdToConsult) {
        fetchAndDisplayMasterRecord(window.animalIdToConsult);
        window.animalIdToConsult = null; // Reset for next time
    }
    
    // --- Event Listeners ---
    searchBtn.addEventListener('click', handleAnimalSearch);
    searchInput.addEventListener('keyup', (event) => {
        if (event.key === 'Enter') {
            handleAnimalSearch();
        }
    });

    searchResultDiv.addEventListener('click', (event) => {
        const resultItem = event.target.closest('.search-result-item');
        if (resultItem) {
            const animalId = resultItem.dataset.animalId;
            fetchAndDisplayMasterRecord(animalId);
        }
    });

    backBtn.addEventListener('click', () => {
        masterRecordView.classList.add('hidden');
        searchView.classList.remove('hidden');
        searchInput.value = '';
        searchResultDiv.innerHTML = '';
    });


    // --- Functions ---
    async function handleAnimalSearch() {
        const earTag = searchInput.value.trim();
        if (!earTag) {
            searchResultDiv.innerHTML = '';
            return;
        }

        searchResultDiv.innerHTML = `<p>${getTranslation('loading_animals')}...</p>`;

        try {
            const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/animal/search?eartag=${earTag}`);
            const animals = await response.json();
            renderSearchResults(animals);
        } catch (error) {
            console.error('Error searching for animal:', error);
            searchResultDiv.innerHTML = `<p style="color: red;">${getTranslation('error_searching_animal')}</p>`;
        }
    }

    function renderSearchResults(animals) {
        searchResultDiv.innerHTML = '';
        if (animals.length === 0) {
            searchResultDiv.innerHTML = `<p style="padding: 10px;">${getTranslation('no_active_animal_found')}</p>`;
            return;
        }

        animals.forEach(animal => {
            const itemDiv = document.createElement('div');
            itemDiv.className = 'search-result-item';
            itemDiv.dataset.animalId = animal.id; // Store ID for easy retrieval
            itemDiv.style.cursor = 'pointer';

            itemDiv.innerHTML = `
                <label>
                    <div class="search-result-details-grid"> 
                        <div class="detail-row">
                            <span><b>${getTranslation('ear_tag')}:</b> ${animal.ear_tag}</span>
                            <span><b>${getTranslation('lot')}:</b> ${animal.lot}</span>
                            <span><b>${getTranslation('sex')}:</b> ${animal.sex}</span>
                        </div>
                        <div class="detail-row">
                             <span><b>${getTranslation('age')}:</b> ${animal.kpis.current_age_months.toFixed(1)} ${getTranslation('months')}</span>
                            <span><b>${getTranslation('location')}:</b> ${animal.kpis.current_location_name || 'N/A'}</span>
                            <span><b>${getTranslation('sublocation_name')}:</b> ${animal.kpis.current_sublocation_name || 'N/A'}</span>
                        </div>
                    </div>
               </label>
            `;
            searchResultDiv.appendChild(itemDiv);
        });
    }

    async function fetchAndDisplayMasterRecord(animalId) {
        if (!animalId) return;

        searchView.classList.add('hidden');
        masterRecordView.classList.remove('hidden');

        // Show loading states
        document.getElementById('animal-details-content').innerHTML = `<p>${getTranslation('loading_summary')}...</p>`;
        document.getElementById('animal-weight-history-grid').innerHTML = `<p>${getTranslation('loading_animals')}...</p>`;

        try {
            const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/animal/${animalId}`);
            if (!response.ok) throw new Error('Failed to fetch master record');
            const masterRecord = await response.json();

            renderMasterRecord(masterRecord);

        } catch (error) {
            console.error('Error fetching master record:', error);
            document.getElementById('animal-details-content').innerHTML = `<p style="color:red;">Could not load animal details.</p>`;
        }
    }

    function renderMasterRecord(data) {
        document.getElementById('master-record-title').textContent = `${getTranslation('animal_details_for')} #${data.purchase_details.ear_tag}`;

        // Render Details & KPIs
        const detailsContent = document.getElementById('animal-details-content');
        const pd = data.purchase_details;
        const kpis = data.calculated_kpis;

         // 1. Status Badge Logic
         let statusBadge = '';
         const statusClass = kpis.status.toLowerCase(); // active, sold, or dead
         statusBadge = `<strong class="status-badge ${statusClass}">${kpis.status}</strong>`;
 
         // 2. Exit Details Panel Logic
         let exitDetailsHtml = '';
         if (data.exit_details) {
             if (kpis.status === 'Sold') {
                 const profitLoss = data.exit_details.profit_loss;
                 const profitClass = profitLoss >= 0 ? 'profit' : 'loss';
                 const profitText = profitLoss ? `$${profitLoss.toFixed(2)}` : 'N/A';
 
                 exitDetailsHtml = `
                 <div class="details-panel exit-panel-sold">
                     <h4>${getTranslation('sale_details')}</h4>
                     <div class="info-grid">
                         <span>${getTranslation('exit_date')}:</span><strong>${data.exit_details.exit_date}</strong>
                         <span>${getTranslation('exit_weight_kg')}:</span><strong>${data.exit_details.exit_weight.toFixed(2)} kg</strong>
                         <span>${getTranslation('sale_price')}:</span><strong>$${data.exit_details.exit_price.toFixed(2)}</strong>
                         <span>${getTranslation('profit_loss')}:</span><strong class="${profitClass}">${profitText}</strong>
                     </div>
                 </div>`;
             } else if (kpis.status === 'Dead') {
                 exitDetailsHtml = `
                 <div class="details-panel exit-panel-dead">
                     <h4>${getTranslation('death_details')}</h4>
                     <div class="info-grid">
                         <span>${getTranslation('date_of_death')}:</span><strong>${data.exit_details.date}</strong>
                         <span>${getTranslation('cause_of_death')}:</span><strong>${data.exit_details.cause || 'N/A'}</strong>
                     </div>
                 </div>`;
             }
         }

         detailsContent.innerHTML = `
         <div class="details-container">
             <div class="details-panel info-panel">
                 <h4>${getTranslation('purchase_info')}</h4>
                 <div class="info-grid">
                     <span>${getTranslation('lot')}:</span><strong>${pd.lot}</strong>
                     <span>${getTranslation('sex')}:</span><strong>${pd.sex}</strong>
                     <span>${getTranslation('race')}:</span><strong>${pd.race || 'N/A'}</strong>
                     <span>${getTranslation('entry_date')}:</span><strong>${pd.entry_date}</strong>
                     <span>${getTranslation('entry_age_months')}:</span><strong>${pd.entry_age}</strong>
                     <span>${getTranslation('entry_weight_kg')}:</span><strong>${pd.entry_weight.toFixed(2)} kg</strong>
                     <span>${getTranslation('purchase_price')}:</span><strong>${pd.purchase_price ? `$${pd.purchase_price.toFixed(2)}` : 'N/A'}</strong>
                 </div>
             </div>
             <div class="details-panel kpi-panel">
                 <h4>${getTranslation('performance_kpis')}</h4>
                 <div class="kpi-grid">
                     <div class="kpi-card">
                         <span class="kpi-card-value">${kpis.days_on_farm}</span>
                         <span class="kpi-card-label">${getTranslation('days_on_farm')}</span>
                     </div>
                     <div class="kpi-card">
                         <span class="kpi-card-value">${kpis.current_age_months.toFixed(2)}</span>
                         <span class="kpi-card-label">${getTranslation('current_age_months')}</span>
                     </div>
                     <div class="kpi-card">
                         <span class="kpi-card-value">${kpis.average_daily_gain_kg.toFixed(3)} kg</span>
                         <span class="kpi-card-label">${getTranslation('avg_daily_gain_kg')}</span>
                     </div>
                     <div class="kpi-card">
                         <span class="kpi-card-value">${kpis.forecasted_current_weight_kg ? kpis.forecasted_current_weight_kg.toFixed(2) + ' kg' : 'N/A'}</span>
                         <span class="kpi-card-label">${getTranslation('forecasted_weight')}</span>
                     </div>
                 </div>
                 <div class="info-grid status-grid">
                     <span>${getTranslation('status')}:</span>${statusBadge}
                     <span>${getTranslation('current_location')}:</span><strong>${kpis.current_location_name || 'N/A'}</strong>
                      <span>${getTranslation('diet_type')}:</span><strong>${kpis.current_diet_type || 'N/A'}</strong>
                 </div>
             </div>
             ${exitDetailsHtml}
         </div>
     `;

        // Render Grids
        renderWeightChart(data.weight_history);
        createSubGrid('animal-weight-history-grid', data.weight_history, [
            { headerName: getTranslation("date"), field: "date" },
            { headerName: getTranslation("weighting_kg"), field: "weight_kg" },
            { headerName: getTranslation("gmd_accumulated"), field: "gmd_accumulated_grams", valueFormatter: p => `${(p.value * 1000).toFixed(0)} g` },
            { headerName: getTranslation("gmd_period"), field: "gmd_period_grams", valueFormatter: p => `${(p.value * 1000).toFixed(0)} g` },
        ]);

        createSubGrid('animal-protocol-history-grid', data.protocol_history, [
            { headerName: getTranslation("date"), field: "date" },
            { headerName: getTranslation("protocol_type_placeholder"), field: "protocol_type" },
            { headerName: getTranslation("product_name_placeholder"), field: "product_name" },
            { headerName: getTranslation("dosage_placeholder"), field: "dosage" },
        ]);
        
        createSubGrid('animal-location-history-grid', data.location_history, [
            { headerName: getTranslation("date"), field: "date" },
            { headerName: getTranslation("location_name"), field: "location_name" },
            { headerName: getTranslation("sublocation_name"), field: "sublocation_name" },
        ]);
        
        createSubGrid('animal-diet-history-grid', data.diet_history, [
            { headerName: getTranslation("date"), field: "date" },
            { headerName: getTranslation("diet_type"), field: "diet_type" },
            { headerName: getTranslation("diet_intake"), field: "daily_intake_percentage", valueFormatter: p => p.value ? `${p.value.toFixed(1)}%` : 'N/A' },
        ]);
    }
    
    function renderWeightChart(historyData) {
        const ctx = document.getElementById('weightHistoryChart');
        if (!ctx) return;
    
        if (weightChartInstance) {
            weightChartInstance.destroy();
        }

        if (!historyData || historyData.length < 2) {
            return; 
        }

        const labels = historyData.map(item => item.date);
        const weights = historyData.map(item => item.weight_kg);

        weightChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: getTranslation('weighting_kg'),
                    data: weights,
                    borderColor: 'rgba(0, 123, 255, 1)',
                    backgroundColor: 'rgba(0, 123, 255, 0.1)',
                    fill: true,
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: false,
                        title: { display: true, text: getTranslation('weighting_kg') }
                    },
                    x: {
                        title: { display: true, text: getTranslation('date') }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }

    function createSubGrid(gridId, rowData, columnDefs) {
        const gridDiv = document.getElementById(gridId);
        if (!gridDiv) return;
        
        const gridOptions = {
            columnDefs: columnDefs,
            rowData: rowData,
            defaultColDef: { 
                sortable: true, 
                filter: true, 
                resizable: true, 
                flex: 1,
                cellStyle: { 'text-align': 'center' } 
            },
        };

        gridDiv.innerHTML = ''; // Clear previous grid
        createGrid(gridDiv, gridOptions);
    }
}