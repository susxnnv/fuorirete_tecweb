document.addEventListener('DOMContentLoaded', function () {

    const contenitore = document.getElementById('chat-messaggi');
    const input = document.getElementById('chat-input');
    const form = document.getElementById('chat-form');

    if (!contenitore || !input || !form) {
        return;
    }

    // ======================================
    // INFORMAZIONI DELLA CONVERSAZIONE
    // ======================================

    const mioProfiloId = Number(contenitore.dataset.mioProfiloId);
    const altraPersonaId = Number(contenitore.dataset.altraPersonaId);

    const protocollo = (
        window.location.protocol === 'https:'
        ? 'wss:'
        : 'ws:'
    );

    const indirizzoWebSocket = (
        protocollo
        + '//'
        + window.location.host
        + '/ws/chat/'
        + altraPersonaId
        + '/'
    );

    let socket = null;
    let ultimoGiorno = null;
    let invioInCorso = false;
    let testoInAttesa = null;

    const messaggiVisualizzati = new Set();


    // ======================================
    // MESSAGGI GIÀ PRESENTI
    // ======================================

    const righeEsistenti = contenitore.querySelectorAll(
        '.chat-riga-messaggio'
    );

    righeEsistenti.forEach(function (riga) {

        if (riga.dataset.giorno) {
            ultimoGiorno = riga.dataset.giorno;
        }

        if (riga.dataset.messaggioId) {
            messaggiVisualizzati.add(
                Number(riga.dataset.messaggioId)
            );
        }

    });

    contenitore.scrollTop = contenitore.scrollHeight;


    // ======================================
    // ALTEZZA AUTOMATICA TEXTAREA
    // ======================================

    function aggiornaAltezza() {

        input.style.height = 'auto';

        const altezza = Math.min(
            input.scrollHeight,
            120
        );

        input.style.height = altezza + 'px';

        input.style.overflowY = (
            input.scrollHeight > 120
            ? 'auto'
            : 'hidden'
        );
    }

    input.addEventListener('input', aggiornaAltezza);

    aggiornaAltezza();


    // ======================================
    // MESSAGGI DI ERRORE
    // ======================================

    function mostraErrore(testo) {

        let elemento = document.getElementById(
            'chat-errore-websocket'
        );

        if (!elemento) {

            elemento = document.createElement('p');

            elemento.id = 'chat-errore-websocket';
            elemento.className = 'chat-errore';
            elemento.setAttribute('role', 'alert');

            form.parentNode.insertBefore(
                elemento,
                form
            );
        }

        elemento.textContent = testo;
    }

    function nascondiErrore() {

        const elemento = document.getElementById(
            'chat-errore-websocket'
        );

        if (elemento) {
            elemento.remove();
        }
    }


    // ======================================
    // RIPRISTINO TESTO NON CONFERMATO
    // ======================================

    function ripristinaTestoInAttesa() {

        if (testoInAttesa === null) {
            return;
        }

        // Conserviamo anche eventuale testo
        // scritto dopo il precedente invio.
        if (input.value.trim()) {
            input.value = (
                testoInAttesa
                + '\n'
                + input.value
            );
        } else {
            input.value = testoInAttesa;
        }

        testoInAttesa = null;
        invioInCorso = false;

        aggiornaAltezza();
    }


    // ======================================
    // VISUALIZZAZIONE NUOVI MESSAGGI
    // ======================================

    function aggiungiMessaggio(messaggio) {

        const idMessaggio = Number(messaggio.id);

        if (messaggiVisualizzati.has(idMessaggio)) {
            return;
        }

        messaggiVisualizzati.add(idMessaggio);

        // Eliminiamo lo stato iniziale vuoto.
        const statoVuoto = contenitore.querySelector(
            '.chat-vuota'
        );

        if (statoVuoto) {
            statoVuoto.remove();
        }

        // Separatore quando cambia il giorno.
        if (messaggio.giorno !== ultimoGiorno) {

            const separatore = document.createElement('div');

            separatore.className = 'chat-separatore-data';

            const etichetta = document.createElement('span');

            etichetta.textContent = messaggio.data_etichetta;

            separatore.appendChild(etichetta);
            contenitore.appendChild(separatore);

            ultimoGiorno = messaggio.giorno;
        }

        // Riga messaggio.
        const riga = document.createElement('div');

        const mioMessaggio = (
            Number(messaggio.mittente_id) === mioProfiloId
        );

        riga.className = (
            'chat-riga-messaggio '
            + (
                mioMessaggio
                ? 'chat-riga-mia'
                : 'chat-riga-altra'
            )
        );

        riga.dataset.giorno = messaggio.giorno;
        riga.dataset.messaggioId = idMessaggio;

        // Bolla.
        const bolla = document.createElement('div');
        bolla.className = 'chat-bolla';

        // Testo.
        const testo = document.createElement('p');
        testo.className = 'chat-testo';

        // textContent impedisce che il messaggio
        // ricevuto venga interpretato come HTML.
        testo.textContent = messaggio.testo;
        testo.style.whiteSpace = 'pre-wrap';

        // Orario.
        const orario = document.createElement('time');

        orario.className = 'chat-orario';
        orario.dateTime = messaggio.data_ora;
        orario.textContent = messaggio.orario;

        bolla.appendChild(testo);
        bolla.appendChild(orario);
        riga.appendChild(bolla);

        contenitore.appendChild(riga);

        contenitore.scrollTop = contenitore.scrollHeight;
    }


    // ======================================
    // APERTURA WEBSOCKET
    // ======================================

    try {

        socket = new WebSocket(indirizzoWebSocket);

        socket.addEventListener('open', function () {
            nascondiErrore();
        });

        socket.addEventListener('message', function (event) {

            let dati;

            try {
                dati = JSON.parse(event.data);
            } catch (errore) {
                return;
            }

            if (dati.tipo === 'connessione') {
                return;
            }

            // ERRORE RICEVUTO DAL SERVER

            if (dati.tipo === 'errore') {

                ripristinaTestoInAttesa();
                invioInCorso = false;

                mostraErrore(dati.testo);
                return;
            }

            // NUOVO MESSAGGIO

            if (dati.tipo === 'messaggio') {

                aggiungiMessaggio(dati);

                // Conferma del nostro invio.
                if (
                    Number(dati.mittente_id) === mioProfiloId
                ) {

                    testoInAttesa = null;
                    invioInCorso = false;
                }
            }

        });


        // ==================================
        // CONNESSIONE CHIUSA
        // ==================================

        socket.addEventListener('close', function () {

            if (testoInAttesa !== null) {

                ripristinaTestoInAttesa();

                mostraErrore(
                    'La connessione si è interrotta. '
                    + 'Verifica se il messaggio è già '
                    + 'presente prima di inviarlo nuovamente.'
                );
            }

            invioInCorso = false;
        });


        // ==================================
        // ERRORE DI CONNESSIONE
        // ==================================

        socket.addEventListener('error', function () {

            // Il ripristino viene gestito
            // dall'evento close, per evitare
            // di eseguirlo due volte.
            invioInCorso = false;
        });

    } catch (errore) {

        socket = null;
    }


    // ======================================
    // INVIO MESSAGGI
    // ======================================

    form.addEventListener('submit', function (event) {

        const testo = input.value.trim();

        // Evitiamo invii vuoti.
        if (!testo) {
            event.preventDefault();
            input.focus();
            return;
        }

        // Se il WebSocket è aperto,
        // usiamo la comunicazione in tempo reale.
        if (
            socket &&
            socket.readyState === WebSocket.OPEN
        ) {

            event.preventDefault();

            // Evitiamo un secondo invio prima
            // della conferma del messaggio.
            if (invioInCorso) {
                return;
            }

            invioInCorso = true;
            testoInAttesa = testo;

            try {

                socket.send(JSON.stringify({
                    tipo: 'messaggio',
                    testo: testo
                }));

                // Puliamo il campo soltanto dopo
                // aver consegnato i dati all'API
                // WebSocket del browser.
                input.value = '';

                aggiornaAltezza();
                nascondiErrore();

            } catch (errore) {

                ripristinaTestoInAttesa();

                mostraErrore(
                    'Non è stato possibile inviare '
                    + 'il messaggio. Riprova.'
                );
            }
        }

        // Se WebSocket non è disponibile,
        // il form mantiene la normale POST HTTP.
    });


    // ======================================
    // ENTER / SHIFT + ENTER
    // ======================================

    input.addEventListener('keydown', function (event) {

        if (
            event.key === 'Enter'
            && !event.shiftKey
            && !event.isComposing
        ) {

            event.preventDefault();

            if (input.value.trim()) {
                form.requestSubmit();
            }
        }
    });


    // ======================================
    // CHIUSURA DELLA CONNESSIONE
    // ======================================

    window.addEventListener('pagehide', function () {

        if (socket) {
            socket.close();
        }

    });

});