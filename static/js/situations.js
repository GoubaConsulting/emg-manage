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

    initialiserPaiements();

    recalculerSousTotauxNets();

    const champVentesVersees = document.getElementById(
        "montant-vente-verse"
    );

    const champCreditVerse = document.getElementById(
        "montant-credit-verse"
    );

    [
        champCreditVerse,
        champVentesVersees
    ].forEach(function (champ) {

        if (!champ) {
            return;
        }

        champ.addEventListener(
            "input",
            actualiserManquantAuto
        );

        champ.addEventListener(
            "change",
            actualiserManquantAuto
        );

    });

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
// INITIALISATION DES PAIEMENTS
// ==========================================================

function initialiserPaiements() {

    const champCreditVerse = document.getElementById(
        "montant-credit-verse"
    );

    if (champCreditVerse) {

        const montantCredit = convertirNombre(
            champCreditVerse.dataset.montantCredit
        );

        champCreditVerse.value = formaterNombre(
            montantCredit
        );

    }

    const champVentesVersees = document.getElementById(
        "montant-vente-verse"
    );

    if (
        champVentesVersees &&
        champVentesVersees.value === ""
    ) {

        champVentesVersees.value = "0";

    }

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

    const montantVerse = ligne.querySelector(
        ".montant-verse"
    );

    const remiseVerse = ligne.querySelector(
        ".remise-verse"
    );

    const montantNetVerse = ligne.querySelector(
        ".montant-net-verse"
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

    const montantDistribue = convertirNombre(
        ligne.dataset.montantDistribue
    );

    const montantBrutRestant = convertirNombre(
        montantRestant.value
    );


    // ------------------------------------------------------
    // VERIFICATION
    // ------------------------------------------------------

    if (
        prix <= 0 ||
        montantDistribue < 0 ||
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

        const verse = Math.max(
            0,
            montantDistribue
        );

        const remise = calculerRemise(
            verse,
            taux
        );

        const netVerse = Math.max(
            0,
            verse - remise
        );

        if (montantVerse) {

            montantVerse.value = formaterMontant(
                verse
            );

        }

        if (remiseVerse) {

            remiseVerse.value = formaterMontant(
                remise
            );

        }

        if (montantNetVerse) {

            montantNetVerse.value = formaterMontant(
                netVerse
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

    const verse = Math.max(
        0,
        montantDistribue - montantBrutRestant
    );

    const remise = calculerRemise(
        verse,
        taux
    );

    const netVerse = Math.max(
        0,
        verse - remise
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

    if (montantVerse) {

        montantVerse.value =
            formaterMontant(verse);

    }

    if (remiseVerse) {

        remiseVerse.value =
            formaterMontant(remise);

    }

    if (montantNetVerse) {

        montantNetVerse.value =
            formaterMontant(netVerse);

    }

    recalculerSousTotauxNets();

}


// ==========================================================
// SOUS-TOTAUX PAR COMPAGNIE
// ==========================================================

function recalculerSousTotauxNets() {

    const sousTotaux = {};

    const sousTotauxRemise = {};

    const sousTotauxNetVerse = {};

    let totalDistribue = 0;

    let totalRestant = 0;

    let totalVendu = 0;

    let totalDistribueNet = 0;

    let totalRestantNet = 0;

    let totalRemise = 0;

    let totalNetVerse = 0;

    document.querySelectorAll(
        ".ligne-situation"
    ).forEach(function (ligne) {

        const compagnie = ligne.dataset.compagnie;

        if (!compagnie) {

            return;

        }

        const montantDistribue = convertirNombre(
            ligne.dataset.montantDistribue
        );

        const montantNetDistribue = convertirNombre(
            ligne.dataset.netDistribue
        );

        const montantBrutRestant = convertirNombre(
            ligne.querySelector(".montant-restant")?.value
        );

        const montantVendu = Math.max(
            0,
            montantDistribue - montantBrutRestant
        );

        const taux = convertirNombre(
            ligne.dataset.taux
        );

        const remise = calculerRemise(
            montantVendu,
            taux
        );

        const montantNetRestant = calculerMontantNet(
            montantBrutRestant,
            taux
        );

        const netVerse = Math.max(
            0,
            montantVendu - remise
        );

        totalDistribue += Math.max(
            0,
            montantDistribue
        );

        totalRestant += Math.max(
            0,
            montantBrutRestant
        );

        totalVendu += Math.max(
            0,
            montantVendu
        );

        totalDistribueNet += Math.max(
            0,
            montantNetDistribue
        );

        totalRestantNet += Math.max(
            0,
            montantNetRestant
        );

        totalRemise += Math.max(
            0,
            remise
        );

        totalNetVerse += Math.max(
            0,
            netVerse
        );

        if (!(compagnie in sousTotaux)) {

            sousTotaux[compagnie] = 0;

        }

        if (!(compagnie in sousTotauxRemise)) {

            sousTotauxRemise[compagnie] = 0;

        }

        if (!(compagnie in sousTotauxNetVerse)) {

            sousTotauxNetVerse[compagnie] = 0;

        }

        sousTotaux[compagnie] += montantVendu;

        sousTotauxRemise[compagnie] += remise;

        sousTotauxNetVerse[compagnie] += netVerse;

    });

    document.querySelectorAll(
        ".subtotal-verse-compagnie"
    ).forEach(function (champ) {

        const compagnie = champ.dataset.compagnie;

        champ.value = formaterMontant(
            sousTotaux[compagnie] || 0
        );

    });

    document.querySelectorAll(
        ".subtotal-remise-compagnie"
    ).forEach(function (champ) {

        const compagnie = champ.dataset.compagnie;

        champ.value = formaterMontant(
            sousTotauxRemise[compagnie] || 0
        );

    });

    document.querySelectorAll(
        ".subtotal-net-verse-compagnie"
    ).forEach(function (champ) {

        const compagnie = champ.dataset.compagnie;

        champ.value = formaterMontant(
            sousTotauxNetVerse[compagnie] || 0
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

    const champTotalRemise = document.getElementById(
        "total-remise-verse"
    );

    const champTotalNetVerse = document.getElementById(
        "total-net-verse"
    );

    if (champTotalDistribue) {

        champTotalDistribue.dataset.montantBrut = String(
            totalDistribue
        );

        champTotalDistribue.dataset.montantNet = String(
            totalDistribueNet
        );

        champTotalDistribue.textContent = formaterMontant(
            totalDistribue
        );

    }

    if (champTotalRestant) {

        champTotalRestant.dataset.montantBrut = String(
            totalRestant
        );

        champTotalRestant.dataset.montantNet = String(
            totalRestantNet
        );

        champTotalRestant.textContent = formaterMontant(
            totalRestant
        );

    }

    if (champTotalVendu) {

        champTotalVendu.textContent = formaterMontant(
            totalVendu
        );

    }

    if (champTotalRemise) {

        champTotalRemise.textContent = formaterMontant(
            totalRemise
        );

    }

    if (champTotalNetVerse) {

        champTotalNetVerse.textContent = formaterMontant(
            totalNetVerse
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

    const champTotalDistribue = document.getElementById(
        "total-net-distribue"
    );

    const champTotalRestant = document.getElementById(
        "total-net-restant"
    );

    const totalDistribueBrut = convertirNombre(
        champTotalDistribue?.dataset.montantBrut ||
        champTotalDistribue?.textContent
    );

    const totalDistribueNet = convertirNombre(
        champTotalDistribue?.dataset.montantNet ||
        champTotalDistribue?.textContent
    );

    const totalRestantNet = convertirNombre(
        champTotalRestant?.dataset.montantNet ||
        champTotalRestant?.textContent
    );

    const creditVerse = convertirNombre(
        document.getElementById(
            "montant-credit-verse"
        )?.value
    );

    const ventesVersees = convertirNombre(
        document.getElementById(
            "montant-vente-verse"
        )?.value
    );

    const creditVerseNet = convertirMontantBrutEnNet(
        creditVerse,
        totalDistribueBrut,
        totalDistribueNet
    );

    const manquant = Math.max(
        0,
        totalDistribueNet
        -
        creditVerseNet
        -
        ventesVersees
        -
        totalRestantNet
    );

    champManquant.value = formaterMontant(
        manquant
    );

}


// ==========================================================
// CALCUL DU NET
// ==========================================================

function calculerRemise(
    montantBrut,
    taux
) {

    return (
        montantBrut
        *
        taux
        /
        100
    );

}


function convertirMontantBrutEnNet(
    montantBrut,
    totalBrutReference,
    totalNetReference
) {

    if (
        montantBrut <= 0
    ) {

        return 0;

    }

    if (
        totalBrutReference <= 0
    ) {

        return montantBrut;

    }

    return (
        montantBrut
        *
        totalNetReference
        /
        totalBrutReference
    );

}


function calculerMontantNet(
    montantBrut,
    taux
) {

    return (
        montantBrut
        -
        calculerRemise(
            montantBrut,
            taux
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
