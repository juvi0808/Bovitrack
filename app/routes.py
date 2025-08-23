from flask import Blueprint, request, jsonify, Response, send_file
from datetime import date, datetime, timedelta
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased
from sqlalchemy import func, case, delete
from .models import Farm, Location, Purchase, Sale, Weighting, SanitaryProtocol, LocationChange, DietLog, Death, Sublocation # Notice the '.' - it means "from the same package"
from . import db # Also import the db object
from .utils import find_active_animal_by_eartag, calculate_weight_history_with_gmd, calculate_location_kpis, load_historical_prices, get_closest_price
import json
import random
import io


# Create a Blueprint. 'api' is the name of the blueprint.
api = Blueprint('api', __name__)

# --- General Routes ---

@api.route('/')
def home():
    """A simple test route to confirm the API is running."""
    return "The Livestock Manager Backend is running!"

# --- Create (POST) Routes ---

@api.route('/farm/add', methods=['POST'])
def add_farm():
    """Creates a new farm. Expects JSON with a 'name' field."""
    data = request.get_json()
    if not data or 'name' not in data or not data['name'].strip():
        return jsonify({'error': "The 'name' field is required."}), 400

    farm_name = data['name'].strip()

    # Check if a farm with this name already exists
    if Farm.query.filter_by(name=farm_name).first():
        return jsonify({'error': f"A farm with the name '{farm_name}' already exists."}), 409 # Conflict

    try:
        new_farm = Farm(name=farm_name)
        db.session.add(new_farm)
        db.session.commit()
        return jsonify({
            'message': 'Farm created successfully!',
            'farm': new_farm.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

@api.route('/farm/<int:farm_id>/rename', methods=['POST'])
def rename_farm(farm_id):
    """Renames an existing farm."""
    farm = Farm.query.get_or_404(farm_id)
    data = request.get_json()
    
    if not data or 'name' not in data or not data['name'].strip():
        return jsonify({'error': "The 'name' field is required."}), 400

    new_name = data['name'].strip()

    # Check if another farm with this name already exists
    existing_farm = Farm.query.filter(Farm.name == new_name, Farm.id != farm_id).first()
    if existing_farm:
        return jsonify({'error': f"A farm with the name '{new_name}' already exists."}), 409

    try:
        farm.name = new_name
        db.session.commit()
        return jsonify({'message': 'Farm renamed successfully!', 'farm': farm.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

@api.route('/farm/<int:farm_id>/delete', methods=['DELETE'])
def delete_farm(farm_id):
    """Deletes a farm and all its associated data (animals, sales, etc.)."""
    farm = Farm.query.get_or_404(farm_id)
    try:
        # Thanks to 'cascade="all, delete-orphan"' in models.py,
        # deleting the farm will automatically delete all its children records.
        db.session.delete(farm)
        db.session.commit()
        return jsonify({'message': f"Farm '{farm.name}' and all its data have been deleted."})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

@api.route('/farm/<int:farm_id>/location/add', methods=['POST'])
def add_location(farm_id):
    """
    Creates a new, named location (e.g., a pasture or module) for a specific farm.
    Expects a JSON body with a 'name' and an optional 'area_hectares', 'grass type' and geojson.
    """
    # Verify the farm exists before proceeding.
    Farm.query.get_or_404(farm_id)
    data = request.get_json()

    # Validate that the required 'name' field is present.
    if not data or 'name' not in data:
        return jsonify({'error': "Missing required field: 'name'"}), 400

    location_name = data.get('name')
    area = data.get('area_hectares') # This will be None if not provided
    grass_type = data.get('grass_type') # Optional field
    location_type = data.get('location_type') # Optional field  


    # --- Business Logic: Check for duplicate location names on this farm ---
    existing_location = Location.query.filter_by(farm_id=farm_id, name=location_name).first()
    if existing_location:
        return jsonify({'error': f"A location with the name '{location_name}' already exists on this farm."}), 409 # 409 is "Conflict"

    try:
        # Create the new Location object.
        new_location = Location(
            name=location_name,
            area_hectares=area,
            grass_type=grass_type,
            location_type=location_type,
            geo_json_data=data.get('geo_json_data'),
            farm_id=farm_id
        )

        # Add and commit the new record to the database.
        db.session.add(new_location)
        db.session.commit()

        return jsonify({
            'message': 'Location created successfully!',
            'location': new_location.to_dict() # Return the full new object
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500
    
@api.route('/farm/<int:farm_id>/location/<int:location_id>/sublocation/add', methods=['POST'])
def add_sublocation(farm_id, location_id):
    """Creates a new sublocation (paddock) and attaches it to a parent location."""
    parent_location = Location.query.filter_by(id=location_id, farm_id=farm_id).first_or_404()
    
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'error': "Missing required field: 'name'"}), 400

    sub_name = data.get('name')
    
    # 2. Business Logic: Check for duplicate sublocation names WITHIN the same parent
    existing_sub = Sublocation.query.filter_by(location_id=location_id, name=sub_name).first()
    if existing_sub:
        return jsonify({'error': f"A sublocation named '{sub_name}' already exists in '{parent_location.name}'."}), 409

    try:
        new_sublocation = Sublocation( # 3. Create the new Sublocation object.
            name=sub_name,
            area_hectares=data.get('area_hectares'), # --- THE FIX ---
            geo_json_data=data.get('geo_json_data'),
            location_id=location_id, # Link to the parent
            farm_id=farm_id # Link to the farm
        )
        db.session.add(new_sublocation)
        db.session.commit()
        
        return jsonify({
            'message': 'Sublocation created successfully!',
            'sublocation': new_sublocation.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

@api.route('/farm/<int:farm_id>/sublocation/bulk_move', methods=['POST'])
def bulk_move_herd(farm_id):
    """Moves all active animals from a source sublocation to a destination sublocation."""
    data = request.get_json()
    required_fields = ['date', 'source_sublocation_id', 'destination_sublocation_id']
    if not data or not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields: date, source_sublocation_id, destination_sublocation_id'}), 400

    try:
        source_id = int(data['source_sublocation_id'])
        dest_id = int(data['destination_sublocation_id'])
        move_date = datetime.strptime(data['date'], '%Y-%m-%d').date()

        source_sub = Sublocation.query.get_or_404(source_id)
        dest_sub = Sublocation.query.get_or_404(dest_id)
        
        if not (source_sub.farm_id == farm_id and dest_sub.farm_id == farm_id):
            return jsonify({'error': 'Sublocations do not belong to the specified farm.'}), 403
        
        if source_sub.location_id != dest_sub.location_id:
            return jsonify({'error': 'Source and destination sublocations must be in the same parent location.'}), 400
            
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid sublocation ID format.'}), 400

    sold_animal_ids = db.session.query(Sale.animal_id).filter(Sale.farm_id == farm_id)
    dead_animal_ids = db.session.query(Death.animal_id).filter(Death.farm_id == farm_id)
    exited_animal_ids = sold_animal_ids.union(dead_animal_ids)
    
    # Create a subquery with the latest location change date for each anima_id
    lc_alias = aliased(LocationChange)
    most_recent_changes_subquery = db.session.query(
        func.max(lc_alias.date).label('max_date'),
        lc_alias.animal_id
    ).group_by(lc_alias.animal_id).subquery()
    
    animals_to_move = db.session.query(Purchase).join(
        LocationChange, Purchase.id == LocationChange.animal_id
    ).join(
        most_recent_changes_subquery,
        (LocationChange.animal_id == most_recent_changes_subquery.c.animal_id) &
        (LocationChange.date == most_recent_changes_subquery.c.max_date)
    ).filter(
        Purchase.farm_id == farm_id,
        Purchase.id.notin_(exited_animal_ids),
        LocationChange.sublocation_id == source_id
    ).all()
    
    if not animals_to_move:
        return jsonify({'message': 'No active animals found in the source sublocation to move.'}), 200

    try:
        for animal in animals_to_move:
            new_change = LocationChange(
                date=move_date,
                animal_id=animal.id,
                location_id=dest_sub.location_id,
                sublocation_id=dest_id,
                farm_id=farm_id
            )
            db.session.add(new_change)
        
        db.session.commit()
        return jsonify({'message': f'Successfully moved {len(animals_to_move)} animals.'}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An unexpected error occurred during the move: {str(e)}'}), 500

@api.route('/farm/<int:farm_id>/location/<int:location_id>/bulk_assign_sublocation', methods=['POST'])
def bulk_assign_sublocation(farm_id, location_id):
    """
    Finds all active animals in a parent location that are not yet in a sublocation,
    and assigns them all to a specified destination sublocation.
    """
    data = request.get_json()
    if not data or 'date' not in data or 'destination_sublocation_id' not in data:
        return jsonify({'error': 'Missing required fields: date, destination_sublocation_id'}), 400

    # 1. --- Data Validation and Security ---
    try:
        dest_id = int(data['destination_sublocation_id'])
        move_date = datetime.strptime(data['date'], '%Y-%m-%d').date()

        # Verify the parent location and destination sublocation are valid and linked
        parent_location = Location.query.filter_by(id=location_id, farm_id=farm_id).first_or_404()
        dest_sub = Sublocation.query.get_or_404(dest_id)
        if dest_sub.location_id != parent_location.id:
            return jsonify({'error': 'Destination sublocation does not belong to the specified parent location.'}), 400

    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid ID format.'}), 400

    # 2. --- Find the Animals to Assign (The Engine) ---
    sold_animal_ids = db.session.query(Sale.animal_id).filter(Sale.farm_id == farm_id)
    dead_animal_ids = db.session.query(Death.animal_id).filter(Death.farm_id == farm_id)
    exited_animal_ids = sold_animal_ids.union(dead_animal_ids)
    
    lc_alias = aliased(LocationChange)
    most_recent_changes_subquery = db.session.query(
        func.max(lc_alias.date).label('max_date'),
        lc_alias.animal_id
    ).group_by(lc_alias.animal_id).subquery()
    
    # THE CRITICAL DIFFERENCE: Find animals whose latest move was to the PARENT location
    # AND their sublocation_id IS NULL.
    animals_to_assign = db.session.query(Purchase).join(
        LocationChange, Purchase.id == LocationChange.animal_id
    ).join(
        most_recent_changes_subquery,
        (LocationChange.animal_id == most_recent_changes_subquery.c.animal_id) &
        (LocationChange.date == most_recent_changes_subquery.c.max_date)
    ).filter(
        Purchase.farm_id == farm_id,
        Purchase.id.notin_(exited_animal_ids),
        LocationChange.location_id == location_id,       # Must be in the parent location
    ).all()
    
    if not animals_to_assign:
        return jsonify({'message': 'No unassigned animals found in this location.'}), 200

    # 3. --- Create New LocationChange Records ---
    try:
        for animal in animals_to_assign:
            new_change = LocationChange(
                date=move_date,
                animal_id=animal.id,
                location_id=location_id,
                sublocation_id=dest_id, # Assign to the destination
                farm_id=farm_id
            )
            db.session.add(new_change)
        
        db.session.commit()
        return jsonify({'message': f'Successfully assigned {len(animals_to_assign)} animals to {dest_sub.name}.'}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An unexpected error occurred during assignment: {str(e)}'}), 500

@api.route('/farm/<int:farm_id>/purchase/add', methods=['POST'])
def add_purchase(farm_id):
    """
    Adds a new animal purchase to a specific farm.
    This creates THREE linked records: the Purchase itself, the initial
    Weighting, and the initial LocationChange.
    Expects a JSON body with purchase details including the initial 'location_id'.
    """
    # Verify the farm exists.
    Farm.query.get_or_404(farm_id)
    data = request.get_json()

    # Add 'location_id' to the list of required fields.
    required_fields = ['entry_date', 'ear_tag', 'lot', 'entry_weight', 'sex', 'entry_age', 'location_id']
    if not data or not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    # --- Validate the provided location_id ---
    location_id = data.get('location_id')
    location = Location.query.filter_by(id=location_id, farm_id=farm_id).first()
    if not location:
        return jsonify({'error': f"Location with id {location_id} not found on this farm."}), 404

    initial_diet_type = data.get('diet_type')
    protocols_to_add = data.get('sanitary_protocols', [])
    
    try:
        # Process incoming data.
        entry_date_obj = datetime.strptime(data['entry_date'], '%Y-%m-%d').date()
        entry_weight_val = float(data['entry_weight'])
        price_str = data.get('purchase_price')
        final_price = float(price_str) if price_str else None
        intake_str = data.get('daily_intake_percentage')
        final_intake = float(intake_str) if intake_str else None

        # 1. Create the main Purchase record.
        new_purchase = Purchase(
            entry_date=entry_date_obj,
            ear_tag=str(data['ear_tag']),
            lot=str(data['lot']),
            entry_weight=entry_weight_val,
            sex=data['sex'],
            entry_age=float(data['entry_age']),
            purchase_price=final_price,
            race=data.get('race'),
            farm_id=farm_id
        )
        db.session.add(new_purchase)
        db.session.flush() # Flush to get the ID for the new purchase.

        # 2. Create the corresponding initial Weighting record.
        initial_weighting = Weighting(
            date=entry_date_obj,
            weight_kg=entry_weight_val,
            animal_id=new_purchase.id,
            farm_id=farm_id
        )
        db.session.add(initial_weighting)
        
        # 3. Create the initial LocationChange record.
        initial_location = LocationChange(
            date=entry_date_obj,
            location_id=location_id, # Use the validated location ID
            animal_id=new_purchase.id,
            farm_id=farm_id
        )
        db.session.add(initial_location)
        
        # 4. --- NEW: Loop through and create the SanitaryProtocol records ---
        for protocol_data in protocols_to_add:
            protocol_date = datetime.strptime(protocol_data['date'], '%Y-%m-%d').date()
            new_protocol = SanitaryProtocol(
                date=protocol_date,
                protocol_type=protocol_data.get('protocol_type'),
                product_name=protocol_data.get('product_name'),
                dosage=protocol_data.get('dosage'), # Safely get dosage
                invoice_number=protocol_data.get('invoice_number'),
                animal_id=new_purchase.id, # Link to the animal we just created
                farm_id=farm_id
            )
            db.session.add(new_protocol)

        if initial_diet_type and initial_diet_type.strip():
            new_diet_log = DietLog(
                date=entry_date_obj,
                diet_type=initial_diet_type.strip(),
                daily_intake_percentage=final_intake,
                animal_id=new_purchase.id, # Link to the animal we just created
                farm_id=farm_id
            )
            db.session.add(new_diet_log)

        # Commit all three new records to the database.
        db.session.commit()

        return jsonify({
            'message': 'Purchase, initial weight, and initial location created successfully!',
            'id': new_purchase.id
        }), 201

    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'This animal (ear_tag and lot combination) already exists.'}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

@api.route('/farm/<int:farm_id>/purchase/<int:purchase_id>/weighting/add', methods=['POST'])
def add_weighting(farm_id, purchase_id):
    """
    Adds a new weight record to a specific, existing animal.
    Identifies the animal via its unique purchase_id from the URL.
    Expects a JSON body with date and weight_kg.
    """
    # Find the animal and verify it belongs to the specified farm.
    animal = Purchase.query.get_or_404(purchase_id)
    if animal.farm_id != farm_id:
        return jsonify({'error': 'This animal does not belong to the specified farm.'}), 403

    data = request.get_json()
    # Validate required fields from the request body.
    required_fields = ['date', 'weight_kg']
    if not data or not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields: date and weight_kg'}), 400

    try:
        # Create the new Weighting object.
        weighting_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        new_weighting = Weighting(
            date=weighting_date,
            weight_kg=float(data['weight_kg']),
            animal_id=purchase_id,
            farm_id=farm_id
        )

        # Add and commit the new record to the database.
        db.session.add(new_weighting)
        db.session.commit()

        return jsonify({'message': 'Weighting recorded successfully!', 'id': new_weighting.id}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

@api.route('/farm/<int:farm_id>/purchase/<int:purchase_id>/sale/add', methods=['POST'])
def add_sale(farm_id, purchase_id):
    """
    Adds a new sale record for a specific animal.
    This also creates a final weighting record for the animal.
    Expects a JSON body with date, sale_price, and exit_weight.
    """
    # Find the animal and verify it belongs to the specified farm.
    animal = Purchase.query.get_or_404(purchase_id)
    if animal.farm_id != farm_id:
        return jsonify({'error': 'This animal does not belong to the specified farm.'}), 403

    data = request.get_json()
    # Validate required fields from the request body.
    required_fields = ['date', 'sale_price', 'exit_weight']
    if not data or not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields: date, sale_price, and exit_weight'}), 400

    try:
        # Process and validate incoming data.
        sale_date_obj = datetime.strptime(data['date'], '%Y-%m-%d').date()
        sale_price_val = float(data['sale_price'])
        exit_weight_val = float(data['exit_weight'])

        # Create the final Weighting record for the animal's history.
        final_weighting = Weighting(
            date=sale_date_obj,
            weight_kg=exit_weight_val,
            animal_id=purchase_id,
            farm_id=farm_id
        )
        db.session.add(final_weighting)

        # Create the Sale record itself.
        new_sale = Sale(
            date=sale_date_obj,
            sale_price=sale_price_val,
            animal_id=purchase_id,
            farm_id=farm_id
        )
        db.session.add(new_sale)

        # Commit both new records to the database in one transaction.
        db.session.commit()

        return jsonify({
            'message': 'Sale and final weight recorded successfully!',
            'sale_id': new_sale.id,
            'weighting_id': final_weighting.id
        }), 201

    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'This animal has already been sold.'}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

@api.route('/farm/<int:farm_id>/purchase/<int:purchase_id>/sanitary/add_batch', methods=['POST'])
def add_sanitary_protocols_batch(farm_id, purchase_id):
    """
    Adds a batch of new sanitary protocol records to a specific animal.
    Expects a JSON body with a 'protocols' key, which is a list of protocol objects.
    """
    # Find the animal and verify it belongs to the specified farm.
    animal = Purchase.query.get_or_404(purchase_id)
    if animal.farm_id != farm_id:
        return jsonify({'error': 'This animal does not belong to the specified farm.'}), 403

    data = request.get_json()
    protocols_to_add = data.get('protocols')
    optional_weight = data.get('weight_kg') # Get the optional weight

    # Validate that we received a list.
    if not isinstance(protocols_to_add, list):
        return jsonify({'error': "Request body must contain a 'protocols' list."}), 400

    try:
        # We need a consistent date for both the protocols and the optional weighting
        # We'll take it from the first protocol in the batch.
        if not protocols_to_add:
             return jsonify({'error': "Protocols list cannot be empty."}), 400
        
        reference_date_str = protocols_to_add[0]['date']
        event_date_obj = datetime.strptime(reference_date_str, '%Y-%m-%d').date()

        # 1. Check if an optional weight was provided.
        if optional_weight and float(optional_weight) > 0:
            new_weighting = Weighting(
                date=event_date_obj,
                weight_kg=float(optional_weight),
                animal_id=purchase_id,
                farm_id=farm_id
            )
            db.session.add(new_weighting)
            message = f'{len(protocols_to_add)} protocols and a new weight recorded successfully!'
        else:
            message = f'{len(protocols_to_add)} protocols recorded successfully!'

        # 2. Loop through and add all the protocols
        for protocol_data in protocols_to_add:
            protocol_date = datetime.strptime(protocol_data['date'], '%Y-%m-%d').date()
            
            new_protocol = SanitaryProtocol(
                date=protocol_date,
                protocol_type=protocol_data.get('protocol_type'),
                product_name=protocol_data.get('product_name'),
                dosage=protocol_data.get('dosage'),
                invoice_number=protocol_data.get('invoice_number'),
                animal_id=purchase_id,
                farm_id=farm_id
            )
            db.session.add(new_protocol)


        # Commit the transaction once, after all protocols have been added.
        # This ensures all are saved, or none are.
        db.session.commit()

        return jsonify({
            'message': f'{len(protocols_to_add)} protocols recorded successfully!',
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

@api.route('/farm/<int:farm_id>/purchase/<int:purchase_id>/location/add', methods=['POST'])
def add_location_change(farm_id, purchase_id):
    """
    Adds a new location change record to a specific animal, with optional sublocation support.
    This now expects a JSON body with a 'date' and the unique 'location_id'
    of the new location.
    """
    # Find the animal and perform security check to ensure it belongs to the correct farm.
    animal = Purchase.query.get_or_404(purchase_id)
    if animal.farm_id != farm_id:
        return jsonify({'error': 'This animal does not belong to the specified farm.'}), 403

    # Get the data from the request body.
    data = request.get_json()

    # Validate that the required fields are present.
    if not data or 'date' not in data or 'location_id' not in data:
        return jsonify({'error': 'Missing required fields: date and location_id'}), 400
    
    # --- Verify that the provided location_id is valid for this farm ---
    location_id = data.get('location_id')
    sublocation_id = data.get('sublocation_id') # Get the optional sublocation
    location = Location.query.filter_by(id=location_id, farm_id=farm_id).first_or_404()

    # Get the optional weight from the data
    optional_weight = data.get('weight_kg')

    try:
        # Process incoming data.
        change_date_obj = datetime.strptime(data['date'], '%Y-%m-%d').date()

        # 1. Create the new LocationChange object.
        new_location_change = LocationChange(
            date=change_date_obj, 
            location_id=location.id, 
            sublocation_id=sublocation_id,
            animal_id=purchase_id, 
            farm_id=farm_id
            )
        
        db.session.add(new_location_change)

        message = 'Location change recorded successfully!'
        # 2. Check if an optional weight was provided.
        optional_weight = data.get('weight_kg')
        if optional_weight and float(optional_weight) > 0:
            new_weighting = Weighting(
                date=change_date_obj,
                weight_kg=float(optional_weight),
                animal_id=purchase_id,
                farm_id=farm_id
            )
            db.session.add(new_weighting)
            message = 'Location change and weighting recorded successfully!'

        db.session.commit()

        return jsonify({
            'message': message,
            'location_change_id': location.id
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500
    
@api.route('/farm/<int:farm_id>/purchase/<int:purchase_id>/diet/add', methods=['POST'])
def add_diet_log(farm_id, purchase_id):
    """
    Adds a new diet log record to a specific animal.
    Expects a JSON body with a 'date', 'diet_type', and 'daily_intake_percentage'.
    """
    # Find the animal and perform security check.
    animal = Purchase.query.get_or_404(purchase_id)
    if animal.farm_id != farm_id:
        return jsonify({'error': 'This animal does not belong to the specified farm.'}), 403

    # Get the data from the request body.
    data = request.get_json()

    # Validate the required fields.
    required_fields = ['date', 'diet_type']
    if not data or not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields: date, diet_type, and daily_intake_percentage'}), 400

    optional_weight = data.get('weight_kg')
    intake_str = data.get('daily_intake_percentage')
    final_intake = float(intake_str) if intake_str and intake_str.strip() else None

    try:
        # Process incoming data.
        diet_date_obj = datetime.strptime(data['date'], '%Y-%m-%d').date()

        # Create the new DietLog object.
        new_diet = DietLog(
            date=diet_date_obj,
            diet_type=data['diet_type'],
            daily_intake_percentage=final_intake,
            animal_id=purchase_id,
            farm_id=farm_id
        )
        db.session.add(new_diet)
        # 2. Check if an optional weight was provided.
        if optional_weight and float(optional_weight) > 0:
            new_weighting = Weighting(
                date=diet_date_obj,
                weight_kg=float(optional_weight),
                animal_id=purchase_id,
                farm_id=farm_id
            )
            db.session.add(new_weighting)
            message = 'Diet log and weighting recorded successfully!'
        else:
            message = 'Diet log recorded successfully!'

        db.session.commit()

        return jsonify({
            'message': message,
            'diet_log_id': new_diet.id
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500
    
@api.route('/farm/<int:farm_id>/purchase/<int:purchase_id>/death/add', methods=['POST'])
def add_death(farm_id, purchase_id):
    """
    Creates a new death record for a specific animal.
    Expects a JSON body with a 'date' and an optional 'cause'.
    """
    # 1. Find the animal and perform security check.
    animal = Purchase.query.get_or_404(purchase_id)
    if animal.farm_id != farm_id:
        return jsonify({'error': 'This animal does not belong to the specified farm.'}), 403

    # --- NEW: Business Logic Validation ---
    # 2. Check if the animal has already been sold. An animal cannot die if it was already sold.
    if animal.is_sold:
        return jsonify({'error': 'Cannot record death. This animal has already been sold.'}), 409 # 409 is "Conflict"

    # 3. Get the death data from the request body.
    data = request.get_json()

    # 4. Validate the required 'date' field.
    if not data or 'date' not in data:
        return jsonify({'error': "Missing required field: 'date'"}), 400

    try:
        death_date_obj = datetime.strptime(data['date'], '%Y-%m-%d').date()

        # 5. Create the new Death object.
        new_death = Death(
            date=death_date_obj,
            cause=data.get('cause'), # Safely get the optional 'cause'
            animal_id=purchase_id,
            farm_id=farm_id
        )

        # 6. Add and commit to the database.
        db.session.add(new_death)
        db.session.commit()

        return jsonify({
            'message': 'Death recorded successfully!',
            'death_record': new_death.to_dict()
        }), 201

    except IntegrityError:
        db.session.rollback()
        # This will be triggered if you try to record a death for the same animal twice,
        # thanks to the 'unique=True' constraint on Death.animal_id.
        return jsonify({'error': 'A death record for this animal already exists.'}), 409

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

# --- Read (GET) Routes ---
@api.route('/farms', methods=['GET'])
def get_farms():
    """Gets a list of all farms in the database."""
    farms = Farm.query.order_by(Farm.name).all()
    return jsonify([farm.to_dict() for farm in farms])

@api.route('/farm/<int:farm_id>/purchases', methods=['GET'])
def get_all_purchases(farm_id):
    """
    Gets a list of all animal purchases for a specific farm.
    Accepts optional 'start_date' and 'end_date' query parameters
    in YYYY-MM-DD format to filter the results by entry date.
    """
    # Verify the farm exists.
    Farm.query.get_or_404(farm_id)

    # Start with the base query for all purchases on this farm.
    purchases_query = Purchase.query.filter_by(farm_id=farm_id)

    try:
        # Get optional date strings from the URL's query parameters.
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        # Conditionally add filters to the query if dates are provided.
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            purchases_query = purchases_query.filter(Purchase.entry_date >= start_date)

        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            purchases_query = purchases_query.filter(Purchase.entry_date <= end_date)

    except ValueError:
        # Handle incorrectly formatted dates.
        return jsonify({'error': 'Invalid date format. Please use YYYY-MM-DD.'}), 400

    # Execute the final, assembled query, ordered by most recent purchase first.
    all_purchases = purchases_query.order_by(Purchase.entry_date.desc()).all()
    
    # Convert results to a simple list of dictionaries and return as JSON.
    results = [purchase.to_dict() for purchase in all_purchases]
    return jsonify(results)

@api.route('/farm/<int:farm_id>/sales', methods=['GET'])
def get_all_sales(farm_id):
    """
    Gets a rich, detailed list of all sales for a specific farm, including
    performance KPIs like GMD and Days on Farm for each animal.
    Accepts optional 'start_date' and 'end_date' query parameters.
    """
    # Verify the farm exists.
    Farm.query.get_or_404(farm_id)

    # --- Start building the base query ---
    sales_query = Sale.query.join(Purchase).filter(Sale.farm_id == farm_id)

    try:
        # --- Handle Optional Date Filters ---
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            sales_query = sales_query.filter(Sale.date >= start_date)

        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            sales_query = sales_query.filter(Sale.date <= end_date)

    except ValueError:
        return jsonify({'error': 'Invalid date format. Please use YYYY-MM-DD.'}), 400

    # --- Execute the Final Query ---
    all_sales = sales_query.order_by(Sale.date.desc()).all()

    # --- Assemble the Rich Response with KPIs ---
    # We just loop through the Sale objects and call our powerful to_dict() method.
    # All the complex logic is now neatly contained within the Sale model.
    results = [sale.to_dict() for sale in all_sales]

    return jsonify(results)

@api.route('/farm/<int:farm_id>/weightings', methods=['GET'])
def get_all_weightings(farm_id):
    """
    Gets a list of all weighting records for a specific farm.
    Accepts optional 'start_date' and 'end_date' query parameters
    in YYYY-MM-DD format to filter the results by the weighing date.
    """
    Farm.query.get_or_404(farm_id)

    weightings_query = Weighting.query.filter_by(farm_id=farm_id)

    try:
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            weightings_query = weightings_query.filter(Weighting.date >= start_date)

        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            weightings_query = weightings_query.filter(Weighting.date <= end_date)

    except ValueError:
        return jsonify({'error': 'Invalid date format. Please use YYYY-MM-DD.'}), 400

    all_weightings = weightings_query.order_by(Weighting.date.desc()).all()
    
    results = [weighting.to_dict() for weighting in all_weightings]
    
    # Use jsonify, as it's the standard and correct way.
    return jsonify(results)

@api.route('/farm/<int:farm_id>/location_log', methods=['GET'])
def get_all_location_changes(farm_id):
    """
    Gets a rich list of all location change events for a specific farm.
    Accepts optional 'start_date' and 'end_date' query parameters
    in YYYY-MM-DD format to filter the results by the event date.
    """
    # Verify the farm exists.
    Farm.query.get_or_404(farm_id)

    # Start with the base query for all location changes on this farm.
    changes_query = LocationChange.query.filter_by(farm_id=farm_id)

    try:
        # Get optional date strings from the URL's query parameters.
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        # Conditionally add filters to the query if dates are provided.
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            changes_query = changes_query.filter(LocationChange.date >= start_date)

        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            changes_query = changes_query.filter(LocationChange.date <= end_date)

    except ValueError:
        # Handle incorrectly formatted dates.
        return jsonify({'error': 'Invalid date format. Please use YYYY-MM-DD.'}), 400

    # Execute the final, assembled query, ordered by most recent change first.
    # We use joinedload for performance to fetch related data efficiently.
    all_changes = changes_query.options(
        db.joinedload(LocationChange.animal),
        db.joinedload(LocationChange.location),
        db.joinedload(LocationChange.sublocation)
    ).order_by(LocationChange.date.desc()).all()
    
    return jsonify([change.to_dict() for change in all_changes])

@api.route('/farm/<int:farm_id>/sanitary', methods=['GET'])
def get_all_sanitary_protocols(farm_id):
    """
    Gets a rich list of all sanitary protocol events for a specific farm.
    Accepts optional 'start_date' and 'end_date' query parameters
    in YYYY-MM-DD format to filter the results by the event date.
    """
    # Verify the farm exists.
    Farm.query.get_or_404(farm_id)

    # Start with the base query for all protocols on this farm.
    protocols_query = SanitaryProtocol.query.filter_by(farm_id=farm_id)

    try:
        # Get optional date strings from the URL's query parameters.
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        # Conditionally add filters to the query if dates are provided.
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            protocols_query = protocols_query.filter(SanitaryProtocol.date >= start_date)

        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            protocols_query = protocols_query.filter(SanitaryProtocol.date <= end_date)

    except ValueError:
        # Handle incorrectly formatted dates.
        return jsonify({'error': 'Invalid date format. Please use YYYY-MM-DD.'}), 400

    # Execute the final, assembled query, ordered by most recent event first.
    # Use joinedload to efficiently fetch the related animal data.
    all_protocols = protocols_query.options(
        db.joinedload(SanitaryProtocol.animal)
    ).order_by(SanitaryProtocol.date.desc()).all()
    
    # Assemble the rich response.
    results = [p.to_dict() for p in all_protocols] # Using to_dict for consistency
    return jsonify(results)

@api.route('/farm/<int:farm_id>/diets', methods=['GET'])
def get_all_diet_logs(farm_id):
    """
    Gets a rich list of all diet log events for a specific farm.
    Accepts optional 'start_date' and 'end_date' query parameters
    in YYYY-MM-DD format to filter the results by the event date.
    """
    # Verify the farm exists.
    Farm.query.get_or_404(farm_id)

    # Start with the base query for all diet logs on this farm.
    diets_query = DietLog.query.filter_by(farm_id=farm_id)

    try:
        # Get optional date strings from the URL's query parameters.
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        # Conditionally add filters to the query if dates are provided.
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            diets_query = diets_query.filter(DietLog.date >= start_date)

        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            diets_query = diets_query.filter(DietLog.date <= end_date)

    except ValueError:
        # Handle incorrectly formatted dates.
        return jsonify({'error': 'Invalid date format. Please use YYYY-MM-DD.'}), 400

    # Execute the final, assembled query, ordered by most recent event first.
    # Use joinedload to efficiently fetch the related animal data.
    all_diets = diets_query.options(
        db.joinedload(DietLog.animal)
    ).order_by(DietLog.date.desc()).all()
    
    # Assemble the rich response.
    return jsonify([d.to_dict() for d in all_diets])

@api.route('/farm/<int:farm_id>/locations', methods=['GET'])
def get_all_locations(farm_id):
    """
    Gets a list of all locations for a farm, with KPIs calculated efficiently
    in the database to ensure high performance with large datasets.
    """
    Farm.query.get_or_404(farm_id)

    # --- Subquery to find the latest location for each active animal ---
    last_loc_subquery = db.session.query(
        LocationChange.animal_id,
        func.max(LocationChange.date).label('max_date')
    ).join(Purchase, Purchase.id == LocationChange.animal_id)\
     .outerjoin(Sale, Purchase.id == Sale.animal_id)\
     .outerjoin(Death, Purchase.id == Death.animal_id)\
     .filter(
        LocationChange.farm_id == farm_id,
        Sale.id == None,
        Death.id == None
     ).group_by(LocationChange.animal_id).subquery()

    # --- Subquery to get the latest weight for each active animal ---
    last_weight_subquery = db.session.query(
        Weighting.animal_id,
        func.max(Weighting.date).label('max_date')
    ).join(Purchase, Purchase.id == Weighting.animal_id)\
     .outerjoin(Sale, Purchase.id == Sale.animal_id)\
     .outerjoin(Death, Purchase.id == Death.animal_id)\
     .filter(
        Weighting.farm_id == farm_id,
        Sale.id == None,
        Death.id == None
     ).group_by(Weighting.animal_id).subquery()

    # --- Main Optimized KPI Query ---
    # This single query calculates all KPIs grouped by location.
    ANIMAL_UNIT_WEIGHT_KG = 450.0
    W_last = aliased(Weighting)
    LC_last = aliased(LocationChange)

    days_on_farm = func.julianday('now') - func.julianday(Purchase.entry_date)
    days_since_last_weight = func.julianday('now') - func.julianday(W_last.date)
    total_days_for_gmd = func.julianday(W_last.date) - func.julianday(Purchase.entry_date)
    total_gain = W_last.weight_kg - Purchase.entry_weight
    gmd = func.coalesce(total_gain / func.nullif(total_days_for_gmd, 0), 0.0)
    forecasted_weight = W_last.weight_kg + (gmd * days_since_last_weight)

    kpi_query = db.session.query(
        LC_last.location_id,
        LC_last.sublocation_id,
        func.count(Purchase.id).label('animal_count'),
        func.sum(W_last.weight_kg).label('total_last_actual_weight'),
        func.sum(forecasted_weight).label('total_forecasted_weight')
    ).select_from(Purchase)\
     .join(last_loc_subquery, Purchase.id == last_loc_subquery.c.animal_id)\
     .join(LC_last, (Purchase.id == LC_last.animal_id) & (last_loc_subquery.c.max_date == LC_last.date))\
     .join(last_weight_subquery, Purchase.id == last_weight_subquery.c.animal_id)\
     .join(W_last, (Purchase.id == W_last.animal_id) & (last_weight_subquery.c.max_date == W_last.date))\
     .group_by(LC_last.location_id, LC_last.sublocation_id)
    
    kpi_results = kpi_query.all()

    # --- Organize KPI results for easy lookup ---
    location_kpis = {}
    sublocation_kpis = {}
    for kpi in kpi_results:
        # Aggregate totals for the parent location
        if kpi.location_id not in location_kpis:
            location_kpis[kpi.location_id] = {'animal_count': 0, 'total_last_actual_weight': 0, 'total_forecasted_weight': 0}
        location_kpis[kpi.location_id]['animal_count'] += kpi.animal_count
        location_kpis[kpi.location_id]['total_last_actual_weight'] += kpi.total_last_actual_weight
        location_kpis[kpi.location_id]['total_forecasted_weight'] += kpi.total_forecasted_weight
        
        # Store KPIs for the specific sublocation
        if kpi.sublocation_id:
            sublocation_kpis[kpi.sublocation_id] = {'animal_count': kpi.animal_count}

    # --- Fetch all locations and merge with calculated KPIs ---
    all_locations = Location.query.filter_by(farm_id=farm_id).order_by(Location.name).all()
    results = []
    for loc in all_locations:
        loc_dict = loc.to_dict()
        kpis = location_kpis.get(loc.id)

        # Attach sublocation animal counts
        for sub_dict in loc_dict.get('sublocations', []):
            sub_dict['animal_count'] = sublocation_kpis.get(sub_dict['id'], {}).get('animal_count', 0)

        # Calculate final capacity rates
        if kpis and loc.area_hectares and loc.area_hectares > 0:
            ua_actual = kpis['total_last_actual_weight'] / ANIMAL_UNIT_WEIGHT_KG
            ua_forecasted = kpis['total_forecasted_weight'] / ANIMAL_UNIT_WEIGHT_KG
            loc_dict['kpis'] = {
                'animal_count': kpis['animal_count'],
                'capacity_rate_actual_ua_ha': round(ua_actual / loc.area_hectares, 2),
                'capacity_rate_forecasted_ua_ha': round(ua_forecasted / loc.area_hectares, 2)
            }
        else:
            loc_dict['kpis'] = {
                'animal_count': kpis['animal_count'] if kpis else 0,
                'capacity_rate_actual_ua_ha': None,
                'capacity_rate_forecasted_ua_ha': None
            }
        results.append(loc_dict)
        
    return jsonify(results)
    
@api.route('/farm/<int:farm_id>/deaths', methods=['GET'])
def get_all_deaths(farm_id):
    """
    Gets a rich list of all death records for a specific farm.
    Accepts optional 'start_date' and 'end_date' query parameters.
    """
    # Verify the farm exists.
    Farm.query.get_or_404(farm_id)

    # Start with the base query for all deaths on this farm.
    deaths_query = Death.query.filter_by(farm_id=farm_id)

    try:
        # Handle optional date filters.
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            deaths_query = deaths_query.filter(Death.date >= start_date)

        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            deaths_query = deaths_query.filter(Death.date <= end_date)

    except ValueError:
        return jsonify({'error': 'Invalid date format. Please use YYYY-MM-DD.'}), 400

    # Execute the final query, ordering by most recent first.
    all_deaths = deaths_query.options(
        db.joinedload(Death.animal)
    ).order_by(Death.date.desc()).all()
    
    # Assemble the rich response.
    return jsonify([d.to_dict() for d in all_deaths])

@api.route('/farm/<int:farm_id>/sublocations', methods=['GET'])
def get_all_sublocations(farm_id):
    """
    Gets a list of all sublocations for a specific farm.
    """
    # Verify the farm exists.
    Farm.query.get_or_404(farm_id)

    # Start with the base query for all sublocations on this farm.
    sublocations_query = Sublocation.query.filter_by(farm_id=farm_id)

    # Execute the final, assembled query, ordered by name.
    all_sublocations = sublocations_query.order_by(Sublocation.name.asc()).all()
    
    # Convert results to a simple list of dictionaries and return as JSON.
    results = [subloc.to_dict() for subloc in all_sublocations]
    return jsonify(results)

# --- Search and Master Record Routes ---

@api.route('/farm/<int:farm_id>/animal/search', methods=['GET'])
def search_animal_by_eartag(farm_id):
    """
    Searches for active animals within a farm by their ear tag.
    Accepts an optional 'date' query parameter (YYYY-MM-DD) to find
    animals that were active on that specific date.
    """
    # Verify the farm exists.
    Farm.query.get_or_404(farm_id)
    # Get search parameters from the URL.
    tag_to_search = request.args.get('eartag')
 

    # Ensure the required eartag parameter was provided.
    if not tag_to_search:
        return jsonify({'error': 'An eartag parameter is required.'}), 400

    try:
        # Call the helper function to perform the complex query logic.
        active_animals = find_active_animal_by_eartag(farm_id, tag_to_search)
        # Convert results and return.
        results = []
        for animal in active_animals:
            purchase_details = animal.to_dict()
            kpis = animal.calculate_kpis()
            # Combine the base details with the calculated KPIs
            animal_summary = {**purchase_details, 'kpis': kpis}
            results.append(animal_summary)
        
        return jsonify(results)
    except ValueError:
        # Catch errors from incorrectly formatted dates.
        return jsonify({'error': 'Invalid date format. Please use YYYY-MM-DD.'}), 400

@api.route('/farm/<int:farm_id>/animal/<int:purchase_id>', methods=['GET'])
def get_animal_master_record(farm_id, purchase_id):
    """
    Retrieves the complete master record for a single animal, including its
    purchase details, all historical events (weights, protocols, etc.),
    and calculated key performance indicators (KPIs).
    """
    # Find the animal.
    animal = Purchase.query.get_or_404(purchase_id)
    # Security check: ensure the animal belongs to the specified farm.
    if animal.farm_id != farm_id:
        return jsonify({'error': 'This animal does not belong to the specified farm.'}), 403

    # Use helper functions to process the data.
    smart_weight_history = calculate_weight_history_with_gmd(animal)
    calculated_kpis = animal.calculate_kpis()
    
    # Determine the exit details, defaulting to null if not sold or dead.
    exit_details_data = None
    if animal.is_sold:
        sale_data = animal.sale.to_dict()
        # Calculate profit/loss if purchase price is available
        if animal.purchase_price:
            sale_data['profit_loss'] = sale_data['exit_price'] - animal.purchase_price
        else:
            sale_data['profit_loss'] = None
        exit_details_data = sale_data
    elif animal.is_dead:
        exit_details_data = animal.death.to_dict()


    # Assemble the final master record. The JSON structure is now always the same.
    master_record = {
        'purchase_details': animal.to_dict(),
        'exit_details': exit_details_data, # This key will always exist.
        'calculated_kpis': calculated_kpis,
        'weight_history': smart_weight_history,
        'protocol_history': [protocol.to_dict() for protocol in animal.protocols],
        'location_history': [change.to_dict() for change in animal.location_changes],
        'diet_history': [diet.to_dict() for diet in animal.diet_logs]
    }

    return jsonify(master_record)

# --- Business Intelligence (BI) and Summary Routes ---

@api.route('/farm/<int:farm_id>/lots/summary', methods=['GET'])
def get_lots_summary(farm_id):
    """
    Gets a summary of all active lots for a farm, with aggregated KPIs
    calculated efficiently in the database.
    """
    Farm.query.get_or_404(farm_id)

    # --- Reusable subquery and expressions from Active Stock ---
    last_weight_subquery = db.session.query(
        Weighting.animal_id,
        func.max(Weighting.date).label('max_date')
    ).filter(Weighting.farm_id == farm_id).group_by(Weighting.animal_id).subquery()
    
    W_last = aliased(Weighting)
    days_on_farm = func.julianday('now') - func.julianday(Purchase.entry_date)
    days_since_last_weight = func.julianday('now') - func.julianday(W_last.date)
    total_days_for_gmd = func.julianday(W_last.date) - func.julianday(Purchase.entry_date)
    total_gain = W_last.weight_kg - Purchase.entry_weight
    gmd = func.coalesce(total_gain / func.nullif(total_days_for_gmd, 0), 0.0)
    forecasted_weight = W_last.weight_kg + (gmd * days_since_last_weight)

    # --- Main Optimized Query, Grouped by Lot ---
    summary_query = db.session.query(
        Purchase.lot.label('lot_number'),
        func.count(Purchase.id).label('animal_count'),
        func.coalesce(func.sum(case((Purchase.sex == 'M', 1))), 0).label('male_count'),
        func.coalesce(func.sum(case((Purchase.sex == 'F', 1))), 0).label('female_count'),
        func.avg(Purchase.entry_age + (days_on_farm / 30.44)).label('average_age_months'),
        func.avg(gmd).label('average_gmd_kg'),
        func.avg(forecasted_weight).label('average_weight_kg')
    ).outerjoin(Sale, Purchase.id == Sale.animal_id) \
     .outerjoin(Death, Purchase.id == Death.animal_id) \
     .join(last_weight_subquery, Purchase.id == last_weight_subquery.c.animal_id) \
     .join(W_last, (Purchase.id == W_last.animal_id) & (last_weight_subquery.c.max_date == W_last.date)) \
     .filter(
        Purchase.farm_id == farm_id,
        Sale.id == None,
        Death.id == None
     ).group_by(Purchase.lot).order_by(Purchase.lot)

    results = [dict(row._mapping) for row in summary_query.all()]
    
    return jsonify(results)

@api.route('/farm/<int:farm_id>/lot/<lot_number>', methods=['GET'])
def get_lot_summary(farm_id, lot_number):
    """
    Gets a summary of animals within a specific lot on a farm.
    Optimized to perform all calculations in a single database query.
    Currently focuses on 'active' status for maximum performance.
    """
    Farm.query.get_or_404(farm_id)
    status_filter = request.args.get('status', 'active').lower()

    if status_filter != 'active':
        # For now, we only optimize the 'active' case which is the slow one.
        # Sold/dead animals could be implemented later if needed.
        return jsonify({'error': "Only 'active' status is supported in this optimized endpoint."}), 400

    # --- This is essentially the same optimized query from get_active_stock_summary ---
    # --- with one extra filter: Purchase.lot == lot_number ---
    
    last_weight_subquery = db.session.query(
        Weighting.animal_id,
        func.max(Weighting.date).label('max_date')
    ).filter(Weighting.farm_id == farm_id).group_by(Weighting.animal_id).subquery()
    
    last_loc_subquery = db.session.query(
        LocationChange.animal_id,
        func.max(LocationChange.date).label('max_date')
    ).filter(LocationChange.farm_id == farm_id).group_by(LocationChange.animal_id).subquery()

    last_diet_subquery = db.session.query(
        DietLog.animal_id,
        func.max(DietLog.date).label('max_date')
    ).filter(DietLog.farm_id == farm_id).group_by(DietLog.animal_id).subquery()

    W_last = aliased(Weighting)
    LC_last = aliased(LocationChange)
    L_loc = aliased(Location)
    DL_last = aliased(DietLog)

    days_on_farm = func.julianday('now') - func.julianday(Purchase.entry_date)
    days_since_last_weight = func.julianday('now') - func.julianday(W_last.date)
    total_days_for_gmd = func.julianday(W_last.date) - func.julianday(Purchase.entry_date)
    total_gain = W_last.weight_kg - Purchase.entry_weight
    gmd = func.coalesce(total_gain / func.nullif(total_days_for_gmd, 0), 0.0)

    base_query = db.session.query(
        Purchase, # Select the whole Purchase object
        (Purchase.entry_age + (days_on_farm / 30.44)).label('current_age_months'),
        W_last.weight_kg.label('last_weight_kg'),
        W_last.date.label('last_weighting_date'),
        gmd.label('average_daily_gain_kg'),
        (W_last.weight_kg + (gmd * days_since_last_weight)).label('forecasted_current_weight_kg'),
        L_loc.name.label('current_location_name'),
        L_loc.id.label('current_location_id'),
        DL_last.diet_type.label('current_diet_type')
    ).outerjoin(Sale, Purchase.id == Sale.animal_id) \
     .outerjoin(Death, Purchase.id == Death.animal_id) \
     .join(last_weight_subquery, Purchase.id == last_weight_subquery.c.animal_id) \
     .join(W_last, (Purchase.id == W_last.animal_id) & (last_weight_subquery.c.max_date == W_last.date)) \
     .outerjoin(last_loc_subquery, Purchase.id == last_loc_subquery.c.animal_id) \
     .outerjoin(LC_last, (Purchase.id == LC_last.animal_id) & (last_loc_subquery.c.max_date == LC_last.date)) \
     .outerjoin(L_loc, LC_last.location_id == L_loc.id) \
     .outerjoin(last_diet_subquery, Purchase.id == last_diet_subquery.c.animal_id) \
     .outerjoin(DL_last, (Purchase.id == DL_last.animal_id) & (last_diet_subquery.c.max_date == DL_last.date)) \
     .filter(
        Purchase.farm_id == farm_id,
        Purchase.lot == lot_number, # The key filter for this specific lot
        Sale.id == None,
        Death.id == None
     ).order_by(Purchase.ear_tag)

    results = []
    for row in base_query.all():
        purchase_details = row.Purchase.to_dict()
        kpis = {
            'current_age_months': row.current_age_months,
            'last_weight_kg': row.last_weight_kg,
            'last_weighting_date': row.last_weighting_date.isoformat(),
            'average_daily_gain_kg': row.average_daily_gain_kg,
            'forecasted_current_weight_kg': row.forecasted_current_weight_kg,
            'current_location_name': row.current_location_name,
            'current_location_id': row.current_location_id,
            'current_diet_type': row.current_diet_type
        }
        animal_summary = {**purchase_details, 'kpis': kpis}
        results.append(animal_summary)
        
    return jsonify(results)

@api.route('/farm/<int:farm_id>/location/<int:location_id>/summary', methods=['GET'])
def get_location_summary(farm_id, location_id):
    """
    Gets a detailed summary for a single location, with all calculations
    performed efficiently in the database by filtering for relevant animals first.
    """
    location = Location.query.filter_by(id=location_id, farm_id=farm_id).first_or_404()

    # --- Step 1: Find the IDs of active animals whose LATEST location is the target location ---
    # This subquery is the key to performance. It runs first and is very fast.
    last_loc_subquery = db.session.query(
        LocationChange.animal_id,
        func.max(LocationChange.date).label('max_date')
    ).join(Purchase, Purchase.id == LocationChange.animal_id)\
     .outerjoin(Sale, Purchase.id == Sale.animal_id)\
     .outerjoin(Death, Purchase.id == Death.animal_id)\
     .filter(
        LocationChange.farm_id == farm_id,
        Sale.id == None,
        Death.id == None
     ).group_by(LocationChange.animal_id).subquery()

    animal_ids_in_location_query = db.session.query(
        LocationChange.animal_id
    ).join(last_loc_subquery, 
           (LocationChange.animal_id == last_loc_subquery.c.animal_id) &
           (LocationChange.date == last_loc_subquery.c.max_date)
    ).filter(LocationChange.location_id == location_id)

    # --- Step 2: Now run the complex KPI query ONLY on those specific animal IDs ---
    last_weight_subquery = db.session.query(
        Weighting.animal_id,
        func.max(Weighting.date).label('max_date')
    ).filter(Weighting.animal_id.in_(animal_ids_in_location_query)).group_by(Weighting.animal_id).subquery()

    last_diet_subquery = db.session.query(
        DietLog.animal_id,
        func.max(DietLog.date).label('max_date')
    ).filter(DietLog.animal_id.in_(animal_ids_in_location_query)).group_by(DietLog.animal_id).subquery()

    # Aliases and expressions
    W_last = aliased(Weighting)
    DL_last = aliased(DietLog)
    days_on_farm = func.julianday('now') - func.julianday(Purchase.entry_date)
    total_days_for_gmd = func.julianday(W_last.date) - func.julianday(Purchase.entry_date)
    total_gain = W_last.weight_kg - Purchase.entry_weight
    gmd = func.coalesce(total_gain / func.nullif(total_days_for_gmd, 0), 0.0)
    forecasted_weight = W_last.weight_kg + (gmd * days_on_farm)

    # --- Query for the animal list ---
    animal_list_query = db.session.query(
        Purchase,
        (Purchase.entry_age + (days_on_farm / 30.44)).label('current_age_months'),
        W_last.weight_kg.label('last_weight_kg'),
        gmd.label('average_daily_gain_kg'),
        forecasted_weight.label('forecasted_current_weight_kg'),
        DL_last.diet_type.label('current_diet_type')
    ).join(last_weight_subquery, Purchase.id == last_weight_subquery.c.animal_id) \
     .join(W_last, (Purchase.id == W_last.animal_id) & (last_weight_subquery.c.max_date == W_last.date)) \
     .outerjoin(last_diet_subquery, Purchase.id == last_diet_subquery.c.animal_id) \
     .outerjoin(DL_last, (Purchase.id == DL_last.animal_id) & (last_diet_subquery.c.max_date == DL_last.date)) \
     .filter(Purchase.id.in_(animal_ids_in_location_query)) # The crucial performance filter
    
    animal_details_list = []
    for row in animal_list_query.all():
        purchase_details = row.Purchase.to_dict()
        kpis = {
            'current_age_months': row.current_age_months,
            'last_weight_kg': row.last_weight_kg,
            'average_daily_gain_kg': row.average_daily_gain_kg,
            'forecasted_current_weight_kg': row.forecasted_current_weight_kg,
            'current_diet_type': row.current_diet_type
        }
        animal_summary = {**purchase_details, 'kpis': kpis}
        animal_details_list.append(animal_summary)
        
    # --- Query for the location's summary KPIs ---
    ANIMAL_UNIT_WEIGHT_KG = 450.0
    kpi_summary_query = db.session.query(
        func.count(Purchase.id).label('animal_count'),
        func.sum(W_last.weight_kg).label('total_last_actual_weight'),
        func.sum(forecasted_weight).label('total_forecasted_weight')
    ).join(last_weight_subquery, Purchase.id == last_weight_subquery.c.animal_id)\
     .join(W_last, (Purchase.id == W_last.animal_id) & (last_weight_subquery.c.max_date == W_last.date))\
     .filter(Purchase.id.in_(animal_ids_in_location_query)) # The crucial performance filter
    
    kpis = kpi_summary_query.first()
    
    location_details_dict = location.to_dict()
    if kpis and location.area_hectares and location.area_hectares > 0:
        ua_actual = (kpis.total_last_actual_weight or 0) / ANIMAL_UNIT_WEIGHT_KG
        ua_forecasted = (kpis.total_forecasted_weight or 0) / ANIMAL_UNIT_WEIGHT_KG
        location_details_dict['kpis'] = {
            'animal_count': kpis.animal_count,
            'capacity_rate_actual_ua_ha': round(ua_actual / location.area_hectares, 2),
            'capacity_rate_forecasted_ua_ha': round(ua_forecasted / location.area_hectares, 2)
        }
    else:
        location_details_dict['kpis'] = {
            'animal_count': kpis.animal_count if kpis else 0,
            'capacity_rate_actual_ua_ha': None,
            'capacity_rate_forecasted_ua_ha': None
        }

    # --- Assemble the final response ---
    final_response = {
        "location_details": location_details_dict,
        "animals": animal_details_list
    }

    return jsonify(final_response)

@api.route('/farm/<int:farm_id>/stock/active_summary', methods=['GET'])
def get_active_stock_summary(farm_id):
    """
    Gets a complete, paginated summary of the active stock for a specific farm,
    with all calculations performed efficiently in the database.
    """
    Farm.query.get_or_404(farm_id)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 100, type=int)

    # --- Subquery to get the latest weighting for each animal ---
    last_weight_subquery = db.session.query(
        Weighting.animal_id,
        func.max(Weighting.date).label('max_date')
    ).filter(Weighting.farm_id == farm_id).group_by(Weighting.animal_id).subquery()

    # --- Subquery to get the latest location for each animal ---
    last_loc_subquery = db.session.query(
        LocationChange.animal_id,
        func.max(LocationChange.date).label('max_date')
    ).filter(LocationChange.farm_id == farm_id).group_by(LocationChange.animal_id).subquery()

    # --- Subquery to get the latest diet for each animal ---
    last_diet_subquery = db.session.query(
        DietLog.animal_id,
        func.max(DietLog.date).label('max_date')
    ).filter(DietLog.farm_id == farm_id).group_by(DietLog.animal_id).subquery()

    # Aliases for joins
    W_last = aliased(Weighting)
    LC_last = aliased(LocationChange)
    L_loc = aliased(Location)
    DL_last = aliased(DietLog)

    # --- The Main, Optimized Query ---
    # NOTE: func.julianday is specific to SQLite. For PostgreSQL/MySQL, use funcs like DATE_PART or DATEDIFF.
    days_on_farm = func.julianday('now') - func.julianday(Purchase.entry_date)
    days_since_last_weight = func.julianday('now') - func.julianday(W_last.date)
    
    total_days_for_gmd = func.julianday(W_last.date) - func.julianday(Purchase.entry_date)
    total_gain = W_last.weight_kg - Purchase.entry_weight
    
    # We call the .else_() method on the case object.
    gmd = func.coalesce(total_gain / func.nullif(total_days_for_gmd, 0), 0.0)

    base_query = db.session.query(
        Purchase.id,
        Purchase.ear_tag,
        Purchase.lot,
        Purchase.entry_date,
        Purchase.sex,
        (Purchase.entry_age + (days_on_farm / 30.44)).label('current_age_months'),
        W_last.weight_kg.label('last_weight_kg'),
        W_last.date.label('last_weighting_date'),
        gmd.label('average_daily_gain_kg'),
        (W_last.weight_kg + (gmd * days_since_last_weight)).label('forecasted_current_weight_kg'),
        L_loc.name.label('current_location_name'),
        L_loc.id.label('current_location_id'),
        DL_last.diet_type.label('current_diet_type'),
        DL_last.daily_intake_percentage.label('current_diet_intake')
    ).outerjoin(Sale, Purchase.id == Sale.animal_id) \
     .outerjoin(Death, Purchase.id == Death.animal_id) \
     .join(last_weight_subquery, Purchase.id == last_weight_subquery.c.animal_id) \
     .join(W_last, (Purchase.id == W_last.animal_id) & (last_weight_subquery.c.max_date == W_last.date)) \
     .outerjoin(last_loc_subquery, Purchase.id == last_loc_subquery.c.animal_id) \
     .outerjoin(LC_last, (Purchase.id == LC_last.animal_id) & (last_loc_subquery.c.max_date == LC_last.date)) \
     .outerjoin(L_loc, LC_last.location_id == L_loc.id) \
     .outerjoin(last_diet_subquery, Purchase.id == last_diet_subquery.c.animal_id) \
     .outerjoin(DL_last, (Purchase.id == DL_last.animal_id) & (last_diet_subquery.c.max_date == DL_last.date)) \
     .filter(
        Purchase.farm_id == farm_id,
        Sale.id == None, # This is how we find active animals with a JOIN
        Death.id == None
     ).order_by(Purchase.lot, Purchase.ear_tag)

    all_animals = base_query.all()

    # --- Summary Calculation (also done in the DB for efficiency) ---
    summary_query = db.session.query(
        func.count(Purchase.id).label('total_active_animals'),
        func.coalesce(func.sum(case((Purchase.sex == 'M', 1))), 0).label('number_of_males'),
        func.coalesce(func.sum(case((Purchase.sex == 'F', 1))), 0).label('number_of_females'),
        func.avg(Purchase.entry_age + (days_on_farm / 30.44)).label('average_age_months'),
        func.avg(gmd).label('average_gmd_kg_day')
    ).outerjoin(Sale, Purchase.id == Sale.animal_id) \
     .outerjoin(Death, Purchase.id == Death.animal_id) \
     .join(last_weight_subquery, Purchase.id == last_weight_subquery.c.animal_id) \
     .join(W_last, (Purchase.id == W_last.animal_id) & (last_weight_subquery.c.max_date == W_last.date)) \
     .filter(
        Purchase.farm_id == farm_id,
        Sale.id == None,
        Death.id == None
     )
    
    summary_kpis_result = summary_query.first()
    summary_kpis = {
        "total_active_animals": summary_kpis_result.total_active_animals or 0,
        "number_of_males": int(summary_kpis_result.number_of_males or 0),
        "number_of_females": int(summary_kpis_result.number_of_females or 0),
        "average_age_months": float(summary_kpis_result.average_age_months or 0),
        "average_gmd_kg_day": float(summary_kpis_result.average_gmd_kg_day or 0)
    }

    # Convert paginated results (which are Row objects) into dictionaries
    animal_details_list = [
        {
            'id': animal.id, 'ear_tag': animal.ear_tag, 'lot': animal.lot, 'entry_date': animal.entry_date.isoformat(),
            'sex': animal.sex,
            'kpis': {
                'current_age_months': animal.current_age_months,
                'last_weight_kg': animal.last_weight_kg,
                'last_weighting_date': animal.last_weighting_date.isoformat(),
                'average_daily_gain_kg': animal.average_daily_gain_kg,
                'forecasted_current_weight_kg': animal.forecasted_current_weight_kg,
                'current_location_name': animal.current_location_name,
                'current_location_id': animal.current_location_id,
                'current_diet_type': animal.current_diet_type,
                'current_diet_intake': animal.current_diet_intake
            }
        } for animal in all_animals
    ]

    return jsonify({
        "summary_kpis": summary_kpis,
        "animals": animal_details_list
        # 'total_items': pagination.total,
        # 'total_pages': pagination.pages,
        # 'current_page': page,
        # 'has_next': pagination.has_next,
        # 'has_prev': pagination.has_prev
    })

@api.route('/dev/seed-test-farm', methods=['POST'])
def seed_test_farm():
    """
    (For Developers) Creates a test farm with a large volume of simulated data over 10 years.
    This is a destructive operation if the farm already exists.
    """
    params = request.get_json()
    if not params:
        return jsonify({'error': 'Missing JSON request body'}), 400
    print("Starting seed test farm...")
    # --- 1. Parameter Extraction and Validation ---
    try:
        farm_name = params['farm_name']
        purchases_per_year = int(params['total_animal_purchases_per_year'])
        monthly_dist = params['monthly_concentration']
        weighting_freq = int(params['weighting_frequency_days'])
        sell_after_days = int(params['sell_after_days'])
        assumed_gmd = float(params['assumed_gmd_kg'])
        sanitary_protocols_config = params['sanitary_protocols']
        initial_diet_config = params['initial_diet']
        diet_change_config = params.get('diet_change')
        num_locations = int(params['num_locations'])
        num_sublocations = int(params['num_sublocations_per_location'])
        total_farm_area_ha = float(params['total_farm_area_ha'])
        fixed_purchase_price = params.get('fixed_purchase_price')
        fixed_sale_price_per_kg = params.get('fixed_sale_price_per_kg')
        years = int(params['years'])
        end_date = datetime.strptime(params['end_date'], '%Y-%m-%d').date()

    except (KeyError, ValueError) as e:
        return jsonify({'error': f'Invalid or missing parameter: {str(e)}'}), 400

    market_prices, sorted_market_dates = load_historical_prices()
    if not market_prices and (fixed_purchase_price is None or fixed_sale_price_per_kg is None):
        return jsonify({'error': 'Historical price data is missing and no fixed prices were provided. Cannot proceed.'}), 400

    print("Creating farm infrastructure...")
    existing_farm = Farm.query.filter_by(name=farm_name).first()
    if existing_farm:
        farm_id_to_delete = existing_farm.id
        print(f"Farm '{farm_name}' exists. Beginning optimized deletion for farm ID: {farm_id_to_delete}...")

        # Execute bulk deletes in the correct order to respect foreign key constraints
        # We delete from "many" tables before "one" tables.
        try:
            # Tables pointing to Purchase
            db.session.execute(delete(Weighting).where(Weighting.farm_id == farm_id_to_delete))
            db.session.execute(delete(Sale).where(Sale.farm_id == farm_id_to_delete))
            db.session.execute(delete(Death).where(Death.farm_id == farm_id_to_delete))
            db.session.execute(delete(SanitaryProtocol).where(SanitaryProtocol.farm_id == farm_id_to_delete))
            db.session.execute(delete(LocationChange).where(LocationChange.farm_id == farm_id_to_delete))
            db.session.execute(delete(DietLog).where(DietLog.farm_id == farm_id_to_delete))
            print("Cleared child records of purchases.")

            # Purchase table itself
            db.session.execute(delete(Purchase).where(Purchase.farm_id == farm_id_to_delete))
            print("Cleared purchases.")

            # Tables pointing to Location
            db.session.execute(delete(Sublocation).where(Sublocation.farm_id == farm_id_to_delete))
            print("Cleared sublocations.")

            # Location table itself
            db.session.execute(delete(Location).where(Location.farm_id == farm_id_to_delete))
            print("Cleared locations.")
            
            # Finally, delete the parent farm object itself
            db.session.delete(existing_farm)
            print("Cleared farm record.")

            db.session.commit()
            print("Optimized deletion complete.")
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'An error occurred during optimized deletion: {str(e)}'}), 500

    print("Creating new farm and locations...")
    new_farm = Farm(name=farm_name)
    db.session.add(new_farm)
    db.session.flush() # This gives new_farm an ID to be used by locations
    
    location_ids = []
    location_areas = [] # This list will hold the area for each locatio
    
    random_proportions = [random.uniform(0.7, 1.3) for _ in range(num_locations)]
    total_proportion = sum(random_proportions)
    normalized_proportions = [p / total_proportion for p in random_proportions]
    
    print("Creating locations...")
    for i in range(num_locations):
        location_area = total_farm_area_ha * normalized_proportions[i]
        sublocation_area = location_area / num_sublocations if num_sublocations > 0 else 0
        loc = Location(name=f'Pasture {i+1}', 
            farm_id=new_farm.id, 
            area_hectares=location_area, 
            grass_type=random.choice(['Brachiaria decumbens', 'Brachiaria humidicola', 'Mombaça']),
            location_type='Rotacionado'
            )
        db.session.add(loc)
        db.session.flush()


        location_ids.append(loc.id)
        location_areas.append(location_area)
        for j in range(num_sublocations):
             subloc = Sublocation(name=f'Paddock {j+1}', location_id=loc.id, farm_id=new_farm.id, area_hectares=sublocation_area)
             db.session.add(subloc)

    # --- 4. Main Simulation Loop ---
    start_date = end_date - timedelta(days=365 * years)
    current_date = start_date
    animal_eartag_counter = 0
    lot_counter = 0 
    last_purchase_date = None
    
    # --- Add a variable to track the year for batch commits ---
    last_processed_year = start_date.year - 1

    while current_date < end_date:
        # --- Commit data in yearly batches for performance ---
        if current_date.year > last_processed_year:
            if last_processed_year > start_date.year - 1:
                print(f"Committing data for year {last_processed_year}...")
                db.session.commit()
            last_processed_year = current_date.year
            print(f"Processing year {last_processed_year}...")

        if last_purchase_date != current_date:
            lot_counter += 1
            last_purchase_date = current_date
            lot_sex = random.choice(['M', 'F'])

            lot_initial_location_id = random.choices(location_ids, weights=location_areas, k=1)[0]
            lot_race = random.choice(['Nelore', 'Angus', 'Hereford','Simmental',"Brahman","Tabapuã",'Mestiço'])

        month_key = str(current_date.month)
        num_purchases_this_month = int(purchases_per_year * monthly_dist.get(month_key, 0))

        for _ in range(num_purchases_this_month):
            purchase_date = current_date
            purchase_price = fixed_purchase_price
            if purchase_price is None:
                price_info = get_closest_price(purchase_date, market_prices, sorted_market_dates)
                purchase_price = price_info['purchase']
            
            initial_weight = random.uniform(180, 250)
            new_animal = Purchase(
                ear_tag=str(animal_eartag_counter), lot=lot_counter, entry_date=purchase_date,
                entry_weight=initial_weight, sex=lot_sex, race=lot_race,
                entry_age=random.uniform(8, 12), farm_id=new_farm.id,
                purchase_price=purchase_price,
            )
            db.session.add(new_animal)
            db.session.flush()
            animal_eartag_counter = (animal_eartag_counter + 1) % 1001

            db.session.add(Weighting(date=purchase_date, weight_kg=initial_weight, animal_id=new_animal.id, farm_id=new_farm.id))
            db.session.add(LocationChange(date=purchase_date, location_id=lot_initial_location_id, animal_id=new_animal.id, farm_id=new_farm.id))
            db.session.add(DietLog(date=purchase_date, diet_type=initial_diet_config['diet_type'], daily_intake_percentage=initial_diet_config['daily_intake_percentage'], animal_id=new_animal.id, farm_id=new_farm.id))

            sale_date = purchase_date + timedelta(days=sell_after_days)
            last_weight = initial_weight
            last_weight_date = purchase_date
            
            next_event_date = purchase_date + timedelta(days=weighting_freq)
            while next_event_date < sale_date and next_event_date < end_date:
                days_diff = (next_event_date - last_weight_date).days
                weight_gain = days_diff * (assumed_gmd * random.uniform(0.8, 1.2))
                new_weight = last_weight + weight_gain
                db.session.add(Weighting(date=next_event_date, weight_kg=new_weight, animal_id=new_animal.id, farm_id=new_farm.id))
                last_weight = new_weight
                last_weight_date = next_event_date
                next_event_date += timedelta(days=weighting_freq)

            for protocol in sanitary_protocols_config:
                next_protocol_date = purchase_date + timedelta(days=protocol['frequency_days'])
                while next_protocol_date < sale_date and next_protocol_date < end_date:
                    db.session.add(SanitaryProtocol(date=next_protocol_date, protocol_type=protocol['protocol_type'], product_name=protocol['product_name'], animal_id=new_animal.id, farm_id=new_farm.id))
                    next_protocol_date += timedelta(days=protocol['frequency_days'])
            
            if diet_change_config:
                diet_change_date = purchase_date + timedelta(days=diet_change_config['days_after_purchase'])
                if diet_change_date < sale_date and diet_change_date < end_date:
                    db.session.add(DietLog(date=diet_change_date, diet_type=diet_change_config['new_diet']['diet_type'], daily_intake_percentage=diet_change_config['new_diet']['daily_intake_percentage'], animal_id=new_animal.id, farm_id=new_farm.id))
            
            if sale_date < end_date:
                sale_price_per_kg = fixed_sale_price_per_kg
                if sale_price_per_kg is None:
                    price_info = get_closest_price(sale_date, market_prices, sorted_market_dates)
                    sale_price_per_kg = price_info['sale']
                days_diff_final = (sale_date - last_weight_date).days
                final_gain = days_diff_final * assumed_gmd
                exit_weight = last_weight + final_gain
                
                # Using the sale_price_per_kg to calculate total price
                total_sale_price = exit_weight * sale_price_per_kg
                
                db.session.add(Sale(date=sale_date, sale_price=total_sale_price, animal_id=new_animal.id, farm_id=new_farm.id))
                db.session.add(Weighting(date=sale_date, weight_kg=exit_weight, animal_id=new_animal.id, farm_id=new_farm.id))

        next_month = current_date.month + 1
        next_year = current_date.year
        if next_month > 12:
            next_month = 1
            next_year += 1
        current_date = date(next_year, next_month, 1)

    # --- 5. Final Commit ---
    try:
        # Commit the final batch of data
        print(f"Committing final batch of data for year {last_processed_year}...")
        db.session.commit()
        return jsonify({'message': f"Successfully seeded farm '{farm_name}' with thousands of records."}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An error occurred during final commit: {str(e)}'}), 500

# --- Import / Export Routes ---

@api.route('/export/farms', methods=['POST'])
def export_farms():
    """
    Exports all data for a given list of farm IDs into a single JSON file.
    Expects a JSON body with a 'farm_ids' key, which is a list of integers.
    """
    data = request.get_json()
    if not data or 'farm_ids' not in data:
        return jsonify({'error': "Request body must contain a 'farm_ids' list."}), 400

    farm_ids = data['farm_ids']
    if not isinstance(farm_ids, list):
        return jsonify({'error': "'farm_ids' must be a list."}), 400

    try:
        # Eagerly load relationships for performance to avoid N+1 query problems
        farms_to_export = Farm.query.filter(Farm.id.in_(farm_ids)).options(
            db.selectinload(Farm.locations).selectinload(Location.sublocations),
            db.selectinload(Farm.purchases).selectinload(Purchase.weightings),
            db.selectinload(Farm.purchases).selectinload(Purchase.protocols),
            db.selectinload(Farm.purchases).selectinload(Purchase.location_changes),
            db.selectinload(Farm.purchases).selectinload(Purchase.diet_logs),
            db.selectinload(Farm.purchases).selectinload(Purchase.sale),
            db.selectinload(Farm.purchases).selectinload(Purchase.death),
        ).all()

        if not farms_to_export:
            return jsonify({'error': 'No farms found for the provided IDs.'}), 404

        export_data = {
            'export_format_version': '1.0',
            'export_date': datetime.now().isoformat(),
            'farms': []
        }

        for farm in farms_to_export:
            farm_data = farm.to_dict()
            farm_data['locations'] = []
            farm_data['purchases'] = []

            # Locations and Sublocations
            for loc in farm.locations:
                loc_data = loc.to_dict()
                # `to_dict` already includes sublocations, but this ensures it
                loc_data['sublocations'] = [sub.to_dict() for sub in loc.sublocations]
                farm_data['locations'].append(loc_data)
            
            # Animals and all their related events
            for p in farm.purchases:
                p_data = p.to_dict()
                p_data['weightings'] = [w.to_dict() for w in p.weightings]
                p_data['protocols'] = [sp.to_dict() for sp in p.protocols]
                p_data['location_changes'] = [lc.to_dict() for lc in p.location_changes]
                p_data['diet_logs'] = [dl.to_dict() for dl in p.diet_logs]
                p_data['sale'] = p.sale.to_dict() if p.sale else None
                p_data['death'] = p.death.to_dict() if p.death else None
                farm_data['purchases'].append(p_data)

            export_data['farms'].append(farm_data)
        
        # Use default=str to handle date/datetime objects that aren't already strings
        json_string = json.dumps(export_data, indent=4, default=str)

        # Create an in-memory file-like object to avoid writing to disk
        mem_file = io.BytesIO()
        mem_file.write(json_string.encode('utf-8'))
        mem_file.seek(0) # Rewind to the beginning of the stream

        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        filename = f"bovitrack_export_{timestamp}.json"

        return send_file(
            mem_file,
            as_attachment=True,
            download_name=filename,
            mimetype='application/json'
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An unexpected error occurred during export: {str(e)}'}), 500

@api.route('/import/farms', methods=['POST'])
def import_farms():
    """
    Imports farm data from an uploaded JSON file. This is a transactional operation.
    """
    if 'import_file' not in request.files:
        return jsonify({'error': 'No file part in the request.'}), 400
    
    file = request.files['import_file']
    if file.filename == '':
        return jsonify({'error': 'No file selected.'}), 400

    if not file or not file.filename.endswith('.json'):
        return jsonify({'error': 'Invalid file type. Please upload a .json file.'}), 400

    try:
        content = file.read().decode('utf-8')
        import_data = json.loads(content)
    except Exception as e:
        return jsonify({'error': f'Failed to parse JSON file: {str(e)}'}), 400

    # --- Data Processing and Import within a transaction ---
    try:
        farm_id_map = {}
        location_id_map = {}
        sublocation_id_map = {}
        purchase_id_map = {}
        imported_farm_names = []

        for farm_json in import_data.get('farms', []):
            original_farm_name = farm_json['name']
            
            # Conflict Resolution: Skip farms that already exist by name
            if Farm.query.filter_by(name=original_farm_name).first():
                continue

            # 1. Create Farm
            new_farm = Farm(name=original_farm_name)
            db.session.add(new_farm)
            db.session.flush() # Assigns an ID to new_farm
            farm_id_map[farm_json['id']] = new_farm.id
            imported_farm_names.append(new_farm.name)

            # 2. Create Locations & Sublocations
            for loc_json in farm_json.get('locations', []):
                new_loc = Location(
                    name=loc_json['name'], area_hectares=loc_json.get('area_hectares'),
                    grass_type=loc_json.get('grass_type'), location_type=loc_json.get('location_type'),
                    farm_id=new_farm.id
                )
                db.session.add(new_loc)
                db.session.flush()
                location_id_map[loc_json['id']] = new_loc.id

                for sub_json in loc_json.get('sublocations', []):
                    new_sub = Sublocation(
                        name=sub_json['name'], area_hectares=sub_json.get('area_hectares'),
                        location_id=new_loc.id, farm_id=new_farm.id
                    )
                    db.session.add(new_sub)
                    db.session.flush()
                    sublocation_id_map[sub_json['id']] = new_sub.id

            # 3. Create Purchases and all related events
            for p_json in farm_json.get('purchases', []):
                new_purchase = Purchase(
                    ear_tag=p_json['ear_tag'], lot=p_json['lot'],
                    entry_date=datetime.fromisoformat(p_json['entry_date']).date(),
                    entry_weight=p_json['entry_weight'], sex=p_json['sex'],
                    entry_age=p_json['entry_age'], purchase_price=p_json.get('purchase_price'),
                    race=p_json.get('race'), farm_id=new_farm.id
                )
                db.session.add(new_purchase)
                db.session.flush()
                purchase_id_map[p_json['id']] = new_purchase.id

                for w_json in p_json.get('weightings', []):
                    db.session.add(Weighting(date=datetime.fromisoformat(w_json['date']).date(), weight_kg=w_json['weight_kg'], animal_id=new_purchase.id, farm_id=new_farm.id))
                for sp_json in p_json.get('protocols', []):
                     db.session.add(SanitaryProtocol(date=datetime.fromisoformat(sp_json['date']).date(), protocol_type=sp_json['protocol_type'], product_name=sp_json.get('product_name'), dosage=sp_json.get('dosage'), invoice_number=sp_json.get('invoice_number'), animal_id=new_purchase.id, farm_id=new_farm.id))
                for lc_json in p_json.get('location_changes', []):
                    new_loc_id = location_id_map.get(lc_json['location_id'])
                    new_subloc_id = sublocation_id_map.get(lc_json['sublocation_id'])
                    if new_loc_id:
                        db.session.add(LocationChange(date=datetime.fromisoformat(lc_json['date']).date(), location_id=new_loc_id, sublocation_id=new_subloc_id, animal_id=new_purchase.id, farm_id=new_farm.id))
                for dl_json in p_json.get('diet_logs', []):
                    db.session.add(DietLog(date=datetime.fromisoformat(dl_json['date']).date(), diet_type=dl_json['diet_type'], daily_intake_percentage=dl_json.get('daily_intake_percentage'), animal_id=new_purchase.id, farm_id=new_farm.id))
                if p_json.get('sale'):
                    sale_json = p_json['sale']
                    db.session.add(Sale(date=datetime.fromisoformat(sale_json['exit_date']).date(), sale_price=sale_json['exit_price'], animal_id=new_purchase.id, farm_id=new_farm.id))
                if p_json.get('death'):
                    death_json = p_json['death']
                    db.session.add(Death(date=datetime.fromisoformat(death_json['date']).date(), cause=death_json.get('cause'), animal_id=new_purchase.id, farm_id=new_farm.id))
        
        db.session.commit()
        
        if not imported_farm_names:
            return jsonify({'message': 'Import complete. No new farms were added as farms with the same names already exist.'}), 200

        return jsonify({'message': f'Successfully imported data for farms: {", ".join(imported_farm_names)}'}), 201

    except IntegrityError as e:
        db.session.rollback()
        return jsonify({'error': f'Database integrity error. This can happen if an animal ear tag/lot combination in the file already exists in the target farm. Import cancelled. Error: {str(e)}'}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An unexpected error occurred during import, and all changes have been rolled back. Error: {str(e)}'}), 500