const { app, BrowserWindow, shell } = require("electron");
const path = require("path");
const { spawn } = require("child_process");

/**
 * SoulCare Electron shell.
 * Spawns the local FastAPI backend so all AI stays on-device.
 */

let mainWindow = null;
let backendProcess = null;

const isDev = !app.isPackaged;
const BACKEND_HOST = process.env.SOULCARE_HOST || "127.0.0.1";
const BACKEND_PORT = process.env.SOULCARE_PORT || "8000";

function backendDir() {
  // Repo layout: soulcare-snapdragon/frontend → ../backend
  return path.join(__dirname, "..", "..", "backend");
}

function startBackend() {
  if (process.env.SOULCARE_SKIP_BACKEND === "1") {
    console.log("[SoulCare] Skipping backend spawn (SOULCARE_SKIP_BACKEND=1)");
    return;
  }

  const cwd = backendDir();
  const venvPython = process.platform === "win32"
    ? path.join(cwd, "..", ".venv", "Scripts", "python.exe")
    : path.join(cwd, "..", ".venv", "bin", "python");

  const python = require("fs").existsSync(venvPython) ? venvPython : (process.platform === "win32" ? "python" : "python3");

  backendProcess = spawn(
    python,
    ["main.py"],
    {
      cwd,
      env: {
        ...process.env,
        HOST: "127.0.0.1",
        PORT: BACKEND_PORT,
        SOULCARE_DEMO: process.env.SOULCARE_DEMO || "1",
      },
      stdio: "inherit",
    }
  );

  backendProcess.on("exit", (code) => {
    console.log(`[SoulCare] Backend exited with code ${code}`);
    backendProcess = null;
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1100,
    height: 760,
    minWidth: 840,
    minHeight: 600,
    title: "SoulCare — On-Device Mental Health Companion",
    backgroundColor: "#0f1c1a",
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  if (isDev) {
    mainWindow.loadURL(process.env.SOULCARE_UI || "http://127.0.0.1:5173");
  } else {
    mainWindow.loadFile(path.join(__dirname, "..", "dist", "index.html"));
  }

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });
}

app.whenReady().then(() => {
  startBackend();
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (backendProcess) {
    backendProcess.kill();
    backendProcess = null;
  }
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => {
  if (backendProcess) {
    backendProcess.kill();
    backendProcess = null;
  }
});
