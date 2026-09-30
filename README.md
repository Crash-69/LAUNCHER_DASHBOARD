# Launcher Dashboard

Questa guida descrive un'architettura di riferimento per un launcher locale e una procedura per aggiungere o aggiornare le applicazioni mostrate nella dashboard.

> **Stato del repository:** al momento contiene solo questo README, senza codice sorgente né configurazione del launcher. Le componenti e il modello dati descritti qui sono quindi una proposta da adattare all'implementazione, non una descrizione di componenti già presenti.

## Architettura

Il launcher può essere organizzato in quattro componenti con responsabilità distinte:

1. **Catalogo delle applicazioni** — una configurazione locale contiene i metadati e il riferimento di avvio di ciascuna applicazione.
2. **Caricamento e validazione** — all'avvio, il launcher legge il catalogo, controlla i campi obbligatori e ignora o segnala le voci non valide.
3. **Dashboard** — l'interfaccia presenta una scheda per ogni voce valida, usando nome, descrizione, icona ed eventuale categoria.
4. **Avvio locale** — l'azione sulla scheda passa il riferimento di avvio al meccanismo previsto dalla piattaforma. Il catalogo descrive cosa avviare; l'interfaccia non deve costruire comandi di shell a partire da valori immessi dall'utente.

Tenere separati catalogo, interfaccia e avvio consente di aggiornare le applicazioni senza duplicarne la logica nella dashboard.

## Modello di una voce

Il formato concreto dipende dall'implementazione. Una voce dovrebbe avere almeno un identificatore stabile, un nome e un riferimento di avvio. Per esempio:

```json
{
  "id": "editor",
  "name": "Editor",
  "description": "Editor di testo",
  "icon": "icons/editor.png",
  "launch": {
    "type": "path",
    "target": "/percorso/locale/editor"
  },
  "category": "Strumenti"
}
```

`id`, `name` e `launch` sono i campi essenziali dell'esempio; `description`, `icon` e `category` sono facoltativi. Il valore di `launch` deve seguire i tipi effettivamente supportati dal launcher e dal sistema operativo. I percorsi e le icone devono essere validi sulla macchina locale.

## Aggiungere un'applicazione

1. Individuare il catalogo usato dal launcher (o il punto in cui viene definito l'elenco delle applicazioni).
2. Aggiungere una voce con un `id` univoco, il nome visualizzato e un riferimento di avvio supportato.
3. Aggiungere descrizione, icona e categoria se previste; verificare che i relativi file esistano e siano accessibili.
4. Avviare o ricaricare la dashboard e controllare che la scheda venga visualizzata correttamente.
5. Fare clic sulla scheda e verificare che venga avviata l'applicazione desiderata. Controllare anche il comportamento quando il riferimento non è disponibile o l'avvio fallisce.

## Aggiornare o rimuovere un'applicazione

Per aggiornare un'app, modificare la voce esistente mantenendone l'`id` se rappresenta ancora la stessa applicazione. Aggiornare il percorso di avvio quando cambia la posizione dell'eseguibile e sostituire descrizione o icona se necessario. Per rimuoverla, eliminare la voce dal catalogo e rimuovere eventuali risorse dedicate non più utilizzate.

## Verifiche e sicurezza

- Verificare che il catalogo sia sintatticamente valido e che ogni `id` sia univoco.
- Controllare che i riferimenti a eseguibili e icone siano raggiungibili sulla macchina di destinazione.
- Provare sia un avvio riuscito sia il caso di un'applicazione o di un percorso mancante.
- Consentire solo tipi di avvio esplicitamente supportati; non eseguire direttamente comandi arbitrari letti dal catalogo e non interpolare i metadati in una shell.
