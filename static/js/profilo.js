document.addEventListener('DOMContentLoaded', function () {

    const pulsanteApri = document.getElementById('apri-conferma-logout');
    const overlay = document.getElementById('conferma-logout');
    const popup = overlay.querySelector('.logout-popup');
    const pulsanteAnnulla = document.getElementById('annulla-logout');

    if (!pulsanteApri || !overlay || !popup || !pulsanteAnnulla) {
        return;
    }

    let elementoPrecedente = null;

    function apriPopup() {
        elementoPrecedente = document.activeElement;
        overlay.hidden = false;
        document.body.classList.add('logout-aperto');
        pulsanteAnnulla.focus();
    }

    function chiudiPopup() {
        overlay.hidden = true;
        document.body.classList.remove('logout-aperto');

        if (elementoPrecedente) {
            elementoPrecedente.focus();
        }
    }

    pulsanteApri.addEventListener('click', apriPopup);
    pulsanteAnnulla.addEventListener('click', chiudiPopup);

    overlay.addEventListener('click', function (event) {
        if (event.target === overlay) {
            chiudiPopup();
        }
    });

    document.addEventListener('keydown', function (event) {

        if (overlay.hidden) return;

        if (event.key === 'Escape') {
            chiudiPopup();
        }

        if (event.key === 'Tab') {

            const elementi = Array.from(
                popup.querySelectorAll(
                    'button:not([disabled]), a[href], input:not([disabled])'
                )
            );

            const primo = elementi[0];
            const ultimo = elementi[elementi.length - 1];

            if (event.shiftKey && document.activeElement === primo) {
                event.preventDefault();
                ultimo.focus();
            } else if (!event.shiftKey && document.activeElement === ultimo) {
                event.preventDefault();
                primo.focus();
            }
        }
    });

});
