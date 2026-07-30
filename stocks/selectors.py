"""
==========================================================
Projet : EMG MANAGE

Module : Stocks

Description :
Toutes les requêtes de lecture du module Stocks.

==========================================================
"""

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Sum

from .models import (
    Stock,
    TYPE_NORMAL,
    TYPE_TAMPON
)


# ==========================================================
# REQUETE DE BASE
# ==========================================================

def stocks_queryset():
    """
    Requête de base optimisée.
    """

    return (

        Stock.objects

        .filter(
            actif=True
        )

        .select_related(
            "point_vente",
            "produit",
            "produit__compagnie"
        )

    )


# ==========================================================
# STOCK D'UN POINT DE VENTE
# ==========================================================

def stocks_point_vente(
    point_vente,
    type_stock=None
):

    queryset = stocks_queryset().filter(

        point_vente=point_vente

    )

    if type_stock:

        queryset = queryset.filter(

            type_stock=type_stock

        )

    return queryset.order_by(

        "produit__compagnie__designation",

        "produit__designation"

    )


# ==========================================================
# STOCK D'UN PRODUIT
# ==========================================================

def stock_produit(
    point_vente,
    produit,
    type_stock=TYPE_NORMAL
):

    return stocks_queryset().filter(

        point_vente=point_vente,

        produit=produit,

        type_stock=type_stock

    ).first()


# ==========================================================
# STOCKS SOUS LE SEUIL
# ==========================================================

def stocks_en_alerte(point_vente):

    return (

        stocks_queryset()

        .filter(
            point_vente=point_vente
        )

        .filter(
            quantite__lte=0
        )

        .order_by(

            "produit__compagnie__designation",

            "produit__designation"

        )

    )


# ==========================================================
# TOTAL DU STOCK
# ==========================================================

def total_stock(
    point_vente,
    type_stock=None
):

    queryset = stocks_queryset().filter(

        point_vente=point_vente

    )

    if type_stock:

        queryset = queryset.filter(

            type_stock=type_stock

        )

    return (

        queryset.aggregate(

            total=Sum("quantite")

        )["total"]

        or 0

    )


# ==========================================================
# PAGINATION
# ==========================================================

def paginer(queryset, page):

    nb = getattr(

        settings,

        "NB_LIGNES_PAR_PAGE",

        20

    )

    paginator = Paginator(

        queryset,

        nb

    )

    return paginator.get_page(page)