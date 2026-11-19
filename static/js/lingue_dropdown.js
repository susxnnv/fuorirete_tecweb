document.addEventListener('DOMContentLoaded', function () {

    const contenitore = document.getElementById('lingue-dropdown');
    const trigger = document.getElementById('lingue-dropdown-trigger');
    const opzioni = document.getElementById('lingue-dropdown-opzioni');
    const selezionate = document.getElementById('lingue-dropdown-selezionate');
    const aiuto = document.getElementById('lingue-dropdown-aiuto');

    if (!contenitore || !trigger || !opzioni || !selezionate) {
        return;
    }

    const checkbox = Array.from(
        opzioni.querySelectorAll('input[type="checkbox"]')
    );

    const massimo = 4;

    function nomeLingua(input) {
        const label = input.closest('label');
        return label ? label.textContent.trim() : input.value;
    }

    function impostaApertura(aperto) {
        trigger.setAttribute('aria-expanded', String(aperto));
        opzioni.classList.toggle('lingue-js-chiuso', !aperto);
    }

    function aggiornaSelezione() {

        const attive = checkbox.filter(input => input.checked);

        selezionate.replaceChildren();

        if (attive.length === 0) {

            const placeholder = document.createElement('span');
            placeholder.className = 'lingue-dropdown-placeholder';
            placeholder.textContent = 'Seleziona le lingue...';

            selezionate.appendChild(placeholder);

        } else {

            attive.forEach(input => {

                const tag = document.createElement('span');

                tag.className = 'lingue-dropdown-tag';
                tag.textContent = nomeLingua(input);

                selezionate.appendChild(tag);

            });

        }

        const limiteRaggiunto = attive.length >= massimo;

        checkbox.forEach(input => {

            const disabilita = limiteRaggiunto && !input.checked;
            input.disabled = disabilita;

            const label = input.closest('label');

            if (label) {
                label.classList.toggle(
                    'lingue-disabilitata',
                    disabilita
                );
            }

        });

        if (aiuto) {
            aiuto.textContent =
                attive.length + ' di ' + massimo +
                ' lingue selezionate.';
        }

    }

    impostaApertura(false);
    aggiornaSelezione();

    trigger.addEventListener('click', function () {

        const aperto =
            trigger.getAttribute('aria-expanded') === 'true';

        impostaApertura(!aperto);

    });

    checkbox.forEach(input => {
        input.addEventListener('change', aggiornaSelezione);
    });

    document.addEventListener('click', function (event) {

        if (!contenitore.contains(event.target)) {
            impostaApertura(false);
        }

    });

    document.addEventListener('keydown', function (event) {

        if (event.key === 'Escape') {

            impostaApertura(false);

            if (contenitore.contains(document.activeElement)) {
                trigger.focus();
            }

        }

    });

});
