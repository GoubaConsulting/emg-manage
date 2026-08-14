"""
==========================================================
Projet : EMG MANAGE

Module : Mouvements de stock

Description :
Gestion de la numerotation des mouvements de stock.

==========================================================
"""

from django.db.models import Max

from .models import MouvementStock


def generer_numero_mouvement_stock():
    """
    Genere automatiquement le numero d'un mouvement.
    Format : MST-000001
    """

    dernier = MouvementStock.objects.aggregate(
        Max("idmouvementstock")
    )["idmouvementstock__max"]

    if dernier is None:

        numero = 1

    else:

        numero = dernier + 1

    return f"MST-{numero:06d}"
