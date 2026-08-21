/*
==========================================================
Projet : EMG MANAGE

Module : Situations

Gestion du formulaire de situation journalière.
==========================================================
*/


// ==========================================================
// INITIALISATION
// ==========================================================

if (document.readyState === "loading") {

    document.addEventListener(
        "DOMContentLoaded",
        initialiserSituation
    );

}

else {

    initialiserSituation();

}


// ==========================================================
// INITIALISATION
// ==========================================================

function initialiserSituation() {

    const lignes = document.querySelectorAll(
        ".ligne-situation"
    );

    lignes.forEach(function (ligne) {

        initialiserLigne(ligne);

    });

    recalculerSousTotauxNets();

    const champVentesVersees = document.getElementById(
        "montant-vente-verse"
    );

    if (champVentesVersees) {

        champVentesVersees.addEventListener(
            "input",
            actualiserManquantAuto
        );

        champVentesVersees.addEventListener(
            "change",
            actualiserManquantAuto
        );

    }

    document.addEventListener(
        "input",
        gererSaisieMontantRestant
    );

    document.addEventListener(
        "change",
        gererSaisieMontantRestant
    );

}


// ==========================================================
// ECOUTE GLOBALE DES MONTANTS BRUTS RESTANTS
// ==========================================================

function gererSaisieMontantRestant(evenement) {

    if (
        !evenement.target.classList.contains(
            "montant-restant"
        )
    ) {

        return;

    }

    const ligne = evenement.target.closest(
        ".ligne-situation"
    );

    if (!ligne) {

        return;

    }

    calculerMontants(ligne);

}


// ==========================================================
// INITIALISATION D'UNE LIGNE
// ==========================================================

function initialiserLigne(ligne) {

    const montantRestant = ligne.querySelector(
        ".montant-restant"
    );

    if (!montantRestant) {
        return;
    }

    // ------------------------------------------------------
    // Calcul initial
    // ------------------------------------------------------

    calculerMontants(ligne);


    // ------------------------------------------------------
    // Recalcul à chaque modification
    // ------------------------------------------------------

    montantRestant.addEventListener(
        "input",
        function () {

            calculerMontants(ligne);

        }
    );

}


// ==========================================================
// CALCUL DES MONTANTS
// ==========================================================

function calculerMontants(ligne) {

    const montantRestant = ligne.querySelector(
        ".montant-restant"
    );

    const montantNetRestant = ligne.querySelector(
        ".montant-net-restant"
    );

    const montantNetVendu = ligne.querySelector(
        ".montant-net-vendu"
    );


    // ------------------------------------------------------
    // RECUPERATION DES DONNEES
    // ------------------------------------------------------

    const prix = convertirNombre(
        ligne.dataset.prix
    );

    const taux = convertirNombre(
        ligne.dataset.taux
    );

    const montantNetDistribue = convertirNombre(
        ligne.dataset.netDistribue
    );

    const montantBrutRestant = convertirNombre(
        montantRestant.value
    );


    // ------------------------------------------------------
    // VERIFICATION
    // ------------------------------------------------------

    if (
        prix <= 0 ||
        montantNetDistribue < 0 ||
        montantBrutRestant < 0
    ) {

        if (montantNetRestant) {

            montantNetRestant.value = "0 FCFA";

        }

        if (montantNetVendu) {

            montantNetVendu.value = formaterMontant(
                Math.max(0, montantNetDistribue)
            );

        }

        recalculerSousTotauxNets();

        return;

    }


    // ------------------------------------------------------
    // CALCUL DU MONTANT NET RESTANT
    // ------------------------------------------------------

    const netRestant = calculerMontantNet(
        montantBrutRestant,
        taux
    );


    // ------------------------------------------------------
    // CALCUL DU MONTANT NET VENDU
    // ------------------------------------------------------

    const netVendu = Math.max(
        0,
        montantNetDistribue - netRestant
    );


    // ------------------------------------------------------
    // AFFICHAGE
    // ------------------------------------------------------

    if (montantNetRestant) {

        montantNetRestant.value =
            formaterMontant(netRestant);

    }

    if (montantNetVendu) {

        montantNetVendu.value =
            formaterMontant(netVendu);

    }

    recalculerSousTotauxNets();

}


// ==========================================================
// SOUS-TOTAUX NETS PAR COMPAGNIE
// ==========================================================

function recalculerSousTotauxNets() {

    const sousTotaux = {};

    let totalNetDistribue = 0;

    let totalNetRestant = 0;

    let totalNetVendu = 0;

    document.querySelectorAll(
        ".ligne-situation"
    ).forEach(function (ligne) {

        const compagnie = ligne.dataset.compagnie;

        if (!compagnie) {

            return;

        }

        const montantNetDistribue = convertirNombre(
            ligne.dataset.netDistribue
        );

        const taux = convertirNombre(
            ligne.dataset.taux
        );

        const montantBrutRestant = convertirNombre(
            ligne.querySelector(".montant-restant")?.value
        );

        const montantNetRestant = calculerMontantNet(
            montantBrutRestant,
            taux
        );

        const montantNetVendu = Math.max(
            0,
            montantNetDistribue - montantNetRestant
        );

        totalNetDistribue += Math.max(
            0,
            montantNetDistribue
        );

        totalNetRestant += Math.max(
            0,
            montantNetRestant
        );

        totalNetVendu += Math.max(
            0,
            montantNetVendu
        );

        if (!(compagnie in sousTotaux)) {

            sousTotaux[compagnie] = 0;

        }

        sousTotaux[compagnie] += Math.max(
            0,
            montantNetVendu
        );

    });

    document.querySelectorAll(
        ".subtotal-net-compagnie"
    ).forEach(function (champ) {

        const compagnie = champ.dataset.compagnie;

        champ.value = formaterMontant(
            sousTotaux[compagnie] || 0
        );

    });

    const champTotalDistribue = document.getElementById(
        "total-net-distribue"
    );

    const champTotalRestant = document.getElementById(
        "total-net-restant"
    );

    const champTotalVendu = document.getElementById(
        "total-net-vendu"
    );

    if (champTotalDistribue) {

        champTotalDistribue.textContent = formaterMontant(
            totalNetDistribue
        );

    }

    if (champTotalRestant) {

        champTotalRestant.textContent = formaterMontant(
            totalNetRestant
        );

    }

    if (champTotalVendu) {

        champTotalVendu.textContent = formaterMontant(
            totalNetVendu
        );

    }

    actualiserManquantAuto();

}


// ==========================================================
// MANQUANT AUTOMATIQUE
// ==========================================================

function actualiserManquantAuto() {

    const champManquant = document.getElementById(
        "montant-manquant-auto"
    );

    if (!champManquant) {

        return;

    }

    const totalNetDistribue = convertirNombre(
        document.getElementById(
            "total-net-distribue"
        )?.textContent
    );

    const totalNetRestant = convertirNombre(
        document.getElementById(
            "total-net-restant"
        )?.textContent
    );

    const montantVerse = convertirNombre(
        document.getElementById(
            "montant-vente-verse"
        )?.value
    );

    const manquant = Math.max(
        0,
        totalNetDistribue - montantVerse - totalNetRestant
    );

    champManquant.value = formaterMontant(
        manquant
    );

}


// ==========================================================
// CALCUL DU NET
// ==========================================================

function calculerMontantNet(
    montantBrut,
    taux
) {

    return (
        montantBrut
        -
        (
            montantBrut
            *
            taux
            /
            100
        )
    );

}


// ==========================================================
// CONVERSION D'UN NOMBRE
// ==========================================================

function convertirNombre(valeur) {

    if (
        valeur === null ||
        valeur === undefined ||
        valeur === ""
    ) {

        return 0;

    }

    // ------------------------------------------------------
    // Conversion du format français
    //
    // Exemple :
    // "5 500,00" → 5500
    // "500,00"   → 500
    // ------------------------------------------------------

    let texte = String(valeur)
        .replace(/\s/g, "")
        .replace(/[^\d,.-]/g, "")
        .replace(",", ".");

    const nombre = Number(texte);

    if (Number.isNaN(nombre)) {

        return 0;

    }

    return nombre;

}


// ==========================================================
// FORMATAGE
// ==========================================================

function formaterNombre(nombre) {

    if (!Number.isFinite(nombre)) {

        return "0";

    }

    // Evite les longues décimales
    // provoquées par les calculs JavaScript.

    if (
        Number.isInteger(nombre)
    ) {

        return String(nombre);

    }

    return nombre
        .toFixed(2)
        .replace(/\.?0+$/, "");

}


// ==========================================================
// FORMATAGE MONETAIRE
// ==========================================================

function formaterMontant(nombre) {

    if (!Number.isFinite(nombre)) {

        return "0 FCFA";

    }

    return nombre.toLocaleString(
        "fr-FR",
        {
            minimumFractionDigits: 0,
            maximumFractionDigits: 2
        }
    ) + " FCFA";

}
