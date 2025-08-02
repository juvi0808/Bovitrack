
---

# BoviTrack - Livestock Management Application

BoviTrack is a robust, desktop-based application designed for efficient and detailed management of livestock operations. Built with a powerful **Python/Flask backend** and a dynamic **JavaScript/HTML/CSS frontend**, it provides farmers and managers with the tools to track individual animal performance, manage resources, and gain key insights into their herd's productivity.

The application leverages an **AG-Grid** interface for powerful data visualization and interaction, ensuring a smooth and responsive user experience.



## Core Features

BoviTrack is centered around the complete lifecycle of livestock, from acquisition to sale, providing detailed tracking at every stage.

### 1. Multi-Farm Management
*   **Create, Rename, and Delete Farms:** The system is designed to handle multiple distinct farm properties, keeping all data completely separate and organized.
*   **Persistent Selection:** The application intelligently remembers the last farm you were working on, providing a seamless experience across sessions.

### 2. Comprehensive Animal Records
*   **Detailed Purchase Entry:** Record new animals with extensive details, including ear tag, lot number, entry date, weight, age, sex, race, and purchase price.
*   **Initial Location & Health Protocols:** Assign an initial pasture or module and log all sanitary protocols administered at the time of purchase in a single, streamlined workflow.
*   **Full Historical View:** Access a complete history for every animal, including every weighting, location change, health treatment, and diet log.

### 3. Key Performance Indicator (KPI) Tracking
The backend automatically calculates critical performance metrics in real-time:
*   **Average Daily Gain (GMD):** Both overall (since entry) and period-specific (between weightings).
*   **Current & Forecasted Weight:** Get an up-to-the-minute estimated weight for any animal based on its historical GMD.
*   **Days on Farm & Current Age:** Instantly know how long an animal has been on the property and its current age in months.

### 4. Resource & Stock Management
*   **Active Stock Dashboard:** A centralized view of all active animals on the farm, complete with their individual KPIs and a herd-level summary (total animals, average age, average GMD).
*   **Location Management:** Define and manage distinct locations (e.g., pastures, modules) and view location-specific KPIs like animal count and capacity rates.
*   **Efficient Data Entry:** The "Add Purchase" form is optimized for power users, remembering sanitary protocols from the previous entry and keeping the form open to allow for rapid recording of entire lots.

## Technology Stack

*   **Backend:** Python 3, Flask, SQLAlchemy (for ORM), Flask-CORS
*   **Frontend:** Vanilla JavaScript (ES6+), HTML5, CSS3
*   **Database:** SQLite (for ease of setup and portability)
*   **Core UI Library:** AG-Grid Community for powerful and feature-rich data tables.
*   **Desktop App Framework:** Electron (as implied by the file structure)

## Future Development & Planned Features

BoviTrack is an evolving platform. The following features are on the development roadmap to provide even greater value:

*   **[ ] Financial Module:**
    *   Track costs associated with feed, medicine, and labor.
    *   Calculate profitability per animal and per lot.
    *   Generate financial summary reports.
*   **[ ] Diet & Feed Management:**
    *   Create and manage different diet formulations.
    *   Track feed inventory and consumption rates.
*   **[ ] Location KPIs & History:**
    *   Detailed historical view of a location's occupancy over time.
    *   Calculate total weight and animal units (UA) per pasture.
*   **[ ] Advanced Reporting & Analytics:**
    *   Generate and export PDF/CSV reports for sales, stock summaries, and animal histories.
    *   Visual dashboards with charts and graphs for herd performance over time.
*   **[ ] Death & Sale Records:**
    *   Fully implement forms and history pages for recording animal sales and deaths, which will automatically move them from the "Active Stock" view.

---

## Developer Instructions

Follow these instructions to set up and run the BoviTrack application in a development environment.

### 1. Initial Project Setup

These steps only need to be performed once.

1.  **Create a Virtual Environment:**
    From the project's root directory (`BoviTrack/`), run:
    ```bash
    python -m venv venv
    ```

2.  **Activate the Virtual Environment:**
    *   On Windows (PowerShell):
        ```bash
        .\venv\Scripts\Activate.ps1
        ```
    *   On macOS/Linux:
        ```bash
        source venv/bin/activate
        ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### 2. Database Management

1.  **First-Time Database Creation:** To create the initial `database.db` file and all its tables, open a terminal with the virtual environment activated and run:
    ```bash
    flask shell
    ```
    Inside the shell, run these commands:
    ```python
    >>> from app import db
    >>> db.create_all()
    >>> exit()
    ```

2.  **Seeding with Test Data:** To populate the database with sample data, run the seed scripts from the root directory:
    ```bash
    python Seed/Seed_Location.py
    python Seed/Seed_Purchases.py
    python Seed/Seed_Weightings.py
    # ... and other seed scripts
    ```

### 3. Running the Application

1.  Ensure your virtual environment is active.
2.  Start the Flask backend server:
    ```bash
    python run.py
    ```
    The API will now be running at `http://127.0.0.1:5000`.

3.  To launch the frontend, you will need to run the Electron application (details depend on the `package.json` setup, but typically involves `npm start`).

---
