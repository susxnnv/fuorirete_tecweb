
document.addEventListener("DOMContentLoaded", function () {

    // ANTEPRIMA IMMAGINI

    const campiFile = document.querySelectorAll(
        ".gestione-immagine-input[type='file']"
    );

    campiFile.forEach(function (input) {

        const anteprima = document.getElementById(
            input.dataset.anteprima
        );

        if (!anteprima) {
            return;
        }

        let urlTemporaneo = null;

        input.addEventListener("change", function () {

            const file = input.files[0];

            if (!file) {
                return;
            }

            if (urlTemporaneo) {
                URL.revokeObjectURL(urlTemporaneo);
            }

            urlTemporaneo = URL.createObjectURL(file);

            anteprima.src = urlTemporaneo;
            anteprima.hidden = false;

            const segnaposto = anteprima.parentElement.querySelector(
                ".gestione-immagine-segnaposto"
            );

            if (segnaposto) {
                segnaposto.hidden = true;
            }

            // Se scelgo una nuova immagine,
            // annullo l'eventuale richiesta di rimozione.

            const checkboxRimozione = document.getElementById(
                "id_immagine-clear"
            );

            if (input.id === "id_immagine" && checkboxRimozione) {

                checkboxRimozione.checked = false;

                const stato = document.getElementById(
                    "stato-rimozione-community"
                );

                if (stato) {
                    stato.textContent = "";
                }
            }

        });

    });


    // RIMOZIONE IMMAGINE COMMUNITY

    const pulsanteRimuovi = document.getElementById(
        "rimuovi-immagine-community"
    );

    const checkboxRimozione = document.getElementById(
        "id_immagine-clear"
    );

    const inputCommunity = document.getElementById(
        "id_immagine"
    );

    const anteprimaCommunity = document.getElementById(
        "anteprima-community"
    );

    const statoRimozione = document.getElementById(
        "stato-rimozione-community"
    );

    if (
        pulsanteRimuovi &&
        checkboxRimozione &&
        inputCommunity &&
        anteprimaCommunity
    ) {

        const fotoOriginale = anteprimaCommunity.getAttribute(
            "src"
        );

        pulsanteRimuovi.addEventListener("click", function () {

            checkboxRimozione.checked =
                !checkboxRimozione.checked;

            if (checkboxRimozione.checked) {

                // Rimuove anche un eventuale file appena scelto.
                inputCommunity.value = "";

                anteprimaCommunity.hidden = true;

                pulsanteRimuovi.textContent =
                    "Annulla rimozione";

                statoRimozione.textContent =
                    "L'immagine verrà rimossa quando salverai.";

            } else {

                if (fotoOriginale) {
                    anteprimaCommunity.src = fotoOriginale;
                    anteprimaCommunity.hidden = false;
                } else {
                    anteprimaCommunity.hidden = true;
                }

                pulsanteRimuovi.textContent = "Rimuovi";
                statoRimozione.textContent = "";
            }

            const segnaposto =
                anteprimaCommunity.parentElement.querySelector(
                    ".gestione-immagine-segnaposto"
                );

            if (segnaposto) {
                segnaposto.hidden = !anteprimaCommunity.hidden;
            }

        });

    }

});


/* ==========================================
   ANTEPRIMA IMMAGINI - CREAZIONE
========================================== */

document.addEventListener("DOMContentLoaded", function () {

    document.querySelectorAll(
        ".gestione-immagine-creazione"
    ).forEach(function (contenitore) {

        const input = contenitore.querySelector('input[type="file"]');

        const anteprima = contenitore.querySelector(
            ".gestione-immagine-anteprima img"
        );

        const segnaposto = contenitore.querySelector(
            ".gestione-immagine-segnaposto"
        );

        const rimuovi = contenitore.querySelector(
            ".gestione-immagine-rimuovi"
        );

        if (!input || !anteprima || !segnaposto || !rimuovi) {
            return;
        }

        let urlTemporaneo = null;

        function pulisciAnteprima() {

            if (urlTemporaneo) {
                URL.revokeObjectURL(urlTemporaneo);
                urlTemporaneo = null;
            }

            anteprima.removeAttribute("src");
            anteprima.hidden = true;

            segnaposto.hidden = false;
            rimuovi.hidden = true;
        }

        input.addEventListener("change", function () {

            const file = input.files[0];

            if (!file) {
                pulisciAnteprima();
                return;
            }

            if (!file.type.startsWith("image/")) {
                input.value = "";
                pulisciAnteprima();
                return;
            }

            if (urlTemporaneo) {
                URL.revokeObjectURL(urlTemporaneo);
            }

            urlTemporaneo = URL.createObjectURL(file);

            anteprima.src = urlTemporaneo;
            anteprima.hidden = false;

            segnaposto.hidden = true;
            rimuovi.hidden = false;
        });

        // Solo quando clicchi Rimuovi
        // cancelliamo il file selezionato.

        rimuovi.addEventListener("click", function () {

            input.value = "";
            pulisciAnteprima();

        });

        // Nascondiamo gli elementi iniziali,
        // senza svuotare il campo file.
        if (input.files.length === 0) {
            pulisciAnteprima();
        }

    });

});
