
// Think of main.js as the launch control center for your entire desktop application. 
// It does not control what's inside the window (the buttons, text, etc.), 
// but it controls the window itself and its fundamental properties. 
// It's the only script that runs in the powerful "Main Process."

const { app, BrowserWindow } = require('electron');
const path = require('path');

const createWindow = () => {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      // This is the line that solves the problem.
      // It turns off the sandbox for the preload script, giving it full Node.js powers.
      sandbox: false,
      

      // These settings are still important
    //   preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: true,
      contextIsolation: false,
    }
  });

  win.loadFile('index.html');
  win.webContents.openDevTools();
};

app.whenReady().then(() => {
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});