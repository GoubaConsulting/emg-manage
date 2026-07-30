"""
==========================================================
Projet : EMG MANAGE

Module : Stocks

Description :
Services métier du module Stocks.

==========================================================
"""

from decimal import Decimal

from django.db import transaction

from .models import (
    Stock,
    TYPE_NORMAL,
    TYPE_TAMPON
)


# ==========================================================
# CREATION DU STOCK
# ==========================================================

def creer_stock(
    point_vente,
    produit,
    type_stock=TYPE_NORMAL
):
    """
    Crée un stock s'il n'existe pas.
    """

    stock, created = Stock.objects.get_or_create(

        point_vente=point_vente,

        produit=produit,

        type_stock=type_stock,

        defaults={

            "quantite": Decimal("0"),

            "seuil_alerte": Decimal("0")

        }

    )

    return stock


# ==========================================================
# CONSULTATION DU STOCK
# ==========================================================

def stock_disponible(
    point_vente,
    produit,
    type_stock=TYPE_NORMAL
):
    """
    Retourne le stock.
    """

    return creer_stock(

        point_vente,

        produit,

        type_stock

    )


# ==========================================================
# AJOUT AU STOCK
# ==========================================================

@transaction.atomic
def ajouter_stock(
    point_vente,
    produit,
    quantite,
    type_stock=TYPE_NORMAL
):
    """
    Ajoute une quantité au stock.
    """

    stock = creer_stock(

        point_vente,

        produit,

        type_stock

    )

    stock.quantite += Decimal(str(quantite))

    stock.save(
        update_fields=[
            "quantite",
            "date_modification"
        ]
    )

    return stock


# ==========================================================
# RETRAIT DU STOCK
# ==========================================================

@transaction.atomic
def retirer_stock(
    point_vente,
    produit,
    quantite,
    type_stock=TYPE_NORMAL
):
    """
    Retire une quantité du stock.
    """

    stock = creer_stock(

        point_vente,

        produit,

        type_stock

    )

    quantite = Decimal(str(quantite))

    if stock.quantite < quantite:

        raise Exception(

            f"Stock insuffisant pour {produit.designation}."

        )

    stock.quantite -= quantite

    stock.save(
        update_fields=[
            "quantite",
            "date_modification"
        ]
    )

    return stock


# ==========================================================
# MODIFICATION DIRECTE
# ==========================================================

@transaction.atomic
def modifier_quantite(
    point_vente,
    produit,
    quantite,
    type_stock=TYPE_NORMAL
):
    """
    Modifie directement le stock.
    (Inventaire, régularisation...)
    """

    stock = creer_stock(

        point_vente,

        produit,

        type_stock

    )

    stock.quantite = Decimal(str(quantite))

    stock.save(
        update_fields=[
            "quantite",
            "date_modification"
        ]
    )

    return stock

# ==========================================================
# TRANSFERT DE STOCK
# ==========================================================

@transaction.atomic
def transferer_stock(
    point_vente_source,
    point_vente_destination,
    produit,
    quantite,
    type_stock=TYPE_NORMAL
):
    """
    Transfère une quantité de stock
    d'un point de vente vers un autre.
    """

    retirer_stock(

        point_vente=point_vente_source,

        produit=produit,

        quantite=quantite,

        type_stock=type_stock

    )

    ajouter_stock(

        point_vente=point_vente_destination,

        produit=produit,

        quantite=quantite,

        type_stock=type_stock

    )