/*
==========================================================
Projet : EMG MANAGE
Module : Commandes
==========================================================
*/



document.addEventListener("DOMContentLoaded", function () {

    const lignes = document.querySelectorAll(".ligne-produit");

    lignes.forEach(function (ligne) {

        const check = ligne.querySelector(".produit-check");
        const montant = ligne.querySelector(".montant");
        const taux = ligne.querySelector(".taux");

        // Etat initial
        montant.disabled = true;
        taux.disabled = true;
        montant.value = "";
        taux.value = "0";

        ligne.querySelector(".quantite").value = "0";
        ligne.querySelector(".net").value = "0";

        // Sélection / désélection
        check.addEventListener("change", function () {

            if (check.checked) {

                montant.disabled = false;
                taux.disabled = false;

                ligne.classList.add("table-success");

                montant.focus();

            }

            else {

                montant.disabled = true;
                taux.disabled = true;

                montant.value = "";
                taux.value = "0";

                ligne.querySelector(".quantite").value = "0";
                ligne.querySelector(".net").value = "0";

                ligne.classList.remove("table-success");

                calculerTotaux();

                calculerSousTotauxCompagnies();

            }

        });

        montant.addEventListener("input", function () {

            calculerLigne(ligne);

        });

        taux.addEventListener("input", function () {

            calculerLigne(ligne);

        });

    });

    document.getElementById("form-distribution").addEventListener("submit", verifierFormulaire);

    calculerSousTotauxCompagnies();

});

// ======================================================
// Calcul d'une ligne
// ======================================================

function calculerLigne(ligne) {

    const prix = parseFloat(ligne.dataset.prix) || 0;

    const montant = parseFloat(

        ligne.querySelector(".montant").value

    ) || 0;

    const taux = parseFloat(

        ligne.querySelector(".taux").value

    ) || 0;

    let quantite = 0;

    if (prix > 0) {

        quantite = montant / prix;

    }

    const remise = montant * taux / 100;

    const net = montant - remise;

    ligne.querySelector(".quantite").value = quantite.toFixed(2);

    ligne.querySelector(".net").value = net.toFixed(2);

    calculerTotaux();
    calculerSousTotauxCompagnies();

}


// ======================================================
// Totaux
// ======================================================

function calculerTotaux() {

    let brut = 0;

    let net = 0;

    document.querySelectorAll(".ligne-produit").forEach(function (ligne) {

        const check = ligne.querySelector(".produit-check");

        if (!check.checked) {

            return;

        }

        brut += parseFloat(

            ligne.querySelector(".montant").value

        ) || 0;

        net += parseFloat(

            ligne.querySelector(".net").value

        ) || 0;

    });

    document.getElementById("total-brut").innerText = formater(brut);

    document.getElementById("total-net").innerText = formater(net);

}

// ======================================================
// SOUS-TOTAUX PAR COMPAGNIE
// ======================================================

function calculerSousTotauxCompagnies() {

    let sousTotaux = {};

    document.querySelectorAll(".ligne-produit").forEach(function (ligne) {

        const check = ligne.querySelector(".produit-check");

        if (!check.checked) {

            return;

        }

        const compagnie = ligne.dataset.compagnie;

        const net = parseFloat(
            ligne.querySelector(".net").value
        ) || 0;

        if (!(compagnie in sousTotaux)) {

            sousTotaux[compagnie] = 0;

        }

        sousTotaux[compagnie] += net;

    });

    document.querySelectorAll(".subtotal-compagnie").forEach(function (champ) {

        const compagnie = champ.dataset.compagnie;

        if (compagnie in sousTotaux) {

            champ.value = formater(sousTotaux[compagnie]);

        }

        else {

            champ.value = formater(0);

        }

    });

}

// ======================================================
// Formatage
// ======================================================

function formater(nombre) {

    return Number(nombre).toLocaleString(

        "fr-FR",

        {

            minimumFractionDigits: 2,

            maximumFractionDigits: 2

        }

    ) + " FCFA";

}


// ======================================================
// Validation
// ======================================================

function verifierFormulaire(e) {

    let auMoinsUn = false;

    let erreur = false;

    document.querySelectorAll(".ligne-produit").forEach(function (ligne) {

        const check = ligne.querySelector(".produit-check");

        if (!check.checked) {

            return;

        }

        auMoinsUn = true;

        const montant = parseFloat(

            ligne.querySelector(".montant").value

        ) || 0;

        const taux = parseFloat(

            ligne.querySelector(".taux").value

        ) || 0;

        if (montant <= 0) {

            erreur = true;

        }

        if (taux < 0 || taux > 100) {

            erreur = true;

        }

    });

    if (!auMoinsUn) {

        alert("Veuillez sélectionner au moins un produit.");

        e.preventDefault();

        return;

    }

    if (erreur) {

        alert("Veuillez corriger les montants ou les taux.");

        e.preventDefault();

    }

}