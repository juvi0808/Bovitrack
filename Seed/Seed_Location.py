import sys
import os
import pandas as pd
from datetime import datetime

# --- GPS Block ---
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(script_dir, '..')
sys.path.insert(0, project_root)

from app import create_app, db
# Import only the models needed for this script
from app.models import Purchase, LocationChange, Farm

# --- Mappings and Path for the Location Changes CSV ---
CSV_COLUMN_MAP = {
    'ear_tag_col': 'N° Brinco',
    'lot_col': 'Lote',
    'date_col': 'Data',
    'location_id_col': 'Location ID', # The column with the ID of the master location
    'sublocation_id_col': 'Sublocation ID'
}
# The path to your CSV file
CSV_FILE_PATH = "B:\live_stock_manager\Support\Location_Artificial_Data.csv" # Adjust file name

def seed_location_changes_database():
    """
    Seeds the database with the historical log of animal location changes.
    """
    print(f"Reading Location Changes CSV data from {CSV_FILE_PATH}...")
    try:
        df = pd.read_csv(CSV_FILE_PATH)
        print(f"Found {len(df)} rows in CSV.")
    except FileNotFoundError:
        print(f"Error: {CSV_FILE_PATH} not found. Aborting.")
        return

    # Cache for animal lookups to improve performance
    animal_id_cache = {}
    print("Staging location change records...")

    for index, row in df.iterrows():
        try:
            # Get animal identifiers from the CSV
            ear_tag = str(int(row[CSV_COLUMN_MAP['ear_tag_col']]))
            lot = str(int(row[CSV_COLUMN_MAP['lot_col']]))
            cache_key = f"{ear_tag}-{lot}"

            # --- Animal Lookup (The Librarian Lookup) ---
            animal_id, farm_id = None, None
            if cache_key in animal_id_cache:
                animal_id, farm_id = animal_id_cache[cache_key]
            else:
                animal = Purchase.query.filter_by(ear_tag=ear_tag, lot=lot).first()
                if animal:
                    animal_id = animal.id
                    farm_id = animal.farm_id
                    animal_id_cache[cache_key] = (animal_id, farm_id)
                else:
                    print(f"  > WARNING: Animal ear_tag '{ear_tag}', lot '{lot}' not found. Skipping row {index+1}.")
                    continue

                        # --- THE FIX: Gracefully handle empty sublocation IDs ---
            sublocation_id_raw = row[CSV_COLUMN_MAP['sublocation_id_col']]
            
            # Use pd.isna() to check for NaN (missing) values
            if pd.isna(sublocation_id_raw):
                final_sublocation_id = None # Use Python's None for database NULL
            else:
                final_sublocation_id = int(sublocation_id_raw) # It's safe to convert
            
            # --- Create the LocationChange object ---
            change_date = datetime.strptime(row[CSV_COLUMN_MAP['date_col']], '%Y-%m-%d').date()

            new_location_change = LocationChange(
                date=change_date,
                location_id=int(row[CSV_COLUMN_MAP['location_id_col']]),
                sublocation_id=final_sublocation_id,
                animal_id=animal_id,
                farm_id=farm_id
            )
            db.session.add(new_location_change)

        except Exception as e:
            db.session.rollback()
            print(f"  > ERROR processing row {index+1}: {e}")
            print("  > Skipping this row.")

    print("\nCommitting all staged location change records to the database...")
    db.session.commit()
    print("Location change seeding complete!")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        # This script should only clear its own table.
        print("Clearing existing data from the location_change table...")
        #db.session.query(LocationChange).delete()
        db.session.commit()

        seed_location_changes_database()