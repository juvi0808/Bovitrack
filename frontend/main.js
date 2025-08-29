
// Think of main.js as the launch control center for your entire desktop application. 
// It does not control what's inside the window (the buttons, text, etc.), 
// but it controls the window itself and its fundamental properties. 
// It's the only script that runs in the powerful "Main Process."

const { app, BrowserWindow, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process'); // Import Node.js's child process module
const http = require('http');

require('dotenv').config({ path: path.join(__dirname, '..', '.env') });  // This loads the .env file

let backendProcess = null;

// This new function combines starting the process and checking for readiness.
// It returns a Promise, which is the modern way to handle asynchronous tasks.
function startBackend() {
  return new Promise((resolve, reject) => {
    let command;
    let args;
    let options = {};

    if (app.isPackaged) {
      // --- PRODUCTION MODE ---
      console.log('Running in PRODUCTION mode.');
      // The path to the executable created by PyInstaller
      command = path.join(process.resourcesPath, 'backend', 'bovitrack_backend.exe');
      args = [];
    } else {
      // --- DEVELOPMENT MODE ---
      console.log('Running in DEVELOPMENT mode.');
      // The path to the Python interpreter in your virtual environment
      command = path.join(__dirname, '..', 'venv', 'Scripts', 'python.exe');
      const managePyPath = path.join(__dirname, '..', 'backend_django', 'manage.py');
      args = [managePyPath, 'runserver', '--noreload'];
      options.cwd = path.join(__dirname, '..', 'backend_django');
    }

    console.log(`Starting backend with command: ${command}`, args.join(' '));
    backendProcess = spawn(command, args, options);

    // Listen for errors during the spawn process itself (e.g., file not found)
    backendProcess.on('error', (err) => {
        console.error('Failed to start backend process:', err);
        reject(err); // Reject the promise if spawn fails
    });

    backendProcess.stdout.on('data', (data) => {
      console.log(`Backend stdout: ${data}`);
    });
    backendProcess.stderr.on('data', (data) => {
      console.error(`Backend stderr: ${data}`);
    });

    // --- Readiness Check ---
    const url = 'http://127.0.0.1:8000/api/farms/';
    const check = () => {
      http.get(url, (res) => {
        if (res.statusCode >= 200 && res.statusCode < 500) {
          console.log('Backend is ready!');
          resolve(); // Resolve the promise once the backend responds
        } else {
          console.log(`Backend responded with ${res.statusCode}, retrying in 500ms...`);
          setTimeout(check, 500);
        }
      }).on('error', (err) => {
        console.log('Backend not ready, retrying in 500ms...');
        setTimeout(check, 500);
      });
    };
    
    // Start checking after a short delay to give the process time to initialize.
    setTimeout(check, 1000);
  });
}


// --- Function to check if the backend is ready ---
function checkBackendReady(callback) {
  // THE FIX: Check a valid Django endpoint. The port is now 8000.
  const url = 'http://127.0.0.1:8000/api/farms/'; 
  const check = () => {
      http.get(url, (res) => {
          // A 200 OK or 404 Not Found both mean the server is running and responding.
          if (res.statusCode >= 200 && res.statusCode < 500) {
              console.log('Backend is ready!');
              callback();
          } else {
              console.log(`Backend responded with ${res.statusCode}, retrying in 500ms...`);
              setTimeout(check, 500);
          }
      }).on('error', (err) => {
          console.log('Backend not ready, retrying in 500ms...');
          setTimeout(check, 500);
      });
  };
  check();
}

const createWindow = async () => {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    }
  });

  // --- ADD THIS DEBUGGING CODE ---
  win.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
    console.error(`Failed to load page: ${errorDescription} (Code: ${errorCode})`);
    dialog.showErrorBox(
      'Page Load Error',
      `Failed to load the application page. Please contact support.\n\nError: ${errorDescription} (Code: ${errorCode})`
    );
  });

  win.webContents.on('crashed', (event, killed) => {
    console.error(`Renderer process crashed! Killed: ${killed}`);
    dialog.showErrorBox(
      'Application Error',
      'The application has encountered a critical error and must close. This might be due to a problem with dependencies.'
    );
    app.quit();
  });
  // --- END OF DEBUGGING CODE ---


  win.setAutoHideMenuBar(true)
  if (!app.isPackaged) {
    win.webContents.openDevTools();
  }
  
  // --- Wait for the backend to be fully ready before loading the file ---
  try {
    await startBackend();
    win.loadFile('index.html');

    // Send the API key to the renderer process after it has finished loading
    win.webContents.on('did-finish-load', () => {
      const apiKey = process.env.GOOGLE_MAPS_API_KEY;
      if (apiKey) {
        win.webContents.send('maps-api-key', apiKey);
      } else {
        console.error("Google Maps API key not found in .env file!");
      }
    });

  } catch (error) {
    console.error('Could not start backend, quitting app.', error);
    dialog.showErrorBox(
        'Backend Error',
        `The backend process failed to start. The application will now close.\n\nError: ${error.message}`
    );
    app.quit();
  }
};

app.whenReady().then(() => {
  startBackend(); // Start the backend first
  createWindow(); // Then create the window

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

// When the app is about to close, shut down the backend process.
app.on('will-quit', () => {
  if (backendProcess) {
      console.log('Killing backend process...');
      backendProcess.kill();
      backendProcess = null;
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
      app.quit();
  }
});