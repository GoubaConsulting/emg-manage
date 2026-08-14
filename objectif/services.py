"""
==========================================================
Projet : EMG MANAGE

Module : Objectif

Description :
Services métier du module Objectif.

==========================================================
"""

from decimal import Decimal

from django.db import transaction

from .models import (
    Objectif,
    LigneObjectif
)

from .validators import (
    verifier_produits_selectionnes,
    verifier_meme_compagnie,
    verifier_objectif_unique,
    verifier_montant,
    verifier_point_vente
)

from django.db.models import Sum

from django.apps import apps


# ==========================================================
# Génération de la désignation
# ==========================================================

def generer_designation(compagnie, produits):
    """
    Si un seul produit est sélectionné,
    la désignation prend le nom du produit.

    Sinon elle prend le nom de la compagnie.
    """

    if len(produits) == 1:
        return produits[0].designation

    return compagnie.designation


# ==========================================================
# Création des lignes d'objectif
# ==========================================================

def creer_lignes(objectif, produits):
    """
    Crée les lignes correspondant
    aux produits sélectionnés.
    """

    lignes = []

    for produit in produits:

        lignes.append(

            LigneObjectif(
                objectif=objectif,
                produit=produit
            )

        )

    LigneObjectif.objects.bulk_create(lignes)


# ==========================================================
# Suppression des lignes
# ==========================================================

def supprimer_lignes(objectif):
    """
    Supprime toutes les lignes
    d'un objectif.
    """

    LigneObjectif.objects.filter(
        objectif=objectif
    ).delete()


# ==========================================================
# Calcul du taux de réalisation
# ==========================================================

def calculer_taux(objectif):
    """
    Recalcule automatiquement
    le taux de réalisation.
    """

    if objectif.montant_cible == 0:

        objectif.taux_realise = Decimal("0.00")

    else:

        objectif.taux_realise = round(

            (
                objectif.montant_realise
                * Decimal("100")
            )

            /

            objectif.montant_cible,

            2

        )

    objectif.save(
        update_fields=[
            "taux_realise"
        ]
    )


# ==========================================================
# Création
# ==========================================================

@transaction.atomic
def creer_objectif(utilisateur, donnees):
    """
    Création complète d'un objectif.
    """

    compagnie = donnees["compagnie"]

    mois = int(
        donnees["mois"]
    )

    annee = int(
        donnees["annee"]
    )

    montant_cible = donnees[
        "montant_cible"
    ]

    produits = list(
        donnees["produits"]
    )

    point_vente = utilisateur.profil.point_vente

    # ------------------------------
    # VALIDATIONS
    # ------------------------------

    verifier_point_vente(
        utilisateur
    )

    verifier_montant(
        montant_cible
    )

    verifier_produits_selectionnes(
        produits
    )

    verifier_meme_compagnie(
        compagnie,
        produits
    )

    verifier_objectif_unique(

        compagnie,

        point_vente,

        mois,

        annee,

        produits

    )

    # ------------------------------
    # CREATION
    # ------------------------------

    objectif = Objectif(

        designation=generer_designation(
            compagnie,
            produits
        ),

        compagnie=compagnie,

        mois=mois,

        annee=annee,

        montant_cible=montant_cible,

        montant_realise=Decimal("0.00"),

        taux_realise=Decimal("0.00"),

        point_vente=point_vente

    )

    objectif.save()

    creer_lignes(
        objectif,
        produits
    )

    return objectif


# ==========================================================
# Modification
# ==========================================================

@transaction.atomic
def modifier_objectif(
    objectif,
    donnees
):
    """
    Modification complète
    d'un objectif.
    """

    compagnie = donnees["compagnie"]

    mois = int(
        donnees["mois"]
    )

    annee = int(
        donnees["annee"]
    )

    montant_cible = donnees[
        "montant_cible"
    ]

    produits = list(
        donnees["produits"]
    )

    verifier_montant(
        montant_cible
    )

    verifier_produits_selectionnes(
        produits
    )

    verifier_meme_compagnie(
        compagnie,
        produits
    )

    verifier_objectif_unique(

        compagnie,

        objectif.point_vente,

        mois,

        annee,

        produits,

        objectif

    )

    objectif.compagnie = compagnie

    objectif.mois = mois

    objectif.annee = annee

    objectif.montant_cible = montant_cible

    objectif.designation = generer_designation(
        compagnie,
        produits
    )

    objectif.save()

    supprimer_lignes(
        objectif
    )

    creer_lignes(
        objectif,
        produits
    )

    calculer_taux(
        objectif
    )

    return objectif


# ==========================================================
# Suppression logique
# ==========================================================

def supprimer_objectif(objectif):
    """
    Désactive un objectif.
    """

    objectif.actif = False

    objectif.save(
        update_fields=[
            "actif"
        ]
    )


# ==========================================================
# RECALCUL D'UN OBJECTIF
# ==========================================================

def recalculer_objectif(objectif):
    """
    Recalcule complètement le montant réalisé
    et le taux de réalisation d'un objectif.
    """
    LigneCommande = apps.get_model(
        "commandes",
        "LigneCommande"
    )

    total = (
        LigneCommande.objects.filter(
            commande__actif=True,
            commande__point_vente=objectif.point_vente,
            commande__date_commande__month=objectif.mois,
            commande__date_commande__year=objectif.annee,
            produit__in=objectif.lignes.values_list(
                "produit",
                flat=True
            )
        ).aggregate(
            total=Sum("montant_net")
        )["total"]
        or Decimal("0.00")
    )

    objectif.montant_realise = total

    if objectif.montant_cible > 0:

        objectif.taux_realise = round(

            (
                total * Decimal("100")
            )
            /
            objectif.montant_cible,

            2

        )

    else:

        objectif.taux_realise = Decimal("0.00")

    objectif.save(
        update_fields=[
            "montant_realise",
            "taux_realise"
        ]
    )


def recalculer_objectifs(objectifs):
    """
    Recalcule une liste d'objectifs.
    """

    total = 0

    for objectif in objectifs:

        recalculer_objectif(
            objectif
        )

        total += 1

    return total


def existe_commandes_periode(mois, annee, point_ventes):
    """
    Verifie s'il existe des commandes sur une periode.
    """

    Commande = apps.get_model(
        "commandes",
        "Commande"
    )

    return Commande.objects.filter(
        actif=True,
        point_vente__in=point_ventes,
        date_commande__month=mois,
        date_commande__year=annee
    ).exists()
