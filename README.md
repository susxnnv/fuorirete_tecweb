# FuoriRete

**Progetto per l'esame di Tecnologie Web**  
Corso di Laurea in Scienze Informatiche – Università degli Studi di Modena e Reggio Emilia

**Studentessa:** Susanna Gnaccarini  
**Matricola:** 184144

## Descrizione del progetto

**FuoriRete** è un'applicazione web pensata per favorire la conoscenza tra persone con interessi comuni e promuovere l'organizzazione di attività ed eventi condivisi.

L'applicazione permette agli utenti di creare un profilo personale, scoprire altre persone in base alle proprie preferenze, esprimere Like o Dislike e comunicare privatamente quando si verifica un Match reciproco.

FuoriRete offre inoltre un sistema di Community, attraverso il quale gli utenti possono creare gruppi tematici, richiedere di partecipare, interagire con gli altri membri e organizzare eventi.

## Funzionalità principali

### Autenticazione e profilo

- Registrazione, accesso e disconnessione.
- Creazione e modifica del profilo personale.
- Gestione delle informazioni personali, delle immagini e degli interessi.
- Modifica della password ed eliminazione dell'account.
- Controllo degli accessi alle funzionalità riservate agli utenti autenticati con un profilo completo.

### Persone e Match

- Scoperta di profili attraverso un sistema di filtri e ordinamento.
- Visualizzazione del dettaglio degli altri utenti.
- Possibilità di esprimere Like o Dislike.
- Creazione automatica di un Match in presenza di Like reciproci.
- Visualizzazione dei Like ricevuti e dei Match.
- Possibilità di annullare un Match.

### Chat private

- Conversazioni private tra utenti che hanno ottenuto un Match.
- Salvataggio dei messaggi nel database.
- Comunicazione tramite WebSocket con Django Channels.
- Controllo dei permessi di accesso alle conversazioni.

### Community

- Visualizzazione e ricerca delle Community.
- Creazione, modifica ed eliminazione delle Community.
- Gestione degli interessi associati alle Community.
- Invio e annullamento delle richieste di partecipazione.
- Accettazione e rifiuto delle richieste da parte dell'organizzatore.
- Gestione della partecipazione e uscita dalle Community.
- Valutazione delle Community da parte degli utenti autorizzati.
- Chat di gruppo per i membri delle Community.

### Eventi 

- Creazione, modifica ed eliminazione di eventi associati alle Community.
- Visualizzazione degli eventi.

### Notifiche

- Notifiche relative alle interazioni e alle attività dell'applicazione.
- Indicatore delle notifiche non lette nell'interfaccia autenticata.

## Tecnologie utilizzate

| Componente | Tecnologia |
|---|---|
| Backend | Python, Django |
| Database | SQLite |
| Frontend | HTML, CSS, JavaScript |
| Comunicazione WebSocket | Django Channels |
| Server ASGI | Daphne |
| Gestione interfaccia | Django Template Language |

## Struttura del progetto

```text
fuorirete_tecweb/
├── fuorirete/       # Configurazione principale Django
├── gestione/        # Modelli, form, view e logica applicativa
│   ├── migrations/
│   ├── management/
│   │   └── commands/
│   ├── templates/
│   ├── consumers.py
│   ├── routing.py
│   └── tests.py
├── templates/       # Template HTML condivisi
├── static/
│   ├── css/         # Fogli di stile
│   └── js/          # Script JavaScript
├── dati_demo/       # Risorse per il popolamento dimostrativo
├── manage.py
└── README.md
```

Le immagini caricate dagli utenti vengono archiviate nella cartella `media/`, mentre il database locale SQLite è contenuto nel file `db.sqlite3`.

## Installazione e avvio

Il progetto è pensato per essere eseguito in un ambiente di sviluppo locale.

### 1. Clonare il repository

```bash
git clone https://github.com/susxnnv/fuorirete_tecweb.git
cd fuorirete_tecweb
```

### 2. Creare e attivare un ambiente virtuale

Su Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Su Windows (PowerShell):

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Installare le dipendenze

Con un file `requirements.txt` nella cartella principale:

```bash
python -m pip install -r requirements.txt
```

### 4. Preparare il database

```bash
python manage.py migrate
```

### 5. Avviare il server

```bash
python manage.py runserver
```

L'applicazione sarà accessibile all'indirizzo:

http://127.0.0.1:8000/

L'area di amministrazione Django è accessibile da:

http://127.0.0.1:8000/admin/

## Dati dimostrativi

Il progetto comprende comandi di gestione Django dedicati al popolamento del database con dati dimostrativi.

I comandi principali sono:

```bash
python manage.py popola_persone_demo
python manage.py popola_community_demo
```

Il dataset originale comprende 25 profili dimostrativi, 15 Community e 27 eventi.

Il popolamento consente di esplorare le funzionalità dell'applicazione senza dover inserire manualmente tutti i dati.

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

## Note

- Le funzionalità riservate richiedono l'autenticazione e il completamento del profilo.
- Le chat utilizzano WebSocket e richiedono il supporto ASGI configurato nel progetto.
- Il database SQLite, le immagini caricate e le configurazioni locali non sono inclusi nel repository Git.
- Il progetto è destinato alla dimostrazione e alla valutazione universitaria in ambiente locale.

---

**FuoriRete – Progetto di Tecnologie Web**  
Susanna Gnaccarini – Matricola 184144