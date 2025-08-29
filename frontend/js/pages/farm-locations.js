let tempGeoJson = null;

// This class lets us create custom HTML elements that act like map markers.

const farmLocationsPageManager = (() => {
    console.log("Initializing Locations Page...");


    const COLOR_PALETTE = [
        '#FFFF00', // Yellow
        '#1E90FF', // DodgerBlue
        '#FF6347', // Tomato
        '#00FA9A', // MediumSpringGreen
        '#FF00FF', // Fuchsia
        '#00FFFF', // Aqua
        '#FFD700', // Gold
        '#BA55D3', // MediumOrchid
        '#ADFF2F', // GreenYellow
        '#FFA500', // Orange
    ];

    // --- Page-Specific State Variables ---
    let map;
    let drawingManager;
    let infoWindow;
    let isMapInitialized = false;
    let currentlyEditingFeature = null;
    let originalGeoJsonForCancel = null;
    let currentParentLocationId = null;
    
    // --- NEW STATE VARIABLES FOR CROSS-VIEW ACTIONS ---
    let locationIdToDrawFor = null; // Stores {id, name} of location needing a shape
    let locationIdToFocusOnLoad = null; // Stores ID of location to focus on when map loads
    let mapLabels = []; // To keep track of our custom labels

    let Label = null; 

    let pageContainer, locationsContainer, locationsListView, locationConsultView, locationsMapView,
        showListViewBtn, showMapViewBtn, showAddLocationModalBtn, addLocationModal,
        addLocationForm, cancelAddLocationBtn, editLocationModal, editLocationForm,
        cancelEditLocationBtn, addSublocationModal, addSublocationForm,
        cancelAddSublocationBtn, backBtn, editSublocationModal, editSublocationForm,
        cancelEditSublocationBtn, mapEditBox, mapEditTitle, mapSaveChangesBtn, mapCancelEditBtn;


   

    // This function can now be called from outside (e.g., from main-renderer.js)
    async function loadLocationsData() {
        const locationsContainer = document.getElementById('locations-container');
        if (!locationsContainer) return; // Safety check

        if (!selectedFarmId) {
            locationsContainer.innerHTML = `<p>${getTranslation('select_farm_to_view_locations')}</p>`;
            return;
        }
        try {
            const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/locations/`);
            if (!response.ok) throw new Error('Failed to fetch locations');
            const locations = await response.json();
            renderLocationsList(locations);
            if (isMapInitialized) {
                renderLocationsOnMap(locations);
            }
        } catch (error) {
            console.error("Error loading locations:", error);
            locationsContainer.innerHTML = `<p style="color: red;">${getTranslation('error_loading_locations_history')}</p>`;
        }
    }

    function renderLocationsList(locations) {
        if (!locationsContainer) return;
        locationsContainer.innerHTML = '';
        if (locations.length === 0) {
            locationsContainer.innerHTML = `<p>${getTranslation('no_locations_found')}</p>`;
            return;
        }
        locations.forEach(location => {
            const locationCard = document.createElement('div');
            locationCard.className = 'location-card';

            const mapButtonHtml = location.geo_json_data
                ? `<button class="button-secondary see-on-map-btn" data-location-id="${location.id}">${getTranslation('see_on_map')}</button>`
                : `<button class="button-primary draw-on-map-btn" data-location-id="${location.id}" data-location-name="${location.name}">${getTranslation('draw_on_map')}</button>`;
            let sublocationsHtml = `<p>${getTranslation('no_subdivisions_yet')}</p>`;
            if (location.sublocations && location.sublocations.length > 0) {
                sublocationsHtml = `<ul class="sublocation-list">${location.sublocations.map(sub => `
                    <li class="${sub.animal_count > 0 ? 'occupied' : ''}">
                        <div class="sublocation-info">
                            <span>${sub.name}</span>
                            <span class="sublocation-area">${sub.area_hectares ? sub.area_hectares.toFixed(2) + ' ha' : ''}</span>
                        </div>
                        ${sub.animal_count > 0 ? `<span class="occupied-animal-count">${getTranslation('animal_occupation')}: ${sub.animal_count}</span>` : ''}
                        <div class="sublocation-actions">
                             <button class="button-secondary assign-herd-btn" data-location-id="${location.id}" data-location-name="${location.name}" data-sublocation-id="${sub.id}" data-sublocation-name="${sub.name}">${getTranslation('assign_herd')}</button>
                            <button class="action-button edit-sublocation-btn" data-sublocation-id="${sub.id}" title="${getTranslation('edit')}">✏️</button>
                            <button class="action-button btn-danger delete-sublocation-btn" data-sublocation-id="${sub.id}" data-sublocation-name="${sub.name}" title="${getTranslation('delete')}">🗑️</button>
                        </div>
                    </li>`).join('')}</ul>`;
            }
            locationCard.innerHTML = `
                <div class="location-card-header">
                    <h3>${location.name}</h3>
                    <div class="location-card-actions">
                        ${mapButtonHtml}
                        <button class="action-button edit-location-btn" data-location-id="${location.id}" title="${getTranslation('edit')}">✏️</button>
                        <button class="action-button btn-danger delete-location-btn" data-location-id="${location.id}" data-location-name="${location.name}" title="${getTranslation('delete')}">🗑️</button>
                        <button class="button-primary see-details-btn" data-location-id="${location.id}" data-location-name="${location.name}">${getTranslation('see_details')}</button>
                        <button class="button-secondary add-subdivision-btn" data-location-id="${location.id}" data-location-name="${location.name}">${getTranslation('add_new_subdivision')}</button>
                    </div>
                </div>
                <div class="location-card-kpis">
                    <div class="kpi-item"><span class="kpi-value">${location.kpis.animal_count}</span><span class="kpi-label">${getTranslation('animal_count')}</span></div>
                    <div class="kpi-item"><span class="kpi-value">${location.area_hectares ? location.area_hectares.toFixed(2) + ' ha' : 'N/A'}</span><span class="kpi-label">${getTranslation('area_hectares')}</span></div>
                    <div class="kpi-item"><span class="kpi-value">${location.grass_type || 'N/A'}</span><span class="kpi-label">${getTranslation('grass_type')}</span></div>
                    <div class="kpi-item"><span class="kpi-value">${location.kpis.capacity_rate_actual_ua_ha || 'N/A'}</span><span class="kpi-label">${getTranslation('capacity_rate_actual_ua_ha')}</span></div>
                    <div class="kpi-item"><span class="kpi-value">${location.kpis.capacity_rate_forecasted_ua_ha || 'N/A'}</span><span class="kpi-label">${getTranslation('capacity_rate_forecasted_ua_ha')}</span></div>
                </div>
                <div class="location-card-body"><h4 class="subdivision-header">${getTranslation('subdivisions')}</h4>${sublocationsHtml}</div>`;
            locationsContainer.appendChild(locationCard);
        });
    }

    function initializeMapView() {
        if (!Label) {
            Label = class extends google.maps.OverlayView {
                constructor(map, position, text, color) {
                    super();
                    this.map = map;
                    this.position = position;
                    this.text = text;
                    this.color = color;
                    this.div = null;
                    this.setMap(map);
                }
            
                onAdd() {
                    this.div = document.createElement('div');
                    this.div.className = 'map-location-label';
                    this.div.innerHTML = this.text;
                    this.div.style.color = this.color; // Apply dynamic color
            
                    const panes = this.getPanes();
                    panes.overlayLayer.appendChild(this.div);
                }
            
                draw() {
                    const projection = this.getProjection();
                    const point = projection.fromLatLngToDivPixel(this.position);
            
                    if (point) {
                        this.div.style.left = `${point.x}px`;
                        this.div.style.top = `${point.y}px`;
                    }
                }
            
                onRemove() {
                    if (this.div) {
                        this.div.parentNode.removeChild(this.div);
                        this.div = null;
                    }
                }
            
                setText(text) {
                    this.text = text;
                    if (this.div) {
                        this.div.innerHTML = this.text;
                    }
                }
            }
        }
        
        // This part only runs once to create the map objects
        if (!isMapInitialized) {
            let initialCenter = { lat: -15.7942, lng: -47.8825 }, initialZoom = 4;
            try {
                const savedCenter = localStorage.getItem('bovitrack-map-center'), savedZoom = localStorage.getItem('bovitrack-map-zoom');
                if (savedCenter) initialCenter = JSON.parse(savedCenter);
                if (savedZoom) initialZoom = parseInt(savedZoom, 10);
            } catch (e) { console.error("Error parsing map state", e); }

            map = new google.maps.Map(document.getElementById('map-canvas'), { center: initialCenter, zoom: initialZoom, mapTypeId: 'hybrid' });
            infoWindow = new google.maps.InfoWindow();
            drawingManager = new google.maps.drawing.DrawingManager({
                drawingMode: null, drawingControl: true,
                drawingControlOptions: { position: google.maps.ControlPosition.TOP_CENTER, drawingModes: ['polygon'] },
                polygonOptions: { fillColor: '#FF0000', fillOpacity: 0.35, strokeWeight: 2, strokeColor: '#FF0000', clickable: false, editable: true, zIndex: 1 }
            });
            drawingManager.setMap(map);

            google.maps.event.addListener(drawingManager, 'polygoncomplete', handlePolygonComplete);
            map.addListener('idle', () => {
                const center = map.getCenter();
                const zoom = map.getZoom();
                // We need to convert the center object to a string to store it
                localStorage.setItem('bovitrack-map-center', JSON.stringify(center.toJSON()));
                localStorage.setItem('bovitrack-map-zoom', zoom);
            });

            map.data.setStyle({
                clickable: true, editable: false, fillColor: '#007bff',
                strokeColor: '#007bff', fillOpacity: 0.35, strokeWeight: 2, zIndex: 1
            });

            map.data.addListener('click', event => {
                const feature = event.feature;
                const content = createInfoWindowContent(feature);
                
                // For polygons, we calculate the center to place the info window.
                const bounds = new google.maps.LatLngBounds();
                feature.getGeometry().forEachLatLng(latlng => bounds.extend(latlng));
                const position = bounds.getCenter();

                infoWindow.setContent(content);
                infoWindow.setPosition(position);
                infoWindow.open(map);
            });

            isMapInitialized = true;
        }

        // This part runs EVERY time you switch to the map view
        loadLocationsData();
        
        if (locationIdToDrawFor) {
            drawingManager.setDrawingMode(google.maps.drawing.OverlayType.POLYGON);
        }
    }

    function renderLocationsOnMap(locations) {
        // Clear old shapes and labels
        map.data.forEach(f => { if (f.getProperty('type') === 'pasture') map.data.remove(f); });
        mapLabels.forEach(label => label.setMap(null));
        mapLabels = [];

        if (!locations || locations.length === 0) return;

        const bounds = new google.maps.LatLngBounds();
        let shapesExist = false;
        
        locations.forEach((loc, index) => {
            let geoData = loc.geo_json_data;
            if (geoData && typeof geoData === 'string') { try { geoData = JSON.parse(geoData); } catch (e) { geoData = null; } }
            
            if (geoData && typeof geoData === 'object') {
                shapesExist = true;
                let featureData = (geoData.type === 'Feature') ? geoData : { type: 'Feature', geometry: geoData, properties: {} };
                featureData.properties = { 
                    ...featureData.properties, 
                    type: 'pasture', 
                    locationId: loc.id, 
                    locationName: loc.name, 
                    area: loc.area_hectares, 
                    animalCount: loc.kpis.animal_count, 
                    locationType: loc.location_type, 
                    grassType: loc.grass_type,
                    capacityRateActual: loc.kpis.capacity_rate_actual_ua_ha,
                    capacityRateForecast: loc.kpis.capacity_rate_forecasted_ua_ha
                };
                
                const features = map.data.addGeoJson(featureData);
                const feature = features[0];

                if (feature) {
                    // 1. Calculate and apply the unique color
                    const color = COLOR_PALETTE[index % COLOR_PALETTE.length];
                    map.data.overrideStyle(feature, {
                        fillColor: color,
                        strokeColor: color
                    });

                    // 2. Calculate the center and create the label
                    const featureBounds = new google.maps.LatLngBounds();
                    feature.getGeometry().forEachLatLng(latlng => featureBounds.extend(latlng));
                    
                    const labelText = `${loc.name}<br>${loc.area_hectares ? loc.area_hectares.toFixed(2) + ' ha' : ''}`;
                    const label = new Label(map, featureBounds.getCenter(), labelText, color);
                    mapLabels.push(label);

                    // Extend the main bounds
                    feature.getGeometry().forEachLatLng(latlng => bounds.extend(latlng));
                }
            }
        });

        // Handle auto-zoom and focus logic
        if (shapesExist && !bounds.isEmpty() && !locationIdToFocusOnLoad) {
            map.fitBounds(bounds);
        }

        if (locationIdToFocusOnLoad) {
            let featureFound = false;
            map.data.forEach(feature => {
                if (feature.getProperty('locationId') == locationIdToFocusOnLoad) {
                    featureFound = true;
                    const featureBounds = new google.maps.LatLngBounds();
                    feature.getGeometry().forEachLatLng(latlng => featureBounds.extend(latlng));
                    map.fitBounds(featureBounds);
                    infoWindow.setContent(createInfoWindowContent(feature));
                    infoWindow.setPosition(featureBounds.getCenter());
                    infoWindow.open(map);
                }
            });
            if (!featureFound) console.error(`Could not find feature with ID ${locationIdToFocusOnLoad}`);
            locationIdToFocusOnLoad = null;
        }
    }

    async function handlePolygonComplete(polygon) {
        drawingManager.setDrawingMode(null); // Always turn off drawing mode
        const area = google.maps.geometry.spherical.computeArea(polygon.getPath()) / 10000;
        
        // Case 1: We are assigning a shape to an existing location
        if (locationIdToDrawFor) {
            const locationToUpdate = locationIdToDrawFor;
            locationIdToDrawFor = null; // Clear the flag immediately

            const dataLayer = new google.maps.Data();
            dataLayer.add(new google.maps.Data.Feature({ geometry: new google.maps.Data.Polygon([polygon.getPath().getArray()]) }));
            
            dataLayer.toGeoJson(async (geoJson) => {
                const shapeData = (geoJson.features && geoJson.features.length > 0) ? JSON.stringify(geoJson.features[0]) : null;
                if (!shapeData) {
                    polygon.setMap(null);
                    return;
                }

                const confirmed = await showCustomConfirm(getTranslation('confirm_assign_shape', { name: locationToUpdate.name }));
                
                if (confirmed) {
                    try {
                        // We must fetch the original data to not overwrite other fields
                        const fetchResponse = await fetch(`${API_URL}/api/farm/${selectedFarmId}/location/${locationToUpdate.id}/`);
                        if (!fetchResponse.ok) throw new Error('Could not fetch original location data.');
                        const originalData = (await fetchResponse.json()).location_details;
                        
                        // Create the payload, preserving old data and adding the new shape
                        const payload = {
                            name: originalData.name,
                            location_type: originalData.location_type,
                            grass_type: originalData.grass_type,
                            area_hectares: area, // Use the new calculated area
                            geo_json_data: shapeData // Add the new shape data
                        };

                        const updateResponse = await fetch(`${API_URL}/api/farm/${selectedFarmId}/location/${locationToUpdate.id}/`, {
                            method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
                        });

                        const result = await updateResponse.json();
                        if (!updateResponse.ok) throw new Error(result.error || 'Failed to save shape');
                        
                        showToast(getTranslation('shape_assigned_successfully', { name: result.name }), 'success');
                        loadLocationsData(); // Refresh everything

                    } catch (error) {
                        showToast(`${getTranslation('error_assigning_shape')}: ${error.message}`, 'error');
                    }
                }
            });
            polygon.setMap(null); // Remove the temporary red polygon

        // Case 2: The original behavior - creating a brand new location
        } else {
            const dataLayer = new google.maps.Data();
            dataLayer.add(new google.maps.Data.Feature({ geometry: new google.maps.Data.Polygon([polygon.getPath().getArray()]) }));
            dataLayer.toGeoJson(async (geoJson) => {
                tempGeoJson = (geoJson.features && geoJson.features.length > 0) ? JSON.stringify(geoJson.features[0]) : null;
                const confirmed = await showCustomConfirm(getTranslation('location_drawn_prompt_text', { area: area.toFixed(2) }));
                if (confirmed && tempGeoJson) {
                    addLocationForm.reset();
                    document.getElementById('location-area-input').value = area.toFixed(4);
                    document.getElementById('location-area-input').readOnly = true;
                    addLocationModal.classList.remove('hidden');
                } else {
                    tempGeoJson = null;
                }
            });
            polygon.setMap(null);
        }
    }

    function handleSeeOnMapFromList(locationId) {
        locationIdToFocusOnLoad = locationId;
        switchToView('map');
    }
    
    function handleDrawShapeForLocation(locationId, locationName) {
        locationIdToDrawFor = { id: locationId, name: locationName };
        switchToView('map');
    }

    // --- Sublocation and Herd Assignment Functions (RESTORED) ---
    function openAddSublocationModal(locationId, locationName) {
        currentParentLocationId = locationId;
        document.getElementById('parent-location-name').textContent = locationName;
        addSublocationForm.reset();
        addSublocationModal.classList.remove('hidden');
    }

    async function handleAddSublocationSubmit(event) {
        event.preventDefault();
        if (!currentParentLocationId) return;

        const payload = {
            name: document.getElementById('sublocation-name-input').value,
            area_hectares: document.getElementById('sublocation-area-input').value || null,
        };

        try {
            const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/location/${currentParentLocationId}/sublocations/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.name || result.error || 'Failed to save');

            showToast(getTranslation('subdivision_saved_successfully', { name: payload.name }), 'success');
            addSublocationModal.classList.add('hidden');
            loadLocationsData(); // Refresh the list
        } catch (error) {
            showToast(`${getTranslation('error_saving_subdivision')}: ${error.message}`, 'error');
        }
    }

    async function handleEditSublocationClick(sublocationId) {
        try {
            const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/sublocation/${sublocationId}/`);
            if (!response.ok) throw new Error('Could not fetch sublocation details.');
            const sublocation = await response.json();
            
            // Populate the modal
            document.getElementById('edit-sublocation-id').value = sublocation.id;
            document.getElementById('edit-sublocation-name-input').value = sublocation.name;
            document.getElementById('edit-sublocation-area-input').value = sublocation.area_hectares || '';
            
            editSublocationModal.classList.remove('hidden');
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
        }
    }

    async function handleEditSublocationSubmit(event) {
        event.preventDefault();
        const sublocationId = document.getElementById('edit-sublocation-id').value;
        if (!sublocationId) return;

        const payload = {
            name: document.getElementById('edit-sublocation-name-input').value,
            area_hectares: document.getElementById('edit-sublocation-area-input').value || null
        };

        try {
            const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/sublocation/${sublocationId}/`, {
                method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.name || result.error || 'Failed to update');

            showToast(getTranslation('subdivision_updated_successfully', { name: payload.name }), 'success');
            editSublocationModal.classList.add('hidden');
            loadLocationsData();
        } catch (error) {
            showToast(`${getTranslation('error_updating_subdivision')}: ${error.message}`, 'error');
        }
    }
    
    async function handleDeleteSublocationClick(sublocationId, sublocationName) {
        const confirmed = await showCustomConfirm(getTranslation('confirm_delete_subdivision', { name: sublocationName }));
        if (confirmed) {
            try {
                const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/sublocation/${sublocationId}/`, {
                    method: 'DELETE'
                });
                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    throw new Error(errorData.error || 'Unknown server error');
                }
                showToast(getTranslation('subdivision_deleted_successfully'), 'success');
                loadLocationsData();
            } catch (error) {
                showToast(`${getTranslation('error_deleting_subdivision')}: ${error.message}`, 'error');
            }
        }
    }
    
    async function handleBulkAssignClick(locationId, locationName, sublocationId, sublocationName) {
        const confirmed = await showCustomConfirm(
            getTranslation('confirm_bulk_assign', { parentName: locationName, subName: sublocationName })
        );
        if (!confirmed) return;

        const payload = {
            date: new Date().toISOString().split('T')[0], // Use today's date
            destination_sublocation_id: sublocationId,
        };

        try {
            const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/location/${locationId}/bulk_assign_sublocation/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || 'Failed to assign');
            
            showToast(result.message, 'success');
            loadLocationsData(); // Refresh the list to show new animal counts
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
        }
    }

    // --- Shape Editing Logic ---

    function createInfoWindowContent(feature) {
        const props = { 
            id: feature.getProperty('locationId'), 
            name: feature.getProperty('locationName'), 
            area: feature.getProperty('area'), 
            count: feature.getProperty('animalCount'),
            // --- Read the new properties from the feature ---
            grass: feature.getProperty('grassType'),
            capacity: feature.getProperty('capacityRateActual'),
            forecast: feature.getProperty('capacityRateForecast')

        };
        const contentDiv = document.createElement('div');
        contentDiv.className = 'map-infowindow-content';

        // --- Update the HTML to display the new data ---
        contentDiv.innerHTML = `
        <h4>${props.name}</h4>
        <p><b>${getTranslation('map_area')}:</b> ${props.area ? props.area.toFixed(2) : 'N/A'} ha</p>
        <p><b>${getTranslation('map_animals')}:</b> ${props.count}</p>
        <p><b>${getTranslation('map_grass_type')}:</b> ${props.grass || 'N/A'}</p>
        <p><b>${getTranslation('map_capacity_actual')}:</b> ${props.capacity != null ? props.capacity : 'N/A'}</p>
        <p><b>${getTranslation('map_capacity_forecast')}:</b> ${props.forecast != null ? props.forecast : 'N/A'}</p>
        <div class="map-infowindow-actions">
            <button class="button-secondary edit-shape-btn">${getTranslation('edit_shape')}</button>
        </div>
    `;
        const editButton = contentDiv.querySelector('.edit-shape-btn');
        if (editButton) { editButton.onclick = () => handleEditShapeClick(props.id); }
        return contentDiv;
    }

    function handleEditShapeClick(locationId) {
        try {
            infoWindow.close();
            cancelEditing();
            let featureFound = false;
            map.data.forEach(feature => {
                if (feature.getProperty('locationId') == locationId) {
                    featureFound = true;
                    currentlyEditingFeature = feature;
                    feature.toGeoJson(geoJson => { originalGeoJsonForCancel = geoJson; });

                    // Use the original stroke color for the editing highlight
                    const originalColor = feature.getProperty('strokeColor') || '#FFD700';

                    map.data.overrideStyle(feature, {
                        editable: true, clickable: false, fillColor: originalColor,
                        strokeColor: originalColor, zIndex: 99
                    });

                    // Temporarily hide the label for the shape being edited
                    const label = mapLabels.find(l => l.text.includes(feature.getProperty('locationName')));
                    if (label) label.setMap(null);

                    mapEditTitle.textContent = `Editing: ${feature.getProperty('locationName')}`;
                    mapEditBox.classList.remove('hidden');
                }
            });

            if (!featureFound) { console.error(`CRITICAL - No feature found with ID ${locationId}`); }
        } catch (error) { console.error("ERROR inside handleEditShapeClick:", error); }
    }

    async function handleSaveShapeClick() { // No longer needs locationId
        if (!currentlyEditingFeature) return;
        
        const locationId = currentlyEditingFeature.getProperty('locationId'); // Get ID from the feature

        try {
            const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/location/${locationId}/`);
            if (!response.ok) throw new Error('Could not fetch original location data.');
            const originalData = (await response.json()).location_details;

            currentlyEditingFeature.toGeoJson(async (geoJsonFeature) => {
                const geometry = currentlyEditingFeature.getGeometry();
                const path = geometry.getArray()[0].getArray();
                const newArea = google.maps.geometry.spherical.computeArea(path) / 10000;
                const payload = {
                    name: originalData.name, location_type: originalData.location_type,
                    grass_type: originalData.grass_type, area_hectares: newArea,
                    geo_json_data: JSON.stringify(geoJsonFeature)
                };
                const updateResponse = await fetch(`${API_URL}/api/farm/${selectedFarmId}/location/${locationId}/`, {
                    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
                });
                const result = await updateResponse.json();
                if (!updateResponse.ok) throw new Error(result.error || 'Failed to save shape');
                
                showToast(getTranslation('location_saved_successfully', { name: result.name }), 'success');
                cancelEditing(); // This will hide the panel and reset the shape
                loadLocationsData();
            });
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
            cancelEditing();
        }
    }

    function cancelEditing() {
        if (currentlyEditingFeature) {
            map.data.remove(currentlyEditingFeature);
            if (originalGeoJsonForCancel) {
                map.data.addGeoJson(originalGeoJsonForCancel);
            }
            // After canceling, we need to refresh all styles and labels
            loadLocationsData();
        }
        currentlyEditingFeature = null;
        originalGeoJsonForCancel = null;
        infoWindow.close();
        mapEditBox.classList.add('hidden');
    }

    // --- View Switching & Page Event Handlers ---
    const switchToView = (viewToShow) => {
        const contentContainer = document.querySelector('.locations-content-container');
        contentContainer.style.display = 'none';
        locationConsultView.classList.add('hidden');
        [showListViewBtn, showMapViewBtn, locationsListView, locationsMapView].forEach(el => el.classList.remove('active'));
        if (viewToShow === 'list') {
            contentContainer.style.display = 'flex';
            locationsListView.classList.add('active');
            showListViewBtn.classList.add('active');
            loadLocationsData();
        } else if (viewToShow === 'map') {
            contentContainer.style.display = 'flex';
            locationsMapView.classList.add('active');
            showMapViewBtn.classList.add('active');
            initializeMapView();
        } else if (viewToShow === 'consult') {
            locationConsultView.classList.remove('hidden');
        }
    };

    const showConsultView = async (locationId, locationName) => {
        switchToView('consult');
        consultTitle.textContent = `${getTranslation('location_occupancy')}: ${locationName}`;
        try {
            const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/location/${locationId}/`);
            if (!response.ok) throw new Error('Failed to fetch summary');
            const data = await response.json();
            renderLocationSummary(data.location_details, summaryContainer);
            createLocationAnimalsGrid(data.animals);
        } catch (error) {
            console.error("Error loading location summary:", error);
            summaryContainer.innerHTML = `<p style="color:red;">Could not load summary data.</p>`;
        }
    };

    async function handleEditLocationClick(locationId) {
        try {
            const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/location/${locationId}/`);
            if (!response.ok) throw new Error('Could not fetch location details.');
            const data = await response.json();
            const location = data.location_details;
            document.getElementById('edit-location-id').value = location.id;
            document.getElementById('edit-location-name-input').value = location.name;
            document.getElementById('edit-location-area-input').value = location.area_hectares || '';
            document.getElementById('edit-location-type-input').value = location.location_type || '';
            document.getElementById('edit-location-grass-input').value = location.grass_type || '';
            editLocationModal.classList.remove('hidden');
        } catch (error) { showToast(`Error: ${error.message}`, 'error'); }
    }

    async function handleDeleteLocationClick(locationId, locationName) {
        const confirmed = await showCustomConfirm(getTranslation('confirm_delete_location', { name: locationName }));
        if (confirmed) {
            try {
                const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/location/${locationId}/`, { method: 'DELETE' });
                if (!response.ok) throw new Error((await response.json().catch(() => ({}))).error || 'Unknown error');
                showToast(getTranslation('location_deleted_successfully'), 'success');
                loadLocationsData();
            } catch (error) { showToast(`${getTranslation('error_deleting_location')}: ${error.message}`, 'error'); }
        }
    }

    async function handleAddLocationSubmit(event) {
        event.preventDefault();
        const payload = {
            name: document.getElementById('location-name-input').value,
            area_hectares: document.getElementById('location-area-input').value,
            location_type: document.getElementById('location-type-input').value,
            grass_type: document.getElementById('location-grass-input').value,
            geo_json_data: tempGeoJson
        };
        try {
            const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/locations/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            const result = await response.json();
            if (!response.ok) throw new Error(result.name || result.error || 'Failed to save');
            showToast(getTranslation('location_saved_successfully', { name: payload.name }), 'success');
            addLocationModal.classList.add('hidden');
            tempGeoJson = null;
            loadLocationsData();
        } catch (error) { showToast(`${getTranslation('error_saving_location')}: ${error.message}`, 'error'); }
    }

    async function handleEditLocationSubmit(event) {
        event.preventDefault();
        const locationId = document.getElementById('edit-location-id').value;
        const payload = {
            name: document.getElementById('edit-location-name-input').value,
            area_hectares: document.getElementById('edit-location-area-input').value,
            location_type: document.getElementById('edit-location-type-input').value,
            grass_type: document.getElementById('edit-location-grass-input').value
        };
        try {
            const response = await fetch(`${API_URL}/api/farm/${selectedFarmId}/location/${locationId}/`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            const result = await response.json();
            if (!response.ok) throw new Error(result.name || result.error || 'Failed to update');
            showToast(getTranslation('location_updated_successfully', { name: payload.name }), 'success');
            editLocationModal.classList.add('hidden');
            loadLocationsData();
        } catch (error) { showToast(`${getTranslation('error_updating_location')}: ${error.message}`, 'error'); }
    }

    // This is the main entry point for the page
    function init() {
        console.log("Initializing Locations Page...");

        isMapInitialized = false;
        map = null;
        drawingManager = null;
        infoWindow = null;
        mapLabels = [];

         // --- Element References ---
        pageContainer = document.getElementById('farm-locations-page');
        locationsContainer = document.getElementById('locations-container');
        locationsListView = document.getElementById('locations-list-view');
        locationConsultView = document.getElementById('location-consult-view');
        locationsMapView = document.getElementById('locations-map-view');
        showListViewBtn = document.getElementById('show-list-view-btn');
        showMapViewBtn = document.getElementById('show-map-view-btn');
        showAddLocationModalBtn = document.getElementById('show-add-location-modal-btn');
        addLocationModal = document.getElementById('add-location-modal');
        addLocationForm = document.getElementById('add-location-form');
        cancelAddLocationBtn = document.getElementById('cancel-add-location');
        editLocationModal = document.getElementById('edit-location-modal');
        editLocationForm = document.getElementById('edit-location-form');
        cancelEditLocationBtn = document.getElementById('cancel-edit-location');
        addSublocationModal = document.getElementById('add-sublocation-modal');
        addSublocationForm = document.getElementById('add-sublocation-form');
        cancelAddSublocationBtn = document.getElementById('cancel-add-sublocation');
        backBtn = document.getElementById('back-to-locations-list-btn');
        editSublocationModal = document.getElementById('edit-sublocation-modal');
        editSublocationForm = document.getElementById('edit-sublocation-form');
        cancelEditSublocationBtn = document.getElementById('cancel-edit-sublocation');
        mapEditBox = document.getElementById('map-edit-box');
        mapEditTitle = document.getElementById('map-edit-title');
        mapSaveChangesBtn = document.getElementById('map-save-changes-btn');
        mapCancelEditBtn = document.getElementById('map-cancel-edit-btn');
        
        // --- INITIAL EVENT LISTENERS ---
        showListViewBtn.onclick = () => switchToView('list');
        showMapViewBtn.onclick = () => switchToView('map');
        showAddLocationModalBtn.onclick = () => { /* ... */ };
        cancelAddLocationBtn.onclick = () => addLocationModal.classList.add('hidden');
        addLocationForm.onsubmit = handleAddLocationSubmit;
        cancelEditLocationBtn.onclick = () => editLocationModal.classList.add('hidden');
        editLocationForm.onsubmit = handleEditLocationSubmit;
        
        // Listeners for sublocation modals
        cancelAddSublocationBtn.onclick = () => addSublocationModal.classList.add('hidden');
        addSublocationForm.onsubmit = handleAddSublocationSubmit;
        cancelEditSublocationBtn.onclick = () => editSublocationModal.classList.add('hidden');
        editSublocationForm.onsubmit = handleEditSublocationSubmit;

        // Listeners for fixed map panel
        mapSaveChangesBtn.onclick = handleSaveShapeClick;
        mapCancelEditBtn.onclick = cancelEditing;

        // --- DELEGATED EVENT LISTENER 
        document.body.addEventListener('click', function(event) {
            if (!pageContainer.contains(event.target)) return;

            const editLocationBtn = event.target.closest('.edit-location-btn');
            const deleteLocationBtn = event.target.closest('.delete-location-btn');

            const seeDetailsBtn = event.target.closest('.see-details-btn');
            const addSubdivisionBtn = event.target.closest('.add-subdivision-btn');
            const editSublocationBtn = event.target.closest('.edit-sublocation-btn');
            const deleteSublocationBtn = event.target.closest('.delete-sublocation-btn');
            const assignHerdBtn = event.target.closest('.assign-herd-btn');

            const editShapeOnMapBtn = event.target.closest('.edit-shape-on-map-btn');
            const drawOnMapBtn = event.target.closest('.draw-on-map-btn');
            const seeOnMapBtn = event.target.closest('.see-on-map-btn');

            if (editLocationBtn) handleTopLevelEditClick(editLocationBtn.dataset.locationId);
            if (deleteLocationBtn) handleDeleteLocationClick(deleteLocationBtn.dataset.locationId, deleteLocationBtn.dataset.locationName);
            if (seeDetailsBtn) showConsultView(seeDetailsBtn.dataset.locationId, seeDetailsBtn.dataset.locationName);
            if (addSubdivisionBtn) openAddSublocationModal(addSubdivisionBtn.dataset.locationId, addSubdivisionBtn.dataset.locationName);
            if (editSublocationBtn) handleEditSublocationClick(editSublocationBtn.dataset.sublocationId);
            if (deleteSublocationBtn) handleDeleteSublocationClick(deleteSublocationBtn.dataset.sublocationId, deleteSublocationBtn.dataset.sublocationName);
            if (assignHerdBtn) handleBulkAssignClick(assignHerdBtn.dataset.locationId, assignHerdBtn.dataset.locationName, assignHerdBtn.dataset.sublocationId, assignHerdBtn.dataset.sublocationName);

            if (seeOnMapBtn) handleSeeOnMapFromList(seeOnMapBtn.dataset.locationId);
            if (drawOnMapBtn) handleDrawShapeForLocation(drawOnMapBtn.dataset.locationId, drawOnMapBtn.dataset.locationName);
        });

        if (window.locationToConsult) {
            const { id, name } = window.locationToConsult;
            window.locationToConsult = null;
            showConsultView(id, name);
        } else {
            switchToView('list');
        }
    }


    return {
        init: init,
        loadData: loadLocationsData
    };
})();