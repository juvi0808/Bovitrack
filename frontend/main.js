
// Think of main.js as the launch control center for your entire desktop application. 
// It does not control what's inside the window (the buttons, text, etc.), 
// but it controls the window itself and its fundamental properties. 
// It's the only script that runs in the powerful "Main Process."

const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process'); // Import Node.js's child process module
const http = require('http');


let backendProcess = null;

function startBackend() {
    let command;
    let backendPath;

    // This is the magic switch!
    if (app.isPackaged) {
        // --- PRODUCTION MODE ---
        // In the packaged app, the executable is in the 'resources' folder
        console.log('Running in PRODUCTION mode.');
        backendPath = path.join(process.resourcesPath, 'backend', 'bovitrack_backend.exe');
        command = backendPath;
    } else {
        // --- DEVELOPMENT MODE ---
        // In development, we run the Python script directly.
        // Go up one level from 'frontend' to the project root.
        console.log('Running in DEVELOPMENT mode.');
        backendPath = path.join(__dirname, '..', 'run.py'); 
        command = 'python'; // The command is 'python', and the script is an argument
    }

    console.log(`Starting backend with command: ${command} and path: ${backendPath}`);

    // Spawn the process. The arguments are handled differently for an exe vs. a script.
    if (app.isPackaged) {
        backendProcess = spawn(command);
    } else {
        backendProcess = spawn(command, [backendPath]);
    }
    
    // The rest of the function (logging stdout/stderr) stays the same
    backendProcess.stdout.on('data', (data) => {
        console.log(`Backend stdout: ${data}`);
    });
    backendProcess.stderr.on('data', (data) => {
        console.error(`Backend stderr: ${data}`);
    });
}

// --- Function to check if the backend is ready ---
function checkBackendReady(callback) {
  const url = 'http://127.0.0.1:5000/api/'; // Use your API's base URL
  const check = () => {
      http.get(url, (res) => {
          if (res.statusCode === 200) {
              console.log('Backend is ready!');
              callback();
          } else {
              console.log('Backend not ready, retrying in 500ms...');
              setTimeout(check, 500);
          }
      }).on('error', (err) => {
          console.log('Backend not ready, retrying in 500ms...');
          setTimeout(check, 500);
      });
  };
  check();
}

const createWindow = () => {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      // These settings are still important
      nodeIntegration: true,
      contextIsolation: false,
    }
  });

  win.setAutoHideMenuBar(true)
  if (!app.isPackaged) {
    win.webContents.openDevTools();
}
  checkBackendReady(() => {
    win.loadFile('index.html');
  });
  
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