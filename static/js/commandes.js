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

                calculerTotaux();
                calculerSousTotauxCompagnies();

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

    document.getElementById("form-commande").addEventListener("submit", verifierFormulaire);

    calculerSousTotauxCompagnies();
    calculerTotaux();

});

// ======================================================
// Calcul d'une ligne
// ======================================================

function calculerLigne(ligne) {

    const prix = lireNombre(ligne.dataset.prix);

    const montant = lireNombre(

        ligne.querySelector(".montant").value

    );

    const taux = lireNombre(

        ligne.querySelector(".taux").value

    );

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

        brut += lireNombre(

            ligne.querySelector(".montant").value

        );

        net += lireNombre(

            ligne.querySelector(".net").value

        );

    });

    document.getElementById("total-brut").innerText = formater(brut);

    document.getElementById("total-net").innerText = formater(net);

    actualiserSyntheseGerant(brut);

}

// ======================================================
// Synthese du gerant
// ======================================================

function calculerTotalMontantsInitiaux() {

    let total = 0;

    document.querySelectorAll(".ligne-produit").forEach(function (ligne) {

        total += lireNombre(ligne.dataset.montantInitial);

    });

    const champTotal = document.getElementById("total-montants-initiaux");

    if (champTotal) {

        champTotal.innerText = formater(total);

    }

    return total;

}


function actualiserSyntheseGerant(totalBrut) {

    const champFond = document.getElementById("fond-gerant");
    const champDifference = document.getElementById("difference-fond");
    const champCredit = document.getElementById("credit-fond");

    if (!champFond || !champDifference || !champCredit) {

        return;

    }

    const fond = lireNombre(champFond.dataset.fond);
    const totalInitial = calculerTotalMontantsInitiaux();
    const totalEngage = lireNombre(totalBrut) + totalInitial;
    const difference = fond - totalEngage;
    const credit = Math.max(totalEngage - fond, 0);

    champFond.innerText = formater(fond);
    champDifference.innerText = formater(difference);
    champCredit.innerText = formater(credit);

    champDifference.classList.toggle("text-danger", difference < 0);
    champDifference.classList.toggle("text-success", difference >= 0);
    champCredit.classList.toggle("text-danger", credit > 0);
    champCredit.classList.toggle("text-success", credit <= 0);

    const carte = document.getElementById("carte-difference-fond");
    const entete = document.getElementById("entete-difference-fond");
    const carteCredit = document.getElementById("carte-credit-fond");
    const enteteCredit = document.getElementById("entete-credit-fond");

    if (!carte || !entete || !carteCredit || !enteteCredit) {

        return;

    }

    carte.classList.toggle("border-danger", difference < 0);
    carte.classList.toggle("border-success", difference >= 0);
    carte.classList.toggle("border-secondary", false);

    entete.classList.toggle("bg-danger", difference < 0);
    entete.classList.toggle("bg-success", difference >= 0);
    entete.classList.toggle("bg-secondary", false);

    carteCredit.classList.toggle("border-danger", credit > 0);
    carteCredit.classList.toggle("border-success", credit <= 0);

    enteteCredit.classList.toggle("bg-danger", credit > 0);
    enteteCredit.classList.toggle("bg-success", credit <= 0);

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

        const net = lireNombre(
            ligne.querySelector(".net").value
        );

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

function lireNombre(valeur) {

    if (valeur === undefined || valeur === null) {

        return 0;

    }

    const valeurTexte = String(valeur)
        .replace(/\s/g, "")
        .replace(",", ".");

    return parseFloat(valeurTexte) || 0;

}


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

        const montant = lireNombre(

            ligne.querySelector(".montant").value

        );

        const taux = lireNombre(

            ligne.querySelector(".taux").value

        );

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
