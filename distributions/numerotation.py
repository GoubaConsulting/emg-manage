"""
==========================================================
Projet : EMG MANAGE

Module : Distributions

Description :
Gestion de la numérotation des distributions.

==========================================================
"""

from django.db.models import Max

from .models import Distribution


# ==========================================================
# GENERATION DU NUMERO DE DISTRIBUTION
# ==========================================================

def generer_numero_distribution():
    """
    Génère automatiquement le numéro
    de la distribution.

    Format :

    DIS-000001
    DIS-000002
    DIS-000003
    """

    dernier = Distribution.objects.aggregate(

        Max("iddistribution")

    )["iddistribution__max"]

    if dernier is None:

        numero = 1

    else:

        numero = dernier + 1

    return f"DIS-{numero:06d}"