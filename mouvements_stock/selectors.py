"""
==========================================================
Projet : EMG MANAGE

Module : Mouvements de stock

Description :
Requetes de lecture du module.

==========================================================
"""

from django.conf import settings
from django.core.paginator import Paginator

from comptes.utils import (
    est_administrateur,
    est_directeur,
)

from referentiel.models import Produit

from stocks.models import Stock

from .models import MouvementStock


def mouvements_queryset():
    """
    Retourne les mouvements actifs optimises.
    """

    return (
        MouvementStock.objects
        .filter(
            actif=True
        )
        .select_related(
            "point_vente",
            "utilisateur",
        )
        .prefetch_related(
            "lignes__produit__compagnie",
        )
    )


def mouvements_visibles(utilisateur):
    """
    Retourne les mouvements visibles selon le profil.
    """

    queryset = mouvements_queryset()

    if est_administrateur(utilisateur):

        return queryset

    if est_directeur(utilisateur):

        return queryset.filter(
            point_vente=utilisateur.profil.point_vente
        )

    return queryset.none()


def produits_actifs():
    """
    Retourne les produits actifs pour la saisie.
    """

    return (
        Produit.objects
        .filter(
            actif=True
        )
        .select_related(
            "compagnie"
        )
        .order_by(
            "compagnie__designation",
            "designation"
        )
    )


def stock_par_produit(point_vente):
    """
    Retourne une table produit -> quantites normal/tampon.
    """

    stocks = (
        Stock.objects
        .filter(
            point_vente=point_vente,
            actif=True,
        )
        .values(
            "produit_id",
            "type_stock",
            "quantite",
        )
    )

    donnees = {}

    for stock in stocks:

        produit_id = stock["produit_id"]

        donnees.setdefault(
            produit_id,
            {}
        )[stock["type_stock"]] = stock["quantite"]

    return donnees


def paginer(queryset, page):
    """
    Pagine un queryset.
    """

    taille = getattr(
        settings,
        "NB_LIGNES_PAR_PAGE",
        20
    )

    return Paginator(
        queryset,
        taille
    ).get_page(
        page
    )
