function initSettingsPage() {
    console.log("Initializing Settings Page...");
    const languageSelect = document.getElementById('language-select');

    const exportBtn = document.getElementById('export-data-btn');
    const importBtn = document.getElementById('import-data-btn');
    const importFileInput = document.getElementById('import-file-input');
    
    // Export Modal Elements
    const exportModal = document.getElementById('export-farms-modal');
    const exportForm = document.getElementById('export-farms-form');
    const cancelExportBtn = document.getElementById('cancel-export-farms');
    const farmListContainer = document.getElementById('export-farm-list');

    // Load saved language and set the dropdown to the correct value
    const savedLanguage = localStorage.getItem('bovitrack-language') || 'en';
    languageSelect.value = savedLanguage;

    // Listen for changes
    languageSelect.addEventListener('change', handleLanguageChange);

    if (exportBtn) {
        exportBtn.addEventListener('click', openExportModal);
    }

    if (cancelExportBtn) {
        cancelExportBtn.addEventListener('click', () => {
            exportModal.classList.add('hidden');
        });
    }

    if (exportForm) {
        exportForm.addEventListener('submit', handleExportSubmit);
    }
    
    if (importBtn) {
        importBtn.addEventListener('click', () => {
            importFileInput.click(); // Trigger the hidden file input
        });
    }
    
    if (importFileInput) {
        importFileInput.addEventListener('change', handleFileSelectedForImport);
    }
    async function openExportModal() {
        // 'allFarms' is a global variable from main-renderer.js
        if (!allFarms || allFarms.length === 0) {
            showToast("No farms available to export.", "error");
            return;
        }
    
        farmListContainer.innerHTML = ''; // Clear previous list
        allFarms.forEach(farm => {
            const farmItem = document.createElement('div');
            farmItem.className = 'farm-checkbox-item';
            farmItem.innerHTML = `
                <input type="checkbox" id="farm-export-${farm.id}" name="farm_ids" value="${farm.id}">
                <label for="farm-export-${farm.id}">${farm.name}</label>
            `;
            farmListContainer.appendChild(farmItem);
        });
    
        exportModal.classList.remove('hidden');
    }
    
    async function handleExportSubmit(event) {
        event.preventDefault();
        const submitButton = event.submitter;
        
        const selectedFarmIds = Array.from(exportForm.querySelectorAll('input[name="farm_ids"]:checked'))
                                     .map(checkbox => parseInt(checkbox.value, 10));
    
        if (selectedFarmIds.length === 0) {
            showToast(getTranslation('no_farms_selected_for_export'), 'error');
            return;
        }

        // --- Immediate UI Feedback ---
        const originalButtonText = submitButton.textContent;
        submitButton.disabled = true;
        submitButton.textContent = getTranslation('exporting');
        exportModal.classList.add('hidden'); // Hide modal immediately
        showToast(getTranslation('export_initiated'), 'success'); // Show initial toast
    
        try {
            const response = await fetch(`${API_URL}/api/export/farms/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ farm_ids: selectedFarmIds })
            });
    
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }
    
            // Handle the file download
            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = downloadUrl;
            
            // Extract filename from Content-Disposition header
            const disposition = response.headers.get('Content-Disposition');
            let filename = 'bovitrack_export.json';
            if (disposition && disposition.indexOf('attachment') !== -1) {
                const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
                const matches = filenameRegex.exec(disposition);
                if (matches != null && matches[1]) { 
                  filename = matches[1].replace(/['"]/g, '');
                }
            }
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(downloadUrl);
            a.remove();
    
        } catch (error) {
            console.error('Export failed:', error);
            showToast(`${getTranslation('export_failed')}: ${error.message}`, 'error');
        } finally {
            // --- Restore Button State ---
            submitButton.disabled = false;
            submitButton.textContent = originalButtonText;
        }
    }
    
    async function handleFileSelectedForImport(event) {
        const file = event.target.files[0];
        if (!file) {
            return;
        }
        
        // Reset file input to allow re-selecting the same file
        importFileInput.value = '';
    
        const confirmed = await showCustomConfirm(getTranslation('confirm_import_message', { fileName: file.name }));
        
        if (!confirmed) {
            return;
        }
    
        const formData = new FormData();
        formData.append('import_file', file);
    
        try {
            showToast("Importing data...", "success");
            const response = await fetch(`${API_URL}/api/import/farms/`, {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
    
            if (!response.ok) {
                throw new Error(result.error || `HTTP error! status: ${response.status}`);
            }
    
            showToast(result.message, 'success');
            
            // Reload the farm list and refresh current page data
            await loadFarms(); 
            await handleFarmSelection();
    
        } catch (error) {
            console.error('Import failed:', error);
            showToast(`${getTranslation('import_failed')}: ${error.message}`, 'error');
        }
    }
}

function handleLanguageChange(event) {
    const selectedLanguage = event.target.value;
    console.log(`Language changed to: ${selectedLanguage}`);
    
    // THE FIX: Call the correct global function from main-renderer.js
    // This is the designated function to handle all language-switching logic.
    setLanguage(selectedLanguage); 
}

async function openExportModal() {
    // 'allFarms' is a global variable from main-renderer.js
    if (!allFarms || allFarms.length === 0) {
        showToast("No farms available to export.", "error");
        return;
    }

    farmListContainer.innerHTML = ''; // Clear previous list
    allFarms.forEach(farm => {
        const farmItem = document.createElement('div');
        farmItem.className = 'farm-checkbox-item';
        farmItem.innerHTML = `
            <input type="checkbox" id="farm-export-${farm.id}" name="farm_ids" value="${farm.id}">
            <label for="farm-export-${farm.id}">${farm.name}</label>
        `;
        farmListContainer.appendChild(farmItem);
    });

    exportModal.classList.remove('hidden');
}

async function handleExportSubmit(event) {
    event.preventDefault();
    
    const selectedFarmIds = Array.from(exportForm.querySelectorAll('input[name="farm_ids"]:checked'))
                                 .map(checkbox => parseInt(checkbox.value, 10));

    if (selectedFarmIds.length === 0) {
        showToast(getTranslation('no_farms_selected_for_export'), 'error');
        return;
    }

    try {
        const response = await fetch(`${API_URL}/api/export/farms/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ farm_ids: selectedFarmIds })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }

        // Handle the file download
        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = downloadUrl;
        
        // Extract filename from Content-Disposition header
        const disposition = response.headers.get('Content-Disposition');
        let filename = 'bovitrack_export.json';
        if (disposition && disposition.indexOf('attachment') !== -1) {
            const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
            const matches = filenameRegex.exec(disposition);
            if (matches != null && matches[1]) { 
              filename = matches[1].replace(/['"]/g, '');
            }
        }
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(downloadUrl);
        a.remove();
        
        showToast(getTranslation('export_successful'), 'success');
        exportModal.classList.add('hidden');

    } catch (error) {
        console.error('Export failed:', error);
        showToast(`${getTranslation('export_failed')}: ${error.message}`, 'error');
    }
}

async function handleFileSelectedForImport(event) {
    const file = event.target.files[0];
    if (!file) {
        return;
    }
    
    // Reset file input to allow re-selecting the same file
    importFileInput.value = '';

    const confirmed = await showCustomConfirm(getTranslation('confirm_import_message', { fileName: file.name }));
    
    if (!confirmed) {
        return;
    }

    const formData = new FormData();
    formData.append('import_file', file);

    try {
        showToast("Importing data...", "success");
        const response = await fetch(`${API_URL}/api/import/farms/`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || `HTTP error! status: ${response.status}`);
        }

        showToast(result.message, 'success');
        
        // Reload the farm list and refresh current page data
        await loadFarms(); 
        await handleFarmSelection();

    } catch (error) {
        console.error('Import failed:', error);
        showToast(`${getTranslation('import_failed')}: ${error.message}`, 'error');
    }
}
