/*
==========================================================
Projet : EMG MANAGE

Module : Distributions

Description :
Gestion du formulaire de distribution
Directeur -> Gérant
==========================================================
*/

console.log("========== distributions_directeur.js chargé ==========");
// ======================================================
// Variables globales
// ======================================================

const tbody = document.getElementById(
    "lignes-distribution"
);

const champCommande = document.getElementById(
    "commande-selectionnee"
);


// ======================================================
// Initialisation
// ======================================================

document.addEventListener(

    "DOMContentLoaded",

    initialiser

);


// ======================================================
// Initialisation du formulaire
// ======================================================

function initialiser() {

    const radios = document.querySelectorAll(

        'input[name="commande"]'

    );

    radios.forEach(function (radio) {

        radio.addEventListener(

            "change",

            function () {

                chargerCommande(

                    this.value

                );

            }

        );

    });

}


// ======================================================
// Chargement d'une commande
// ======================================================

function chargerCommande(idCommande) {

    champCommande.value = idCommande;

    console.clear();

    console.log(

        "Commande :", idCommande

    );

    console.log(

        commandes[idCommande]

    );

    const produits = Object.values(

        commandes[idCommande]

    );

    construireTableau(

        produits

    );

}


// ======================================================
// Construction du tableau
// ======================================================

function construireTableau(produits) {

    tbody.innerHTML = "";

    // ==========================================
    // Regroupement par compagnie
    // ==========================================

    const groupes = {};

    produits.forEach(function (produit) {

        if (!(produit.compagnie in groupes)) {

            groupes[produit.compagnie] = [];

        }

        groupes[produit.compagnie].push(produit);

    });

    // ==========================================
    // Construction HTML
    // ==========================================

    Object.keys(groupes).forEach(function (compagnie) {

        tbody.innerHTML += `

            <tr class="table-secondary">

                <td colspan="7">

                    <strong>

                        ${compagnie.toUpperCase()}

                    </strong>

                </td>

            </tr>

        `;

        let sousTotal = 0;

        groupes[compagnie].forEach(function (produit) {

            const montantInitialBrut = lireNombre(
                produit.montant_initial_brut || produit.montant_initial || 0
            );

            const montantBrutASuivre = (
                montantInitialBrut
                +
                lireNombre(produit.montant)
            );

            const taux = lireNombre(
                produit.taux
            );

            const montantRemiseASuivre = (
                montantBrutASuivre
                *
                taux
                /
                100
            );

            const montantNetASuivre = (
                calculerMontantNet(
                    montantBrutASuivre,
                    taux
                )
            );

            sousTotal += montantNetASuivre;

            tbody.innerHTML += `

                <tr

                    class="ligne-produit"

                    data-produit="${produit.id}"

                    data-prix="${produit.prix}"

                    data-compagnie="${produit.compagnie_id}"

                    data-initiale="${montantInitialBrut}"

                    data-initiale-brut="${montantInitialBrut}"

                >

                    <td>

                        ${produit.designation}

                    </td>

                    <td class="text-end">

                        ${produit.prix}

                    </td>

                    <td class="text-end">

                        ${formaterMontant(montantInitialBrut)}

                    </td>

                    <td>

                        <input

                            type="hidden"

                            name="produit_${produit.id}"

                            value="${produit.id}"

                        >

                        <input

                            type="number"

                            class="form-control montant"

                            name="montant_${produit.id}"

                            value="${produit.montant}"

                            min="0"

                            max="${produit.montant}"

                            data-max="${produit.montant}"

                        >

                    <div class="invalid-feedback">

                        Le montant ne peut pas dépasser celui de la commande.

                    </div>

                    </td>

                    <td>

                        <input

                            type="number"

                            class="form-control taux"

                            name="taux_${produit.id}"

                            value="${produit.taux}"

                            min="0"

                            max="100"

                        >

                    </td>

                    <td>

                        <input

                            type="text"

                            class="form-control remise"

                            value="${montantRemiseASuivre.toFixed(0)}"

                            readonly

                        >

                    </td>

                    <td>

                        <input

                            type="text"

                            class="form-control net"

                            value="${montantNetASuivre.toFixed(0)}"

                            readonly

                        >

                    </td>

                </tr>

            `;

        });

        tbody.innerHTML += `

            <tr class="table-warning">

                <td colspan="6" class="text-end">

                    <strong>

                        Sous-total ${compagnie}

                    </strong>

                </td>

                <td>

                    <input

                        type="text"

                        class="form-control fw-bold sous-total"

                        data-compagnie="${groupes[compagnie][0].compagnie_id}"

                        value="${sousTotal.toFixed(0)}"

                        readonly

                    >

                </td>

            </tr>

        `;

    });

    // ==========================================
    // Activation des événements
    // ==========================================

    initialiserEvenements();

    // ==========================================
    // Calcul initial des totaux
    // ==========================================

    recalculerTotaux();


}


// ======================================================
// Activation des événements
// ======================================================

function initialiserEvenements() {

    document.querySelectorAll(

        ".ligne-produit"

    ).forEach(function (ligne) {

        ligne.querySelector(

            ".montant"

        ).addEventListener(

            "input",

            function () {

                recalculerLigne(ligne);

            }

        );

        ligne.querySelector(

            ".taux"

        ).addEventListener(

            "input",

            function () {

                recalculerLigne(ligne);

            }

        );

    });

}


// ======================================================
// Recalcul d'une ligne
// ======================================================

function recalculerLigne(ligne) {

    const prix = Number(
        ligne.dataset.prix
    );

    const montantInput = ligne.querySelector(
        ".montant"
    );

    const montantMaximum = Number(
        montantInput.dataset.max
    );

    const tauxInput = ligne.querySelector(
        ".taux"
    );

    const remiseInput = ligne.querySelector(
        ".remise"
    );

    const netInput = ligne.querySelector(
        ".net"
    );

    let montant = Number(
        montantInput.value
    );

    let taux = Number(
        tauxInput.value
    );

    if (isNaN(montant)) {

        montant = 0;

    }

    if (isNaN(taux)) {

        taux = 0;

    }

    // ==========================================
    // Vérification du montant maximum
    // ==========================================

    if (montant > montantMaximum) {

        montantInput.classList.add(
            "is-invalid"
        );

        return;

    }

    // ==========================================
    // Vérification du montant
    // ==========================================

    if (montant % prix !== 0) {

        montantInput.classList.add(
            "is-invalid"
        );

        return;

    }

    montantInput.classList.remove(
        "is-invalid"
    );

    // ==========================================
    // Calculs
    // ==========================================

    const montantInitialBrut = (
        Number(ligne.dataset.initialeBrut)
        ||
        Number(ligne.dataset.initiale)
        ||
        0
    );

    const montantBrutSuivi = (
        montantInitialBrut
        +
        montant
    );

    const montantRemise = montantBrutSuivi * taux / 100;

    const montantNet = (
        calculerMontantNet(
            montantBrutSuivi,
            taux
        )
    );

    remiseInput.value = montantRemise.toFixed(0);

    netInput.value = montantNet.toFixed(0);

    // ==========================================
    // Recalcul des totaux
    // ==========================================

    recalculerTotaux();

}


// ======================================================
// Recalcul des totaux
// ======================================================

function recalculerTotaux() {

    let totalBrut = 0;

    let totalNet = 0;

    const sousTotaux = {};

    document.querySelectorAll(".ligne-produit").forEach(function (ligne) {

        const compagnie = ligne.dataset.compagnie;

        const montant = Number(
            ligne.querySelector(".montant").value
        ) || 0;

        const montantInitialBrut = Number(
            ligne.dataset.initialeBrut
        ) || 0;

        const net = Number(
            ligne.querySelector(".net").value
        ) || 0;

        totalBrut += (
            montantInitialBrut
            +
            montant
        );

        totalNet += net;

        if (!(compagnie in sousTotaux)) {

            sousTotaux[compagnie] = 0;

        }

        sousTotaux[compagnie] += net;

    });

    document.querySelectorAll(".sous-total").forEach(function (champ) {

        const compagnie = champ.dataset.compagnie;

        champ.value = (sousTotaux[compagnie] || 0).toFixed(0);

    });

    // ==========================================
    // Affichage des totaux
    // ==========================================

    document.getElementById("total-brut").textContent =

        totalBrut.toLocaleString(

            "fr-FR"

        ) + " FCFA";

    document.getElementById("total-net").textContent =

        totalNet.toLocaleString(

            "fr-FR"

        ) + " FCFA";
    
}


function calculerMontantNet(montantBrut, taux) {

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


function lireNombre(valeur) {

    const nombre = Number(
        String(valeur || "0")
            .replace(/\s/g, "")
            .replace(/[^\d,.-]/g, "")
            .replace(",", ".")
    );

    if (Number.isNaN(nombre)) {

        return 0;

    }

    return nombre;

}


function formaterMontant(valeur) {

    return (
        lireNombre(valeur)
        .toLocaleString("fr-FR")
        +
        " FCFA"
    );

}
