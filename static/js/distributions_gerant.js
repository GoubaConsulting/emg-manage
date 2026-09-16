/*
==========================================================
Projet : EMG MANAGE

Module : Distributions

Description :
Gestion du formulaire de distribution
Gérant -> Distributeur
==========================================================
*/


// ======================================================
// Variables globales
// ======================================================

const lignes = document.querySelectorAll(

    ".ligne-produit"

);

const totalBrut = document.getElementById(

    "total-brut"

);

const totalNet = document.getElementById(

    "total-net"

);

const selectDistributeur = document.getElementById(

    "id_distributeur"

);


// ======================================================
// Initialisation
// ======================================================

document.addEventListener(

    "DOMContentLoaded",

    initialiser

);


// ======================================================
// Initialisation
// ======================================================

function initialiser() {

    lignes.forEach(function (ligne) {

        initialiserLigne(

            ligne

        );

    });

    recalculerTotaux();

    recalculerSousTotaux();

    if (
        selectDistributeur &&
        !window.modeModificationDistribution
    ) {

        selectDistributeur.addEventListener(

            "change",

            actualiserMontantsInitiaux

        );

        actualiserMontantsInitiaux();

    }

}


// ======================================================
// Affichage des montants initiaux du destinataire
// ======================================================

function actualiserMontantsInitiaux() {

    const reliquats = (
        window.montantsInitiauxParDistributeur
        ||
        window.reliquatsParDistributeur
        ||
        {}
    );

    const distributeur = selectDistributeur.value;

    const montants = reliquats[distributeur] || {};

    lignes.forEach(function (ligne) {

        const produit = ligne.dataset.produit;

        const champ = ligne.querySelector(

            ".montant-initial"

        );

        if (!champ) {

            return;

        }

        const donneesInitiales = (
            montants[produit] || 0
        );

        const montantInitialBrut = lireMontantInitialBrut(
            donneesInitiales
        );

        const montantInitialNet = lireMontantInitialNet(
            donneesInitiales,
            montantInitialBrut
        );

        const tauxInitial = lireTauxInitial(
            donneesInitiales
        );

        ligne.dataset.initialBrut = montantInitialBrut;
        ligne.dataset.initialNet = montantInitialNet;
        ligne.dataset.initialTaux = tauxInitial;

        renseignerChampCache(
            ligne,
            ".montant-initial-valeur",
            montantInitialBrut
        );

        renseignerChampCache(
            ligne,
            ".montant-net-initial-valeur",
            montantInitialNet
        );

        renseignerChampCache(
            ligne,
            ".taux-initial-valeur",
            tauxInitial
        );

        champ.textContent = formaterMontant(
            montantInitialBrut
        );

        appliquerReliquatLigne(

            ligne,

            montantInitialBrut

        );

        recalculerLigne(

            ligne

        );

    });

    recalculerSousTotaux();

    recalculerTotaux();

}


// ======================================================
// Selection automatique des lignes avec reliquat
// ======================================================

function appliquerReliquatLigne(
    ligne,
    montantInitial
) {

    const check = ligne.querySelector(

        ".produit-check"

    );

    if (!check) {

        return;

    }

    if (montantInitial > 0) {

        activerLigne(

            ligne

        );

        check.dataset.autoReliquat = "1";

        return;

    }

    if (check.dataset.autoReliquat === "1") {

        desactiverLigne(

            ligne

        );

        delete check.dataset.autoReliquat;

    }

}


function activerLigne(ligne) {

    const check = ligne.querySelector(

        ".produit-check"

    );

    const montant = ligne.querySelector(

        ".montant"

    );

    const taux = ligne.querySelector(

        ".taux"

    );

    check.checked = true;

    montant.disabled = false;

    taux.disabled = false;

    ligne.classList.add(

        "table-success"

    );

}


function desactiverLigne(ligne) {

    const check = ligne.querySelector(

        ".produit-check"

    );

    const montant = ligne.querySelector(

        ".montant"

    );

    const taux = ligne.querySelector(

        ".taux"

    );

    check.checked = false;

    if (check.checked) {

        activerLigne(

            ligne

        );

        recalculerLigne(

            ligne

        );

    }

    else {

        montant.disabled = true;

        taux.disabled = true;

        if (montant.value === "") {

            montant.value = 0;

        }

        if (taux.value === "") {

            taux.value = 0;

        }

    }

    ligne.querySelector(

        ".remise"

    ).value = 0;

    ligne.querySelector(

        ".net"

    ).value = 0;

    ligne.classList.remove(

        "table-success"

    );

}

// ======================================================
// Initialisation d'une ligne
// ======================================================

function initialiserLigne(ligne) {

    const check = ligne.querySelector(

        ".produit-check"

    );

    const montant = ligne.querySelector(

        ".montant"

    );

    const taux = ligne.querySelector(

        ".taux"

    );

    montant.disabled = true;

    taux.disabled = true;

    montant.value = 0;

    taux.value = 0;

    check.addEventListener(

        "change",

        function () {

            if (this.checked) {

                delete this.dataset.autoReliquat;

                activerLigne(

                    ligne

                );

            }

            else {

                delete this.dataset.autoReliquat;

                desactiverLigne(

                    ligne

                );

                recalculerSousTotaux();

                recalculerTotaux();

            }

        }

    );

    montant.addEventListener(

        "input",

        function () {

            recalculerLigne(

                ligne

            );

        }

    );

    taux.addEventListener(

        "input",

        function () {

            recalculerLigne(

                ligne

            );

        }

    );

}

// ======================================================
// Recalcul d'une ligne
// ======================================================

function recalculerLigne(ligne) {

    const prix = Number(
        ligne.dataset.prix.replace(",", ".")
    );

    const stock = Number(
        ligne.dataset.stock.replace(",", ".")
    );

    const montantInput = ligne.querySelector(
        ".montant"
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
    // Le montant doit être un multiple du prix
    // ==========================================

    if (montant % prix !== 0) {

        montantInput.classList.add(
            "is-invalid"
        );

        return;

    }

    // ==========================================
    // Vérification du stock
    // ==========================================

    const quantite = montant / prix;

    if (quantite > stock) {

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

    const montantBrutInitial = calculerMontantBrutInitial(
        ligne
    );

    const montantNetInitial = calculerMontantNetInitial(
        ligne
    );

    const montantRemiseInitial = (
        montantBrutInitial
        -
        montantNetInitial
    );

    const montantRemiseNouveau = (
        montant
        *
        taux
        /
        100
    );

    const montantRemise = (
        montantRemiseInitial
        +
        montantRemiseNouveau
    );

    const montantNet = (
        montantNetInitial
        +
        calculerMontantNet(
            montant,
            taux
        )
    );

    remiseInput.value = montantRemise.toFixed(0);

    netInput.value = montantNet.toFixed(0);

    recalculerSousTotaux();

    recalculerTotaux();

}

// ======================================================
// Recalcul des sous-totaux
// ======================================================

function recalculerSousTotaux() {

    const sousTotaux = {};

    document.querySelectorAll(

        ".ligne-produit"

    ).forEach(function (ligne) {

        const check = ligne.querySelector(

            ".produit-check"

        );

        if (!check.checked) {

            return;

        }

        const compagnie = ligne.dataset.compagnie;

        const net = Number(

            ligne.querySelector(

                ".net"

            ).value

        ) || 0;

        if (!(compagnie in sousTotaux)) {

            sousTotaux[compagnie] = 0;

        }

        sousTotaux[compagnie] += net;

    });

    document.querySelectorAll(

        ".subtotal-compagnie"

    ).forEach(function (champ) {

        const compagnie = champ.dataset.compagnie;

        champ.value = (

            sousTotaux[compagnie] || 0

        ).toLocaleString(

            "fr-FR"

        ) + " FCFA";

    });

}

// ======================================================
// Recalcul des totaux
// ======================================================

function recalculerTotaux() {

    let brut = 0;

    let net = 0;

    document.querySelectorAll(

        ".ligne-produit"

    ).forEach(function (ligne) {

        const check = ligne.querySelector(

            ".produit-check"

        );

        if (!check.checked) {

            return;

        }

        brut += (
            calculerMontantBrutInitial(
                ligne
            )
            +
            (
                Number(

                    ligne.querySelector(

                        ".montant"

                    ).value

                ) || 0
            )
        );

        net += Number(

            ligne.querySelector(

                ".net"

            ).value

        ) || 0;

    });

    totalBrut.textContent =

        brut.toLocaleString(

            "fr-FR"

        ) + " FCFA";

    totalNet.textContent =

        net.toLocaleString(

            "fr-FR"

        ) + " FCFA";

}


// ======================================================
// Calcul du net
// ======================================================

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


function calculerMontantBrutInitial(ligne) {

    const montantDataset = lireNombre(
        ligne.dataset.initialBrut
    );

    if (montantDataset > 0) {

        return montantDataset;

    }

    const champ = ligne.querySelector(
        ".montant-initial-valeur"
    );

    return lireNombre(
        champ ? champ.value : 0
    );

}


function calculerMontantNetInitial(ligne) {

    const montantDataset = lireNombre(
        ligne.dataset.initialNet
    );

    if (montantDataset > 0) {

        return montantDataset;

    }

    const champ = ligne.querySelector(
        ".montant-net-initial-valeur"
    );

    return lireNombre(
        champ ? champ.value : 0
    );

}


function renseignerChampCache(
    ligne,
    selecteur,
    valeur
) {

    const champ = ligne.querySelector(
        selecteur
    );

    if (!champ) {

        return;

    }

    champ.value = valeur;

}


function lireMontantInitialBrut(donneesInitiales) {

    if (
        donneesInitiales
        &&
        typeof donneesInitiales === "object"
    ) {

        return lireNombre(
            donneesInitiales.brut
        );

    }

    return lireNombre(
        donneesInitiales
    );

}


function lireMontantInitialNet(
    donneesInitiales,
    montantInitialBrut
) {

    if (
        donneesInitiales
        &&
        typeof donneesInitiales === "object"
    ) {

        if ("net" in donneesInitiales) {

            return lireNombre(
                donneesInitiales.net
            );

        }

        if ("taux" in donneesInitiales) {

            return calculerMontantNet(
                montantInitialBrut,
                lireNombre(
                    donneesInitiales.taux
                )
            );

        }

    }

    return montantInitialBrut;

}


function lireTauxInitial(donneesInitiales) {

    if (
        donneesInitiales
        &&
        typeof donneesInitiales === "object"
        &&
        "taux" in donneesInitiales
    ) {

        return lireNombre(
            donneesInitiales.taux
        );

    }

    return 0;

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
