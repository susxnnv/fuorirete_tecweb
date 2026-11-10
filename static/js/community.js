
document.addEventListener("DOMContentLoaded", function () {

    const apri = document.getElementById(
        "apri-filtri-community"
    );

    const chiudi = document.getElementById(
        "chiudi-filtri-community"
    );

    const overlay = document.getElementById(
        "filtri-community-overlay"
    );

    const azzera = document.getElementById(
        "azzera-filtri-community"
    );

    if (!apri || !chiudi || !overlay) {
        return;
    }

    const form = overlay.querySelector("form");

    function apriFiltri() {
        overlay.hidden = false;

        document.body.classList.add(
            "scoperta-community-filtri-aperti"
        );

        chiudi.focus();
    }

    function chiudiFiltri() {
        overlay.hidden = true;

        document.body.classList.remove(
            "scoperta-community-filtri-aperti"
        );

        apri.focus();
    }

    apri.addEventListener("click", apriFiltri);

    chiudi.addEventListener("click", chiudiFiltri);

    // Clic sullo sfondo oscurato.
    overlay.addEventListener("click", function (event) {

        if (event.target === overlay) {
            chiudiFiltri();
        }
    });

    // Chiusura tramite Escape.
    document.addEventListener("keydown", function (event) {

        if (event.key === "Escape" && !overlay.hidden) {
            chiudiFiltri();
        }
    });

    // Azzera soltanto i tre filtri.
    // La ricerca testuale rimane invariata.
    if (azzera && form) {

        azzera.addEventListener("click", function (event) {

            event.preventDefault();

            const citta = form.querySelector(
                'input[name="citta"]'
            );

            if (citta) {
                citta.value = "";
            }

            form.querySelectorAll(
                'input[name="interessi"]'
            ).forEach(function (input) {
                input.checked = false;
            });

            const tutte = form.querySelector(
                'input[name="partecipazione"][value="tutte"]'
            );

            if (tutte) {
                tutte.checked = true;
            }

        });
    }

});
