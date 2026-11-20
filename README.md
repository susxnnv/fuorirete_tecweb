# FuoriRete

**Progetto per l'esame di Tecnologie Web**  
Corso di Laurea in Scienze Informatiche – Università degli Studi di Modena e Reggio Emilia

**Studentessa:** Susanna Gnaccarini  
**Matricola:** 184144

---

## Descrizione del progetto

**FuoriRete** è un'applicazione web pensata per favorire la conoscenza tra persone con interessi comuni e promuovere l'organizzazione di attività ed eventi condivisi.

L'applicazione permette agli utenti di creare un profilo personale, scoprire altre persone in base alle proprie preferenze, esprimere Like o Dislike e comunicare privatamente quando si verifica un Match reciproco.

FuoriRete offre inoltre un sistema di Community, attraverso il quale gli utenti possono creare gruppi tematici, richiedere di partecipare, interagire con gli altri membri e organizzare eventi.

## Funzionalità principali

### Autenticazione e profilo

FuoriRete permette di registrarsi, accedere al proprio account e creare un profilo personale, specificando informazioni, interessi e preferenze. È inoltre possibile modificare i propri dati, cambiare password o eliminare l'account.

La Home pubblica e la consultazione delle Community sono accessibili anche senza autenticazione, mentre le funzionalità riservate richiedono l'accesso e il completamento del profilo.

### Scoperta delle persone e Match

Gli utenti possono scoprire nuovi profili, proposti attraverso un sistema di ranking basato sulla compatibilità e personalizzabile mediante filtri.

Per ogni persona è possibile visualizzare il profilo ed esprimere un Like o un Dislike. Quando due utenti si scambiano reciprocamente un Like, viene generato un **Match**, che può essere successivamente annullato.

### Chat private

Gli utenti che hanno ottenuto un Match possono comunicare attraverso una chat privata. I messaggi vengono salvati nel database e la comunicazione avviene in tempo reale tramite WebSocket, utilizzando Django Channels.

L'accesso alle conversazioni è consentito esclusivamente agli utenti coinvolti nel Match.

### Scoperta e gestione delle Community

FuoriRete permette di esplorare Community tematiche tramite ricerca testuale e filtri. Le Community vengono ordinate attraverso un ranking che considera sia le valutazioni ricevute sia l'affinità con il profilo dell'utente.

Ogni utente autenticato può creare una Community e diventarne organizzatore, con la possibilità di modificarne le informazioni, gestire le richieste di partecipazione e organizzare eventi.

Per entrare in una Community è necessario inviare una richiesta e ottenere l'approvazione dell'organizzatore. I partecipanti possono successivamente abbandonarla e lasciare una valutazione.

### Interazioni ed eventi nelle Community

I membri di una Community possono comunicare attraverso una chat di gruppo in tempo reale, gestita tramite WebSocket.

Ogni Community può inoltre organizzare eventi, creati e gestiti dall'organizzatore. La visualizzazione degli eventi e l'accesso alla chat sono riservati ai membri della Community.

### Notifiche

Un sistema di notifiche informa gli utenti sulle interazioni e sulle attività che li riguardano. Le notifiche sono consultabili nella sezione dedicata e segnalate attraverso un indicatore nella barra di navigazione dell'area autenticata.

## Tecnologie utilizzate

| Componente | Tecnologia |
|---|---|
| Backend | Python, Django |
| Database | SQLite |
| Frontend | HTML, CSS, JavaScript |
| Comunicazione WebSocket | Django Channels |
| Server ASGI | Daphne |
| Gestione interfaccia | Django Template Language |

## Requisiti

Per eseguire FuoriRete in locale sono necessari:

- Python 3.12.
- Git, per clonare il repository.
- Una connessione Internet per installare le dipendenze.

Le librerie Python necessarie sono elencate nel file `requirements.txt`.

## Installazione e avvio

La procedura seguente permette di installare FuoriRete partendo da un database vuoto.

### 1. Clonare il repository

Aprire un terminale ed eseguire:

```bash
git clone https://github.com/susxnnv/fuorirete_tecweb.git
cd fuorirete_tecweb
```

### 2. Creare e attivare un ambiente virtuale

**Linux/macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell):**

```powershell
py 3.12 -m venv .venv
.venv\Scripts\Activate.ps1
```

Tutti i comandi successivi devono essere eseguiti con l'ambiente virtuale attivo e dalla cartella principale del progetto, contenente `manage.py`.

### 3. Installare le dipendenze

```bash
python -m pip install -r requirements.txt
```

### 4. Preparare il database

```bash
python manage.py migrate
```

Questo comando crea le tabelle del database e applica le migrazioni Django.

**Il catalogo degli interessi viene inizializzato automaticamente al termine delle migrazioni.**

Il catalogo comprende 16 macrocategorie e 79 sottointeressi, per un totale di 95 interessi.

A questo punto è possibile scegliere se utilizzare FuoriRete con un database inizialmente vuoto oppure con i dati dimostrativi.

### 5. Scelta della modalità di utilizzo

**Opzione A — Utilizzo normale, senza dati dimostrativi**

Non è necessario eseguire altri comandi di preparazione.

Il database contiene il catalogo degli interessi, ma non vengono creati utenti, Community o eventi dimostrativi.

È possibile avviare il sito e registrare normalmente nuovi utenti.

**Opzione B — Utilizzo dimostrativo**

Per caricare tutti i dati necessari alla dimostrazione, eseguire:

```bash
python manage.py prepara_demo
```

Il comando esegue automaticamente, nell'ordine:

1. Creazione dei 25 profili dimostrativi.
2. Creazione delle 15 Community e dei 27 eventi.
3. Creazione delle interazioni dimostrative tra i profili.

Non è necessario eseguire separatamente i singoli comandi di popolamento.

**Per la valutazione del progetto è consigliata l'opzione B**, che permette di esplorare immediatamente le funzionalità senza dover creare manualmente utenti e relazioni.

### 6. Avviare il server

Indipendentemente dalla modalità scelta:

```bash
python manage.py runserver
```

Aprire il browser all'indirizzo:

http://127.0.0.1:8000/

Per interrompere il server, premere `Ctrl + C` nel terminale.

---

## Dati dimostrativi e credenziali di accesso

Il popolamento dimostrativo crea un insieme di dati predefiniti per consentire la verifica delle principali funzionalità dell'applicazione.

| Tipo di dato | Quantità |
|---|---:|
| Profili dimostrativi | 25 |
| Community | 15 |
| Eventi | 27 |
| Like | 6 |
| Dislike | 1 |
| Messaggi privati | 5 |
| Messaggi Community | 4 |
| Richieste di partecipazione | 2 |
| Valutazioni Community | 1 |
| Notifiche | 8 |

I profili dimostrativi utilizzano gli username da `demo_01` a `demo_25`.

**Credenziali comuni:**

```text
Username: demo_01 ... demo_25
Password: FuoriReteDemo2026!
```

### Profilo consigliato per la dimostrazione

Per esplorare le funzionalità dell'applicazione è consigliato accedere con il profilo di **Sara**:

```text
Username: demo_04
Password: FuoriReteDemo2026!
```

Questo profilo è stato predisposto con uno scenario dimostrativo che comprende:

- Due Match reciproci, con Marco (`demo_02`) e Alice (`demo_05`).
- Due conversazioni private contenenti messaggi predefiniti.
- Un Like ricevuto non ancora ricambiato.
- Like e Dislike già espressi.
- Partecipazione a diverse Community.
- Organizzazione della Community *Club del libro*.
- Una richiesta di partecipazione ricevuta e una inviata.
- Messaggi nelle chat delle Community.
- Una valutazione di una Community.
- Notifiche relative alle principali interazioni.

È possibile accedere con altri account demo utilizzando la stessa password per verificare le funzionalità da differenti prospettive.

Le credenziali indicate sono destinate esclusivamente all'ambiente dimostrativo locale.

---

## Ripristino dei dati dimostrativi

Durante le prove dell'applicazione è possibile creare utenti, Community, eventi e interazioni aggiuntive oppure modificare i dati dimostrativi.

Per riportare il database allo scenario originale è disponibile il comando:

```bash
python manage.py pulisci_dati_test
```

Eseguito senza opzioni, il comando mostra un'anteprima delle operazioni previste **senza modificare il database**.

Per applicare effettivamente il ripristino:

```bash
python manage.py pulisci_dati_test --applica --conferma RIPRISTINA_DEMO
```

Il comando:

- Crea un backup del database SQLite prima della pulizia.
- Elimina gli account di prova non appartenenti al dataset e non amministrativi.
- Elimina le Community e gli eventi aggiuntivi.
- Ripristina i dati originali delle persone e delle Community.
- Elimina le interazioni create durante le prove.
- Ricrea le relazioni dimostrative predefinite.
- Conserva gli account amministrativi.

I backup vengono salvati nella cartella `backup_database/`.

**Attenzione:** il comando è destinato esclusivamente a database dimostrativi locali con `DEBUG=True` e SQLite. Non deve essere utilizzato su database contenenti dati reali o in produzione.

---

## Struttura del progetto

```text
fuorirete_tecweb/
├── fuorirete/             # Configurazione principale Django
├── gestione/              # Logica applicativa
│   ├── migrations/
│   ├── management/
│   │   └── commands/     # Inizializzazione e dati demo
│   ├── templates/
│   ├── models.py
│   ├── forms.py
│   ├── views.py
│   ├── consumers.py
│   ├── routing.py
│   └── tests.py
├── templates/             # Template HTML condivisi
├── static/
│   ├── css/               # Fogli di stile
│   └── js/                # Script JavaScript
├── dati_demo/             # Immagini per il popolamento demo
├── manage.py
├── requirements.txt
└── README.md
```

Le immagini caricate dagli utenti vengono archiviate nella cartella `media/`, mentre il database locale SQLite è contenuto nel file `db.sqlite3`.

Questi file vengono generati durante l'utilizzo e non sono inclusi nel repository Git.

---

## Test

Il progetto comprende test automatizzati Django per verificare il funzionamento di modelli, view e logica applicativa.

Per eseguire i test:

```bash
python manage.py test gestione
```

Per verificare la configurazione Django:

```bash
python manage.py check
```

I test possono essere eseguiti indipendentemente dal popolamento dimostrativo, utilizzando il database di test gestito da Django.

---

## Amministrazione Django

L'interfaccia di amministrazione è disponibile all'indirizzo:

http://127.0.0.1:8000/admin/

Per accedervi è necessario un account amministratore.

Se non ne è stato ancora creato uno, eseguire:

```bash
python manage.py createsuperuser
```

Seguire le istruzioni mostrate nel terminale per impostare le credenziali.

Gli account dimostrativi `demo_01`–`demo_25` non sono account amministratori.

---

## Note

- La Home pubblica è accessibile anche senza autenticazione.
- Le funzionalità riservate richiedono l'accesso e il completamento del profilo personale.
- Le chat utilizzano WebSocket tramite Django Channels e la configurazione ASGI del progetto.
- Il catalogo degli interessi è indipendente dai dati dimostrativi e viene inizializzato automaticamente durante la preparazione del database.
- I dati dimostrativi sono facoltativi e vengono caricati soltanto tramite il comando dedicato.
- Il database SQLite, le immagini caricate dagli utenti e le configurazioni locali non sono inclusi nel repository Git.
- Il progetto è destinato alla dimostrazione e alla valutazione universitaria in ambiente di sviluppo locale.

---

**FuoriRete – Progetto di Tecnologie Web**  
Susanna Gnaccarini – Matricola 184144
