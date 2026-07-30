"""
==========================================================
Projet : EMG MANAGE

Module : Commandes

Description :
Gestion de la numérotation des commandes.

==========================================================
"""

from django.db.models import Max

from .models import Commande


# ==========================================================
# GENERATION DU NUMERO DE COMMANDE
# ==========================================================

def generer_numero_commande():
    """
    Génère automatiquement le numéro
    de la commande.

    Format :

    CMD-000001
    CMD-000002
    CMD-000003
    """

    dernier = Commande.objects.aggregate(

        Max("idcommande")

    )["idcommande__max"]

    if dernier is None:

        numero = 1

    else:

        numero = dernier + 1

    return f"CMD-{numero:06d}"