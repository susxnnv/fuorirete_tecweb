document.addEventListener('DOMContentLoaded', function () {

    // ========================================
    // POPUP FILTRI
    // ========================================

    const pulsanteApri = document.getElementById('apri-filtri');
    const overlay = document.getElementById('popup-filtri');
    const popup = overlay.querySelector('.persone-filtri-popup');
    const pulsanteChiudi = document.getElementById('chiudi-filtri');

    let elementoPrecedente = null;

    function apriFiltri() {
        elementoPrecedente = document.activeElement;
        overlay.hidden = false;
        document.body.classList.add('persone-filtri-aperti');
        pulsanteChiudi.focus();
    }

    function chiudiFiltri() {
        overlay.hidden = true;
        document.body.classList.remove('persone-filtri-aperti');

        if (elementoPrecedente) {
            elementoPrecedente.focus();
        }
    }

    pulsanteApri.addEventListener('click', apriFiltri);
    pulsanteChiudi.addEventListener('click', chiudiFiltri);

    overlay.addEventListener('click', function (event) {
        if (event.target === overlay) {
            chiudiFiltri();
        }
    });


    // ========================================
    // SLIDER ETA MINIMA E MASSIMA
    // ========================================

    // ========================================
    // BARRA ETA CON DUE CURSORI
    // ========================================

    const sliderMinimo = document.getElementById(
        'filtro-eta-minima'
    );

    const sliderMassimo = document.getElementById(
        'filtro-eta-massima'
    );

    const valoreMinimo = document.getElementById(
        'valore-eta-minima'
    );

    const valoreMassimo = document.getElementById(
        'valore-eta-massima'
    );

    const intervalloEta = document.getElementById(
        'persone-eta-intervallo'
    );

    function aggiornaIntervalloEta() {

        const minimo = Number(sliderMinimo.value);
        const massimo = Number(sliderMassimo.value);

        const percentualeMinima =
            ((minimo - 18) / (100 - 18)) * 100;

        const percentualeMassima =
            ((massimo - 18) / (100 - 18)) * 100;

        intervalloEta.style.left =
            percentualeMinima + '%';

        intervalloEta.style.right =
            (100 - percentualeMassima) + '%';

        valoreMinimo.textContent = minimo;
        valoreMassimo.textContent = massimo;

        // Il cursore attualmente selezionato
        // resta davanti all'altro.

        if (minimo >= 90) {
            sliderMinimo.style.zIndex = '2';
            sliderMassimo.style.zIndex = '1';
        } else {
            sliderMinimo.style.zIndex = '1';
            sliderMassimo.style.zIndex = '2';
        }
    }

    // MUOVO IL CURSORE SINISTRO

    sliderMinimo.addEventListener('input', function () {

        if (
            Number(sliderMinimo.value) >
            Number(sliderMassimo.value)
        ) {
            sliderMinimo.value = sliderMassimo.value;
        }

        aggiornaIntervalloEta();
    });

    // MUOVO IL CURSORE DESTRO

    sliderMassimo.addEventListener('input', function () {

        if (
            Number(sliderMassimo.value) <
            Number(sliderMinimo.value)
        ) {
            sliderMassimo.value = sliderMinimo.value;
        }

        aggiornaIntervalloEta();
    });

    // STATO INIZIALE

    aggiornaIntervalloEta();


    // ========================================
    // MULTISELEZIONE CON RICERCA
    // ========================================

    const multiselects = document.querySelectorAll(
        '.persone-multiselect'
    );

    multiselects.forEach(function (multiselect) {

        const triggerTesto = multiselect.querySelector(
            '.persone-multiselect-testo'
        );

        const opzioni = Array.from(
            multiselect.querySelectorAll(
                '.persone-multiselect-opzioni .persone-filtro-opzione'
            )
        );

        const testoIniziale = triggerTesto.textContent.trim();

        function aggiornaSelezione() {

            const selezionati = opzioni.filter(function (opzione) {
                return opzione.querySelector(
                    'input[type="checkbox"]'
                ).checked;
            });

            if (selezionati.length === 0) {

                triggerTesto.textContent = testoIniziale;

            } else if (selezionati.length === 1) {

                triggerTesto.textContent = selezionati[0]
                    .querySelector('span')
                    .textContent
                    .trim();

            } else {

                triggerTesto.textContent =
                    selezionati.length + ' selezionate';

            }
        }

        opzioni.forEach(function (opzione) {

            const checkbox = opzione.querySelector(
                'input[type="checkbox"]'
            );

            checkbox.addEventListener(
                'change',
                aggiornaSelezione
            );

        });

        multiselect.addEventListener('toggle', function () {

            if (multiselect.open) {

                multiselects.forEach(function (altro) {

                    if (altro !== multiselect) {
                        altro.open = false;
                    }

                });

            }

        });

        aggiornaSelezione();

    });

    // Chiudi i menu cliccando fuori da essi

    document.addEventListener('click', function (event) {

        multiselects.forEach(function (multiselect) {

            if (
                multiselect.open &&
                !multiselect.contains(event.target)
            ) {
                multiselect.open = false;
            }

        });

    });


    // ========================================
    // TASTIERA: ESC E TAB
    // ========================================

    document.addEventListener('keydown', function (event) {

        if (overlay.hidden) {
            return;
        }

        if (event.key === 'Escape') {

            const menuAperti = Array.from(multiselects).filter(
                function (multiselect) {
                    return multiselect.open;
                }
            );

            if (menuAperti.length > 0) {

                menuAperti.forEach(function (multiselect) {
                    multiselect.open = false;
                });

            } else {

                chiudiFiltri();

            }

            event.preventDefault();
            return;
        }

        if (event.key === 'Tab') {

            const elementi = Array.from(
                popup.querySelectorAll(
                    'button:not([disabled]), a[href], summary, input:not([disabled]), select:not([disabled])'
                )
            ).filter(function (elemento) {

                return elemento.getClientRects().length > 0;

            });

            if (!elementi.length) {
                return;
            }

            const primo = elementi[0];
            const ultimo = elementi[elementi.length - 1];

            if (
                event.shiftKey &&
                document.activeElement === primo
            ) {

                event.preventDefault();
                ultimo.focus();

            } else if (
                !event.shiftKey &&
                document.activeElement === ultimo
            ) {

                event.preventDefault();
                primo.focus();

            }

        }

    });

});

document.addEventListener('DOMContentLoaded', function () {

    const scheda = document.querySelector('.persone-scheda');

    if (!scheda) {
        return;
    }

    // Apertura del dettaglio della persona

    function apriDettaglio() {
        window.location.href = scheda.dataset.dettaglioUrl;
    }

    scheda.addEventListener('click', function (event) {

        // I controlli interattivi non aprono il dettaglio.
        if (event.target.closest(
            'button, a, input, select, textarea, form'
        )) {
            return;
        }

        apriDettaglio();
    });

    scheda.addEventListener('keydown', function (event) {

        if (
            event.target === scheda &&
            (event.key === 'Enter' || event.key === ' ')
        ) {
            event.preventDefault();
            apriDettaglio();
        }

    });

    // Animazione Like e Dislike

    const formValutazioni = scheda.querySelectorAll(
        '.persone-form-valutazione'
    );

    let invioInCorso = false;

    formValutazioni.forEach(function (form) {

        form.addEventListener('submit', function (event) {

            if (invioInCorso) {
                event.preventDefault();
                return;
            }

            // Se l'utente preferisce animazioni ridotte,
            // il form viene inviato normalmente.
            if (
                window.matchMedia(
                    '(prefers-reduced-motion: reduce)'
                ).matches
            ) {
                return;
            }

            event.preventDefault();
            invioInCorso = true;

            // Direzione dell'animazione:
            // Like a destra, Dislike a sinistra.
            const direzione = form.dataset.direzione || 'destra';

            if (direzione === 'sinistra') {
                scheda.classList.add('persone-scheda-dislike');
            } else {
                scheda.classList.add('persone-scheda-like');
            }

            // Disabilita i pulsanti per impedire
            // valutazioni multiple durante l'animazione.
            formValutazioni.forEach(function (altroForm) {
                const pulsante = altroForm.querySelector(
                    'button[type="submit"]'
                );

                if (pulsante) {
                    pulsante.disabled = true;
                }
            });

            // Terminata l'animazione, invia il form
            // originale a Django.
            window.setTimeout(function () {
                HTMLFormElement.prototype.submit.call(form);
            }, 320);

        });

    });

});

