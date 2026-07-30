"""
==========================================================
Projet : EMG MANAGE

Module : Stocks

Description :
Validations métier du module Stocks.

==========================================================
"""

from decimal import Decimal

from .services import stock_disponible


# ==========================================================
# VERIFICATION STOCK
# ==========================================================

def verifier_stock_suffisant(
    point_vente,
    produit,
    quantite,
    type_stock
):
    """
    Vérifie que le stock est suffisant.
    """

    stock = stock_disponible(

        point_vente,

        produit,

        type_stock

    )

    if stock.quantite < Decimal(str(quantite)):

        raise Exception(

            f"Stock insuffisant pour "

            f"{produit.designation}."

        )