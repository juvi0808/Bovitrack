import sys
import os
import pandas as pd
from datetime import datetime

# --- GPS Block ---
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(script_dir, '..')
sys.path.insert(0, project_root)

from app import create_app, db
from app.models import Purchase, DietLog # Import the correct model

# --- IMPORTANT ---
# Adjust these column names to EXACTLY match the headers in your seed_diets.csv
CSV_COLUMN_MAP = {
    'ear_tag_col': 'N° Brinco',  
    'lot_col': 'Lote',
    'date_col': 'Data',
    'type_col': 'Tipo de Dieta',
    'intake_col': 'Consumo %'
}

# The path to your CSV file
CSV_FILE_PATH = "B:\live_stock_manager\Support\Diet_Artificial_Data.csv" # Adjust file name if needed

def seed_diets_database():
    print(f"Reading Diet Log CSV data from {CSV_FILE_PATH}...")
    try:
        df = pd.read_csv(CSV_FILE_PATH)
        print(f"Found {len(df)} rows in CSV.")
    except FileNotFoundError:
        print(f"Error: {CSV_FILE_PATH} not found. Aborting.")
        return

    animal_id_cache = {}
    print("Staging diet log records...")

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
                    print(f"  > WARNING: Animal ear_tag '{ear_tag}', lot '{lot}' not found. Skipping row {index+1}.")
                    continue

            # Create the new DietLog object
            diet_date = datetime.strptime(row[CSV_COLUMN_MAP['date_col']], '%Y-%m-%d').date() # Adjust date format if needed

            new_diet_log = DietLog(
                date=diet_date,
                diet_type=str(row[CSV_COLUMN_MAP['type_col']]),
                daily_intake_percentage=float(row[CSV_COLUMN_MAP['intake_col']]),
                animal_id=animal_id,
                farm_id=farm_id # Explicitly add the farm_id
            )
            db.session.add(new_diet_log)

        except Exception as e:
            db.session.rollback()
            print(f"  > ERROR processing row {index+1}: {e}")
            print("  > Skipping this row.")

    print("\nCommitting all staged diet log records to the database...")
    db.session.commit()
    print("Diet log seeding complete!")

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        print("Clearing existing data from the diet_log table...")
        db.session.query(DietLog).delete()
        db.session.commit()

        seed_diets_database()
