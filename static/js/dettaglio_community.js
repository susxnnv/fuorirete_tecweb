
document.addEventListener("DOMContentLoaded", function () {

    const apri = document.getElementById(
        "apri-uscita-community"
    );

    const annulla = document.getElementById(
        "annulla-uscita-community"
    );

    const overlay = document.getElementById(
        "uscita-community-overlay"
    );

    if (!apri || !annulla || !overlay) {
        return;
    }

    function apriPopup() {
        overlay.hidden = false;
        annulla.focus();
    }

    function chiudiPopup() {
        overlay.hidden = true;
        apri.focus();
    }

    apri.addEventListener("click", apriPopup);

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


document.addEventListener("DOMContentLoaded", function () {
    const pulsante = document.getElementById("apri-eliminazione-community");
    const overlay = document.getElementById("eliminazione-community-overlay");
    const annulla = document.getElementById("annulla-eliminazione-community");

    if (!pulsante || !overlay || !annulla) return;

    pulsante.addEventListener("click", function () {
        overlay.hidden = false;
    });

    annulla.addEventListener("click", function () {
        overlay.hidden = true;
    });
});