
document.addEventListener("DOMContentLoaded", function () {

    // ==========================================
    // ELEMENTI DELLA PAGINA
    // ==========================================

    const pagina = document.querySelector(".chat-gruppo-pagina");

    const contenitore = document.getElementById(
        "chat-gruppo-messaggi"
    );

    if (!pagina || !contenitore) {
        return;
    }

    const form = document.getElementById("chat-gruppo-form");

    const input = document.getElementById("chat-gruppo-testo");

    const stato = document.getElementById("chat-gruppo-stato");

    // Identificativi forniti dal template Django.
    const communityId = Number(
        pagina.dataset.communityId
    );

    const mioProfiloId = Number(
        pagina.dataset.profiloId
    );

    const anteprima = pagina.dataset.anteprima === "1";

    if (!Number.isInteger(communityId) || communityId <= 0) {
        return;
    }

    if (!Number.isInteger(mioProfiloId) || mioProfiloId <= 0) {
        return;
    }


    // ==========================================
    // VARIABILI
    // ==========================================

    let socket = null;

    let ultimoGiorno = null;

    let invioInCorso = false;

    let testoInAttesa = null;

    const messaggiVisualizzati = new Set();


    // ==========================================
    // MESSAGGI GIÀ PRESENTI
    // ==========================================

    const messaggiEsistenti = contenitore.querySelectorAll(
        ".chat-gruppo-messaggio"
    );

    messaggiEsistenti.forEach(function (elemento) {

        if (elemento.dataset.messaggioId) {

            messaggiVisualizzati.add(
                Number(elemento.dataset.messaggioId)
            );
        }

        if (elemento.dataset.giorno) {
            ultimoGiorno = elemento.dataset.giorno;
        }

    });


    // ==========================================
    // SCORRIMENTO AUTOMATICO
    // ==========================================

    function scorriInBasso() {

        contenitore.scrollTop = contenitore.scrollHeight;
    }

    scorriInBasso();


    // ==========================================
    // AGGIORNAMENTO STATO CONNESSIONE
    // ==========================================

    function aggiornaStato(testo) {

        if (stato) {
            stato.textContent = testo;
        }
    }


    // ==========================================
    // GESTIONE ERRORI
    // ==========================================

    function mostraErrore(testo) {

        if (!form) {
            return;
        }

        let elemento = document.getElementById(
            "chat-gruppo-errore-websocket"
        );

        if (!elemento) {

            elemento = document.createElement("p");

            elemento.id = "chat-gruppo-errore-websocket";

            elemento.className = "chat-gruppo-errore";

            elemento.setAttribute("role", "alert");

            form.parentNode.insertBefore(elemento, form);
        }

        elemento.textContent = testo;
    }

    function nascondiErrore() {

        const elemento = document.getElementById(
            "chat-gruppo-errore-websocket"
        );

        if (elemento) {
            elemento.remove();
        }
    }


    // ==========================================
    // RIPRISTINO MESSAGGIO NON CONFERMATO
    // ==========================================

    function ripristinaMessaggio() {

        if (testoInAttesa === null) {
            return;
        }

        if (input) {

            // Non perdiamo eventuale testo nuovo.
            if (input.value.trim()) {

                input.value = (
                    testoInAttesa + "\n" + input.value
                );

            } else {

                input.value = testoInAttesa;
            }

        }

        testoInAttesa = null;

        invioInCorso = false;
    }


    // ==========================================
    // FORMATTAZIONE DELLE DATE
    // ==========================================

    function formattaGiorno(giorno) {

        const parti = giorno.split("-").map(Number);

        if (parti.length !== 3) {
            return giorno;
        }

        const data = new Date(
            parti[0],
            parti[1] - 1,
            parti[2]
        );

        return new Intl.DateTimeFormat("it-IT", {
            day: "numeric",
            month: "long"
        }).format(data);
    }


    // ==========================================
    // CREAZIONE SEPARATORE DATA
    // ==========================================

    function aggiungiSeparatore(giorno) {

        if (giorno === ultimoGiorno) {
            return;
        }

        const separatore = document.createElement("div");

        separatore.className = "chat-gruppo-separatore-data";

        const etichetta = document.createElement("span");

        etichetta.textContent = formattaGiorno(giorno);

        separatore.appendChild(etichetta);

        contenitore.appendChild(separatore);

        ultimoGiorno = giorno;
    }


    // ==========================================
    // CREAZIONE DELL'ORARIO
    // ==========================================

    function creaOrario(messaggio) {

        const orario = document.createElement("time");

        orario.className = "chat-gruppo-orario";

        orario.dateTime = messaggio.data_ora;

        orario.textContent = messaggio.orario;

        return orario;
    }


    // ==========================================
    // CREAZIONE DELLA BOLLA
    // ==========================================

    function creaBolla(messaggio, mioMessaggio) {

        const bolla = document.createElement("div");

        bolla.className = "chat-gruppo-bolla";

        // Per i messaggi degli altri membri
        // mostriamo anche il nome dell'autore.
        if (!mioMessaggio) {

            const autore = document.createElement("span");

            autore.className = "chat-gruppo-autore";

            autore.textContent = messaggio.autore_nome;

            bolla.appendChild(autore);
        }

        const testo = document.createElement("p");

        // Usiamo textContent per evitare
        // l'interpretazione di codice HTML.
        testo.textContent = messaggio.testo;

        // Manteniamo gli eventuali a capo.
        testo.style.whiteSpace = "pre-wrap";

        bolla.appendChild(testo);

        return bolla;
    }


    // ==========================================
    // CREAZIONE AVATAR
    // ==========================================

    function creaAvatar(messaggio) {

        const avatar = document.createElement("div");

        avatar.className = "chat-gruppo-avatar";

        if (messaggio.autore_foto) {

            const immagine = document.createElement("img");

            immagine.src = messaggio.autore_foto;

            immagine.alt = "";

            avatar.appendChild(immagine);

        } else {

            const simbolo = document.createElement("span");

            simbolo.setAttribute("aria-hidden", "true");

            simbolo.textContent = "♡";

            avatar.appendChild(simbolo);
        }

        return avatar;
    }


    // ==========================================
    // VISUALIZZAZIONE NUOVO MESSAGGIO
    // ==========================================

    function aggiungiMessaggio(messaggio) {

        const idMessaggio = Number(messaggio.id);

        if (
            !Number.isInteger(idMessaggio)
            || messaggiVisualizzati.has(idMessaggio)
        ) {
            return;
        }

        messaggiVisualizzati.add(idMessaggio);

        // Eliminiamo il messaggio iniziale
        // che segnala la conversazione vuota.
        const statoVuoto = contenitore.querySelector(
            ".chat-gruppo-vuota"
        );

        if (statoVuoto) {
            statoVuoto.remove();
        }

        aggiungiSeparatore(messaggio.giorno);

        const mioMessaggio = (
            Number(messaggio.autore_id) === mioProfiloId
        );

        // Elemento principale.
        const articolo = document.createElement("article");

        articolo.className = (
            "chat-gruppo-messaggio "
            + (
                mioMessaggio
                ? "chat-gruppo-mio"
                : "chat-gruppo-altro"
            )
        );

        articolo.dataset.messaggioId = idMessaggio;

        articolo.dataset.giorno = messaggio.giorno;

        const bolla = creaBolla(
            messaggio,
            mioMessaggio
        );

        const orario = creaOrario(messaggio);


        // ==================================
        // MESSAGGIO INVIATO DA ME
        // ==================================

        if (mioMessaggio) {

            articolo.appendChild(bolla);

            articolo.appendChild(orario);

        } else {

            // ==================================
            // MESSAGGIO DI UN ALTRO MEMBRO
            // ==================================

            const avatar = creaAvatar(messaggio);

            const contenuto = document.createElement("div");

            contenuto.className = (
                "chat-gruppo-messaggio-contenuto"
            );

            contenuto.appendChild(bolla);

            contenuto.appendChild(orario);

            articolo.appendChild(avatar);

            articolo.appendChild(contenuto);
        }

        contenitore.appendChild(articolo);

        scorriInBasso();
    }


    // ==========================================
    // CONFIGURAZIONE WEBSOCKET
    // ==========================================

    const protocollo = (
        window.location.protocol === "https:"
        ? "wss:"
        : "ws:"
    );

    const indirizzoWebSocket = (
        protocollo
        + "//"
        + window.location.host
        + "/ws/community/"
        + communityId
        + "/chat/"
        + (anteprima ? "?anteprima=1" : "")
    );


    // ==========================================
    // APERTURA CONNESSIONE
    // ==========================================

    try {

        socket = new WebSocket(indirizzoWebSocket);

        socket.addEventListener("open", function () {

            aggiornaStato(
                "Chat in tempo reale attiva."
            );

            nascondiErrore();
        });


        // ======================================
        // MESSAGGI RICEVUTI DAL SERVER
        // ======================================

        socket.addEventListener("message", function (event) {

            let dati;

            try {

                dati = JSON.parse(event.data);

            } catch (errore) {

                return;
            }

            if (dati.tipo === "connessione") {
                return;
            }

            // Errore restituito dal Consumer.
            if (dati.tipo === "errore") {

                ripristinaMessaggio();

                mostraErrore(dati.testo);

                return;
            }

            // Messaggio ricevuto in tempo reale.
            if (dati.tipo === "messaggio") {

                aggiungiMessaggio(dati);

                // Conferma del messaggio inviato da me.
                if (
                    Number(dati.autore_id) === mioProfiloId
                ) {

                    testoInAttesa = null;

                    invioInCorso = false;
                }

            }

        });


        // ======================================
        // CONNESSIONE CHIUSA
        // ======================================

        socket.addEventListener("close", function () {

            const messaggioDaVerificare = (
                testoInAttesa !== null
            );

            ripristinaMessaggio();

            aggiornaStato(
                "Connessione in tempo reale non disponibile. "
                + "Puoi utilizzare l'invio normale."
            );

            if (messaggioDaVerificare) {

                mostraErrore(
                    "Connessione interrotta durante l'invio. "
                    + "Prima di riprovare, verifica che il "
                    + "messaggio non sia già stato salvato."
                );
            }

            invioInCorso = false;
        });


        // ======================================
        // ERRORE DI CONNESSIONE
        // ======================================

        socket.addEventListener("error", function () {

            // Il ripristino viene gestito
            // dall'evento close.
            aggiornaStato(
                "Connessione in tempo reale non disponibile."
            );
        });

    } catch (errore) {

        socket = null;

        aggiornaStato(
            "Connessione in tempo reale non disponibile."
        );
    }


    // ==========================================
    // INVIO MESSAGGI
    // ==========================================

    // In anteprima il form non esiste:
    // la connessione serve solo a leggere.
    if (anteprima || !form || !input) {
        return;
    }

    form.addEventListener("submit", function (event) {

        const testo = input.value.trim();

        if (!testo) {

            event.preventDefault();

            input.focus();

            return;
        }

        // Blocchiamo altri invii quando uno
        // precedente non è ancora confermato.
        if (invioInCorso) {

            event.preventDefault();

            return;
        }

        // Se WebSocket è attivo, lo utilizziamo
        // al posto del normale invio HTTP.
        if (
            socket
            && socket.readyState === WebSocket.OPEN
        ) {

            event.preventDefault();

            invioInCorso = true;

            testoInAttesa = testo;

            try {

                socket.send(JSON.stringify({
                    tipo: "messaggio",
                    testo: testo
                }));

                input.value = "";

                nascondiErrore();

            } catch (errore) {

                ripristinaMessaggio();

                mostraErrore(
                    "Impossibile inviare il messaggio. Riprova."
                );
            }

        }

        // Se il WebSocket non è disponibile,
        // lasciamo procedere il form POST Django.
    });


    // ==========================================
    // CHIUSURA DEL WEBSOCKET
    // ==========================================

    window.addEventListener("pagehide", function () {

        if (socket) {
            socket.close();
        }

    });

});
