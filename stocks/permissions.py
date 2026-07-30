"""
==========================================================
Projet : EMG MANAGE

Module : Stocks

Description :
Permissions du module Stocks.

==========================================================
"""

def peut_consulter(utilisateur):
    """
    Tous les utilisateurs connectés
    peuvent consulter leur stock.
    """

    return utilisateur.is_authenticated