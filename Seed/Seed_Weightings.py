import sys
import os

# This gets the absolute path of the directory the script is in (e.g., .../livestock_manager/seed)
script_dir = os.path.dirname(os.path.abspath(__file__))
# This gets the path of the parent directory (e.g., .../livestock_manager)
project_root = os.path.join(script_dir, '..')
# This adds the parent directory to Python's list of places to look for modules.
sys.path.insert(0, project_root)
# --- End of new block ---

import pandas as pd
from datetime import datetime
from app import create_app, db
from app.models import Purchase, Weighting # Import our app, db object, and Purchase model

# --- IMPORTANT ---
# Adjust these column names to EXACTLY match the headers in your seed_weightings.csv
CSV_COLUMN_MAP = {
    'ear_tag_col': 'N° Brinco',  # CHANGE THIS to your ear tag column name
    'lot_col': 'Lote',        # CHANGE THIS to your lot column name
    'date_col': 'Data',       # CHANGE THIS to your date column name
    'weight_col': 'Peso'      # CHANGE THIS to your weight column name
}

def seed_weightings_database():
    print("Reading Weightings CSV data...")
    try:
        # Read the CSV file into a pandas DataFrame.
        df = pd.read_csv('B:\live_stock_manager\Support\Weighting_Artificial_Data.csv')
        print(f"Found {len(df)} rows in CSV.")
    except FileNotFoundError:
        print("Error: seed_weightings.csv not found. Aborting.")
        return # Stop the function if the file doesn't exist.

    # This is a cache to store animal IDs we've already looked up.
    # It dramatically speeds up the script by avoiding repeated database queries for the same animal.
    animal_id_cache = {}

    print("Staging weighting records...")
    # Loop through each row in the DataFrame (our CSV data).
    for index, row in df.iterrows():
        try:
            ear_tag = str(row[CSV_COLUMN_MAP['ear_tag_col']])
            lot = str(row[CSV_COLUMN_MAP['lot_col']])
            cache_key = f"{ear_tag}-{lot}" # A unique key for our cache dictionary

            # --- The "Librarian Lookup" Process ---
            animal_id = None
            if cache_key in animal_id_cache:
                # Get the TUPLE of (animal_id, farm_id) from the cache
                animal_id, farm_id = animal_id_cache[cache_key]
            else:
                # If it's a new animal, query the database to find its purchase record.
                animal = Purchase.query.filter_by(ear_tag=ear_tag, lot=lot).first()
                if animal:
                    # Store a TUPLE of (animal_id, farm_id) in the cache
                    animal_id = animal.id
                    farm_id = animal.farm_id
                    animal_id_cache[cache_key] = (animal_id, farm_id)
                else:
                    # ...if not, print a warning and skip to the next row in the CSV.
                    print(f"  > WARNING: Animal ear_tag '{ear_tag}', lot '{lot}' not found in purchases. Skipping row {index+1}.")
                    continue

            # --- Create the New Weighting Object ---
            # Convert the date string from the CSV to a real Python date object.
            # Remember to change '%Y-%m-%d' if your CSV date format is different!
            weighting_date = datetime.strptime(row[CSV_COLUMN_MAP['date_col']], '%Y-%m-%d').date()

            new_weighting = Weighting(
                date=weighting_date,
                weight_kg=float(row[CSV_COLUMN_MAP['weight_col']]),
                animal_id=animal_id, # Here is the crucial link!
                farm_id=farm_id # Explicitly add the farm_id
            )
            # Add the new object to the "staging area" (the session).
            db.session.add(new_weighting)

        except Exception as e:
            print(f"  > ERROR processing row {index+1}: {e}")
            print("  > Skipping this row.")

    # After the loop finishes, commit all the staged records to the database at once.
    print("\nCommitting all staged weightings to the database...")
    db.session.commit()
    print("Weighting seeding complete!")

# --- This is the code that actually runs the function ---
if __name__ == '__main__':
    app = create_app() # Create an app instance
    # The 'with app.app_context()' part is crucial. It makes our script
    # aware of the Flask application's settings, especially the database connection.
    # Without it, our script wouldn't know which database to talk to.
    with app.app_context(): # Use the context from that instance
        # First, clear out any old data from the weighting table to start fresh.
        print("Clearing existing data from the weighting table...")
        #db.session.query(Weighting).delete()
        db.session.commit()

        # Now, run our main seeding function.
        seed_weightings_database()