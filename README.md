# Livestock Manager Backend

This folder contains the backend source code for the Livestock Manager application.
It is built using Python and the Flask framework.

---

## 1. Initial Project Setup

These steps only need to be performed once when setting up the project on a new machine.

1.  **Create a Virtual Environment:**
    From the project's root directory (`livestock_manager/`), run:
    ```bash
    python -m venv venv
    ```

2.  **Activate the Virtual Environment:**
    *   On Windows:
        ```bash
        .\venv\Scripts\activate
        ```
    *   On macOS/Linux:
        ```bash
        source venv/bin/activate
        ```

3.  **Install Dependencies:**
    Install all required Python packages from the `requirements.txt` file.
    ```bash
    pip install -r requirements.txt
    ```

---

## 2. Database Management

The application's database is a SQLite file located at `instance/database.db`. The tables and columns are defined as classes (models) in `app/models.py`.

### A. Initial Database Creation

Perform these steps once to create a brand new, empty database with all the required tables.

**Warning:** This process is for a fresh setup. If `instance/database.db` already exists, these steps are not necessary.

1.  Make sure your virtual environment is active.
2.  Open the Flask shell, which loads the application context:
    ```bash
    flask shell
    ```
3.  Inside the shell (`>>>`), import the `db` object and run the creation command. This reads your models and creates the physical tables in the database file.
    ```python
    >>> db.create_all()
    >>> exit()
    ```

### B. Adding a New Table to an Existing Database

Use this process when you have added a **new model class** to `app/models.py` and need to add the corresponding new table to your database **without deleting existing data**.

1.  Make sure your virtual environment is active.
2.  **Make sure you saved the changes in models.py before opening tha flask shell**
3.  Open the Flask shell:
    ```bash
    flask shell
    ```
4.  Run the `db.create_all()` command. SQLAlchemy is smart enough to see which tables already exist and will only create the new, missing ones. Your existing data will not be affected.
    ```python
    >>> db.create_all()
    >>> exit()
    ```
    
### C. Seeding the Database with Test Data

Use this process to populate the tables with artificial data from the project's CSV files. It's safe to run these multiple times, as each script first clears its corresponding table. Run these commands from the project's root directory.

1.  Seed animal purchases:
    ```bash
    python seed/seed.py
    ```
2.  Seed historical weightings:
    ```bash
    python seed/seed_weightings.py
    ```
3.  Seed historical sales (which also adds exit weights):
    ```bash
    python seed/seed_sales.py
    ```

**Note on Modifying Existing Tables:**
The `db.create_all()` command can only create new tables. It **cannot** modify existing ones (e.g., add or remove a column). For that, the simplest development workflow is to delete the `instance/database.db` file and recreate it from scratch using the steps in section A, then re-seed the data.

---```

## 3. Running the Application

To run the Flask development server:

1.  Activate the virtual environment.
2.  Run the application:
    ```bash
    python run.py
    ```
3.  The API will be accessible at `http://127.0.0.1:5000`.