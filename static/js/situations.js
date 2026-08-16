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
        gererSaisieMontantVendu
    );

    document.addEventListener(
        "change",
        gererSaisieMontantVendu
    );

}


// ==========================================================
// ECOUTE GLOBALE DES MONTANTS BRUTS
// ==========================================================

function gererSaisieMontantVendu(evenement) {

    if (
        !evenement.target.classList.contains(
            "montant-vendu"
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

    calculerQuantites(ligne);

}


// ==========================================================
// INITIALISATION D'UNE LIGNE
// ==========================================================

function initialiserLigne(ligne) {

    const montantVendu = ligne.querySelector(
        ".montant-vendu"
    );

    if (!montantVendu) {
        return;
    }

    // ------------------------------------------------------
    // Calcul initial
    // ------------------------------------------------------

    calculerQuantites(ligne);


    // ------------------------------------------------------
    // Recalcul à chaque modification
    // ------------------------------------------------------

    montantVendu.addEventListener(
        "input",
        function () {

            calculerQuantites(ligne);

        }
    );

}


// ==========================================================
// CALCUL DES QUANTITES
// ==========================================================

function calculerQuantites(ligne) {

    const montantVendu = ligne.querySelector(
        ".montant-vendu"
    );

    const quantiteVendue = ligne.querySelector(
        ".quantite-vendue"
    );

    const quantiteRestante = ligne.querySelector(
        ".quantite-restante"
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

    const quantiteDistribuee = convertirNombre(
        ligne.dataset.distribuee
    );

    const montant = convertirNombre(
        montantVendu.value
    );


    // ------------------------------------------------------
    // VERIFICATION
    // ------------------------------------------------------

    if (
        prix <= 0 ||
        quantiteDistribuee < 0 ||
        montant < 0
    ) {

        quantiteVendue.value = "0";

        if (montantNetVendu) {

            montantNetVendu.value = "0 FCFA";

        }

        quantiteRestante.value =
            formaterNombre(
                quantiteDistribuee
            );

        recalculerSousTotauxNets();

        return;

    }


    // ------------------------------------------------------
    // CALCUL DE LA QUANTITE VENDUE
    // ------------------------------------------------------

    const quantite = montant / prix;

    const montantNet = calculerMontantNet(
        montant,
        taux
    );


    // ------------------------------------------------------
    // CALCUL DE LA QUANTITE RESTANTE
    // ------------------------------------------------------

    const restante =
        quantiteDistribuee - quantite;


    // ------------------------------------------------------
    // AFFICHAGE
    // ------------------------------------------------------

    quantiteVendue.value =
        formaterNombre(quantite);

    if (montantNetVendu) {

        montantNetVendu.value =
            formaterMontant(montantNet);

    }

    quantiteRestante.value =
        formaterNombre(
            Math.max(0, restante)
        );

    recalculerSousTotauxNets();

}


// ==========================================================
// SOUS-TOTAUX NETS PAR COMPAGNIE
// ==========================================================

function recalculerSousTotauxNets() {

    const sousTotaux = {};

    let totalBrut = 0;

    let totalNet = 0;

    document.querySelectorAll(
        ".ligne-situation"
    ).forEach(function (ligne) {

        const compagnie = ligne.dataset.compagnie;

        if (!compagnie) {

            return;

        }

        const montantBrut = convertirNombre(
            ligne.querySelector(".montant-vendu").value
        );

        const taux = convertirNombre(
            ligne.dataset.taux
        );

        const montantNet = calculerMontantNet(
            montantBrut,
            taux
        );

        totalBrut += Math.max(
            0,
            montantBrut
        );

        totalNet += Math.max(
            0,
            montantNet
        );

        if (!(compagnie in sousTotaux)) {

            sousTotaux[compagnie] = 0;

        }

        sousTotaux[compagnie] += Math.max(
            0,
            montantNet
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

    const champTotalBrut = document.getElementById(
        "total-brut-vendu"
    );

    const champTotalNet = document.getElementById(
        "total-net-vendu"
    );

    if (champTotalBrut) {

        champTotalBrut.value = formaterMontant(
            totalBrut
        );

    }

    if (champTotalNet) {

        champTotalNet.value = formaterMontant(
            totalNet
        );

    }

    actualiserManquantAuto(
        totalNet
    );

}


// ==========================================================
// MANQUANT AUTOMATIQUE
// ==========================================================

function actualiserManquantAuto(totalNetCalcule) {

    const champManquant = document.getElementById(
        "montant-manquant-auto"
    );

    if (!champManquant) {

        return;

    }

    let totalNet = totalNetCalcule;

    if (
        typeof totalNet !== "number" ||
        !Number.isFinite(totalNet)
    ) {

        totalNet = convertirNombre(
            document.getElementById(
                "total-net-vendu"
            )?.value
        );

    }

    const montantVerse = convertirNombre(
        document.getElementById(
            "montant-vente-verse"
        )?.value
    );

    const manquant = Math.max(
        0,
        totalNet - montantVerse
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
