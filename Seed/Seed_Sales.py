import sys
import os
import pandas as pd
from datetime import datetime

# --- GPS Block ---
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(script_dir, '..')
sys.path.insert(0, project_root)

from app import create_app, db
from app.models import Purchase, Sale, Weighting # MODIFIED: Add Weighting model

# --- IMPORTANT ---
# MODIFIED: Add a mapping for the exit weight column
CSV_COLUMN_MAP = {
    'ear_tag_col': 'N° Unico',
    'lot_col': 'Lote',
    'date_col': 'Data de Saída',
    'price_col': 'Preço de Venda',
    'weight_col': 'Peso de Saída (Kg)' # NEW: Add the exit weight column name
}

# The path to your CSV file
CSV_FILE_PATH = os.path.join(project_root, 'Support', 'Sales_Artificial_Data.csv') # Adjust folder/file name if needed

def seed_sales_database():
    print(f"Reading Sales CSV data from {CSV_FILE_PATH}...")
    
    try:
        df = pd.read_csv('B:\live_stock_manager\Support\Sales_Artificial_Data.csv')
        print(f"Found {len(df)} rows in CSV.")
    except FileNotFoundError:
        print(f"Error: {CSV_FILE_PATH} not found. Aborting.")
        return

    animal_id_cache = {}
    print("Staging sale records...")

    for index, row in df.iterrows():
        try:
            ear_tag = str(int(row[CSV_COLUMN_MAP['ear_tag_col']]))
            lot = str(int(row[CSV_COLUMN_MAP['lot_col']]))
            cache_key = f"{ear_tag}-{lot}"

            # --- The Librarian Lookup ---
            animal_id = None
            if cache_key in animal_id_cache:
                animal_id, farm_id = animal_id_cache[cache_key]
            else:
                animal = Purchase.query.filter_by(ear_tag=ear_tag, lot=lot).first()
                if animal:
                    animal_id = animal.id
                    farm_id = animal.farm_id
                    animal_id_cache[cache_key] = (animal_id, farm_id)
                else:
                    print(f"  > WARNING: Animal ear_tag '{ear_tag}', lot '{lot}' not found in purchases. Skipping row {index+1}.")
                    continue

            # Create the new Sale object
            sale_date = datetime.strptime(row[CSV_COLUMN_MAP['date_col']], '%Y-%m-%d').date() # Adjust date format if needed

            # 1. Create the new Weighting record for the exit weight
            exit_weight = float(row[CSV_COLUMN_MAP['weight_col']])
            new_exit_weighting = Weighting(
                date=sale_date,
                weight_kg=exit_weight,
                animal_id=animal_id, # The crucial link
                farm_id=farm_id # Explicitly add the farm_id
            )
            db.session.add(new_exit_weighting) # Add it to the staging area

            # 2. Create the new Sale record
            new_sale = Sale(
                date=sale_date,
                sale_price=float(row[CSV_COLUMN_MAP['price_col']]),
                animal_id=animal_id, # The same crucial link
                farm_id=farm_id # Explicitly add the farm_id
            )
            db.session.add(new_sale) # Add it to the staging area

            print(f"  > Staged sale and exit weight for animal ID {animal_id}") # MODIFIED: Updated print message

        except Exception as e:
            db.session.rollback()
            print(f"  > ERROR processing row {index+1}: {e}")
            print("  > Skipping this row.")


    print("\nCommitting all staged sales and exit weights to the database...") # MODIFIED: Updated print message
    db.session.commit()
    print("Sales and exit weight seeding complete!") # MODIFIED: Updated print message


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        # IMPORTANT: We only want to clear the 'sale' table here. We do NOT want
        # to clear the 'weighting' table, as it already contains good data.
        print("Clearing existing data from the sale table...")
        db.session.query(Sale).delete()
        db.session.commit()

        seed_sales_database()