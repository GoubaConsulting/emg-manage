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

document.addEventListener(
    "DOMContentLoaded",
    initialiserSituation
);


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


    // ------------------------------------------------------
    // RECUPERATION DES DONNEES
    // ------------------------------------------------------

    const prix = convertirNombre(
        ligne.dataset.prix
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

        quantiteRestante.value =
            formaterNombre(
                quantiteDistribuee
            );

        return;

    }


    // ------------------------------------------------------
    // CALCUL DE LA QUANTITE VENDUE
    // ------------------------------------------------------

    const quantite = montant / prix;


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

    quantiteRestante.value =
        formaterNombre(
            Math.max(0, restante)
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