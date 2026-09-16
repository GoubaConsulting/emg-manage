/*
==========================================================
Projet : EMG MANAGE

Confirmation avant enregistrement des formulaires.
==========================================================
*/

(function () {

    let dernierBoutonSubmit = null;

    document.addEventListener(
        "click",
        function (event) {

            const bouton = event.target.closest(
                "button, input"
            );

            if (
                bouton &&
                String(bouton.type || "").toLowerCase() === "submit"
            ) {

                dernierBoutonSubmit = bouton;

            }

        },
        true
    );

    document.addEventListener(
        "submit",
        function (event) {

            const formulaire = event.target;

            if (!formulaire || formulaire.dataset.confirmedSubmit === "1") {

                if (formulaire) {

                    delete formulaire.dataset.confirmedSubmit;

                }

                return;

            }

            const bouton = (
                event.submitter ||
                dernierBoutonSubmit
            );

            const declencheur = trouverDeclencheurConfirmation(
                formulaire,
                bouton
            );

            if (!declencheur) {

                return;

            }

            event.preventDefault();

            demanderConfirmation(
                {
                    titre: (
                        declencheur.dataset.confirmTitle ||
                        "Confirmation"
                    ),
                    message: (
                        declencheur.dataset.confirmMessage ||
                        "Voulez-vous vraiment enregistrer ces informations ?"
                    ),
                    libelleConfirmer: (
                        declencheur.dataset.confirmButton ||
                        "Confirmer"
                    )
                },
                function () {

                    soumettreFormulaire(
                        formulaire,
                        bouton
                    );

                }
            );

        }
    );


    function trouverDeclencheurConfirmation(formulaire, bouton) {

        if (
            bouton &&
            bouton.matches &&
            bouton.matches("[data-confirm-submit]")
        ) {

            return bouton;

        }

        if (
            formulaire.matches &&
            formulaire.matches("[data-confirm-submit]")
        ) {

            return formulaire;

        }

        return null;

    }


    function demanderConfirmation(options, callback) {

        if (!window.bootstrap) {

            if (window.confirm(options.message)) {

                callback();

            }

            return;

        }

        const modal = obtenirModalConfirmation();

        modal.querySelector(
            "[data-confirm-title]"
        ).textContent = options.titre;

        modal.querySelector(
            "[data-confirm-message]"
        ).textContent = options.message;

        const boutonConfirmer = modal.querySelector(
            "[data-confirm-ok]"
        );

        boutonConfirmer.textContent = options.libelleConfirmer;

        const instance = window.bootstrap.Modal.getOrCreateInstance(
            modal
        );

        boutonConfirmer.onclick = function () {

            instance.hide();

            callback();

        };

        instance.show();

    }


    function obtenirModalConfirmation() {

        let modal = document.getElementById(
            "modal-confirm-submit"
        );

        if (modal) {

            return modal;

        }

        modal = document.createElement(
            "div"
        );

        modal.className = "modal fade";
        modal.id = "modal-confirm-submit";
        modal.tabIndex = -1;
        modal.setAttribute(
            "aria-hidden",
            "true"
        );

        modal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" data-confirm-title>
                            Confirmation
                        </h5>
                        <button
                            type="button"
                            class="btn-close"
                            data-bs-dismiss="modal"
                            aria-label="Fermer">
                        </button>
                    </div>
                    <div class="modal-body">
                        <p class="mb-0" data-confirm-message>
                            Voulez-vous vraiment enregistrer ces informations ?
                        </p>
                    </div>
                    <div class="modal-footer">
                        <button
                            type="button"
                            class="btn btn-outline-secondary"
                            data-bs-dismiss="modal">
                            Annuler
                        </button>
                        <button
                            type="button"
                            class="btn btn-success"
                            data-confirm-ok>
                            Confirmer
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(
            modal
        );

        return modal;

    }


    function soumettreFormulaire(formulaire, bouton) {

        formulaire.dataset.confirmedSubmit = "1";

        if (
            bouton &&
            formulaire.requestSubmit
        ) {

            formulaire.requestSubmit(
                bouton
            );

            return;

        }

        if (
            bouton &&
            bouton.name
        ) {

            const champ = document.createElement(
                "input"
            );

            champ.type = "hidden";
            champ.name = bouton.name;
            champ.value = bouton.value;

            formulaire.appendChild(
                champ
            );

        }

        formulaire.submit();

    }

})();
