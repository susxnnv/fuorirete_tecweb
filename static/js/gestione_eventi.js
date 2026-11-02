
document.addEventListener("DOMContentLoaded", function () {

    const overlay = document.getElementById(
        "elimina-evento-overlay"
    );

    const nome = document.getElementById(
        "elimina-evento-nome"
    );

    const form = document.getElementById(
        "elimina-evento-form"
    );

    const annulla = document.getElementById(
        "annulla-elimina-evento"
    );

    const pulsanti = document.querySelectorAll(
        ".apri-elimina-evento"
    );

    if (!overlay || !nome || !form || !annulla) {
        return;
    }

    let pulsanteAttivo = null;

    function chiudiPopup() {
        overlay.hidden = true;

        if (pulsanteAttivo) {
            pulsanteAttivo.focus();
        }
    }

    pulsanti.forEach(function (pulsante) {

        pulsante.addEventListener("click", function () {

            pulsanteAttivo = pulsante;

            nome.textContent = pulsante.dataset.eliminaTitolo;

            form.action = pulsante.dataset.eliminaUrl;

            overlay.hidden = false;

            annulla.focus();
        });

    });

    annulla.addEventListener("click", chiudiPopup);

    overlay.addEventListener("click", function (event) {

        if (event.target === overlay) {
            chiudiPopup();
        }

    });

    document.addEventListener("keydown", function (event) {

        if (event.key === "Escape" && !overlay.hidden) {
            chiudiPopup();
        }

    });

});
