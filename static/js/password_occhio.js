
document.addEventListener('DOMContentLoaded', function () {

    const pulsanti = document.querySelectorAll('.password-occhio');

    pulsanti.forEach(function (pulsante) {

        const contenitore = pulsante.closest('.password-contenitore');

        if (!contenitore) {
            return;
        }

        const input = contenitore.querySelector('input');

        if (!input) {
            return;
        }

        pulsante.addEventListener('click', function () {

            const visibile = input.type === 'password';

            // Mostra o nasconde la password.
            input.type = visibile ? 'text' : 'password';

            // Aggiorna le informazioni di accessibilità.
            pulsante.setAttribute(
                'aria-label',
                visibile ? 'Nascondi password' : 'Mostra password'
            );

            pulsante.setAttribute(
                'aria-pressed',
                String(visibile)
            );

            pulsante.setAttribute(
                'title',
                visibile ? 'Nascondi password' : 'Mostra password'
            );

            // Cambia l'icona quando la password è visibile.
            const svg = pulsante.querySelector('svg');

            if (svg) {
                svg.innerHTML = visibile
                    ? '<path d="M3 3l18 18"/><path d="M10.6 6.1A11 11 0 0 1 12 6c6.5 0 10 6 10 6a15 15 0 0 1-4 4.2"/><path d="M6.4 6.5C3.5 8.3 2 12 2 12s3.5 6 10 6c1.2 0 2.3-.2 3.3-.6"/><path d="M10 10a3 3 0 0 0 4 4"/>'
                    : '<path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>';
            }

        });

    });

});
