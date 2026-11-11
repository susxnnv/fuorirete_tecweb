
document.addEventListener("DOMContentLoaded", function () {

    const form = document.getElementById("form-interessi");

    if (!form) {
        return;
    }

    const clusters = Array.from(
        form.querySelectorAll(".cloud-cluster")
    );

    const inputs = Array.from(
        form.querySelectorAll(".cloud-input")
    );

    const contatore = document.getElementById(
        "interessi-contatore"
    );

    const riepilogo = document.getElementById(
        "interessi-scelti"
    );

    const messaggio = document.getElementById(
        "interessi-messaggio"
    );

    const conferma = document.getElementById(
        "interessi-conferma"
    );

    const MAX_INTERESSI = 6;


    // ======================================
    // FUNZIONI DI SUPPORTO
    // ======================================

    function inputMacro(cluster) {

        return cluster.querySelector(
            ".cloud-input-macro"
        );
    }

    function inputsSotto(cluster) {

        return Array.from(
            cluster.querySelectorAll(
                ".cloud-input-sotto"
            )
        );
    }

    function numeroSelezionati() {

        return inputs.filter(function (input) {
            return input.checked;
        }).length;
    }

    function mostraErrore(testo) {

        messaggio.textContent = testo;
    }

    function pulisciErrore() {

        messaggio.textContent = "";
    }


    // ======================================
    // POSIZIONAMENTO DEI SATELLITI
    // ======================================

    function posizionaSatelliti(cluster) {

        const satelliti = Array.from(
            cluster.querySelectorAll(".cloud-satellite")
        );

        const numero = satelliti.length;

        if (numero === 0) {
            return;
        }

        const larghezza = cluster.clientWidth;
        const altezza = cluster.clientHeight;

        const centroX = larghezza / 2;
        const centroY = altezza / 2;

        // Raggio dinamico per evitare che
        // gli interessi numerosi siano troppo vicini.

        const mobile = window.innerWidth <= 720;

        const minimo = mobile ? 117 : 136;

        const raggioNecessario =
            numero * (mobile ? 102 : 108) /
            (2 * Math.PI);

        const raggio = Math.max(
            minimo,
            raggioNecessario
        );

        satelliti.forEach(function (satellite, indice) {

            const angolo = (
                -90 + (360 / numero) * indice
            ) * Math.PI / 180;

            const x =
                centroX + raggio * Math.cos(angolo);

            const y =
                centroY + raggio * Math.sin(angolo);


            satellite.style.left = x + "px";
            satellite.style.top = y + "px";

            satellite.style.setProperty(
                "--indice-satellite",
                indice
            );

            satellite.style.setProperty(
                "--spostamento-x",
                (centroX - x) + "px"
            );

            satellite.style.setProperty(
                "--spostamento-y",
                (centroY - y) + "px"
            );


        });

    }


    // ======================================
    // APERTURA / CHIUSURA BOLLE
    // ======================================

    function chiudiCategoria(cluster) {

        const satelliti = cluster.querySelectorAll(
            ".cloud-satellite"
        );

        satelliti.forEach(function (satellite) {

            // Interrompe il movimento eventualmente in corso.
            satellite.getAnimations().forEach(function (animazione) {
                animazione.cancel();
            });

            // Ripristina lo stato originale.
            satellite.style.opacity = "";
            satellite.style.pointerEvents = "";
        });

        cluster.classList.remove("is-open");

        cluster.querySelector(
            ".cloud-macro"
        ).setAttribute("aria-expanded", "false");

        cluster.querySelector(
            ".cloud-satelliti"
        ).setAttribute("aria-hidden", "true");
    }



    function chiudiTutte() {

        clusters.forEach(function (cluster) {
            chiudiCategoria(cluster);
        });

    }


    function apriCategoria(cluster) {

        chiudiTutte();

        // Attivazione della categoria.
        cluster.classList.add("is-open");

        cluster.querySelector(
            ".cloud-macro"
        ).setAttribute("aria-expanded", "true");

        cluster.querySelector(
            ".cloud-satelliti"
        ).setAttribute("aria-hidden", "false");

        // Calcola le posizioni finali.
        posizionaSatelliti(cluster);

        const satelliti = Array.from(
            cluster.querySelectorAll(".cloud-satellite")
        );

        // Accessibilità: se il sistema richiede
        // movimento ridotto, mostra subito i satelliti.
        if (window.matchMedia(
            "(prefers-reduced-motion: reduce)"
        ).matches) {
            return;
        }

        const centroX = cluster.clientWidth / 2;
        const centroY = cluster.clientHeight / 2;

        const DURATA = 360;
        const INTERVALLO = 115;

        // Nasconde TUTTI i satelliti prima di avviare
        // la sequenza, evitando comparse improvvise.
        satelliti.forEach(function (satellite) {
            satellite.style.opacity = "0";
            satellite.style.pointerEvents = "none";
        });

        satelliti.forEach(function (satellite, indice) {

            const fineX = parseFloat(satellite.style.left);
            const fineY = parseFloat(satellite.style.top);

            let inizioX = centroX;
            let inizioY = centroY;

            if (indice > 0) {

                // Ogni satellite parte dalla posizione
                // finale del satellite precedente.
                const precedente = satelliti[indice - 1];

                inizioX = parseFloat(precedente.style.left);
                inizioY = parseFloat(precedente.style.top);
            }

            const dx = inizioX - fineX;
            const dy = inizioY - fineY;

            // Movimento progressivo in senso orario.
            const animazione = satellite.animate(
                [
                    {
                        opacity: 0,
                        transform:
                            `translate(-50%, -50%) ` +
                            `translate(${dx}px, ${dy}px) ` +
                            `scale(0.7)`
                    },
                    {
                        opacity: 1,
                        transform:
                            "translate(-50%, -50%) " +
                            "translate(0px, 0px) scale(1)"
                    }
                ],
                {
                    duration: DURATA,
                    delay: indice * INTERVALLO,
                    easing: "cubic-bezier(.22, 1, .36, 1)",
                    fill: "both"
                }
            );

            // Al termine lascia la bolla nella posizione
            // finale e ripristina la sua interattività.
            animazione.onfinish = function () {

                satellite.style.opacity = "1";
                satellite.style.pointerEvents = "";

                animazione.cancel();
            };

        });
    }




    // ======================================
    // SELEZIONE GENERALE
    // ======================================

    function selezionaMacro(cluster) {

        const generale = inputMacro(cluster);

        const sotto = inputsSotto(cluster);

        const avevaSelezioni = sotto.some(
            input => input.checked
        );

        const numeroAttuale = numeroSelezionati();

        // Se ci sono sottocategorie già scelte,
        // selezionare la macro le sostituisce.

        if (!generale.checked) {

            if (
                !avevaSelezioni &&
                numeroAttuale >= MAX_INTERESSI
            ) {

                mostraErrore(
                    "Puoi selezionare al massimo 6 interessi."
                );

                return;
            }

            sotto.forEach(function (input) {
                input.checked = false;
            });

            generale.checked = true;

        } else {

            // Un nuovo clic sulla macro già
            // selezionata la deseleziona.

            generale.checked = false;

        }

        pulisciErrore();
        aggiornaRiepilogo();

    }


    // ======================================
    // CLICK SULLE MACROCATEGORIE
    // ======================================

    clusters.forEach(function (cluster) {

        const pulsante = cluster.querySelector(
            ".cloud-macro"
        );

        pulsante.addEventListener("click", function () {

            const eraAperta =
                cluster.classList.contains("is-open");

            if (!eraAperta) {

                // Primo clic: apre la categoria.
                apriCategoria(cluster);

                const generale = inputMacro(cluster);

                const sottoPresenti = inputsSotto(
                    cluster
                ).some(input => input.checked);

                // Se non esistono già selezioni,
                // seleziona anche la macro generale.

                if (
                    !generale.checked &&
                    !sottoPresenti
                ) {

                    selezionaMacro(cluster);

                }

            } else {

                // Categoria già aperta:
                // consente di selezionare o
                // deselezionare la macro generale.

                selezionaMacro(cluster);

            }

        });

    });


    // ======================================
    // CLICK SULLE SOTTOCATEGORIE
    // ======================================

    clusters.forEach(function (cluster) {

        const generale = inputMacro(cluster);

        inputsSotto(cluster).forEach(function (input) {

            input.addEventListener("change", function () {

                if (input.checked) {

                    const totale = numeroSelezionati();

                    // Se la macro è selezionata,
                    // il nuovo interesse la sostituisce.

                    const totaleDopoSostituzione =
                        totale - (generale.checked ? 1 : 0);

                    if (
                        totaleDopoSostituzione >
                        MAX_INTERESSI
                    ) {

                        input.checked = false;

                        mostraErrore(
                            "Puoi selezionare al massimo 6 interessi."
                        );

                        aggiornaRiepilogo();
                        return;
                    }

                    generale.checked = false;

                }

                pulisciErrore();
                aggiornaRiepilogo();

            });

        });

    });


    // ======================================
    // CHIUSURA CLICCANDO FUORI
    // ======================================

    document.addEventListener("click", function (event) {

        const aperto = form.querySelector(
            ".cloud-cluster.is-open"
        );

        if (!aperto) {
            return;
        }

        // Un clic su una qualsiasi bolla
        // non chiude automaticamente il cluster.

        if (
            event.target.closest(
                ".cloud-macro, .cloud-satellite"
            )
        ) {
            return;
        }

        chiudiTutte();

    });


    // ======================================
    // CHIUSURA CON ESCAPE
    // ======================================

    document.addEventListener("keydown", function (event) {

        if (event.key === "Escape") {
            chiudiTutte();
        }

    });


    // ======================================
    // RIEPILOGO INTERESSI
    // ======================================

    function aggiornaRiepilogo() {

        const selezionati = inputs.filter(
            input => input.checked
        );

        contatore.textContent =
            selezionati.length +
            " / " +
            MAX_INTERESSI;

        riepilogo.replaceChildren();

        if (selezionati.length === 0) {

            const vuoto = document.createElement("span");

            vuoto.className = "interessi-vuoto";

            vuoto.textContent =
                "Non hai ancora selezionato interessi.";

            riepilogo.appendChild(vuoto);

            conferma.disabled = true;

            return;
        }

        selezionati.forEach(function (input) {

            const cluster = input.closest(
                ".cloud-cluster"
            );

            let testo = "";

            if (input.dataset.tipo === "macro") {

                testo = cluster.querySelector(
                    ".cloud-macro-nome"
                ).textContent.trim();

            } else {

                const nomeCategoria = cluster.querySelector(
                    ".cloud-macro-nome"
                ).textContent.trim();

                const nomeInteresse = input.closest(
                    ".cloud-satellite"
                ).querySelector(
                    ".cloud-satellite-nome"
                ).textContent.trim();

                testo =
                    nomeCategoria +
                    " · " +
                    nomeInteresse;

            }

            const tag = document.createElement("span");

            tag.className = "interessi-tag";

            const nomeTag = document.createElement("span");

            nomeTag.textContent = testo;

            const elimina = document.createElement(
                "button"
            );

            elimina.type = "button";
            elimina.textContent = "×";

            elimina.setAttribute(
                "aria-label",
                "Rimuovi " + testo
            );

            elimina.addEventListener("click", function () {

                input.checked = false;

                pulisciErrore();
                aggiornaRiepilogo();

            });

            tag.appendChild(nomeTag);
            tag.appendChild(elimina);

            riepilogo.appendChild(tag);

        });

        conferma.disabled = false;

    }


    // ======================================
    // VALIDAZIONE INVIO
    // ======================================

    form.addEventListener("submit", function (event) {

        const numero = numeroSelezionati();

        if (
            numero < 1 ||
            numero > MAX_INTERESSI
        ) {

            event.preventDefault();

            mostraErrore(
                "Seleziona da 1 a 6 interessi."
            );

            messaggio.scrollIntoView({
                behavior: "smooth",
                block: "center"
            });

        }

    });


    // ======================================
    // RIDIMENSIONAMENTO FINESTRA
    // ======================================

    window.addEventListener("resize", function () {

        const aperto = form.querySelector(
            ".cloud-cluster.is-open"
        );

        if (aperto) {
            posizionaSatelliti(aperto);
        }

    });


    // ======================================
    // INIZIALIZZAZIONE
    // ======================================

    // Evita selezioni ridondanti eventualmente
    // presenti nei dati iniziali.

    clusters.forEach(function (cluster) {

        const generale = inputMacro(cluster);

        if (generale.checked) {

            inputsSotto(cluster).forEach(function (input) {
                input.checked = false;
            });

        }

    });

    aggiornaRiepilogo();

});

