# BoviTrack - Livestock Management Application

BoviTrack is a robust, desktop-based application for efficient and detailed management of livestock operations. Built with a powerful **Python/Flask backend** and a dynamic **JavaScript/HTML/CSS frontend**, and packaged with **Electron**, it provides a true native desktop experience for farmers and managers.

The application leverages a high-performance **AG-Grid** interface for powerful data visualization, sorting, and filtering, ensuring a smooth and responsive user experience even with thousands of records.

## Core Features

BoviTrack is centered around the complete lifecycle of livestock, from acquisition to sale or loss, providing detailed tracking and analytics at every stage.

### 1. Multi-Farm Operations & Data Portability
*   **Multi-Farm Support:** Create, rename, and manage multiple distinct farm properties, keeping all data completely separate and organized.
*   **Persistent Selection:** The application intelligently remembers the last farm you were working on, providing a seamless experience across sessions.
*   **Full Import/Export:** Backup data from one or more farms to a JSON file, or use it to migrate your entire operation to a new computer.
      <img width="441" height="113" alt="image" src="https://github.com/user-attachments/assets/3e3200ee-eb01-46cd-a11a-26639fdb8eeb" />
      <img width="1920" height="1032" alt="image" src="https://github.com/user-attachments/assets/762c4b87-666f-4341-88d4-8c84b9034e59" />

### 2. Complete Animal Lifecycle Tracking
*   **Comprehensive Animal Records:** Log new animals with extensive details, including ear tag, lot, entry date, weight, age, sex, race, and purchase price.

    <img width="769" height="842" alt="image" src="https://github.com/user-attachments/assets/08c57e96-1d36-4294-a262-f37a0557f8bd" />

*   **Integrated Event Logging:** Record every key event in an animal's life, including weight checks, health protocols, diet changes, and location moves.

     <img width="764" height="319" alt="image" src="https://github.com/user-attachments/assets/443bc9af-fda2-4040-ac01-211a245c65f0" />
     <img width="766" height="502" alt="image" src="https://github.com/user-attachments/assets/e7eb4630-a936-4e7e-97fc-f697dd99d086" />

*   **Sale and Death Management:** Fully implemented workflows for recording sales and deaths, which automatically removes animals from active stock and preserves their data for historical analysis.
*   **Master Record View:** A centralized "single source of truth" for any animal, showing its complete history, performance KPIs, and a weight gain chart at a glance.
      <img width="1920" height="1032" alt="image" src="https://github.com/user-attachments/assets/4327c900-8fe4-41fe-8a33-66663f15e196" />
      <img width="1920" height="1032" alt="image" src="https://github.com/user-attachments/assets/6a3a03a1-85b4-4c9d-b0ee-92c8d28fa616" />
      <img width="1920" height="1032" alt="image" src="https://github.com/user-attachments/assets/432ed3b7-5f9d-4a6b-8f79-ace23e1b485a" />

### 3. Advanced Analytics & KPIs
*   **Real-Time Performance Metrics:** The backend automatically calculates critical KPIs for every active animal:
    *   **Average Daily Gain (GMD):** Both accumulated (since entry) and period-specific (between weightings).
    *   **Forecasted Weight:** An up-to-the-minute estimated weight based on historical performance.
    *   **Days on Farm** and **Current Age**.
      <img width="1344" height="722" alt="image" src="https://github.com/user-attachments/assets/4ba7a9b3-c4b6-46c4-8085-188fba5baa22" />

*   **Location & Pasture KPIs:** The "Locations" view provides an operational dashboard showing animal count, area, and calculated **Capacity Rates (UA/ha)** for effective pasture management.
     <img width="1344" height="722" alt="image" src="https://github.com/user-attachments/assets/e3a283a0-d4c3-4455-a4cd-8295e107f62e" />

*   **Lot Summaries:** Group animals by lot and instantly view aggregated KPIs for the entire group, including average age, average GMD, and total animal count.

### 4. User Experience & Tools
*   **Active Stock Dashboard:** A powerful and sortable main screen showing a complete summary of all active animals and their current performance.
*   **Multi-Language Support:** The interface is fully translated to support English, Spanish, and Portuguese.
*   **Interactive Demo Farm:** New users can load a pre-populated demo farm with thousands of records to immediately explore the application's features without needing to input data first.

## Technology Stack

*   **Backend:** Python 3, Flask, SQLAlchemy
*   **Frontend:** Vanilla JavaScript (ES6+), HTML5, CSS3
*   **Database:** SQLite
*   **Core UI Library:** AG-Grid Community
*   **Desktop App Framework:** Electron

## Future Development & Planned Features

BoviTrack is an evolving platform. The following features are on the development roadmap to provide even greater value:

*   **[ ] Financial Module:**
    *   Track costs associated with feed, medicine, and labor.
    *   Calculate profitability per animal and per lot, including a final profit/loss calculation upon sale.
*   **[ ] Advanced Reporting & Analytics:**
    *   Generate and export PDF/CSV reports for sales, stock summaries, and animal histories.
    *   Visual dashboards with charts for herd performance over time.
*   **[ ] Diet & Feed Management:**
    *   Create and manage different diet formulations.
    *   Track feed inventory and consumption rates to better manage costs.
*   **[ ] Advanced Location Analysis:**
    *   Provide a historical view of a location's occupancy over time to analyze pasture rotation and rest periods.
    *   Provide satelite mapping of locations, allowing users to view the location of their animals in real-time.

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
git clone https://github.com/juvi0808/Bovitrack.git
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
