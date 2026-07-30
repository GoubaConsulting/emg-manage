"""
==========================================================
Projet : EMG MANAGE

Module : Objectif

Description :
Règles de gestion relatives aux objectifs.

==========================================================
"""

from django.core.exceptions import ValidationError

from .models import Objectif


def verifier_produits_selectionnes(produits):
    """
    Vérifie qu'au moins un produit
    a été sélectionné.
    """

    if not produits:
        raise ValidationError(
            "Veuillez sélectionner au moins un produit."
        )


def verifier_meme_compagnie(compagnie, produits):
    """
    Vérifie que tous les produits sélectionnés
    appartiennent à la compagnie choisie.
    """

    for produit in produits:

        if produit.compagnie_id != compagnie.idcompagnie:

            raise ValidationError(
                "Tous les produits sélectionnés doivent appartenir à la compagnie choisie."
            )


def verifier_objectif_unique(
    compagnie,
    point_vente,
    mois,
    annee,
    objectif=None
):
    """
    Vérifie qu'il n'existe pas déjà
    un objectif pour la même compagnie,
    le même point de vente
    et la même période.
    """

    queryset = Objectif.objects.filter(
        compagnie=compagnie,
        point_vente=point_vente,
        mois=mois,
        annee=annee,
        actif=True
    )

    # Cas modification
    if objectif is not None:

        queryset = queryset.exclude(
            pk=objectif.pk
        )

    if queryset.exists():

        raise ValidationError(
            "Un objectif existe déjà pour cette compagnie, cette période et ce point de vente."
        )


def verifier_montant(montant):
    """
    Vérifie que le montant cible est strictement positif.
    """

    if montant <= 0:

        raise ValidationError(
            "Le montant cible doit être supérieur à zéro."
        )


def verifier_point_vente(utilisateur):
    """
    Un utilisateur doit être lié à un point de vente
    pour pouvoir créer un objectif.
    """

    if utilisateur.profil.point_vente is None:

        raise ValidationError(
            "Votre compte n'est associé à aucun point de vente."
        )