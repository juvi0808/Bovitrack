import sys
import os
import pandas as pd
from datetime import datetime

# --- GPS Block to find the 'app' package ---
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(script_dir, '..')
sys.path.insert(0, project_root)

from app import create_app, db
# Import all models that this script will interact with, including Location
from app.models import Farm, Purchase, Weighting, Sale, SanitaryProtocol, LocationChange, DietLog, Location

# --- Mappings and Path ---
CSV_COLUMN_MAP = {
    'ear_tag_col': 'N° Brinco',
    'lot_col': 'Lote',
    'date_col': 'Data Entrada',
    'weight_col': 'Peso Entrada (Kg)',
    'sex_col': 'Sexo',
    'age_col': 'Idade Entrada (meses)',
    'price_col': 'Preço de Venda',
    'race_col': 'Raça',
    'loc_col': 'Localização'  # New column for location
}
# Use os.path.join for a robust file path
CSV_FILE_PATH = "B:\live_stock_manager\Support\Purchases_Artificial_Data.csv" # Adjust file name if needed

def seed_purchases_database():
    """
    Seeds the database with initial farm and purchase data.
    Creates a Purchase, an initial Weighting, and an initial LocationChange
    record for each row in the CSV.
    """
    # --- Get or Create the Default Farm ---
    default_farm_name = "Fazenda Principal"
    farm = Farm.query.filter_by(name=default_farm_name).first()
    if not farm:
        print(f"Creating default farm: {default_farm_name}")
        farm = Farm(name=default_farm_name)
        db.session.add(farm)
        db.session.commit()
    

    print(f"All data will be seeded into farm '{farm.name}' (ID: {farm.id}).")

    try:
        df = pd.read_csv(CSV_FILE_PATH)
        print(f"Found {len(df)} rows in CSV.")
    except FileNotFoundError:
        print(f"Error: {CSV_FILE_PATH} not found. Aborting.")
        return

    print("Staging purchase and initial event records...")
    for index, row in df.iterrows():
        try:
            # Process data from the row
            ear_tag = str(int(row[CSV_COLUMN_MAP['ear_tag_col']]))
            lot = str(int(row[CSV_COLUMN_MAP['lot_col']]))
            entry_date = datetime.strptime(row[CSV_COLUMN_MAP['date_col']], '%Y-%m-%d').date()
            entry_weight = float(row[CSV_COLUMN_MAP['weight_col']])
            race_val = row[CSV_COLUMN_MAP['race_col']]
            race = str(race_val) if not pd.isna(race_val) else None
            location = int(row[CSV_COLUMN_MAP['loc_col']]) 
            # --- Create THREE records for each row ---

            # 1. Create the Purchase record (with the entry weight)
            new_purchase = Purchase(
                entry_date=entry_date,
                ear_tag=ear_tag,
                lot=lot,
                entry_weight=entry_weight,
                sex=str(row[CSV_COLUMN_MAP['sex_col']]),
                entry_age=float(row[CSV_COLUMN_MAP['age_col']]),
                purchase_price=float(row[CSV_COLUMN_MAP['price_col']]) if not pd.isna(row[CSV_COLUMN_MAP['price_col']]) else None,
                race=race,
                farm_id=farm.id
            )
            db.session.add(new_purchase)
            db.session.flush()

            # 2. Create the corresponding initial Weighting record
            initial_weighting = Weighting(
                date=entry_date,
                weight_kg=entry_weight,
                animal_id=new_purchase.id,
                farm_id=farm.id
            )
            db.session.add(initial_weighting)

            # 3. Create the initial LocationChange record
            initial_location_change = LocationChange(
                date=entry_date,
                location_id=location, # Assign to our default location
                animal_id=new_purchase.id,
                farm_id=farm.id
            )
            db.session.add(initial_location_change)

        except Exception as e:
            db.session.rollback()
            print(f"  > ERROR processing row {index+1}: {e}")
            print("  > Skipping this row.")
    
    print("\nCommitting all staged records to the database...")
    db.session.commit()
    print("Purchase and initial event seeding complete!")

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        # --- Correct Deletion Order ---
        print("Clearing all existing data from all tables...")
        
        db.session.query(Weighting).delete()
        db.session.query(Sale).delete()
        db.session.query(SanitaryProtocol).delete()
        db.session.query(LocationChange).delete()
        db.session.query(DietLog).delete()
        
        # We don't clear Location here because it's a master table.
        # We only clear the event/log tables.
        
        db.session.query(Purchase).delete()
        
        db.session.commit()

        # Now run the main seeding function to populate the fresh tables
        seed_purchases_database()