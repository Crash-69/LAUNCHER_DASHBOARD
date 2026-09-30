# Launcher Dashboard

Questa guida descrive l'architettura del launcher locale e la procedura per aggiungere o aggiornare le applicazioni mostrate nella dashboard.

File principale: [launcher_dashboard.py](launcher_dashboard.py)

## Avvio e arresto

Aprire un terminale nella cartella `C:\Progetto_AI\LAUNCHER_DASHBOARD` ed eseguire:

```powershell
Set-Location C:\Progetto_AI\LAUNCHER_DASHBOARD
python .\launcher_dashboard.py
```

Il launcher ascolta esclusivamente su `127.0.0.1` e apre il browser. Cerca la prima porta libera nell'intervallo `8040-8049`; l'indirizzo stampato nel terminale è quello effettivo, normalmente `http://127.0.0.1:8040/`.

Per arrestare la dashboard, usare `Ctrl+C` nel terminale che la esegue. I processi delle sotto-applicazioni sono separati: arrestare il launcher non comporta la chiusura automatica delle app già avviate.

## Come funziona

Il launcher utilizza solo la Standard Library di Python:

- `ThreadingHTTPServer` serve la pagina e le API locali;
- HTML, CSS e JavaScript sono incorporati in `launcher_dashboard.py`, senza framework o risorse web esterne;
- `subprocess.Popen` avvia gli script in processi separati e con la rispettiva cartella di lavoro;
- le porte vengono controllate prima dell'avvio per evitare collisioni;
- lo stato della dashboard viene aggiornato ogni 2,5 secondi.

La UI mantiene il linguaggio visivo dell'estrattore PDF: fondo chiaro, card bianche, accento verde, font di sistema e griglia responsive.

Il launcher è collocato in `C:\Progetto_AI\LAUNCHER_DASHBOARD`, mentre le sotto-app restano in `C:\Progetto_AI`. `LAUNCHER_DIR` identifica la cartella del launcher e `WORKSPACE_DIR` risale alla cartella padre per costruire i percorsi delle app.

Le route interne sono:

| Route | Metodo | Funzione |
| --- | --- | --- |
| `/` | GET | Pagina della dashboard |
| `/api/apps` | GET | Stato delle app configurate |
| `/api/start/<id>` | POST | Avvio o apertura dell'app |
| `/api/stop/<id>` | POST | Arresto del processo avviato dal launcher |

Il pulsante di arresto agisce solo sui processi creati dalla dashboard; non termina processi esterni. Se una porta web è già occupata da un server HTTP, il launcher riutilizza il servizio e apre l'URL. Se la porta è occupata ma non risponde come HTTP, rifiuta l'avvio per evitare conflitti.

## App attualmente registrate

Le configurazioni sono raccolte nella tupla `APPS` del file Python.

| ID | Entry point | Tipo | Porta |
| --- | --- | --- | ---: |
| `pdf` | `Estrae_testo_da_Pdf_richiama_Ollama/estrattore_pdf_webapp.py` | Webapp Python | 8020 |
| `jarvis` | `Jarvis2/run_webapp.py` | Webapp Python, usa `.venv` se presente | 8008 |
| `youtube` | `Script_Python_Scarica_Testi_youtube/app.py` | Streamlit | 8501 |
| `securevault` | `SecureVault/securevault_app.py` | Webapp Python | 8010 |
| `cedolino` | `VerificaCedolino/validate_ced_mapping_gui.py` | GUI desktop | Nessuna |
| `uniemens` | `APP Uniemens/stitch_flussi_uniemens/test_prototipo_dashboard/code_V12_P3_OK_Color_7.htm` | HTML statico | 8021 |
| `certificati` | `Porting APP Chiusura Certificati/stitch_flussi_uniemens/test_prototipo_dashboard/code.html` | HTML statico | 8022 |
| `inlaystudio` | `wsl -d Ubuntu-24.04 -- bash -lc "inlay up --registry"` | WSL / Podman | Metadata o 3002 |

Le descrizioni sono campi della configurazione. Possono essere aggiornate lì senza modificare la pagina HTML.

## Aggiungere una nuova app

1. Individuare lo script di ingresso effettivo, la cartella di lavoro, il comando necessario e, per una webapp, la porta e l'URL locale.
2. Verificare che la porta web non sia già assegnata a un'altra app o servizio del workspace.
3. Aggiungere un elemento `AppConfig` nella tupla `APPS`, vicino alle applicazioni dello stesso tipo.
4. Avviare il launcher e verificare scheda, avvio, stato e arresto.

Esempio per una webapp Python che avvia il browser da sola:

```python
AppConfig(
    app_id="nuova_app",
    title="Nuova applicazione",
    category="Categoria",
    icon="NA",
    description="Descrizione breve mostrata nella scheda.",
    folder=WORKSPACE_DIR / "NuovaApp",
    script=WORKSPACE_DIR / "NuovaApp" / "app.py",
    port=8021,
    url="http://127.0.0.1:8021/",
    opens_browser=True,
),
```

Per una GUI desktop, omettere `port` e `url`; il pulsante verrà etichettato **Avvia finestra**. Per una webapp che non apre il browser autonomamente, omettere `opens_browser` (il valore predefinito è `False`): il launcher attende che l'URL risponda prima di aprirlo.

Per un'app composta da HTML statico e risorse relative, impostare `runner="static"`, specificare come `folder` la directory che contiene la pagina e i suoi asset, impostare `script` sul file HTML, e configurare `port` e `url`. Il launcher avvia `python -m http.server` limitato a `127.0.0.1`, serve l'intera cartella e apre l'URL quando risponde. In questo modo riferimenti come `./eng-logo.png` continuano a funzionare. Assegnare una porta non utilizzata dalle altre app.

La dashboard Uniemens utilizza questo runner e viene servita da `http://127.0.0.1:8021/code_V12_P3_OK_Color_7.htm`. La pagina carica Tailwind e i font da CDN e contiene chiamate verso i servizi locali n8n; l'accesso a tali servizi dipende dal loro stato e dalla configurazione CORS/rete del browser.

La dashboard di monitoraggio Certificati usa lo stesso runner statico ed è disponibile su `http://127.0.0.1:8022/code.html`. Condivide la directory con `eng-logo.png` e gli altri asset relativi; usa le API n8n configurate nell'HTML per diagnostica, estrazione CF e riavvio del proxy. Il pulsante di avvio mantiene il colore verde standard del launcher.

Inlay Studio usa il runner `inlay`: il launcher invoca il comando WSL documentato con la distro `Ubuntu-24.04` e apre il browser quando la porta Studio risponde. Se esiste `%USERPROFILE%\.inlay-studio\launcher.json`, usa `WslDistro`, `StudioPort` e `Url` salvati dall'installer; in assenza dei metadati usa la distro `Ubuntu-24.04` e la porta predefinita `3002`. Lo stato resta aggiornato anche quando il comando `inlay up` termina dopo aver avviato i container.

Il launcher non offre un pulsante di arresto per Inlay: terminare il processo WSL non garantisce l'arresto dello stack. Per spegnerlo senza rimuovere i dati, usare da PowerShell:

```powershell
wsl -d Ubuntu-24.04 -- inlay down
```

Se la distro installata è diversa, sostituire `Ubuntu-24.04` con il valore `WslDistro` del metadata Inlay.

Gli ID devono essere univoci e semplici, preferibilmente in minuscolo con trattini bassi. `APP_BY_ID` viene costruita automaticamente a partire da `APPS`: non occorre aggiungere route o handler per ogni singola app.

## Interpreti e runner

Per il runner Python standard, il comando predefinito è l'interprete che ha avviato la dashboard (`sys.executable`). Se `interpreter` indica un eseguibile esistente, viene usato quello. Jarvis2, per esempio, usa `Jarvis2/.venv/Scripts/python.exe` se disponibile e ripiega sull'interprete della dashboard se non lo trova.

Per Streamlit impostare `runner="streamlit"`. Il launcher usa `python -m streamlit run` con l'interprete corrente, oppure il comando `streamlit` trovato nel `PATH`. Specifica inoltre `port` e `url`: il launcher passa a Streamlit host `127.0.0.1`, porta e modalità headless. Non installa pacchetti; se Streamlit non è già disponibile, il pulsante mostra un messaggio di prerequisito mancante.

Se una nuova app richiede un comando particolare (per esempio argomenti aggiuntivi o un runner diverso), modificare `_command_for()` o aggiungere un runner esplicito. Evitare di concatenare il comando in una stringa: mantenere gli argomenti in una lista passata a `subprocess.Popen`.

## Manutenzione della UI

- **Nome, descrizione, categoria, icona, cartella, script o porta:** aggiornare la relativa `AppConfig` in `APPS`.
- **Colori e layout:** modificare le variabili CSS all'inizio di `HTML_TEMPLATE` e le regole delle card.
- **Etichette o comportamento dei pulsanti:** aggiornare il JavaScript in `HTML_TEMPLATE` e, se necessario, `_render_cards()`.
- **Nuove azioni o logica di stato:** aggiungere la logica lato server in `LauncherRequestHandler` e mantenere l'API limitata agli ID presenti in `APP_BY_ID`.
- **Porte della dashboard:** aggiornare `DASHBOARD_PORTS`; sono porte distinte da quelle delle sotto-applicazioni.

Non esporre il server su `0.0.0.0` senza riprogettare le protezioni: le API possono avviare processi e sono pensate per l'uso locale.

## Verifiche dopo una modifica

Dalla cartella del launcher:

```powershell
Set-Location C:\Progetto_AI\LAUNCHER_DASHBOARD
python -m py_compile .\launcher_dashboard.py
python .\launcher_dashboard.py
```

Controllare poi nel browser che la nuova scheda sia presente, che la porta indicata sia corretta e che avvio/arresto aggiornino lo stato. Per un'app web, verificare anche il suo URL. Se l'avvio viene rifiutato, controllare prima che lo script esista e che la porta non sia occupata.

## Troubleshooting

**La dashboard non parte:** il launcher tenta le porte `8040-8049`. Se sono tutte occupate, liberarne una oppure ampliare `DASHBOARD_PORTS`.

**La pagina Uniemens non si apre:** verificare che la porta `8021` sia libera e che il file HTML e `eng-logo.png` siano presenti nella cartella configurata. La pagina fa inoltre richieste a CDN e servizi locali configurati nel prototipo.

**La dashboard Certificati non si apre:** verificare che la porta `8022` sia libera e che `code.html` e `eng-logo.png` siano presenti nella cartella `Porting APP Chiusura Certificati/stitch_flussi_uniemens/test_prototipo_dashboard`. Le azioni e i dati dipendono anche dai servizi n8n configurati nella pagina.

**Inlay Studio non si apre:** controllare `wsl -l -v`, `wsl -d Ubuntu-24.04 -- inlay status` e la porta configurata (`wsl -d Ubuntu-24.04 -- inlay config get STUDIO_HOST_PORT`). Se l'installer non ha ancora predisposto WSL/Podman o la CLI `inlay`, completare prima l'installazione descritta in `InlayStudio/README.md`.

**La scheda segnala una porta occupata:** verificare se l'app è già attiva. Un server HTTP raggiungibile viene riutilizzato; una porta usata da un altro processo non HTTP non viene terminata automaticamente.

**Un'app Python si chiude subito:** controllare il percorso dello script, l'interprete configurato e le dipendenze già disponibili in quell'ambiente. L'output dei processi figli è reindirizzato; per diagnosticare temporaneamente un errore, avviare manualmente lo script dalla sua cartella oppure modificare `Popen` per registrare stdout e stderr.

**Streamlit non è disponibile:** avviare il launcher con un interprete che abbia già Streamlit o verificare che il comando `streamlit` sia nel `PATH`. Il launcher non esegue installazioni.