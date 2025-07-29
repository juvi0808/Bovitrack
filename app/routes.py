from flask import Blueprint, request, jsonify
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from .models import Farm, Location, Purchase, Sale, Weighting, SanitaryProtocol, LocationChange, DietLog, Death # Notice the '.' - it means "from the same package"
from . import db # Also import the db object
from .utils import find_active_animal_by_eartag, calculate_weight_history_with_gmd, calculate_location_kpis

# Create a Blueprint. 'api' is the name of the blueprint.
api = Blueprint('api', __name__)

# --- General Routes ---

@api.route('/')
def home():
    """A simple test route to confirm the API is running."""
    return "The Livestock Manager Backend is running!"

# --- Create (POST) Routes ---

@api.route('/farm/<int:farm_id>/location/add', methods=['POST'])
def add_location(farm_id):
    """
    Creates a new, named location (e.g., a pasture or module) for a specific farm.
    Expects a JSON body with a 'name' and an optional 'area_hectares'.
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

    # MODIFIED: Add 'location_id' to the list of required fields.
    required_fields = ['entry_date', 'ear_tag', 'lot', 'entry_weight', 'sex', 'entry_age', 'location_id']
    if not data or not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    # --- NEW: Validate the provided location_id ---
    location_id = data.get('location_id')
    location = Location.query.filter_by(id=location_id, farm_id=farm_id).first()
    if not location:
        return jsonify({'error': f"Location with id {location_id} not found on this farm."}), 404

    try:
        # Process incoming data.
        entry_date_obj = datetime.strptime(data['entry_date'], '%Y-%m-%d').date()
        entry_weight_val = float(data['entry_weight'])

        # --- Create THREE records in one transaction ---

        # 1. Create the main Purchase record.
        new_purchase = Purchase(
            entry_date=entry_date_obj,
            ear_tag=str(data['ear_tag']),
            lot=str(data['lot']),
            entry_weight=entry_weight_val,
            sex=data['sex'],
            entry_age=data['entry_age'],
            purchase_price=data.get('purchase_price'),
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

@api.route('/farm/<int:farm_id>/purchase/<int:purchase_id>/sanitary/add', methods=['POST'])
def add_sanitary_protocol(farm_id, purchase_id):
    """
    Adds a new sanitary protocol record to a specific animal.
    Expects a JSON body with date and protocol_type, and optional
    product_name and invoice_number.
    """
    # Find the animal and verify it belongs to the specified farm.
    animal = Purchase.query.get_or_404(purchase_id)
    if animal.farm_id != farm_id:
        return jsonify({'error': 'This animal does not belong to the specified farm.'}), 403

    data = request.get_json()
    # Validate required fields from the request body.
    required_fields = ['date', 'protocol_type']
    if not data or not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields: date and protocol_type'}), 400

    try:
        # Create the new SanitaryProtocol object.
        protocol_date_obj = datetime.strptime(data['date'], '%Y-%m-%d').date()
        new_protocol = SanitaryProtocol(
            date=protocol_date_obj,
            protocol_type=data['protocol_type'],
            product_name=data.get('product_name'),
            invoice_number=data.get('invoice_number'),
            animal_id=purchase_id,
            farm_id=farm_id
        )

        # Add and commit the new record to the database.
        db.session.add(new_protocol)
        db.session.commit()

        return jsonify({
            'message': 'Sanitary protocol recorded successfully!',
            'protocol_id': new_protocol.id
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500
    
@api.route('/farm/<int:farm_id>/purchase/<int:purchase_id>/location/add', methods=['POST'])
def add_location_change(farm_id, purchase_id):
    """
    Adds a new location change record to a specific animal.
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
    required_fields = ['date', 'location_id']
    if not data or not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields: date and location_id'}), 400
    
    # --- NEW: Verify that the provided location_id is valid for this farm ---
    location_id_to_add = data.get('location_id')
    location_to_add = Location.query.filter_by(id=location_id_to_add, farm_id=farm_id).first()
    if not location_to_add:
        return jsonify({'error': f"Location with id {location_id_to_add} not found on this farm."}), 404

    try:
        # Process incoming data.
        change_date_obj = datetime.strptime(data['date'], '%Y-%m-%d').date()

        # Create the new LocationChange object.
        new_location = LocationChange(
            date=change_date_obj,
            location_id=location_id_to_add, # Use the ID from the JSON
            animal_id=purchase_id,
            farm_id=farm_id
        )

        # Add and commit the new record to the database.
        db.session.add(new_location)
        db.session.commit()

        return jsonify({
            'message': 'Location change recorded successfully!',
            'location_change_id': new_location.id
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

    try:
        # Process incoming data.
        diet_date_obj = datetime.strptime(data['date'], '%Y-%m-%d').date()

        # Create the new DietLog object.
        new_diet = DietLog(
            date=diet_date_obj,
            diet_type=data['diet_type'],
            daily_intake_percentage=float(data['daily_intake_percentage']),
            animal_id=purchase_id,
            farm_id=farm_id
        )

        # Add and commit the new record to the database.
        db.session.add(new_diet)
        db.session.commit()

        return jsonify({
            'message': 'Diet log recorded successfully!',
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
    results = []
    for sale in all_sales:
        # Get the final weight from the animal's weight history for accuracy.
        exit_weighting = Weighting.query.filter_by(animal_id=sale.animal_id, date=sale.date).first()
        exit_weight = exit_weighting.weight_kg if exit_weighting else 0.0 # Default to 0 if not found

        # --- NEW KPI CALCULATIONS ---
        days_on_farm = (sale.date - sale.animal.entry_date).days
        
        # Calculate GMD only if the data is valid
        total_gain = exit_weight - sale.animal.entry_weight
        gmd_kg_day = (total_gain / days_on_farm) if days_on_farm > 0 and exit_weight > 0 else 0.0
        
        # Calculate exit age
        exit_age_months = sale.animal.entry_age + (days_on_farm / 30.44)

        sale_summary = {
            "sale_id": sale.id,
            "animal_id": sale.animal_id,
            "ear_tag": sale.animal.ear_tag,
            "lot": sale.animal.lot,
            "race": sale.animal.race,
            "sex": sale.animal.sex,
            "entry_date": sale.animal.entry_date.isoformat(),
            "exit_date": sale.date.isoformat(),
            "entry_weight": sale.animal.entry_weight,
            "exit_weight": exit_weight,
            "entry_price": sale.animal.purchase_price,
            "exit_price": sale.sale_price,
            "exit_age_months": round(exit_age_months, 2),
            # --- ADDED KPIs ---
            "days_on_farm": days_on_farm,
            "gmd_kg_day": round(gmd_kg_day, 3)
        }
        results.append(sale_summary)

    return jsonify(results)

@api.route('/farm/<int:farm_id>/weightings', methods=['GET'])
def get_all_weightings(farm_id):
    """
    Gets a list of all weighting records for a specific farm.
    Accepts optional 'start_date' and 'end_date' query parameters
    in YYYY-MM-DD format to filter the results by the weighing date.
    """
    # Verify the farm exists.
    Farm.query.get_or_404(farm_id)

    # Start with the base query for all weightings on this farm.
    weightings_query = Weighting.query.filter_by(farm_id=farm_id)

    try:
        # Get optional date strings from the URL's query parameters.
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        # Conditionally add filters to the query if dates are provided.
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            weightings_query = weightings_query.filter(Weighting.date >= start_date)

        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            weightings_query = weightings_query.filter(Weighting.date <= end_date)

    except ValueError:
        # Handle incorrectly formatted dates.
        return jsonify({'error': 'Invalid date format. Please use YYYY-MM-DD.'}), 400

    # Execute the final, assembled query, ordered by most recent weighing first.
    all_weightings = weightings_query.order_by(Weighting.date.desc()).all()
    
    # Convert results to a list of dictionaries and return as JSON.
    # The .to_dict() method will automatically include the ear_tag and lot.
    results = [weighting.to_dict() for weighting in all_weightings]
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
        db.joinedload(LocationChange.location)
    ).order_by(LocationChange.date.desc()).all()
    
    # Assemble the rich response.
    results = []
    for change in all_changes:
        change_summary = {
            "location_change_id": change.id,
            "date": change.date.isoformat(),
            "ear_tag": change.animal.ear_tag,
            "lot": change.animal.lot,
            "location_name": change.location.name,
            "location_id": change.location.id,
            "animal_id": change.animal_id
        }
        results.append(change_summary)

    return jsonify(results)

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
    results = []
    for protocol in all_protocols:
        protocol_summary = {
            "protocol_id": protocol.id,
            "date": protocol.date.isoformat(),
            "ear_tag": protocol.animal.ear_tag,
            "lot": protocol.animal.lot,
            "protocol_type": protocol.protocol_type,
            "product_name": protocol.product_name,
            "invoice_number": protocol.invoice_number,
            "animal_id": protocol.animal_id
        }
        results.append(protocol_summary)

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
    results = []
    for diet_log in all_diets:
        diet_summary = {
            "diet_log_id": diet_log.id,
            "date": diet_log.date.isoformat(),
            "ear_tag": diet_log.animal.ear_tag,
            "lot": diet_log.animal.lot,
            "diet_type": diet_log.diet_type,
            "daily_intake_percentage": diet_log.daily_intake_percentage,
            "animal_id": diet_log.animal_id
        }
        results.append(diet_summary)

    return jsonify(results)

@api.route('/farm/<int:farm_id>/locations', methods=['GET'])
def get_all_locations(farm_id):
    """
    Gets a list of all structured locations for a farm, enriched with
    capacity rate KPIs for each location.
    """
    Farm.query.get_or_404(farm_id)

    # 1. Get all master locations for the farm.
    all_locations = Location.query.filter_by(farm_id=farm_id).order_by(Location.name).all()
    if not all_locations:
        return jsonify([])

    # 2. Get all active animals on the farm to perform calculations.
    # This is an efficient query to get all active animal IDs.
    sold_ids = db.session.query(Sale.animal_id).filter(Sale.farm_id == farm_id)
    dead_ids = db.session.query(Death.animal_id).filter(Death.farm_id == farm_id)
    active_animals = Purchase.query.options(
        db.joinedload(Purchase.location_changes) # Pre-load location changes
    ).filter(
        Purchase.farm_id == farm_id,
        Purchase.id.notin_(sold_ids.union(dead_ids))
    ).all()

    # 3. Call the helper to do the heavy lifting.
    results = calculate_location_kpis(all_locations, active_animals)

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
    ref_date = request.args.get('date')

    # Ensure the required eartag parameter was provided.
    if not tag_to_search:
        return jsonify({'error': 'An eartag parameter is required.'}), 400

    try:
        # Call the helper function to perform the complex query logic.
        active_animals = find_active_animal_by_eartag(farm_id, tag_to_search, ref_date)
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
    
    # Determine the sale details, defaulting to null if not sold.
    sale_details_data = animal.sale.to_dict() if animal.is_sold else None

    # Assemble the final master record. The JSON structure is now always the same.
    master_record = {
        'purchase_details': animal.to_dict(),
        'sale_details': sale_details_data, # This key will always exist.
        'calculated_kpis': calculated_kpis,
        'weight_history': smart_weight_history,
        'protocol_history': [protocol.to_dict() for protocol in animal.protocols],
        'location_history': [change.to_dict() for change in animal.location_changes],
        'diet_history': [diet.to_dict() for diet in animal.diet_logs]
    }

    return jsonify(master_record)

# --- Business Intelligence (BI) and Summary Routes ---

@api.route('/farm/<int:farm_id>/lot/<lot_number>', methods=['GET'])
def get_lot_summary(farm_id, lot_number):
    """
    Gets a summary of animals within a specific lot on a farm.
    By default, it returns only ACTIVE animals.
    Accepts an optional query parameter `status` which can be 'active', 'sold', or 'all'.
    For sold animals, it includes the exit_date and sale_price.
    """
    # Verify the farm exists.
    Farm.query.get_or_404(farm_id)
    
    # Get the optional 'status' parameter from the URL, defaulting to 'active'.
    status_filter = request.args.get('status', 'active').lower()

    # Find all animals ever purchased in this lot for this farm.
    all_animals_in_lot = Purchase.query.options(
        db.joinedload(Purchase.sale)
    ).filter_by(farm_id=farm_id, lot=lot_number).all()

    if not all_animals_in_lot:
        return jsonify([])

    # Apply the Status Filter based on the query parameter.
    target_animals = []
    if status_filter == 'active':
        target_animals = [animal for animal in all_animals_in_lot if not animal.is_sold and not animal.is_dead]
    elif status_filter == 'sold':
        target_animals = [animal for animal in all_animals_in_lot if animal.is_sold]
    elif status_filter == 'dead':
        target_animals = [animal for animal in all_animals_in_lot if animal.is_dead]
    elif status_filter == 'all':
        target_animals = all_animals_in_lot
    else:
        return jsonify({'error': "Invalid status parameter. Use 'active', 'sold', or 'all'."}), 400

    # --- ENHANCED RESPONSE ASSEMBLY ---
    results = []
    for animal in target_animals:
        # Always calculate these base details.
        kpis = animal.calculate_kpis()
        purchase_details = animal.to_dict()
        
        # Start building the summary object.
        animal_summary = {**purchase_details, 'kpis': kpis}

        # If the animal is sold, add the extra sale information.
        if animal.is_sold:
            animal_summary['exit_date'] = animal.sale.date.isoformat()
            animal_summary['sale_price'] = animal.sale.sale_price
        elif animal.is_dead:
            animal_summary['death_details'] = animal.death.to_dict()
        
        results.append(animal_summary)

    return jsonify(results)

@api.route('/farm/<int:farm_id>/location/<int:location_id>/summary', methods=['GET'])
def get_location_summary(farm_id, location_id):
    """
    Gets a detailed summary for a single location, including a list of
    all active animals currently in it, each with their individual KPIs.
    """
    # Verify the farm and the location exist.
    location = Location.query.filter_by(id=location_id, farm_id=farm_id).first_or_404()

    # Find all active animals (same logic as get_all_locations)
    sold_ids = db.session.query(Sale.animal_id).filter(Sale.farm_id == farm_id)
    dead_ids = db.session.query(Death.animal_id).filter(Death.farm_id == farm_id)
    active_animals = Purchase.query.filter(
        Purchase.farm_id == farm_id,
        Purchase.id.notin_(sold_ids.union(dead_ids))
    ).all()
    
    # Filter the list of active animals to find only those currently in this location.
    animals_in_this_location = []
    for animal in active_animals:
        if animal.location_changes:
            latest_change = sorted(animal.location_changes, key=lambda lc: lc.date, reverse=True)[0]
            if latest_change.location_id == location_id:
                animals_in_this_location.append(animal)
    
    # Calculate individual KPIs for each animal in this location.
    animal_details_list = []
    for animal in animals_in_this_location:
        kpis = animal.calculate_kpis()
        purchase_details = animal.to_dict()
        animal_summary = {**purchase_details, 'kpis': kpis}
        animal_details_list.append(animal_summary)
    
    # Calculate the summary KPIs for this specific location using our helper.
    # We pass a list containing just this one location.
    location_kpis = calculate_location_kpis([location], active_animals)[0]

    # Assemble the final response.
    final_response = {
        "location_details": location_kpis,
        "animals": animal_details_list
    }

    return jsonify(final_response)

@api.route('/farm/<int:farm_id>/stock/active_summary', methods=['GET'])
def get_active_stock_summary(farm_id):
    """
    Gets a complete summary of the active stock for a specific farm.
    Returns a list of all active animals with their individual KPIs, plus
    a summary object with KPIs for the entire herd.
    """
    # Verify the farm exists.
    Farm.query.get_or_404(farm_id)

    # 1. Get IDs of all animals that have exited (sold or died).
    sold_animal_ids = db.session.query(Sale.animal_id).filter(Sale.farm_id == farm_id)
    dead_animal_ids = db.session.query(Death.animal_id).filter(Death.farm_id == farm_id)
    exited_animal_ids = sold_animal_ids.union(dead_animal_ids)

    # 2. Fetch all Purchase objects for the farm that are NOT in the exited list.
    #    We use joinedload to efficiently pre-fetch all related data we'll need for KPIs.
    active_animals = Purchase.query.options(
        db.joinedload(Purchase.sale),
        db.joinedload(Purchase.death),
        db.joinedload(Purchase.weightings)
    ).filter(
        Purchase.farm_id == farm_id,
        Purchase.id.notin_(exited_animal_ids)
    ).all()

    # 3. Calculate individual KPIs and build the detailed animal list.
    animal_details_list = []
    for animal in active_animals:
        kpis = animal.calculate_kpis()
        purchase_details = animal.to_dict()
        animal_summary = {**purchase_details, 'kpis': kpis}
        animal_details_list.append(animal_summary)

    # 4. Calculate the overall summary KPIs for the entire herd.
    total_animals = len(animal_details_list)
    if total_animals > 0:
        num_males = sum(1 for animal in animal_details_list if animal['sex'] == 'M')
        num_females = total_animals - num_males
        
        avg_age = sum(a['kpis']['current_age_months'] for a in animal_details_list) / total_animals
        avg_gmd = sum(a['kpis']['average_daily_gain_kg'] for a in animal_details_list) / total_animals
        avg_forecasted_weight = sum(a['kpis']['forecasted_current_weight_kg'] for a in animal_details_list) / total_animals

        summary_kpis = {
            "total_active_animals": total_animals,
            "number_of_males": num_males,
            "number_of_females": num_females,
            "average_age_months": round(avg_age, 2),
            "average_gmd_kg_day": round(avg_gmd, 3),
            "average_forecasted_weight_kg": round(avg_forecasted_weight, 2)
        }
    else:
        # If there are no active animals, return a default summary.
        summary_kpis = {
            "total_active_animals": 0,
            "number_of_males": 0,
            "number_of_females": 0,
            "average_age_months": 0,
            "average_gmd_kg_day": 0,
            "average_forecasted_weight_kg": 0
        }

    # 5. Assemble the final response object.
    final_response = {
        "summary_kpis": summary_kpis,
        "animals": animal_details_list
    }

    return jsonify(final_response)