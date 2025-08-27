
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
  let args;
  let options = {};

  if (app.isPackaged) {
      // --- PRODUCTION MODE ---
      console.log('Running in PRODUCTION mode.');
      const backendPath = path.join(process.resourcesPath, 'backend', 'bovitrack_backend.exe');
      command = backendPath;
      args = [];
  } else {
      // --- DEVELOPMENT MODE (THE FIX) ---
      console.log('Running in DEVELOPMENT mode.');

      // --- IMPORTANT ---
      // This path points directly to the Python executable inside your virtual environment.
      // If your virtual environment folder is named something other than "venv", change it here.
      const pythonExecutable = path.join(__dirname, '..', 'backend_django', '.venv', 'Scripts', 'python.exe');
      const managePyPath = path.join(__dirname, '..', 'backend_django', 'manage.py');

      // The command is now the full path to the correct Python.
      command = pythonExecutable; 
      args = [managePyPath, 'runserver', '--noreload'];
      options.cwd = path.join(__dirname, '..', 'backend_django');
  }

  console.log(`Starting backend with command: ${command}`, args.join(' '));

  backendProcess = spawn(command, args, options);

  backendProcess.stdout.on('data', (data) => {
      console.log(`Backend stdout: ${data}`);
  });

  backendProcess.stderr.on('data', (data) => {
      console.error(`Backend stderr: ${data}`);
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