/*
==========================================================
Projet : EMG MANAGE
Module : Commandes
==========================================================
*/



document.addEventListener("DOMContentLoaded", function () {

    const lignes = document.querySelectorAll(".ligne-produit");
    const champDateCommande = document.querySelector("[name='date_commande']");

    lignes.forEach(function (ligne) {

        const check = ligne.querySelector(".produit-check");
        const montant = ligne.querySelector(".montant");
        const taux = ligne.querySelector(".taux");
        const quantite = ligne.querySelector(".quantite");
        const net = ligne.querySelector(".net");
        const estVerrouillee = check.dataset.locked === "1";

        if (estVerrouillee) {

            check.checked = true;

        }

        const ligneSelectionnee = check.checked || estVerrouillee;

        // Etat initial
        montant.disabled = !ligneSelectionnee;
        taux.disabled = !ligneSelectionnee;

        if (ligneSelectionnee) {

            ligne.classList.add("table-success");
            calculerLigne(ligne);

        }

        else {

            montant.value = "";
            taux.value = "0";
            quantite.value = "0";
            net.value = "0";

        }

        // Sélection / désélection
        check.addEventListener("change", function () {

            if (estVerrouillee) {

                check.checked = true;
                montant.disabled = false;
                taux.disabled = false;
                calculerLigne(ligne);
                return;

            }

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

    if (champDateCommande) {

        champDateCommande.addEventListener("change", function () {

            calculerTotaux();

        });

    }

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

    const montantInitial = lireNombre(

        ligne.dataset.montantInitial

    );

    let quantite = 0;

    if (prix > 0) {

        quantite = montant / prix;

    }

    const remise = montant * taux / 100;

    const net = montant - remise;

    const netInitial = lireNombre(

        ligne.dataset.montantNetInitial

    );

    const totalBrutLigne = montantInitial + montant;

    const totalNetLigne = netInitial + net;

    ligne.querySelector(".quantite").value = quantite.toFixed(2);

    ligne.querySelector(".net").value = net.toFixed(2);

    const champNetInitial = ligne.querySelector(".net-initial");
    const champTotalBrutLigne = ligne.querySelector(".montant-total-brut-ligne");
    const champTotalNetLigne = ligne.querySelector(".montant-total-net-ligne");

    if (champNetInitial) {

        champNetInitial.value = netInitial.toFixed(2);

    }

    if (champTotalBrutLigne) {

        champTotalBrutLigne.value = totalBrutLigne.toFixed(2);

    }

    if (champTotalNetLigne) {

        champTotalNetLigne.value = totalNetLigne.toFixed(2);

    }

    calculerTotaux();
    calculerSousTotauxCompagnies();

}


// ======================================================
// Totaux
// ======================================================

function calculerTotaux() {

    let brutInitial = 0;

    let netInitial = 0;

    let brutCommande = 0;

    let netCommande = 0;

    document.querySelectorAll(".ligne-produit").forEach(function (ligne) {

        const check = ligne.querySelector(".produit-check");
        const montantInitial = lireNombre(ligne.dataset.montantInitial);
        const champNetInitial = ligne.querySelector(".net-initial");
        const netInitialLigne = champNetInitial
            ? lireNombre(champNetInitial.value)
            : lireNombre(ligne.dataset.montantNetInitial);

        if (montantInitial > 0) {

            brutInitial += montantInitial;
            netInitial += netInitialLigne;

        }

        if (!check.checked) {

            return;

        }

        brutCommande += lireNombre(

            ligne.querySelector(".montant").value

        );

        netCommande += lireNombre(

            ligne.querySelector(".net").value

        );

    });

    const brutTotal = brutInitial + brutCommande;
    const netTotal = netInitial + netCommande;

    const champBrutInitial = document.getElementById("total-brut-initial");
    const champBrutCommande = document.getElementById("total-brut-commande");
    const champNetInitial = document.getElementById("total-net-initial");
    const champNetCommande = document.getElementById("total-net-commande");

    if (champBrutInitial) {

        champBrutInitial.innerText = formater(brutInitial);

    }

    if (champBrutCommande) {

        champBrutCommande.innerText = formater(brutCommande);

    }

    if (champNetInitial) {

        champNetInitial.innerText = formater(netInitial);

    }

    if (champNetCommande) {

        champNetCommande.innerText = formater(netCommande);

    }

    document.getElementById("total-brut").innerText = formater(brutTotal);

    document.getElementById("total-net").innerText = formater(netTotal);

    actualiserSyntheseGerant(
        brutCommande
    );

}

// ======================================================
// Synthese du gerant
// ======================================================

function calculerTotalMontantsInitiaux() {

    let total = 0;
    let totalNet = 0;

    document.querySelectorAll(".ligne-produit").forEach(function (ligne) {

        total += lireNombre(ligne.dataset.montantInitial);

        const champNetInitial = ligne.querySelector(".net-initial");

        totalNet += champNetInitial
            ? lireNombre(champNetInitial.value)
            : lireNombre(ligne.dataset.montantNetInitial);

    });

    const champTotal = document.getElementById("total-montants-initiaux");

    if (champTotal) {

        champTotal.innerText = formater(total);

    }

    const champTotalNet = document.getElementById("total-montants-initiaux-net");

    if (champTotalNet) {

        champTotalNet.innerText = formater(totalNet);

    }

    return total;

}


function totauxCommandesValideesJour() {

    const balise = document.getElementById("commandes-validees-jour");

    if (!balise) {

        return {};

    }

    try {

        return JSON.parse(balise.textContent || "{}");

    }

    catch (erreur) {

        return {};

    }

}


function totalCommandesValideesPourDate() {

    const champDate = document.querySelector("[name='date_commande']");
    const dateCommande = champDate ? champDate.value : "";
    const totaux = totauxCommandesValideesJour();

    if (
        dateCommande
        &&
        Object.prototype.hasOwnProperty.call(totaux, dateCommande)
    ) {

        return lireNombre(totaux[dateCommande]);

    }

    return 0;

}


function actualiserSyntheseGerant(
    totalBrut
) {

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
    const credit = Math.max(
        0,
        totalEngage - fond
    );
    const creditEnAlerte = credit > 0;

    champFond.innerText = formater(fond);
    champDifference.innerText = formater(difference);
    champCredit.innerText = formater(credit);

    champDifference.classList.toggle("text-danger", difference < 0);
    champDifference.classList.toggle("text-success", difference >= 0);
    champCredit.classList.toggle("text-danger", creditEnAlerte);
    champCredit.classList.toggle("text-success", !creditEnAlerte);

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

    carteCredit.classList.toggle("border-danger", creditEnAlerte);
    carteCredit.classList.toggle("border-success", !creditEnAlerte);

    enteteCredit.classList.toggle("bg-danger", creditEnAlerte);
    enteteCredit.classList.toggle("bg-success", !creditEnAlerte);

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

        const champNetInitial = ligne.querySelector(".net-initial");

        const netInitial = champNetInitial
            ? lireNombre(champNetInitial.value)
            : lireNombre(ligne.dataset.montantNetInitial);

        const net = lireNombre(
            ligne.querySelector(".net").value
        );

        if (!(compagnie in sousTotaux)) {

            sousTotaux[compagnie] = 0;

        }

        sousTotaux[compagnie] += netInitial + net;

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

        const montantInitial = lireNombre(

            ligne.dataset.montantInitial

        );

        const taux = lireNombre(

            ligne.querySelector(".taux").value

        );

        if (montant <= 0 && montantInitial <= 0) {

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
