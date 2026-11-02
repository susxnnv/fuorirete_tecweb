
document.addEventListener("DOMContentLoaded", function () {

    const widgets = document.querySelectorAll(
        ".filtro-interessi-widget"
    );

    widgets.forEach(function (widget) {

        const categorie = Array.from(
            widget.querySelectorAll(".filtro-interessi-categoria")
        ); 
        
        // SCORRIMENTO ORIZZONTALE DELLE MACROCATEGORIE

        const contenitoreCategorie = widget.querySelector(
            ".filtro-interessi-categorie"
        );

        const frecciaSinistra = widget.querySelector(
            ".filtro-interessi-freccia-sinistra"
        );

        const frecciaDestra = widget.querySelector(
            ".filtro-interessi-freccia-destra"
        );

        function aggiornaFrecce() {

            const posizione = contenitoreCategorie.scrollLeft;

            const massimo =
                contenitoreCategorie.scrollWidth -
                contenitoreCategorie.clientWidth;

            frecciaSinistra.disabled = posizione <= 1;

            frecciaDestra.disabled = posizione >= massimo - 1;
        }

        frecciaSinistra.addEventListener("click", function () {

            contenitoreCategorie.scrollBy({
                left: -200,
                behavior: "smooth"
            });

        });

        frecciaDestra.addEventListener("click", function () {

            contenitoreCategorie.scrollBy({
                left: 200,
                behavior: "smooth"
            });

        });

        contenitoreCategorie.addEventListener(
            "scroll",
            aggiornaFrecce
        );

        window.addEventListener("resize", aggiornaFrecce);


        const pannelli = Array.from(
            widget.querySelectorAll(".filtro-interessi-pannello")
        );

        const inputsGenerali = Array.from(
            widget.querySelectorAll(".filtro-interessi-input-generale")
        );

        const inputsSotto = Array.from(
            widget.querySelectorAll(".filtro-interessi-input-sotto")
        );

        const pulsantiGenerali = Array.from(
            widget.querySelectorAll(".filtro-interessi-seleziona-generale")
        );

        const contenitoreTags = widget.querySelector(
            ".filtro-interessi-tags"
        );

        const pulsanteCancella = widget.querySelector(
            ".filtro-interessi-cancella"
        );

        // NAVIGAZIONE TRA MACROCATEGORIE

        function apriCategoria(id) {

            categorie.forEach(function (pulsante) {

                const attiva = pulsante.dataset.categoria === id;

                pulsante.classList.toggle("is-active", attiva);

                pulsante.setAttribute(
                    "aria-expanded",
                    String(attiva)
                );

            });

            pannelli.forEach(function (pannello) {
                pannello.hidden = pannello.dataset.pannello !== id;
            });

        }

        categorie.forEach(function (pulsante) {

            pulsante.addEventListener("click", function () {
                apriCategoria(pulsante.dataset.categoria);
            });

        });


        // AGGIORNAMENTO PULSANTI GENERALI

        function aggiornaPulsantiGenerali() {

            pulsantiGenerali.forEach(function (pulsante) {

                const id = pulsante.dataset.selezionaMacro;

                const input = inputsGenerali.find(function (elemento) {
                    return elemento.dataset.macro === id;
                });

                if (!input) {
                    return;
                }

                pulsante.classList.toggle(
                    "is-selected",
                    input.checked
                );

                pulsante.setAttribute(
                    "aria-pressed",
                    String(input.checked)
                );

                pulsante.textContent = input.checked
                    ? "✓ Categoria generale selezionata"
                    : "Seleziona tutta la categoria";

            });

        }


        // SELEZIONE DELLA MACROCATEGORIA GENERALE

        pulsantiGenerali.forEach(function (pulsante) {

            pulsante.addEventListener("click", function () {

                const id = pulsante.dataset.selezionaMacro;

                const input = inputsGenerali.find(function (elemento) {
                    return elemento.dataset.macro === id;
                });

                if (!input) {
                    return;
                }

                input.checked = !input.checked;

                if (input.checked) {

                    inputsSotto.forEach(function (sotto) {

                        if (sotto.dataset.padre === id) {
                            sotto.checked = false;
                        }

                    });

                }

                aggiornaInterfaccia();
                aggiornaFrecce();

            });

        });

        // SELEZIONE DELLE SOTTOCATEGORIE

        inputsSotto.forEach(function (input) {

            input.addEventListener("change", function () {

                if (input.checked) {

                    const generale = inputsGenerali.find(
                        function (elemento) {
                            return elemento.dataset.macro ===
                                input.dataset.padre;
                        }
                    );

                    if (generale) {
                        generale.checked = false;
                    }

                }

                aggiornaInterfaccia();

            });

        });


        // RIEPILOGO DELLE SELEZIONI

        function aggiornaRiepilogo() {

            contenitoreTags.replaceChildren();

            const selezionati = [
                ...inputsGenerali,
                ...inputsSotto
            ].filter(function (input) {
                return input.checked;
            });

            if (selezionati.length === 0) {

                const vuoto = document.createElement("span");

                vuoto.className =
                    "filtro-interessi-riepilogo-vuoto";

                vuoto.textContent =
                    "Nessun interesse selezionato.";

                contenitoreTags.appendChild(vuoto);

                return;
            }

            selezionati.forEach(function (input) {

                let nome = "";

                if (
                    input.classList.contains(
                        "filtro-interessi-input-generale"
                    )
                ) {

                    const categoria = categorie.find(
                        function (pulsante) {
                            return pulsante.dataset.categoria ===
                                input.dataset.macro;
                        }
                    );

                    if (categoria) {
                        nome = categoria.textContent.trim();
                    }

                } else {

                    const categoria = categorie.find(
                        function (pulsante) {
                            return pulsante.dataset.categoria ===
                                input.dataset.padre;
                        }
                    );

                    if (categoria) {

                        nome =
                            categoria.textContent.trim() +
                            " · " +
                            input.dataset.nome;

                    }

                }

                const tag = document.createElement("button");

                tag.type = "button";
                tag.className = "filtro-interessi-tag";
                tag.textContent = nome + " ×";

                tag.setAttribute(
                    "aria-label",
                    "Rimuovi " + nome
                );

                tag.addEventListener("click", function () {

                    input.checked = false;
                    aggiornaInterfaccia();

                });

                contenitoreTags.appendChild(tag);

            });

        }


        function aggiornaInterfaccia() {

            aggiornaPulsantiGenerali();
            aggiornaRiepilogo();

        }


        // CANCELLA SOLTANTO GLI INTERESSI

        pulsanteCancella.addEventListener("click", function () {

            [...inputsGenerali, ...inputsSotto].forEach(
                function (input) {
                    input.checked = false;
                }
            );

            aggiornaInterfaccia();

        });


        // SINCRONIZZAZIONE DOPO IL RESET DEL FORM

        const form = widget.closest("form");

        if (form) {

            form.addEventListener("reset", function () {

                queueMicrotask(function () {
                    aggiornaInterfaccia();
                });

            });

        }

        // INIZIALIZZAZIONE

        // Se una categoria generale risulta già selezionata,
        // eliminiamo eventuali sottocategorie ridondanti.

        inputsGenerali.forEach(function (generale) {

            if (!generale.checked) {
                return;
            }

            inputsSotto.forEach(function (sotto) {

                if (sotto.dataset.padre === generale.dataset.macro) {
                    sotto.checked = false;
                }

            });

        });

        if (categorie.length > 0) {

            const selezionato = [
                ...inputsGenerali,
                ...inputsSotto
            ].find(function (input) {
                return input.checked;
            });

            const categoriaIniziale = selezionato
                ? (
                    selezionato.dataset.macro ||
                    selezionato.dataset.padre
                )
                : categorie[0].dataset.categoria;

            apriCategoria(categoriaIniziale);

        }

        aggiornaInterfaccia();

    });

});
