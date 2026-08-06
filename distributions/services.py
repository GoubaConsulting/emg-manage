"""
==========================================================
Projet : EMG MANAGE

Module : Distributions

Description :
Services métier du module Distributions.

==========================================================
"""

from decimal import Decimal

from django.db import transaction

from django.db.models import Sum

from commandes.models import (
    Commande,
    LigneCommande,
)

from referentiel.models import (
    PointVente,
    Produit,
)

from stocks.models import Stock

from stocks.services import (
    retirer_stock,
    transferer_stock,
)

from .models import (
    Distribution,
    LigneDistribution,
)

from .calculs import (
    calculer_montant,
    calculer_montant_remise,
    calculer_montant_net,
)

from .validators import (
    verifier_presence_ligne,
    verifier_montant,
    valider_prix,
    valider_quantite,
    valider_taux_remise,
    verifier_commande_selectionnee,
    verifier_date_distribution,
    verifier_commande_distribuable,
    verifier_produits_distribution,
    verifier_quantites_distribution,
    verifier_stock_distribution,
)

from .numerotation import (
    generer_numero_distribution,
)

from objectif.models import Objectif

from objectif.services import recalculer_objectif

# ==========================================================
# CONSTRUCTION DES LIGNES
# ==========================================================

def construire_lignes_depuis_formulaire(donnees):
    """
    Construit les lignes de distribution
    à partir du formulaire Directeur.
    """

    lignes = []

    for cle in donnees:

        if not cle.startswith("produit_"):

            continue

        idproduit = int(cle.split("_")[1])

        produit = Produit.objects.get(
            pk=idproduit
        )

        montant = Decimal(
            donnees.get(
                f"montant_{idproduit}",
                "0"
            )
        )

        # Produit non distribué
        if montant <= 0:

            continue

        taux = Decimal(
            donnees.get(
                f"taux_{idproduit}",
                "0"
            )
        )

        prix = Decimal(str(produit.prix))

        if montant % prix != 0:

            raise Exception(

                f"Le montant du produit "

                f"{produit.designation} "

                f"doit être un multiple de "

                f"{prix} FCFA."

            )

        quantite = montant / prix

        lignes.append({

            "produit": produit,

            "prix_unitaire": prix,

            "montant": montant,

            "quantite": quantite,

            "taux": taux,

        })

    return lignes

# ==========================================================
# CREATION D'UNE DISTRIBUTION
# ==========================================================

@transaction.atomic
def creer_distribution(
    utilisateur,
    type_distribution,
    commande,
    point_vente_destination,
    distributeur,
    date_distribution,
    lignes,
):
    # ======================================================
    # VALIDATIONS
    # ======================================================
    verifier_commande_selectionnee(
        commande
    )

    verifier_date_distribution(
        date_distribution
    )

    verifier_presence_ligne(
        lignes
    )

    verifier_commande_distribuable(
        commande
    )

    verifier_produits_distribution(
        commande,
        lignes
    )

    verifier_quantites_distribution(
        commande,
        lignes
    )

    verifier_stock_distribution(
        utilisateur.profil.point_vente,
        lignes
    )

    point_vente_source = utilisateur.profil.point_vente

    for ligne in lignes:

        stock = Stock.objects.get(

            point_vente=point_vente_source,

            produit=ligne["produit"]

        )

        if ligne["quantite"] > stock.quantite:

            raise Exception(

                f"Stock insuffisant pour le produit "
                f"« {ligne['produit'].designation} ».\n\n"
                f"Stock disponible : {stock.quantite}\n"
                f"Quantité demandée : {ligne['quantite']}.\n\n"
                f"Veuillez réduire la quantité distribuée ou réapprovisionner le stock avant de poursuivre."

            )

    # ======================================================
    # DETERMINATION DES POINTS DE VENTE
    # ======================================================

    point_vente_source = utilisateur.profil.point_vente

    point_vente_destination = None

    if type_distribution == Distribution.TYPE_COMMANDE_GERANT:

        point_vente_destination = commande.point_vente

    elif type_distribution == Distribution.TYPE_DISTRIBUTEUR:

        point_vente_destination = point_vente_source

    elif type_distribution == Distribution.TYPE_CLIENT_DIRECT:

        point_vente_destination = point_vente_source

    # ======================================================
    # CREATION DE LA DISTRIBUTION
    # ======================================================

    distribution = Distribution.objects.create(

        numero=generer_numero_distribution(),

        type_distribution=type_distribution,

        date_distribution=date_distribution,

        point_vente_source=point_vente_source,

        point_vente_destination=point_vente_destination,

        commande=commande,

        distributeur=distributeur,

        utilisateur=utilisateur

    )

    # ======================================================
    # LIGNES
    # ======================================================

    creer_lignes_distribution(
        distribution,
        lignes
    )

    # ======================================================
    # TOTAUX
    # ======================================================

    recalculer_totaux_distribution(
        distribution
    )

    # ======================================================
    # TRAITEMENTS METIER
    # ======================================================

    traiter_distribution_apres_creation(
        distribution
    )

    return distribution

# ==========================================================
# CREATION DES LIGNES DE DISTRIBUTION
# ==========================================================

def creer_lignes_distribution(
    distribution,
    lignes
):
    """
    Crée les lignes d'une distribution.
    """

    lignes_distribution = []

    for ligne in lignes:

        produit = ligne["produit"]

        quantite = Decimal(
            str(ligne["quantite"])
        )

        prix_unitaire = Decimal(
            str(ligne["prix_unitaire"])
        )

        taux = Decimal(
            str(ligne["taux"])
        )

        montant_brut = Decimal(
            str(ligne["montant"])
        )

        montant_remise = calculer_montant_remise(
            montant_brut,
            taux
        )

        montant_net = calculer_montant_net(
            montant_brut,
            montant_remise
        )

        # ------------------------------
        # VALIDATIONS
        # ------------------------------

        valider_prix(
            prix_unitaire
        )

        valider_taux_remise(
            taux
        )

        valider_quantite(
            quantite
        )

        lignes_distribution.append(

            LigneDistribution(

                distribution=distribution,

                produit=produit,

                prix_unitaire=prix_unitaire,

                montant=montant_brut,

                quantite=quantite,

                taux_remise=taux,

                montant_remise=montant_remise,

                montant_net=montant_net,

            )

        )

    LigneDistribution.objects.bulk_create(
        lignes_distribution
    )

# ==========================================================
# RECALCUL DES TOTAUX
# ==========================================================

def recalculer_totaux_distribution(distribution):
    """
    Recalcule automatiquement les montants
    de la distribution.
    """

    totaux = (
        distribution.lignes.aggregate(

            montant_brut=Sum(
                "montant"
            ),

            montant_remise=Sum(
                "montant_remise"
            ),

            montant_net=Sum(
                "montant_net"
            )

        )
    )

    distribution.montant_brut = (
        totaux["montant_brut"]
        or Decimal("0.00")
    )

    distribution.montant_net = (
        totaux["montant_net"]
        or Decimal("0.00")
    )

    distribution.save(
        update_fields=[
            "montant_brut",
            "montant_net",
            "date_modification",
        ]
    )

    return distribution

# ==========================================================
# TRAITEMENT APRES CREATION
# ==========================================================

@transaction.atomic
def traiter_distribution_apres_creation(
    distribution
):
    """
    Exécute les traitements métier
    après la création d'une distribution.
    """

    # ======================================================
    # DISTRIBUTION D'UNE COMMANDE GERANT
    # ======================================================

    if distribution.type_distribution == Distribution.TYPE_COMMANDE_GERANT:

        for ligne in distribution.lignes.select_related("produit"):

            # ----------------------------------------------
            # Transfert du stock Directeur -> Gérant
            # ----------------------------------------------

            transferer_stock(

                point_vente_source=distribution.point_vente_source,

                point_vente_destination=distribution.point_vente_destination,

                produit=ligne.produit,

                quantite=ligne.quantite

            )

            # ----------------------------------------------
            # Mise à jour de la ligne de commande
            # ----------------------------------------------

            ligne_commande = (

                distribution.commande.lignes.get(

                    produit=ligne.produit

                )

            )

            if ligne.quantite > ligne_commande.quantite:

                raise Exception(

                    f"La quantité distribuée du produit "
                    f"{ligne.produit.designation} dépasse "
                    f"la quantité commandée."

                )

            ligne_commande.quantite_distribuee = ligne.quantite

            ligne_commande.save(

                update_fields=[

                    "quantite_distribuee",

                ]

            )

        # --------------------------------------------------
        # Mise à jour de l'état de la commande
        # --------------------------------------------------

        mettre_a_jour_etat_commande(

            distribution.commande

        )

    # ======================================================
    # DISTRIBUTION AU DISTRIBUTEUR
    # ======================================================

    elif distribution.type_distribution == Distribution.TYPE_DISTRIBUTEUR:

        for ligne in distribution.lignes.select_related("produit"):

            retirer_stock(

                point_vente=distribution.point_vente_source,

                produit=ligne.produit,

                quantite=ligne.quantite

            )

        mettre_a_jour_objectifs_distribution(

            distribution

        )

    # ======================================================
    # DISTRIBUTION AU CLIENT DIRECT
    # ======================================================

    elif distribution.type_distribution == Distribution.TYPE_CLIENT_DIRECT:

        for ligne in distribution.lignes.select_related("produit"):

            retirer_stock(

                point_vente=distribution.point_vente_source,

                produit=ligne.produit,

                quantite=ligne.quantite

            )

        mettre_a_jour_objectifs_distribution(

            distribution

        )


# ==========================================================
# MISE A JOUR DE L'ETAT DE LA COMMANDE
# ==========================================================

def mettre_a_jour_etat_commande(
    commande
):
    """
    Met à jour automatiquement
    l'état d'une commande après
    une distribution.
    """

    lignes = commande.lignes.all()

    # Par défaut on considère
    # la commande complètement distribuée.
    commande_complete = True

    for ligne in lignes:

        if ligne.quantite_distribuee < ligne.quantite:

            commande_complete = False

            break

    if commande_complete:

        commande.etat = Commande.VALIDEE

    else:

        commande.etat = Commande.VALIDEE_PARTIELLEMENT

    commande.save(

        update_fields=[

            "etat",
            "date_modification"

        ]

    )

    return commande


# ==========================================================
# MISE A JOUR DES OBJECTIFS
# ==========================================================

def mettre_a_jour_objectifs_distribution(
    distribution
):
    """
    Recalcule les objectifs du point de vente
    après une vente à un distributeur
    ou à un client direct.
    """

    objectifs = Objectif.objects.filter(

        actif=True,

        point_vente=distribution.point_vente_source,

        mois=distribution.date_distribution.month,

        annee=distribution.date_distribution.year

    )

    compagnies = (
        distribution.lignes
        .values_list(
            "produit__compagnie_id",
            flat=True
        )
        .distinct()
    )

    objectifs = objectifs.filter(
        compagnie_id__in=compagnies
    )

    for objectif in objectifs:

        recalculer_objectif(
            objectif
        )

# ==========================================================
# CREATION DISTRIBUTION DEPUIS COMMANDE
# ==========================================================

@transaction.atomic
def creer_distribution_depuis_commande(
    commande,
    utilisateur
):
    """
    Crée automatiquement une distribution
    à partir d'une commande gérant.
    """
    verifier_commande_distribuable(
        commande
    )

    distribution = Distribution.objects.create(

        numero=generer_numero_distribution(),

        type_distribution=Distribution.TYPE_COMMANDE_GERANT,

        date_distribution=commande.date_commande,

        point_vente_source=utilisateur.profil.point_vente,

        point_vente_destination=commande.point_vente,

        commande=commande,

        distributeur=commande.distributeur,

        utilisateur=utilisateur,

    )

    lignes = []

    for ligne in commande.lignes.all():

        lignes.append({

            "produit": ligne.produit,

            "prix_unitaire": ligne.prix_unitaire,

            "montant": ligne.montant,

            "quantite": ligne.quantite,

            "taux": ligne.taux_remise,

        })

    creer_lignes_distribution(

        distribution,

        lignes

    )

    recalculer_totaux_distribution(

        distribution

    )

    traiter_distribution_apres_creation(

        distribution

    )

    return distribution

