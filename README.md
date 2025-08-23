

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

## Development Setup

Follow these instructions to set up the project for local development and testing.

### Prerequisites

Before you begin, ensure you have the following installed on your system:
*   **Python** (version 3.10 or higher)
*   **Node.js** (version 18.x or higher) and **npm**
*   **Git**

### Installation

**1. Clone the Repository**
```bash
git clone https://github.com/your-username/live_stock_manager.git
cd live_stock_manager
```

**2. Configure the Python Backend**
Follow these steps from the project's root directory (`/live_stock_manager`).

*   **Create and activate a virtual environment:**
    ```bash
    # Create the virtual environment
    python -m venv venv

    # Activate on Windows (PowerShell)
    .\venv\Scripts\Activate.ps1

    # Activate on macOS/Linux
    source venv/bin/activate
    ```

*   **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

**3. Configure the Electron Frontend**

*   **Navigate to the frontend directory:**
    ```bash
    cd frontend
    ```
*   **Install Node.js dependencies:**
    ```bash
    npm install
    ```

**4. Initialize the Database**
This is a one-time setup step to create the initial database file.

*   **Navigate back to the project's root directory.**
*   **Ensure your virtual environment (`venv`) is active.**
*   **Run the Flask shell:**
    ```bash
    flask shell
    ```
*   **Inside the shell, execute the following Python commands:**
    ```python
    from app import db
    db.create_all()
    exit()
    ```

### Running the Application for Development

To launch the application in development mode:

1.  Navigate to the `/frontend` directory.
2.  Run the start command:
    ```bash
    npm start
    ```
This will launch the Electron application window and automatically start the Python/Flask backend server in the background. The Flask server will auto-reload upon changes to the backend code.

---

## Building for Production

Follow these steps to package the application into a distributable Windows installer (`.exe`).

**1. Package the Python Backend**
*   Ensure your virtual environment is active.
*   From the **root directory**, run PyInstaller:
    ```bash
    pyinstaller bovitrack_backend.spec
    ```

**2. Copy the Backend Artifacts**
*   Delete the old contents of the `frontend/backend` directory.
*   Copy the newly created folder from `dist/bovitrack_backend` into the `frontend/backend/` directory.

**3. Build the Electron Installer**
*   **Important:** Open your terminal (PowerShell or Command Prompt) **as an Administrator**.
*   Navigate to the `frontend` directory.
*   Run the build command:
    ```bash
    npm run build
    ```

**4. Locate the Installer**
*   The final, shareable installer (e.g., `BoviTrack Setup 1.0.0.exe`) will be located in the `frontend/dist` folder.
