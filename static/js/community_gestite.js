
document.addEventListener("DOMContentLoaded", function () {

    const overlay = document.getElementById(
        "community-elimina-overlay"
    );

    const nome = document.getElementById(
        "community-elimina-nome"
    );

    const form = document.getElementById(
        "community-elimina-form"
    );

    const annulla = document.getElementById(
        "community-elimina-annulla"
    );

    const pulsanti = document.querySelectorAll(
        ".community-gestite-elimina"
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
