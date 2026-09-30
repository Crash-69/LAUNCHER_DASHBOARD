#!/usr/bin/env python3
"""Launcher locale per le applicazioni presenti nel workspace Progetto_AI."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from dataclasses import dataclass
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


# Il launcher vive in una sottocartella; le app restano nella radice del workspace.
LAUNCHER_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = LAUNCHER_DIR.parent
LOGO_PATH = WORKSPACE_DIR / "Logo_BCDIGITAL.png"
HOST = "127.0.0.1"
DASHBOARD_PORTS = range(8040, 8050)
INLAY_METADATA_PATH = Path.home() / ".inlay-studio" / "launcher.json"
INLAY_DEFAULT_DISTRO = "Ubuntu-24.04"


@dataclass(frozen=True)
class AppConfig:
    """Descrive in modo immutabile un'applicazione avviabile dalla dashboard."""

    app_id: str
    title: str
    category: str
    icon: str
    description: str
    folder: Path
    script: Path | None
    port: int | None = None
    url: str | None = None
    interpreter: Path | None = None
    runner: str = "python"
    opens_browser: bool = False


# Le descrizioni sono state ricavate dai README disponibili e, dove assenti,
# dall'entry point e dall'interfaccia delle applicazioni.
APPS = (
    AppConfig(
        app_id="pdf",
        title="Estrattore PDF AI",
        category="Documenti e AI",
        icon="PDF",
        description=(
            "Estrae dati da PDF con PyMuPDF o RapidOCR e li struttura in JSON "
            "tramite Ollama. La webapp nativa espone parametri, anteprima ed export."
        ),
        folder=WORKSPACE_DIR / "Estrae_testo_da_Pdf_richiama_Ollama",
        script=WORKSPACE_DIR / "Estrae_testo_da_Pdf_richiama_Ollama" / "estrattore_pdf_webapp.py",
        port=8020,
        url="http://127.0.0.1:8020/",
        opens_browser=True,
    ),
    AppConfig(
        app_id="jarvis",
        title="Jarvis2",
        category="Assistente locale",
        icon="J2",
        description=(
            "Assistente AI locale con webapp, strumenti documentali e integrazione "
            "SecureVault. Avvio tramite run_webapp.py nell'ambiente virtuale del progetto."
        ),
        folder=WORKSPACE_DIR / "Jarvis2",
        script=WORKSPACE_DIR / "Jarvis2" / "run_webapp.py",
        port=8008,
        url="http://127.0.0.1:8008/",
        interpreter=WORKSPACE_DIR / "Jarvis2" / ".venv" / "Scripts" / "python.exe",
    ),
    AppConfig(
        app_id="youtube",
        title="Trascrizioni YouTube",
        category="Media e trascrizioni",
        icon="YT",
        description=(
            "Webapp Streamlit per acquisire sottotitoli da video e playlist YouTube, "
            "ripulire il testo e salvare trascrizioni Markdown."
        ),
        folder=WORKSPACE_DIR / "Script_Python_Scarica_Testi_youtube",
        script=WORKSPACE_DIR / "Script_Python_Scarica_Testi_youtube" / "app.py",
        port=8501,
        url="http://127.0.0.1:8501/",
        runner="streamlit",
    ),
    AppConfig(
        app_id="securevault",
        title="SecureVault",
        category="Sicurezza file",
        icon="SV",
        description=(
            "Protegge file e cartelle in archivi ZIP cifrati o container SecureVault. "
            "Versione desktop locale Python, senza dipendenze esterne."
        ),
        folder=WORKSPACE_DIR / "SecureVault",
        script=WORKSPACE_DIR / "SecureVault" / "securevault_app.py",
        port=8010,
        url="http://127.0.0.1:8010/",
        opens_browser=True,
    ),
    AppConfig(
        app_id="cedolino",
        title="Verifica Cedolino",
        category="Strumenti HR",
        icon="HR",
        description=(
            "Interfaccia desktop per validare e normalizzare il mapping dei campi "
            "dei cedolini da file TXT, con riepiloghi ed esportazione dei risultati."
        ),
        folder=WORKSPACE_DIR / "VerificaCedolino",
        script=WORKSPACE_DIR / "VerificaCedolino" / "validate_ced_mapping_gui.py",
    ),
    AppConfig(
        app_id="uniemens",
        title="Diagnostics Uniemens",
        category="Flussi Uniemens",
        icon="UNI",
        description=(
            "Dashboard di diagnostica per monitorare workflow, verificare gli endpoint "
            "e avviare le operazioni di controllo dei flussi Uniemens."
        ),
        folder=(
            WORKSPACE_DIR
            / "APP Uniemens"
            / "stitch_flussi_uniemens"
            / "test_prototipo_dashboard"
        ),
        script=(
            WORKSPACE_DIR
            / "APP Uniemens"
            / "stitch_flussi_uniemens"
            / "test_prototipo_dashboard"
            / "code_V12_P3_OK_Color_7.htm"
        ),
        port=8021,
        url=(
            "http://127.0.0.1:8021/"
            "code_V12_P3_OK_Color_7.htm"
        ),
        runner="static",
    ),
    AppConfig(
        app_id="certificati",
        title="Monitoraggio Estrazione CF",
        category="Certificati e workflow",
        icon="CF",
        description=(
            "Monitora il workflow n8n per l'estrazione di Codice Fiscale, Cessione e Delega, "
            "con diagnostica e azioni rapide."
        ),
        folder=(
            WORKSPACE_DIR
            / "Porting APP Chiusura Certificati"
            / "stitch_flussi_uniemens"
            / "test_prototipo_dashboard"
        ),
        script=(
            WORKSPACE_DIR
            / "Porting APP Chiusura Certificati"
            / "stitch_flussi_uniemens"
            / "test_prototipo_dashboard"
            / "code.html"
        ),
        port=8022,
        url="http://127.0.0.1:8022/code.html",
        runner="static",
    ),
    AppConfig(
        app_id="inlaystudio",
        title="Inlay Studio",
        category="Sviluppo e automazione",
        icon="IN",
        description=(
            "Ambiente Inlay Studio locale su WSL e Podman per workspace, strumenti e "
            "workflow di sviluppo."
        ),
        folder=WORKSPACE_DIR / "InlayStudio",
        script=None,
        port=3002,
        url="http://localhost:3002",
        runner="inlay",
    ),
)

APP_BY_ID = {app.app_id: app for app in APPS}
PROCESS_LOCK = threading.RLock()
MANAGED_PROCESSES: dict[str, subprocess.Popen[bytes]] = {}


# L'interfaccia riprende dal webapp PDF il fondo chiaro, le card bianche,
# la tipografia di sistema e l'accento verde usato per le azioni principali.
HTML_TEMPLATE = r"""<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#f5f5f5">
  <title>Progetto AI | Launcher locale</title>
  <style>
    :root {
      color-scheme: light;
      --canvas: #f5f5f5;
      --surface: #ffffff;
      --ink: #0f172a;
      --muted: #64748b;
      --line: #e2e8f0;
      --green: #059669;
      --green-dark: #047857;
      --green-wash: rgba(5, 150, 105, 0.07);
      --navy: #0f172a;
      --red: #dc2626;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background: var(--canvas);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
    }
    .shell { max-width: 1120px; margin: 0 auto; padding: 44px 26px 34px; }
    .masthead { display: flex; align-items: center; gap: 16px; margin-bottom: 30px; }
    .mark {
            width: 72px; height: 48px; flex: 0 0 72px; overflow: hidden;
            border: 1px solid rgba(0,0,0,.12); border-radius: 10px; background: #05080b;
            box-shadow: 0 4px 12px rgba(0,0,0,.08);
    }
        .mark img { display: block; width: 100%; height: 100%; object-fit: contain; }
    .eyebrow { margin: 0 0 5px; color: var(--green-dark); font-size: 11px; font-weight: 700; letter-spacing: 0; text-transform: uppercase; }
    h1 { margin: 0; color: var(--ink); font-size: 28px; line-height: 1.2; font-weight: 700; }
    .intro { margin: 8px 0 0; max-width: 680px; color: var(--muted); font-size: 14px; line-height: 1.55; }
    .toolbar {
      display: flex; align-items: center; justify-content: space-between; gap: 16px;
      margin: 0 0 16px; padding: 0 2px;
    }
    .section-title { margin: 0; font-size: 15px; font-weight: 650; }
    .system-status { display: flex; align-items: center; gap: 8px; color: var(--muted); font-size: 12px; }
    .system-dot { width: 8px; height: 8px; border-radius: 50%; background: #10b981; }
    .grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
    .app-card {
      display: flex; flex-direction: column; min-height: 244px; padding: 22px;
      border: 1px solid rgba(0,0,0,.06); border-radius: 20px; background: var(--surface);
      box-shadow: 0 2px 12px rgba(0,0,0,.03); transition: border-color .18s, transform .18s, box-shadow .18s;
    }
    .app-card:hover { transform: translateY(-2px); border-color: #cbd5e1; box-shadow: 0 8px 22px rgba(15,23,42,.07); }
    .card-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
    .app-mark {
      width: 44px; height: 44px; display: grid; place-items: center; flex: 0 0 44px;
      border-radius: 13px; background: var(--green-wash); color: var(--green-dark);
    font-size: 12px; font-weight: 800; letter-spacing: 0;
    }
    .category {
      max-width: 60%; padding: 6px 9px; border: 1px solid var(--line); border-radius: 999px;
      color: var(--muted); font-size: 10px; font-weight: 650; line-height: 1.2; text-align: right;
    }
    .app-card h3 { margin: 17px 0 7px; font-size: 18px; line-height: 1.3; }
    .description { margin: 0; color: #475569; font-size: 13px; line-height: 1.55; }
    .card-meta { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: auto; padding-top: 19px; }
    .state { display: inline-flex; align-items: center; gap: 7px; min-width: 0; color: var(--muted); font-size: 11px; }
    .state-dot { width: 7px; height: 7px; flex: 0 0 7px; border-radius: 50%; background: #94a3b8; }
    .state[data-state="running"], .state[data-state="external"] { color: var(--green-dark); }
    .state[data-state="running"] .state-dot, .state[data-state="external"] .state-dot { background: #10b981; }
    .state[data-state="error"] { color: var(--red); }
    .state[data-state="error"] .state-dot { background: #ef4444; }
    .port { overflow: hidden; color: #94a3b8; font: 11px/1.4 Consolas, "Courier New", monospace; text-overflow: ellipsis; white-space: nowrap; }
    .actions { display: flex; gap: 8px; margin-top: 13px; }
    button {
      min-height: 40px; border: 0; border-radius: 11px; padding: 0 14px;
      font: inherit; font-size: 12px; font-weight: 650; cursor: pointer; transition: background .15s, transform .15s;
    }
    button:focus-visible { outline: 3px solid rgba(5,150,105,.25); outline-offset: 2px; }
    button:active { transform: scale(.98); }
    .primary { flex: 1; background: var(--green); color: #fff; box-shadow: 0 4px 12px rgba(5,150,105,.16); }
    .primary:hover { background: var(--green-dark); }
    .app-card[data-app="inlaystudio"] .primary { background: #d63384; box-shadow: 0 4px 12px rgba(214,51,132,.24); }
    .app-card[data-app="inlaystudio"] .primary:hover { background: #b02a6f; }
    .app-card[data-app="inlaystudio"] .primary:focus-visible { outline-color: rgba(214,51,132,.38); }
    .secondary { background: var(--navy); color: #fff; }
    .secondary:hover { background: #1e293b; }
    .stop { background: #fff; border: 1px solid #fecaca; color: var(--red); }
    .stop:hover { background: #fef2f2; }
    button:disabled { cursor: wait; opacity: .65; }
    .notice {
      min-height: 20px; margin: 15px 2px 0; color: var(--muted); font-size: 12px; line-height: 1.5;
    }
    .footer { display: flex; justify-content: space-between; gap: 16px; margin-top: 24px; color: #94a3b8; font-size: 11px; }
    @media (max-width: 720px) {
      .shell { padding: 28px 16px 24px; }
      .grid { grid-template-columns: 1fr; gap: 12px; }
      .app-card { min-height: 225px; padding: 19px; }
      .toolbar { align-items: flex-start; }
    }
    @media (max-width: 420px) {
      .masthead { align-items: flex-start; gap: 12px; }
    .mark { width: 60px; height: 40px; flex-basis: 60px; border-radius: 8px; }
      h1 { font-size: 23px; }
      .system-status { font-size: 0; gap: 0; }
      .system-dot { width: 9px; height: 9px; }
      .card-meta { align-items: flex-start; flex-direction: column; gap: 7px; }
      .port { max-width: 100%; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <header class="masthead">
    <div class="mark"><img src="/logo.png" alt="BCDIGITAL" /></div>
      <div>
        <p class="eyebrow">Ambiente locale · Progetto_AI</p>
        <h1>Launcher applicazioni</h1>
        <p class="intro">Un punto di accesso alle webapp e agli strumenti del workspace, avviati ciascuno nel proprio processo.</p>
      </div>
    </header>
    <div class="toolbar">
      <h2 class="section-title">Applicazioni disponibili</h2>
      <div class="system-status"><span class="system-dot"></span> Solo accesso locale</div>
    </div>
    <section class="grid" aria-label="Applicazioni">
      __CARDS__
    </section>
    <p id="notice" class="notice" role="status" aria-live="polite"></p>
    <footer class="footer"><span>Server dashboard: __DASHBOARD_URL__</span><span>Processi avviati in background</span></footer>
  </main>
  <script>
    const notice = document.getElementById('notice');
    const names = Object.fromEntries([...document.querySelectorAll('.app-card')].map(card => [card.dataset.app, card.querySelector('h3').textContent]));

    function updateCard(app) {
      const card = document.querySelector(`[data-app="${app.id}"]`);
      if (!card) return;
      const state = card.querySelector('.state');
      const button = card.querySelector('[data-action="start"]');
      const stop = card.querySelector('[data-action="stop"]');
      state.dataset.state = app.state;
      state.lastChild.textContent = app.state_label;
      button.textContent = app.state === 'running' || app.state === 'external' ? 'Apri applicazione' : (app.is_gui ? 'Avvia finestra' : 'Avvia applicazione');
      stop.hidden = !app.can_stop;
      button.disabled = false;
    }

    async function refreshStatus() {
      try {
        const response = await fetch('/api/apps', { cache: 'no-store' });
        const apps = await response.json();
        apps.forEach(updateCard);
      } catch (_) {
        notice.textContent = 'Impossibile aggiornare lo stato delle applicazioni.';
      }
    }

    document.addEventListener('click', async event => {
      const button = event.target.closest('button[data-action]');
      if (!button) return;
      const card = button.closest('.app-card');
      const appId = card.dataset.app;
      const action = button.dataset.action;
      const endpoint = action === 'stop' ? `/api/stop/${appId}` : `/api/start/${appId}`;
      button.disabled = true;
      notice.textContent = action === 'stop' ? `Arresto di ${names[appId]}...` : `Avvio di ${names[appId]}...`;
      try {
        const response = await fetch(endpoint, { method: 'POST' });
        const result = await response.json();
        notice.textContent = result.message;
        await refreshStatus();
      } catch (_) {
        notice.textContent = 'Richiesta non riuscita. Verifica che il launcher sia ancora attivo.';
      } finally {
        button.disabled = false;
      }
    });

    refreshStatus();
    window.setInterval(refreshStatus, 2500);
  </script>
</body>
</html>"""


def _port_is_open(port: int) -> bool:
    """Restituisce True se un processo accetta connessioni sulla porta locale."""
    try:
        with socket.create_connection((HOST, port), timeout=0.25):
            return True
    except OSError:
        return False


def _http_is_available(url: str) -> bool:
    """Controlla se sulla porta risponde un server HTTP, anche con errore HTTP."""
    try:
        with urllib.request.urlopen(url, timeout=1.0):
            return True
    except urllib.error.HTTPError:
        return True
    except (OSError, urllib.error.URLError, TimeoutError):
        return False


def _get_state(app: AppConfig) -> dict[str, Any]:
    """Calcola lo stato del processo gestito o del servizio già presente sulla porta."""
    port, url, _ = _app_runtime_details(app)
    with PROCESS_LOCK:
        process = MANAGED_PROCESSES.get(app.app_id)
        if process is not None:
            return_code = process.poll()
            if return_code is None:
                return {
                    "state": "running",
                    "state_label": "Avvio WSL in corso" if app.runner == "inlay" else "Avviata da questa dashboard",
                    "can_stop": app.runner != "inlay",
                }
            MANAGED_PROCESSES.pop(app.app_id, None)

    if url and _http_is_available(url):
        return {"state": "external", "state_label": "Servizio già attivo", "can_stop": False}
    if port is not None and _port_is_open(port):
        return {"state": "busy", "state_label": "Porta occupata da un altro processo", "can_stop": False}

    return {"state": "stopped", "state_label": "Non avviata", "can_stop": False}


def _app_payload(app: AppConfig) -> dict[str, Any]:
    """Prepara i dati minimali mostrati dalla pagina e dal suo aggiornamento periodico."""
    state = _get_state(app)
    _, url, _ = _app_runtime_details(app)
    return {
        "id": app.app_id,
        "state": state["state"],
        "state_label": state["state_label"],
        "can_stop": state["can_stop"],
        "is_gui": url is None,
    }


def _app_runtime_details(app: AppConfig) -> tuple[int | None, str | None, str]:
    """Risolve porta, URL e distro WSL, usando il metadata Inlay se disponibile."""
    port = app.port
    url = app.url
    distro = INLAY_DEFAULT_DISTRO
    if app.runner != "inlay" or not INLAY_METADATA_PATH.is_file():
        return port, url, distro

    try:
        metadata = json.loads(INLAY_METADATA_PATH.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return port, url, distro

    if not isinstance(metadata, dict):
        return port, url, distro

    distro_value = metadata.get("WslDistro")
    if isinstance(distro_value, str) and distro_value.strip():
        distro = distro_value.strip()

    port_value = metadata.get("StudioPort", metadata.get("Port"))
    try:
        parsed_port = int(port_value)
        if 1 <= parsed_port <= 65535:
            port = parsed_port
    except (TypeError, ValueError):
        pass

    url_value = metadata.get("Url")
    if isinstance(url_value, str) and url_value.startswith(("http://", "https://")):
        url = url_value
        try:
            if urlsplit(url).port:
                port = urlsplit(url).port
        except ValueError:
            pass
    elif port is not None:
        url = f"http://localhost:{port}"

    return port, url, distro


def _streamlit_command(app: AppConfig) -> list[str] | None:
    """Costruisce il comando Streamlit senza installare o modificare dipendenze."""
    if app.script is None:
        return None
    if importlib.util.find_spec("streamlit") is not None:
        return [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(app.script),
            "--server.address",
            HOST,
            "--server.port",
            str(app.port),
            "--server.headless",
            "true",
        ]

    streamlit_executable = shutil.which("streamlit")
    if streamlit_executable:
        return [
            streamlit_executable,
            "run",
            str(app.script),
            "--server.address",
            HOST,
            "--server.port",
            str(app.port),
            "--server.headless",
            "true",
        ]
    return None


def _command_for(app: AppConfig) -> tuple[list[str] | None, str | None]:
    """Restituisce il comando di avvio, oppure un messaggio di prerequisito mancante."""
    if app.runner == "inlay":
        _, _, distro = _app_runtime_details(app)
        wsl_executable = shutil.which("wsl.exe") or "wsl.exe"
        return [
            wsl_executable,
            "-d",
            distro,
            "--",
            "bash",
            "-lc",
            "inlay up --registry",
        ], None

    if app.runner == "static":
        if app.port is None:
            return None, "Il runner statico richiede una porta configurata."
        return [
            sys.executable,
            "-m",
            "http.server",
            str(app.port),
            "--bind",
            HOST,
            "--directory",
            str(app.folder),
        ], None

    if app.runner == "streamlit":
        command = _streamlit_command(app)
        if command is None:
            return None, (
                "Streamlit non risulta disponibile nell'ambiente Python del launcher. "
                "Non è stato installato nulla; avvia la dashboard con l'ambiente che già lo contiene."
            )
        return command, None

    if app.script is None:
        return None, "Entry point non configurato."
    interpreter = app.interpreter if app.interpreter and app.interpreter.is_file() else Path(sys.executable)
    return [str(interpreter), str(app.script)], None


def _open_when_ready(app: AppConfig, process: subprocess.Popen[bytes]) -> None:
    """Apre l'URL dopo la risposta HTTP, evitando una scheda prima che il server sia pronto."""
    _, url, _ = _app_runtime_details(app)
    if not url:
        return
    wait_seconds = 180 if app.runner == "inlay" else 18
    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        if process.poll() is not None and app.runner != "inlay":
            return
        if _http_is_available(url):
            webbrowser.open(url)
            return
        time.sleep(0.35)


def start_app(app: AppConfig) -> tuple[bool, str]:
    """Avvia l'app isolata, riutilizzando i servizi già attivi e rispettandone la porta."""
    if app.runner != "inlay" and (app.script is None or not app.script.is_file()):
        return False, f"Entry point non trovato: {app.script}"

    port, url, _ = _app_runtime_details(app)

    with PROCESS_LOCK:
        process = MANAGED_PROCESSES.get(app.app_id)
        if process is not None and process.poll() is None:
            if url:
                webbrowser.open(url)
            return True, f"{app.title} è già avviata."
        MANAGED_PROCESSES.pop(app.app_id, None)

        service_available = bool(url and _http_is_available(url))
        if service_available:
            webbrowser.open(url)
            return True, f"{app.title} è già attiva su {url} ed è stata aperta nel browser."
        if port is not None and _port_is_open(port):
            return False, f"Porta {port} già occupata: avvio annullato per evitare conflitti."

        command, error = _command_for(app)
        if error:
            return False, error
        if command is None:
            return False, "Comando di avvio non disponibile."

        # Ogni applicazione riceve il proprio processo e la propria directory di lavoro.
        creation_flags = 0
        if os.name == "nt":
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        try:
            process = subprocess.Popen(
                command,
                cwd=str(app.folder),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                creationflags=creation_flags,
            )
        except OSError as error:
            return False, f"Avvio di {app.title} non riuscito: {error}"

        MANAGED_PROCESSES[app.app_id] = process

    if url and not app.opens_browser:
        threading.Thread(target=_open_when_ready, args=(app, process), daemon=True).start()
    return True, f"{app.title} avviata in un processo separato."


def stop_app(app: AppConfig) -> tuple[bool, str]:
    """Arresta solo il processo avviato da questa dashboard, mai processi esterni."""
    if app.runner == "inlay":
        return False, "Per arrestare Inlay Studio usa il comando documentato 'inlay down' in WSL."

    with PROCESS_LOCK:
        process = MANAGED_PROCESSES.get(app.app_id)
        if process is None or process.poll() is not None:
            MANAGED_PROCESSES.pop(app.app_id, None)
            return False, f"Nessun processo gestito attivo per {app.title}."
        process.terminate()
        MANAGED_PROCESSES.pop(app.app_id, None)
    return True, f"Processo di {app.title} arrestato."


def _render_cards() -> str:
    """Genera le card a partire dalla configurazione, codificando i testi HTML."""
    cards: list[str] = []
    for app in APPS:
        port, _, _ = _app_runtime_details(app)
        port_text = f"127.0.0.1:{port}" if port else "Applicazione desktop"
        cards.append(
            f"""<article class="app-card" data-app="{escape(app.app_id, quote=True)}">
      <div class="card-top">
        <div class="app-mark" aria-hidden="true">{escape(app.icon)}</div>
        <span class="category">{escape(app.category)}</span>
      </div>
      <h3>{escape(app.title)}</h3>
      <p class="description">{escape(app.description)}</p>
      <div class="card-meta">
        <span class="state" data-state="stopped"><span class="state-dot"></span>{"Non avviata"}</span>
        <span class="port">{escape(port_text)}</span>
      </div>
      <div class="actions">
        <button class="primary" type="button" data-action="start">{"Avvia finestra" if not app.url else "Avvia applicazione"}</button>
        <button class="stop" type="button" data-action="stop" hidden>Arresta</button>
      </div>
    </article>"""
        )
    return "\n".join(cards)


class LauncherRequestHandler(BaseHTTPRequestHandler):
    """Gestisce pagina dashboard e API locali per stato, avvio e arresto."""

    server_version = "WorkspaceLauncher/1.0"

    def _send_json(self, payload: Any, status: int = 200) -> None:
        """Invia una risposta JSON UTF-8 con lunghezza esplicita."""
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        """Serve la pagina principale o lo stato aggiornato delle applicazioni."""
        if self.path == "/logo.png":
            try:
                body = LOGO_PATH.read_bytes()
            except OSError:
                self.send_error(404, "Logo non trovato")
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "public, max-age=3600")
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        if self.path == "/api/apps":
            self._send_json([_app_payload(app) for app in APPS])
            return
        if self.path not in ("/", "/index.html"):
            self.send_error(404)
            return

        dashboard_url = f"http://{HOST}:{self.server.server_port}"
        page = HTML_TEMPLATE.replace("__CARDS__", _render_cards()).replace("__DASHBOARD_URL__", escape(dashboard_url))
        body = page.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        """Accetta esclusivamente le azioni avvio/arresto per app note."""
        path_parts = self.path.strip("/").split("/")
        if len(path_parts) != 3 or path_parts[0] != "api" or path_parts[1] not in ("start", "stop"):
            self._send_json({"ok": False, "message": "Richiesta non valida."}, status=404)
            return

        app = APP_BY_ID.get(path_parts[2])
        if app is None:
            self._send_json({"ok": False, "message": "Applicazione non riconosciuta."}, status=404)
            return

        ok, message = start_app(app) if path_parts[1] == "start" else stop_app(app)
        self._send_json({"ok": ok, "message": message}, status=200 if ok else 409)

    def log_message(self, format_string: str, *args: Any) -> None:
        """Mantiene un log essenziale nel terminale da cui è stato avviato il launcher."""
        print(f"[Launcher] {self.address_string()} - {format_string % args}")


def run_server() -> None:
    """Avvia la dashboard sulla prima porta libera dell'intervallo locale riservato."""
    server: ThreadingHTTPServer | None = None
    for port in DASHBOARD_PORTS:
        try:
            server = ThreadingHTTPServer((HOST, port), LauncherRequestHandler)
            break
        except OSError:
            continue

    if server is None:
        raise RuntimeError("Nessuna porta libera tra 8040 e 8049 per la dashboard.")

    url = f"http://{HOST}:{server.server_port}/"
    print(f"Launcher Progetto_AI disponibile su {url}")
    threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nArresto del launcher richiesto.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()