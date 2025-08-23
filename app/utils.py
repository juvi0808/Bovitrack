from . import db
from .models import Purchase, Sale, Death
from datetime import datetime, date # Import the date object
import os
import csv
import bisect

def find_active_animal_by_eartag(farm_id, eartag):
    """
    Finds active animals by ear tag for a especific farm, optionally for a specific reference date.
    - If reference_date_str is provided (e.g., "2024-01-15"), it finds animals
      that were purchased on or before that date, and had not yet been sold
      on or before that date.
    - If reference_date_str is None, it calculates for the current active stock.
    """

    query = Purchase.query.outerjoin(Sale, Purchase.id == Sale.animal_id) \
                          .outerjoin(Death, Purchase.id == Death.animal_id) \
                          .filter(
                              Purchase.farm_id == farm_id,
                              Purchase.ear_tag == eartag,
                              Sale.id == None,
                              Death.id == None
                          )
    
    return query.all()


def calculate_weight_history_with_gmd(animal):
    """
    Takes a Purchase object and returns its weight history, enriched
    with GMD calculations for each entry.
    arg: animal is a Purchase object (row in the purchases table) with related Weighting objects.
    """
    # 1. Standardize all weight events into a list of dictionaries
    #    where the 'date' is GUARANTEED to be a datetime.date object.
    
    all_weight_events = []

    # Add the entry weight, which already has a date object
    all_weight_events.append({
        'date': animal.entry_date,
        'weight_kg': animal.entry_weight
    })

    # Add the historical weights, converting their date strings back to objects
    for w in animal.weightings:
        all_weight_events.append({
            'date': w.date, # The .date attribute is a date object
            'weight_kg': w.weight_kg
        })

    # 2. Remove duplicates and sort chronologically. This is now safe.
    #    This handles cases where the entry weight might be in both lists.
    unique_events = [dict(t) for t in {tuple(d.items()) for d in all_weight_events}]
    sorted_events = sorted(unique_events, key=lambda w: w['date'])

    # 4. Loop through the sorted events to calculate the GMDs.
    enriched_history = []
    if not sorted_events:
        return []

    # The first event is our baseline.
    first_event = sorted_events[0]

    for i, current_event in enumerate(sorted_events):
        # Convert date strings back to date objects for calculations
        current_date = current_event['date']
        first_date = first_event['date']

        # --- GMD Accumulated (since the beginning) ---
        days_since_start = (current_date - first_date).days
        gain_since_start = current_event['weight_kg'] - first_event['weight_kg']
        gmd_accumulated = (gain_since_start / days_since_start) if days_since_start > 0 else 0

        # --- GMD Between Weightings (period GMD) ---
        gmd_period = 0
        if i > 0: # Can only calculate if there's a previous event
            previous_event = sorted_events[i-1]
            previous_date = previous_event['date']

            days_between = (current_date - previous_date).days
            gain_between = current_event['weight_kg'] - previous_event['weight_kg']
            gmd_period = (gain_between / days_between) if days_between > 0 else 0

        enriched_history.append({
            'date': current_date.isoformat(),
            'weight_kg': round(current_event['weight_kg'], 2),
            'gmd_accumulated_grams': round(gmd_accumulated, 3),
            'gmd_period_grams': round(gmd_period, 3)
        })

    return enriched_history

def calculate_location_kpis(locations, active_animals):
    """
    Calculates capacity rate KPIs for a list of locations.
    Takes a list of Location objects and a list of active Purchase objects.
    Returns a list of location dictionaries, enriched with KPIs.
    """
    # Create a dictionary to easily find an animal's most recent location
    animal_locations = {}
    animal_sublocations = {}
    for animal in active_animals:
        if animal.location_changes:
            # Sort changes by date to find the most recent one
            latest_change = sorted(animal.location_changes, key=lambda lc: lc.date, reverse=True)[0]
            animal_locations[animal.id] = latest_change.location_id
            animal_sublocations[animal.id] = latest_change.sublocation_id

    # Count animals per sublocation
    sublocation_counts = {}
    for sub_id in animal_sublocations.values():
        if sub_id: # Only count if they are in a sublocation
            sublocation_counts[sub_id] = sublocation_counts.get(sub_id, 0) + 1
    
    # Create a dictionary to group animals by their current location_id
    location_occupants = {loc.id: [] for loc in locations}
    for animal_id, location_id in animal_locations.items():
        if location_id in location_occupants:
            location_occupants[location_id].append(animal_id)

    # Now, calculate KPIs for each location
    location_results = []
    ANIMAL_UNIT_WEIGHT_KG = 450.0

    for location in locations:
        occupant_ids = location_occupants.get(location.id, [])
        location_animals = [animal for animal in active_animals if animal.id in occupant_ids]

        location_dict = location.to_dict()

        for sub_dict in location_dict.get('sublocations', []):
            sub_id = sub_dict['id']
            sub_dict['animal_count'] = sublocation_counts.get(sub_id, 0)
        
        if location.area_hectares and location.area_hectares > 0:
            # Calculate total weights for animals in this location
            total_last_actual_weight = sum(animal.calculate_kpis()['last_weight_kg'] for animal in location_animals)
            total_forecasted_weight = sum(animal.calculate_kpis()['forecasted_current_weight_kg'] for animal in location_animals)

            # Calculate Animal Units (UA)
            ua_actual = total_last_actual_weight / ANIMAL_UNIT_WEIGHT_KG
            ua_forecasted = total_forecasted_weight / ANIMAL_UNIT_WEIGHT_KG

            # Calculate Capacity Rate (UA/ha)
            capacity_rate_actual = ua_actual / location.area_hectares
            capacity_rate_forecasted = ua_forecasted / location.area_hectares
            
            location_dict['kpis'] = {
                'animal_count': len(location_animals),
                'capacity_rate_actual_ua_ha': round(capacity_rate_actual, 2),
                'capacity_rate_forecasted_ua_ha': round(capacity_rate_forecasted, 2)
            }
        else:
            # If location has no area, KPIs are not applicable
            location_dict['kpis'] = {
                'animal_count': len(location_animals),
                'capacity_rate_actual_ua_ha': None,
                'capacity_rate_forecasted_ua_ha': None
            }
        
        location_results.append(location_dict)

        # --- THIS IS THE NEW DEBUGGING LINE ---
    # It will print the exact data structure to your Python terminal.
    print("--- DEBUG: Data being sent to jsonify from calculate_location_kpis ---")
    print(location_results)
    print("--------------------------------------------------------------------")

    return location_results

# A simple in-memory cache to avoid reading the file on every request
_historical_prices_cache = None
_sorted_dates_cache = None

def load_historical_prices():
    """
    Loads and caches historical price data from the app/data/historical_prices.csv file.
    This version is highly resilient and correctly handles rows with partial data.
    """
    global _historical_prices_cache, _sorted_dates_cache
    if _historical_prices_cache is not None:
        return _historical_prices_cache, _sorted_dates_cache

    prices = {}
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, 'data', 'historical_prices.csv')

    try:
        with open(file_path, mode='r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            headers = [h.lower() for h in reader.fieldnames or []]
            
            # Find the actual names of the columns, case-insensitively
            date_header = next((h for h in headers if 'date' in h), None)
            purchase_header = next((h for h in headers if 'purchase' in h), None)
            sale_header = next((h for h in headers if 'sale' in h), None)

            if not all([date_header, purchase_header, sale_header]):
                print("CRITICAL WARNING: The CSV file is missing one of the required headers: 'date', 'purchase_price', 'sale_price'.")
                _historical_prices_cache, _sorted_dates_cache = {}, []
                return {}, []

            for row_num, row in enumerate(reader, 1):
                date_str = row.get(date_header)
                purchase_str = row.get(purchase_header)
                sale_str = row.get(sale_header)

                if not date_str:
                    print(f"Warning: Skipping row {row_num} due to missing date.")
                    continue

                purchase_val = None
                sale_val = None
                
                try:
                    # Attempt to convert both values if they exist
                    if purchase_str and purchase_str.strip():
                        purchase_val = float(purchase_str)
                    if sale_str and sale_str.strip():
                        sale_val = float(sale_str)

                    # Now, decide what to do based on what we found
                    if purchase_val is not None and sale_val is not None:
                        # Scenario A: Both exist. Use them.
                        prices[date_str] = {'purchase': purchase_val, 'sale': sale_val}
                    elif sale_val is not None:
                        # Scenario B: Only sale price exists. Calculate purchase price.
                        prices[date_str] = {'purchase': sale_val, 'sale': sale_val}
                    elif purchase_val is not None:
                        # Scenario C: Only purchase price exists. Calculate sale price.
                        prices[date_str] = {'purchase': purchase_val, 'sale': purchase_val}
                    else:
                        # Scenario D: Neither exists. Skip the row.
                        print(f"Warning: Skipping row {row_num} for date {date_str} due to missing price values.")
                        continue

                except (ValueError, TypeError):
                    print(f"Warning: Skipping row {row_num} for date {date_str} due to invalid number format.")
                    continue
        
        _historical_prices_cache = prices
        _sorted_dates_cache = sorted(prices.keys())
        
        if not prices:
             print("CRITICAL WARNING: The historical price file was loaded, but NO valid price records were found. Check CSV for data issues.")
        else:
            print(f"Successfully loaded and cached {len(prices)} historical price records.")
        
        return _historical_prices_cache, _sorted_dates_cache
        
    except FileNotFoundError:
        print(f"WARNING: Historical price file not found at {file_path}. Market prices will not be available.")
        _historical_prices_cache, _sorted_dates_cache = {}, []
        return {}, []
    except Exception as e:
        print(f"ERROR: Failed to load historical prices: {e}")
        _historical_prices_cache, _sorted_dates_cache = {}, []
        return {}, []

def get_closest_price(target_date, price_data, sorted_dates):
    """
    Finds the price data for the date closest to the target_date.
    Uses binary search for efficiency.
    
    Args:
        target_date (datetime.date): The date to find the closest match for.
        price_data (dict): The dictionary of prices from load_historical_prices.
        sorted_dates (list): The sorted list of date strings.

    Returns:
        dict: The price dictionary for the closest date.
    """
    if not sorted_dates:
        return None # No data to search in

    target_date_str = target_date.isoformat()
    
    # bisect_left finds the insertion point, which helps us find the neighbors
    pos = bisect.bisect_left(sorted_dates, target_date_str)

    # --- Handle edge cases ---
    if pos == 0:
        # Target date is before the first recorded date
        return price_data[sorted_dates[0]]
    if pos == len(sorted_dates):
        # Target date is after the last recorded date
        return price_data[sorted_dates[-1]]

    # --- Find the two nearest neighbors ---
    date_before_str = sorted_dates[pos - 1]
    date_after_str = sorted_dates[pos]

    date_before = datetime.strptime(date_before_str, '%Y-%m-%d').date()
    date_after = datetime.strptime(date_after_str, '%Y-%m-%d').date()

    # --- Compare which neighbor is closer ---
    if (target_date - date_before) < (date_after - target_date):
        return price_data[date_before_str]
    else:
        return price_data[date_after_str]